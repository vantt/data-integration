# S14 Approach-Script — Backend Data Feed

Backend cho màn S14 (Call Mode Cockpit) đọc kịch bản tiếp cận AI. **File-direct sau repository interface** (YAGNI: chưa lên DB vì JSON còn tạo tay/đổi schema). UI để sau (`ui-port`) consume contract này.

> ✅ **NGHIỆM THU 2026-06-26** — Giai đoạn C đạt: S14 cockpit (tab "Gọi" trong S03, dùng chung sidebar) + worklist filter "Có kịch bản" chạy live; backend file-feed + quy trình tay vận hành; 13+31 test pass, code review + fix xong. Còn lại đều tùy chọn/gác (auto-gen Dagster, B2 auth).

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
| 05 | [Worklist "Có kịch bản" filter (auto-handle scripts mới)](phase-05-worklist-has-script-filter.md) | ✅ |

## Trạng thái Giai đoạn C — S14 trong CRM (cập nhật 2026-06-25)
| Bước | Trạng thái | Commit |
|---|---|---|
| Spec S14 (ui-spec) + wireframe | ✅ | fd8052b |
| Backend file-feed (phases 01–04, 9 test) | ✅ | e45cb45 |
| ui-port: cockpit fragment → tab "Gọi" trong S03 (dùng chung sidebar S03) | ✅ | e45cb45 |
| Glue: route call_cockpit → repo (per-customer) + verify live | ✅ | e45cb45 |
| Code review (2 HIGH + 3 MED → fix) | ✅ | a113db5 |
| Test hardening B1 (13 test: R14 gate + 500/404) | ✅ | 2917a80 |
| Worklist "Có kịch bản" filter — phase 05 (auto-handle scripts mới) | ✅ | 62ff52c |
| Production auto-gen (Dagster + GPT → cache table) | ⬜ chưa làm | — |
| B2 auth endpoint (gác — chính sách LAN-trust, nhất quán `/insight`) | ⬜ gác | — |

## Việc còn lại (chưa làm)
1. **Sinh script — quy trình TAY** (đã chốt làm tay, KHÔNG auto-gen): xem [manual-workflow.md](manual-workflow.md). 3 bước: `build_approach_prompts.py` (prep) → dán GPT (tay) → `load_approach_scripts.py` (nạp). *(Auto-gen Dagster+GPT là tùy chọn tương lai khi muốn hết tạo tay — swap File→SQLite repo, cùng port.)*
2. **B2 auth** — thêm `auth_dependency` cho GET `/approach-script` khi quyết siết auth GET toàn cục (làm cùng `/insight`).
3. **Dữ liệu `recommended=false`** — pilot toàn `recommended=true` → STOP state chỉ demo được bằng patch tay; có data thật/synthetic thì badge "không gọi" mới hiện tự nhiên. *(WS-A2 sinh data thật → gỡ điểm này.)*

## Nâng cấp v2+ — Rich Dynamic Script (định hướng, chưa lên lịch)
Chốt 2026-06-26: nâng kịch bản từ **tài liệu tĩnh** → **engine dẫn thoại động + vòng lặp phản hồi + thu thập lũy tiến + thư viện kết hợp**. Chi tiết: [roadmap-rich-dynamic-script.md](roadmap-rich-dynamic-script.md).

**Phát hiện nền:** vòng lặp đã dựng MỘT NỬA — capture (`crm_activity` outcome + S14 outcome bar + M08) ✅; read-back (`build_approach_prompts.py` hardcode `[]`) ❌ hở. Đòn bẩy lớn nhất = nối nửa hở, không phải sửa prompt.

| WS | Việc | Trạng thái | Trình tự |
|---|---|---|---|
| D | [Benchmark percentile dbt](phase-06-benchmark-percentile-dbt.md) (vị thế top X% CLV — đường chuẩn) | ⬜ ready | 1 |
| A1 | Read-back notes/conversations thật từ `crm_activity` (đóng vòng lặp) | ⬜ | 1 |
| A2 | `data_completeness` IN + `info_to_collect` OUT (progressive profiling, tái dùng capture) | ⬜ | 2 |
| B | Script TĨNH có nhánh + backend interpreter (điều hướng theo outcome; state light trước) | ⬜ vision | 3 |
| C | Auto-gen Dagster + thư viện MODULE KẾT HỢP (không ma trận) + flywheel | ⬜ vision | 4 |

**Mô hình "dynamic" (chốt):** sinh offline 1 script tĩnh có nhánh → backend interpret + điều hướng theo tương tác nhân viên (KHÔNG regen live). Dynamic-behavior TÁCH khỏi auto-gen; pilot tạo tay được nếu cây NÔNG (1–2 tầng).

**Chống over-engineering:** không build engine stateful/durable-session sớm · không materialize ma trận product×type · không thêm field S14 không render · không làm graph tổng quát (cây quyết định nông thôi).

## Ngoài scope dự án này (không chặn)
- 2 test fail pre-existing (xác nhận có trước phase 05) — không thuộc S14.
- Design-folder reorg + plan session khác đang nằm uncommitted trong working tree — chủ của chúng tự xử lý.

**Verify live:** per-customer render + STOP gate R14. URL `http://localhost:3007/customers/895489673` → tab "Gọi".

## Ngoài scope (bàn giao tiếp)
- **Production auto-gen** (Dagster + GPT → cache.wh_approach_script) → khi script hết tạo tay; lúc đó swap `FileApproachScriptRepository` → `SQLiteApproachScriptRepository` (cùng port, S14 không đổi).

## Dependencies
- Spec S14 đã có (`crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`).
- 31 JSON pilot: `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/`.

## Unresolved
- ~~Tên env override thư mục~~ → đã chốt `CRM_APPROACH_SCRIPT_DIR` (override) / `CRM_DATA_DIR` → `{data_dir}/approach_scripts`.
- `?fixture=stop` đã bỏ (review F1) — STOP demo cần 1 row `recommended=false` thật.
