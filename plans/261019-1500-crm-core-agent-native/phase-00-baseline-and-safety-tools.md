# Phase 0: đo hiện trạng, công cụ parity và migration down, chốt câu hỏi

**Effort:** 1d · **Phụ thuộc:** — · **Đụng prod:** chỉ đọc (dùng bản backup có sẵn, khôi phục vào scratch) · **Cần user duyệt giờ:** không · **Migration:** không

## Bối cảnh

- Mọi phase sau phải chứng minh "CRM chạy như cũ". Hiện chưa có công cụ nào so hành vi trước/sau trên dữ liệu thật; test chỉ dùng fixture.
- Runner migration không chạy file down (`crm/src/adapters/outbound/sqlite/migrations.py:30-150`); 26/73 file migration là `.down.sql`, nhiều migration cũ không có down. Muốn "migration có down" dùng được thì cần một công cụ.
- Một số giả định của thiết kế chưa kiểm được khi lập plan (không mở `crm.db`): phân bố `identity_type`, số dòng `crm_party_external_id`, phân bố `consent_enum`, phiên bản sqlite trong image, cách model dbt mới của pack lên serving, bậc CM của `lifetime_contribution_margin`, tương thích MCP SDK.

## Yêu cầu

1. **Khôi phục bản sao để đo:** lấy backup mới nhất từ volume `crm_backups` vào thư mục scratch (lệnh copy ở `crm/docs/backup-restore-runbook.md` dòng 32), chạy `restore_verify_crm.py` trên bản đó. Không ghi gì vào volume prod. Xoá bản sao khi xong plan hoặc giữ trong scratch có quyền hạn chế; không đưa ra ngoài máy.
2. **Đo (chỉ in số đếm):**
   - `crm_party_identity`: số dòng theo (`identity_type`, `source_system`, `contact_quality`, `contact_status`); số party có > 1 dòng `sapo_customer`.
   - `crm_party_external_id`: số dòng (kỳ vọng 0).
   - `crm_identity_link`: số dòng theo `status`.
   - `crm_customer_profile`: phân bố `consent_enum`; số party có hoạt động gần nhất `outcome_reason='do_not_contact'`; số party vừa `consent_enum='denied'` vừa có hoạt động sau đó.
   - `crm_tag.category`: danh sách giá trị và số lần gắn mỗi loại.
   - Số dòng mọi bảng `crm_*` và `wh_*`.
   - `crm_app_user`: số người theo `role`.
3. **Kiểm kỹ thuật:**
   - Phiên bản `sqlite3.sqlite_version` trong image `crm` hiện tại (chạy `docker run --rm --entrypoint python <image crm> -c ...`, không exec vào container đang chạy); cần ≥ 3.35.
   - Cài thử MCP Python SDK (bản mới nhất ổn định) cùng `fastapi==0.115.6`, `pydantic==2.10.6`, `uvicorn==0.34.0` trong venv scratch (`pip install --dry-run` rồi cài thật trong scratch); ghi phiên bản ghim được và xung đột nếu có.
   - Đường đi của một model dbt mới trong `transformation/models/packs/crm/` tới `serving/olap.duckdb` (đọc `bootstrap_serving_views.py`, `refresh_rolling.py`, cấu hình materialization). Kết luận: model hợp đồng là view dbt dùng được không, hay phải dùng phương án SQL trong `crm/sync/contract/` (phase 5).
   - Bậc lợi nhuận của `dim_customers.lifetime_contribution_margin` (CM1/CM2/CM3) theo định nghĩa trong dbt và `docs/analytics-handbook/semantic/metrics.md`.
   - Phân loại 19 file tham chiếu `crm_party_identity` (design §7.2): đọc, ghi, chỉ comment.
   - Liệt kê mọi handler web có lệnh ghi (POST/PUT/PATCH/DELETE) để phase 4 có danh sách đầy đủ.
4. **Công cụ parity `crm/ops/parity_snapshot.py`:**
   - Đầu vào: `--data-dir` (thư mục chứa `crm.db`, `cache.db` bản sao), `--sample 200`, `--out <json>`.
   - Mở DB bằng `CRMDatabase`, dựng service bằng cùng hàm wiring của `composition.py` (không dựng FastAPI).
   - Ghi ra **chỉ số đếm và hash**: số dòng mọi bảng `crm_*`/`wh_*`; với mẫu party chọn tất định (hash `party_id` nhỏ nhất), hash của kết quả `ProfileService` 360, danh sách tag, danh sách task mở, timeline; với mỗi user, số mục worklist và hash danh sách `action_id` theo thứ tự; kết quả tìm kiếm theo SĐT và mã Sapo cho mẫu (hash `party_id` trả về); số thành viên mỗi segment, số target mỗi campaign.
   - Lệnh `diff a.json b.json --allow <file khai báo khác biệt>`: in mục khác, trả mã thoát 1 nếu có khác ngoài danh sách cho phép.
5. **Công cụ parity export `scripts/checks/crm_export_parity.py`:** chạy các `export_query` trong `CRM_WRITEBACK_TABLES` (`orchestration/packs/crm/crm_writeback_assets.py`) bằng DuckDB trên hai bản sao DB, in số dòng và hash nội dung từng bảng, so khác biệt. Không ghi parquet.
6. **Công cụ `crm/ops/migration_down.py`:** `--data-dir`, `--version <tên file up>`, `--confirm-backup <đường dẫn backup đã verify>`. Chạy file `.down.sql` tương ứng trong một SAVEPOINT (tái dùng `_split_statements`), xoá dòng `schema_migrations`, từ chối nếu có migration áp sau nó mà chưa down (trừ `--force`), từ chối nếu không có file down.
7. Ghi kết quả đo vào `plans/261019-1500-crm-core-agent-native/reports/phase-00-baseline.md` (chỉ số đếm) và cập nhật các mục "[chưa kiểm]" của design nếu khác giả định.
8. Trình user các câu hỏi còn mở của plan (Q5, Q7, Q9–Q12) kèm số đo; ghi câu trả lời vào `plan.md` mục "Đã chốt". Đo thêm cho phase 1: số khách có tag sức khoẻ, số khách đó có/không có người phụ trách (`owner_user_id`).

## File

- Tạo: `crm/ops/parity_snapshot.py`, `crm/ops/migration_down.py`, `scripts/checks/crm_export_parity.py`, `crm/src/tests/test_migration_down_tool.py`, `crm/src/tests/test_parity_snapshot.py`.
- Tạo (báo cáo, không phải code): `plans/261019-1500-crm-core-agent-native/reports/phase-00-baseline.md`.

## Các bước

1. Worktree `feat/crm-parity-tools` từ `main`.
2. Viết hai công cụ ops và test (fixture: DB tạm dựng bằng migration, party giả).
3. Viết `crm_export_parity.py`, chạy thử trên DB tạm.
4. Khôi phục bản sao prod vào scratch, chạy đo (yêu cầu 2) và kiểm kỹ thuật (yêu cầu 3).
5. Chạy `parity_snapshot.py` hai lần trên cùng bản sao: `diff` phải rỗng (công cụ tất định).
6. Commit công cụ (không có dữ liệu), merge vào `main`. Không deploy: công cụ chạy từ worktree hoặc image trên bản sao.

## Test

| Mức | Nội dung |
|---|---|
| Unit | `migration_down`: chạy down của một migration giả tạo bảng, bảng biến mất, dòng `schema_migrations` mất; từ chối khi thiếu file down, khi có migration sau, khi thiếu `--confirm-backup`; lỗi giữa chừng thì rollback toàn bộ |
| Unit | `parity_snapshot`: chạy hai lần cho cùng JSON; thêm một task vào DB tạm thì `diff` báo đúng mục; output không chứa chuỗi giống SĐT (regex `\+?84\d{8,10}|0\d{9}`) |
| Tích hợp | `pytest crm/src/tests crm/sync/tests` xanh |

## Kiểm "CRM như cũ"

Phase không đụng code chạy của CRM (chỉ thêm file trong `crm/ops/` và `scripts/checks/`). Kiểm bằng `git diff --stat main..` chỉ có file mới, và toàn bộ test xanh.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Bản sao chứa dữ liệu khách nằm ở scratch | Chắc chắn × Trung bình | Chỉ trong scratch của máy prod, không commit, xoá khi xong; output công cụ chỉ có số và hash |
| Copy backup làm nặng đĩa | Thấp × Thấp | Một bản; DB CRM nhỏ (cỡ chục MB) |
| Công cụ parity dựng service khác với app thật | Trung bình × Trung bình | Tái dùng hàm wiring trong `composition.py` (tách hàm `build_services` nếu cần, không đổi hành vi) |

## Rollback

Xoá file công cụ (`git revert`). Không có thay đổi prod.
