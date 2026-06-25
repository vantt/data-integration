# S14 Approach-Script — Backend Data Feed

Backend cho màn S14 (Call Mode Cockpit) đọc kịch bản tiếp cận AI. **File-direct sau repository interface** (YAGNI: chưa lên DB vì JSON còn tạo tay/đổi schema). UI để sau (`ui-port`) consume contract này.

## Quyết định kiến trúc
- **Lưu:** JSON files `{data_dir}/approach_scripts/{customer_id}.json` — cạnh cache.db trong volume `crm_data` ⇒ **KHÔNG cần docker mount mới**.
- **Đọc qua interface** (hexagonal, giống `CacheRepository`): hôm nay `FileApproachScriptRepository`; mai swap `SQLiteApproachScriptRepository` → S14 không đổi.
- **Entity giữ `data: dict`** (parsed JSON nguyên) + vài field rút (`recommended`, `confidence`, `refreshed_at`) → bền với schema còn đổi, khỏi map từng field.
- **party_id → customer_id**: reuse pattern `list_identities` → `sapo_customer` (giống `insight_handler`).
- **R2 giữ nguyên:** LLM chạy ở pipeline/loader (Python), CRM chỉ đọc.

## Contract bàn giao cho `ui-port` (sau khi backend xong)
- `GET /api/parties/{id}/approach-script` → `{ "script": {<OUTPUT SCHEMA>} | null, "meta": {recommended, confidence, refreshed_at} }`
- Repo method `get_by_customer_id(customer_id) -> ApproachScript | None` cho screen server-rendered gọi trực tiếp.

## Phases
| # | Phase | Trạng thái |
|---|---|---|
| 01 | [Domain entity + port](phase-01-domain-port-entity.md) | ✅ |
| 02 | [File adapter + tests](phase-02-file-adapter.md) | ✅ |
| 03 | [HTTP endpoint + wiring + tests](phase-03-http-endpoint-wiring.md) | ✅ |
| 04 | [Data prep loader + e2e verify](phase-04-data-prep-loader.md) | ✅ |

## Trạng thái Giai đoạn C — S14 trong CRM (cập nhật 2026-06-25)
| Bước | Trạng thái | Commit |
|---|---|---|
| Spec S14 (ui-spec) + wireframe | ✅ | fd8052b |
| Backend file-feed (phases 01–04, 9 test) | ✅ | e45cb45 |
| ui-port: cockpit fragment → tab "Gọi" trong S03 (dùng chung sidebar S03) | ✅ | e45cb45 |
| Glue: route call_cockpit → repo (per-customer) + verify live | ✅ | e45cb45 |
| Code review (2 HIGH + 3 MED → fix) | ✅ | a113db5 |
| Test hardening B1 (13 test: R14 gate + 500/404) | ✅ | 2917a80 |
| Production auto-gen (Dagster + GPT → cache table) | ⬜ chưa làm | — |
| B2 auth endpoint (gác — chính sách LAN-trust, nhất quán `/insight`) | ⬜ gác | — |

**Verify live:** per-customer render + STOP gate R14. URL `http://localhost:3007/customers/895489673` → tab "Gọi".

## Ngoài scope (bàn giao tiếp)
- **Production auto-gen** (Dagster + GPT → cache.wh_approach_script) → khi script hết tạo tay; lúc đó swap `FileApproachScriptRepository` → `SQLiteApproachScriptRepository` (cùng port, S14 không đổi).

## Dependencies
- Spec S14 đã có (`crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`).
- 31 JSON pilot: `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/`.

## Unresolved
- ~~Tên env override thư mục~~ → đã chốt `CRM_APPROACH_SCRIPT_DIR` (override) / `CRM_DATA_DIR` → `{data_dir}/approach_scripts`.
- `?fixture=stop` đã bỏ (review F1) — STOP demo cần 1 row `recommended=false` thật.
