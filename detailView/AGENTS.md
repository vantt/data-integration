# detailView — ⚠️ RETIRED subproject

**Status: RETIRED (as of 2026-07-02).** This subproject (the `detail_view` viewer app) is no
longer active development. Do **not** build new features here.

## For agents / contributors
- **Do NOT borrow this subproject's `.venv`** as a Python interpreter for other subprojects
  (e.g. to run CRM tests). Each subproject uses its own environment. CRM runs in the `crm`
  Docker container (`Dockerfile.crm` → `crm/src/requirements.txt`); run CRM tests there:
  `docker compose exec crm sh -lc 'cd /app/crm/src && python -m pytest ...'`.
- Treat this tree as read-only history. Any change here should be a deliberate decision to
  un-retire it, not incidental.

## What it was
Standalone order/detail viewer (FastAPI app in `app/`, own `requirements.txt`, `tests/`).
Code was baked into its image — templates/static/fonts were NOT volume-mounted.

## Still-wired leftovers (clean up if fully decommissioning)
- `docker-compose.yml` → service **`detail_view`** (`Dockerfile.detailview`, port 8000,
  Caddy host `detailview.lan.fwg.vn`). Remove these when you want the service gone entirely.
