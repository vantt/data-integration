# Phase 6 — Boundary doc + cập nhật docs

**Depends on:** Phase 1–5 (viết theo hiện trạng sau khi các phase kia đã đổ bê tông)
**Mục tiêu:** Ghi thành văn contract giữa components — đây là chỗ "suy nghĩ thấu đáo" được vật chất hóa. Import-linter enforce code boundary; doc này là nguồn chân lý cho **data contracts** (thứ máy không enforce được).

## Files

- **Modify** `docs/system-architecture.md` (đọc bản hiện tại trước; giữ ≤800 LOC theo docs.maxLoc — nếu chật, tách section boundary thành `docs/component-boundaries-and-contracts.md` và link):
  1. **Component table:** 5 components (data-platform, crm, metabase/rill/evidence serving, deployment, detailView-retired), dirs sở hữu, image name, ai được import ai (mirror của `.importlinter`).
  2. **Data contracts** — interface thật giữa components:
     - Data lake zones (`app_data/data_lake/*` parquet) — producer: data-platform; consumers: metabase/rill/evidence/crm (`:ro`).
     - Serving views trong `olap.duckdb` — producer: bootstrap_serving_views; consumers: Metabase, CRM (đổi cột = MAJOR bump + chạy lại bootstrap, xem memory: stop Metabase trước).
     - `cache.db` (wh_* tables) — producer: reverse_etl; consumer: crm.
     - Webhook endpoints (Cloudflare Worker → webhook_consumer payload shape).
     - CRM exports ngược (crm_app_user, crm_task) — producer: crm; consumer: transformation. **Bằng chứng từ [runtime inventory](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md):** data_platform mount volume `data-integration_crm_data` (`:ro`) tại `/app/var/crm_data` — pipeline đọc TRỰC TIẾP SQLite của CRM; đổi schema crm.db = MAJOR bump.
  3. **Ownership của `scripts/`:** pipeline scripts thuộc data-platform; `secure_deploy.ps1`, `fix-duckdb-lock.ps1`, `backup/` thuộc deployment. Chỉ ghi nhận, không di chuyển (YAGNI).
  4. **Release & versioning convention:** `<component>-vX.Y.Z`, SemVer theo data-contract (MAJOR = phá contract consumer), quy trình release/rollback (link deployment-guide).
- **Modify** root `AGENTS.md` + `CLAUDE.md`: cập nhật deployment commands (dev vs prod compose), link boundary doc, 1 dòng quy tắc "thêm dependency chéo component = sửa `.importlinter` + boundary doc trước, code sau".
- **Modify** `docs/codebase-summary.md` nếu có mô tả cấu trúc Dockerfile cũ.

## Steps

1. Đọc `docs/system-architecture.md` + `docs/codebase-summary.md` hiện tại, xác định chỗ chèn/sửa.
2. Viết component table + data contracts (đối chiếu compose mounts thực tế sau Phase 5 — mounts là bằng chứng của contract).
3. Cập nhật AGENTS.md/CLAUDE.md.
4. Verify chéo: mọi claim trong doc khớp `.importlinter`, compose files, release script (dates, links, tên biến).

## Validation

- Mỗi consumer→producer trong data-contract table chỉ ra được bằng chứng (mount `:ro`, import, hoặc SQL query cụ thể).
- Doc không chứa plan ID/phase number (rule: stable artifacts không mang audit labels) — mô tả invariant trực tiếp.
- Link nội bộ trong docs mở được.

## Definition of Done (toàn plan)

Sau phase này: dev thêm 1 tính năng CRM → chỉ đụng `crm/`; muốn đọc data mới từ pipeline → phải qua serving view/cache table có trong contract, không import trực tiếp; release CRM không kéo theo release pipeline; máy prod cập nhật bằng đổi 1 tag. Nếu 1–2 tháng sau vẫn muốn tách repo thật, mỗi component đã tự chứa — tách chỉ còn là `git filter-repo` mechanical.
