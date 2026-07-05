# Phase 3 — Cưỡng chế boundary bằng import-linter + CI

**Depends on:** Phase 2 (import chéo cuối cùng đã cắt)
**Mục tiêu:** Boundary được kiểm bằng máy, vi phạm = fail đỏ. Với workflow chủ yếu qua Claude Code, check tự động có sức cưỡng chế ngang repo boundary.

## Context

- Repo chưa có CI (`.github/workflows` không tồn tại), chưa có import-linter.
- Các top-level Python packages: `crm`, `ingestion`, `transformation`, `orchestration`, `webhook_consumer`, `scripts`, `detailView` (retired).
- Quan hệ cho phép (điều tra xác nhận lại ở step 1): orchestration → {ingestion, transformation, scripts}; crm ↛ mọi pipeline package; ingestion/transformation ↛ orchestration (tránh vòng); webhook_consumer độc lập hoặc chỉ được orchestration import.

## Files

- **Create** `.importlinter` (hoặc section trong `pyproject.toml` nếu root đã có — kiểm tra trước, ưu tiên file có sẵn):
  ```ini
  [importlinter]
  root_packages = crm, ingestion, transformation, orchestration, webhook_consumer

  [importlinter:contract:crm-independent]
  name = CRM must not import pipeline packages
  type = forbidden
  source_modules = crm
  forbidden_modules = orchestration, ingestion, transformation, webhook_consumer

  [importlinter:contract:pipeline-layering]
  name = ingestion/transformation must not import orchestration
  type = forbidden
  source_modules = ingestion, transformation
  forbidden_modules = orchestration
  ```
- **Create** `.github/workflows/boundary-check.yml` — job duy nhất: checkout, setup-python, `pip install import-linter`, `lint-imports`. Chạy trên push + PR. (GitHub Actions free cho private repo 2000 phút/tháng — job này <1 phút.)
- **Create** `tools/check_boundaries.ps1` — wrapper chạy local (dev không phải chờ CI): cài import-linter vào venv nào? → dùng `pip install --user` hoặc venv riêng `tools/.venv`; quyết định lúc implement, ghi vào script.

## Steps

1. Điều tra ma trận import thực tế: grep import chéo giữa 5 packages, xác nhận contract không fail oan (ví dụ `scripts/` import gì — nếu scripts import orchestration thì bỏ scripts khỏi root_packages, nó là glue của data-platform).
2. Viết config, chạy `lint-imports` local → pass.
3. Tự phá thử: thêm tạm 1 import crm→orchestration → phải FAIL → gỡ. (Sanity check contract thật sự bite.)
4. Thêm workflow CI + script local.
5. Ghi 1 dòng vào `crm/AGENTS.md` + root `AGENTS.md`: "boundary contracts enforced by import-linter, see .importlinter".

## Validation

- `lint-imports` pass trên main.
- Bước tự phá (step 3) fail đúng contract, đúng tên module vi phạm.
- Push lên GitHub → workflow xanh.

## Risks & Rollback

- import-linter chỉ bắt import tĩnh Python — không bắt coupling qua subprocess/file path. Chấp nhận: data contracts (file/schema) thuộc Phase 6 doc, không enforce máy được ở mức này.
- Python version CI khác local → parse lỗi: pin python-version trong workflow khớp container (3.11/3.12 — kiểm tra).
- Rollback: xóa workflow + config, không ảnh hưởng runtime.
