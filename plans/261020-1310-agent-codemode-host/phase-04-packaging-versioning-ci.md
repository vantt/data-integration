# Phase 4: đóng gói trong monorepo, luật ranh giới cho thư viện dùng chung, test trong `run-all.sh`

**Effort:** 1d · **Phụ thuộc:** phase 3 · **Đụng prod:** không · **Cần user duyệt:** có, duyệt bản `0.1.0` (không cần giờ deploy)

## Bối cảnh

- Thư viện nằm trong repo này (`packages/agent-codemode/`), không có repo, registry, CI riêng. Kiểm tra trước commit của repo là `scripts/checks/run-all.sh` (dbt parse, `check_boundaries.py`, Dagster validate, pytest trong container shadow `--network none`, analytics), `scripts/checks/run-all.sh:1-30`.
- `check_boundaries.py` hiện có luật `py-import` dạng danh sách `(thư mục, {module cấm})` (`scripts/checks/check_boundaries.py:86-129`) và luật `orch-import` dùng `_imported_modules` (`:132-176`); vi phạm đã biết nằm trong `boundary_allowlist.yaml`. Luật mới theo cùng kiểu, nhưng **không** cho phép allowlist (như `module-config`).
- Bố cục thư mục chưa chốt (Đợt 2); `packages/agent-codemode/` là vị trí tạm. Repo quản lý phụ thuộc bằng `requirements.txt` theo thành phần và `pip install -r` trong Dockerfile, chưa có `pyproject.toml` nào (plan, mục "Cách gói sản phẩm dùng").

## Yêu cầu

1. **Đóng gói:**
   - `packages/agent-codemode/pyproject.toml`: tên `agent-codemode`, `version = "0.1.0"`, `requires-python >=3.12`, phụ thuộc có cận phiên bản; `license` theo Q1 (đề xuất "Proprietary, internal use").
   - `requirements.lock` có hash (sinh bằng `uv pip compile --generate-hashes` hoặc `pip-compile`), gồm `pydantic-monty`, `pydantic-monty-runtime`, MCP SDK, `httpx`.
   - Dựng wheel: `uv build packages/agent-codemode` (hoặc `python -m build`) ra `packages/agent-codemode/dist/` (thư mục `dist/` vào `.gitignore`).
   - `agent_codemode.__version__` đọc từ metadata gói.
2. **Luật ranh giới tổng quát cho thư viện dùng chung** trong `scripts/checks/check_boundaries.py` (theo kiểu luật hiện có; thêm mô tả vào docstring đầu file và `scripts/checks/README.md`). Danh sách thư viện đọc từ `scripts/checks/libraries.yaml` (mỗi mục: `path`, `module`; mục đầu `packages/agent-codemode` / `agent_codemode`), không viết cứng thư mục:
   - `lib-import`: với **mỗi** thư viện trong `libraries.yaml`, mọi file `.py` dưới thư mục của nó không được import module gốc của các thư mục khác trong repo (tính tự động: mọi thư mục cấp một chứa `.py`, trừ chính thư viện; hôm nay gồm `crm`, `orchestration`, `ingestion`, `transformation`, `analytics`, `detailView`, `scripts`, `webhook_receiver`, `webhook_consumer`, …), cũng không import nội bộ của thư viện khác trong danh sách (chỉ được API công khai).
   - `lib-public-api`: với mỗi thư viện trong `libraries.yaml`, mọi file `.py` **ngoài** thư mục của nó chỉ được `import <module>` hoặc `from <module> import <tên>`; import `<module>.<module con>` là vi phạm.
   - Hai luật này không có allowlist; thư mục khai báo mà không tồn tại thì báo lỗi (như `py-scan`), danh sách rỗng thì không báo gì.
   - Test cho luật trong `scripts/tests/` bằng cây thư mục giả (fixture): bắt được import ngược, import nội bộ gói khác, import module con từ ngoài; không báo nhầm import thư viện chuẩn và phụ thuộc bên thứ ba.
3. **Chạy test thư viện trong `run-all.sh`:** thêm bước "7. shared libraries" chạy `pytest <path>/tests` cho từng thư viện trong `libraries.yaml` trong container dựng từ base của prod (`python:3.12-slim`), `--network none`, cài phụ thuộc offline từ bộ phụ thuộc shadow (`scripts/shadow/prepare-deps.sh` tải thêm wheel trong `requirements.lock` của từng thư viện), mount worktree chỉ đọc; bộ kiểm phá chạy trong container có `--memory 384m`. Bước báo `passed/failed` như các bước khác.
4. **Kiểm tự đứng được:** một test (chạy trong bước 7) chép `packages/agent-codemode/` sang thư mục tạm ngoài cây repo, cài vào venv riêng từ wheel và `requirements.lock`, chạy test của thư viện ở đó.
5. **Mẫu container** `packages/agent-codemode/deploy/compose.example.yml` và `Dockerfile.example`: cách gói sản phẩm dựng image cho server của mình (cài wheel + lock có hash, user không đặc quyền, `read_only: true`, `tmpfs`, `mem_limit`, `pids_limit`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, healthcheck). Đây là mẫu cho `Dockerfile.crm_codemode` của CRM.
6. `CHANGELOG.md`: mục `0.1.0` (API công khai, runner, giới hạn mặc định, dải `x-agent-catalog-version` hỗ trợ, phiên bản Monty/MCP SDK).

## File

- Tạo: `scripts/checks/libraries.yaml`, `packages/agent-codemode/{pyproject.toml,requirements.lock,CHANGELOG.md}`, `packages/agent-codemode/deploy/{compose.example.yml,Dockerfile.example}`, test luật trong `scripts/tests/test_check_boundaries_packages.py`.
- Sửa: `scripts/checks/check_boundaries.py` (hai luật mới), `scripts/checks/README.md`, `scripts/checks/run-all.sh` (bước 7), `scripts/shadow/prepare-deps.sh` (wheel trong `requirements.lock` của thư viện), `.gitignore` (`packages/agent-codemode/dist/`), `docs/architecture/modules.md` (thư viện dùng chung nằm ngoài mọi bộ, vị trí tạm, luật `lib-import`, `lib-public-api`; không ghi bố cục `apps/` vì chưa chốt).

## Các bước

1. pyproject, lock, dựng wheel.
2. Hai luật ranh giới + test fixture; chạy `check_boundaries.py` trên repo thật: 0 vi phạm.
3. Bước 7 của `run-all.sh`, bộ phụ thuộc offline; chạy toàn bộ `run-all.sh`.
4. Test tự đứng được.
5. Mẫu container.
6. Trình user bản `0.1.0`.

## Test

| Mức | Nội dung |
|---|---|
| Luật | Fixture: thư viện import `crm` → `lib-import`; thư viện A import module con của thư viện B → `lib-import`; file ở `crm/` import `agent_codemode.runner.monty` → `lib-public-api`; đổi `path` trong `libraries.yaml` sang thư mục khác thì luật theo vị trí mới; `from agent_codemode import MontyRunner` → không vi phạm |
| run-all | Bước 7 xanh; các bước cũ không đổi kết quả |
| Tự đứng | Test của thư viện chạy xanh ngoài cây repo |
| Mẫu | Dựng image từ `Dockerfile.example` với server mẫu + backend giả, healthcheck xanh dưới `read_only`, `cap_drop ALL` |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Thêm bước làm `run-all.sh` chậm | Thấp × Thấp | Bộ test thư viện nhỏ; 1.000 lần chạy để ở chế độ chậm chạy tay, `run-all.sh` chạy bản rút gọn 100 lần |
| Luật tự tính module gốc của repo báo nhầm | Thấp × Thấp | Test fixture; chỉ xét thư mục cấp một có `.py` |

## Rollback

`git revert`; luật mới và bước 7 mất, không ảnh hưởng prod.
