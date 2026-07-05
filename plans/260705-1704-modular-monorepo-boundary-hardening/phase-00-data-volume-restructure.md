# Phase 0 — Đánh giá + tái cơ cấu data storage: bind mount → named volume

**Depends on:** [runtime inventory report](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md) (data map §3)
**Chạy TRƯỚC các phase khác** (compose volumes ổn định trước khi Phase 1/5 sửa compose tiếp).
**Mục tiêu:** Tốc độ I/O + portability + backup-ability cho data stores. Đánh giá bằng benchmark trước, migrate có chọn lọc — KHÔNG mặc định chuyển hết.

## Bối cảnh kỹ thuật

- Docker Desktop WSL2: bind mount từ `D:\` (NTFS) đi qua 9p/gRPC-FUSE — chậm với small-files (parquet zones) và mmap/WAL (DuckDB, SQLite). Named volume nằm trong ext4 VHDX của VM — I/O native.
- Tiền lệ ngay trong repo: `monitoring_db` đã là named volume vì SQLite WAL hỏng trên bind mount Windows. Máy này cũng đang chạy `offen/docker-volume-backup:v2` (stack vnstock) — pattern backup volume đã chứng minh.
- Trade-off chính: data trong volume KHÔNG truy cập trực tiếp từ host được nữa — mọi ad-hoc query (Claude Code sessions mở olap.duckdb read_only, inspect parquet) phải qua `docker exec`; file-drop `input_source` cần host path.
- **Code-as-volume: LOẠI TRỪ.** Portability code prod = GHCR image (Phase 4/5); dev cần bind mount cho flow sửa-restart. Volume code thêm sync/staleness, không thêm giá trị.

## Phân loại đề xuất (quyết định cuối sau benchmark + user confirm)

| Store | Size | Hiện tại | Đề xuất | Lý do |
|---|---|---|---|---|
| `data_lake/*_raw` zones + `sapo_warehouse.duckdb` | ~phần lớn 1.1GB | bind | **→ volume `lake_hot`** | I/O nóng nhất: dlt write, dbt read/write, DuckDB WAL. Chỉ pipeline đụng — host không cần trực tiếp |
| `data_lake/serving/` (olap.duckdb + standalone) | — | bind | **⚖ 2 phương án** (xem dưới) | Metabase/CRM/fileserver đọc; NHƯNG host ad-hoc query thường xuyên |
| `dagster_home/` | 6.4GB | bind | **→ volume** | Run-history SQLite ghi liên tục, không cần host access, /purge-dagster-runs chạy trong container |
| `metabase_data/` (H2 app db) | 680MB | bind | **→ volume** | App state thuần container |
| `app_data/rill/` (.rill state) | ~0 | bind | → volume | Cùng lý do |
| `input_source/` | 49MB | bind | **GIỮ bind** | File-drop từ Windows là interface người dùng |
| `backups/` | 12GB | bind | **GIỮ bind** | Output backup phải host-visible để copy offsite; là ĐÍCH backup, không phải data nóng |
| `analysis/`, `logs/` | ~1MB | bind | giữ nguyên | Không đáng công |

### Hai phương án cho `serving/`

- **A — hybrid (khuyến nghị khởi điểm):** serving/ giữ bind mount; chỉ raw+warehouse+dagster_home+metabase_data vào volume. Được ~80% perf win (I/O nóng nằm ở raw/warehouse/dagster), giữ nguyên 100% workflow host (ad-hoc olap.duckdb, standalone exports). Nhược: serving vẫn chịu 9p khi Metabase query nặng.
- **B — all-in volume:** thêm serving/ vào volume; host access qua `docker exec data_platform duckdb ...` hoặc `\\wsl.localhost\` path (mong manh, không khuyến khích ghi). Chỉ chọn nếu benchmark cho thấy serving-over-9p là bottleneck thật của Metabase.

## Steps

1. **Benchmark (trước khi quyết):**
   - Copy 1 zone parquet + sapo_warehouse.duckdb vào volume thử nghiệm (`docker run --rm -v test_vol:/dst -v $PWD/app_data/data_lake:/src alpine cp -r ...`).
   - Đo 3 thứ, bind vs volume, chạy trong container: (a) DuckDB aggregate scan trên zone parquet; (b) 1 dbt model nặng (hoặc `dbt build` subset); (c) Metabase-style query vào olap.duckdb. Ghi số vào report `plans/reports/`.
   - Nếu chênh <20%: dừng phase, chỉ migrate dagster_home + metabase_data (khỏi rủi ro data_lake), ghi lý do.
2. **Chốt phương án A/B với user** dựa trên số đo.
3. **Migrate** (cửa sổ pipeline nghỉ, stop stack):
   - `docker compose down` → tạo volumes → `docker run --rm -v <vol>:/dst -v <host>:/src alpine sh -c "cp -a /src/. /dst/"` từng store → sửa `docker-compose.yml` mounts → `up -d`.
   - Verify: Dagster chạy 1 job end-to-end; Metabase dashboard load; CRM đọc lake OK; row counts khớp (so 2-3 bảng chính trước/sau).
   - GIỮ thư mục host cũ (rename `app_data/<x>.pre-volume`) 7 ngày rồi mới xóa.
4. **Backup theo volume:** mở rộng `scripts/backup/` hoặc thêm sidecar `offen/docker-volume-backup` cho các volume mới (đích: `app_data/backups/` — vẫn host-visible). Restore drill 1 lần cho volume lớn nhất.
5. **Cập nhật tài liệu ăn theo:** inventory report (data map mới), `docs/deployment-guide.md`, và các chỗ plan này đụng: phase-05 `tools/seed-dev-data.ps1` phải seed volume bằng tar-copy (không còn copy dir thuần), phase-06 data contracts (vị trí lưu trữ mới).
6. **Cập nhật workflow host bị ảnh hưởng:** nếu chọn B — viết helper `tools/lake-query.ps1` (wrap `docker exec` duckdb read_only) + cập nhật memory/AGENTS.md hướng dẫn ad-hoc query mới.

## Validation

- Benchmark report có số cụ thể bind-vs-volume cho 3 workload.
- Pipeline full run xanh sau migrate; không container nào còn mount store đã chuyển từ host path cũ (`docker inspect` sweep).
- Backup mới chạy + restore drill thành công 1 volume.
- File-drop `input_source` và offsite copy `backups/` vẫn thao tác được từ Windows Explorer.

## Risks & Rollback

- **DuckDB single-writer:** migrate lúc stack down tuyệt đối (tránh lock storm — có skill /fix-duckdb-lock nếu dính).
- **VHDX phình:** volume làm ext4 VHDX to ra (~2GB ngay, hơn nếu chọn B) và không tự co — kiểm tra disk trống C: trước; biết trước lệnh compact (`wsl --shutdown` + `Optimize-VHD`) nếu cần đòi chỗ. Lưu ý memory: WSL2 9p lỗi "file exists" → fix bằng `wsl --shutdown`, KHÔNG restart Docker Desktop.
- **Đường lui dễ:** volume→bind là copy ngược y hệt chiều đi; thư mục `.pre-volume` giữ 7 ngày là fallback tức thì (chỉ mất delta từ lúc migrate).
- Phase 5 seed script phụ thuộc kết quả phase này — làm Phase 0 xong mới viết seed script.
