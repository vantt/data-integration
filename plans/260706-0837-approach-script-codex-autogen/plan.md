# Approach Script — Codex Auto-Gen (Stage 0+1+2)

Nâng cấp luồng sinh kịch bản tiếp cận: bỏ bước copy-dán tay (thay bằng `codex` headless), thêm linter guardrail khi nạp, đóng vòng lặp read-back notes từ CRM. Stage 2: hexagon hoá LLM caller (đổi provider được) + tự động sinh/nạp theo nhịp worklist-refresh, bỏ gate người duyệt cho luồng tự động.

**Quyết định đã chốt (user, 2026-07-06):**
- LLM caller = **codex CLI headless** (`codex exec`, lệnh configurable qua `--codex-cmd`/env `CODEX_CMD` — codex không nằm trong PATH của mọi shell). *(Stage 0+1 — vẫn giữ làm adapter thủ công/dry-run.)*
- **Chính sách duyệt (tiered) — Stage 0+1:** 31 script pilot đã duyệt → KHÔNG duyệt lại chừng nào nội dung không đổi. Script sinh mới bằng codex: linter máy 100%; người duyệt 100% cho lô đầu, sau đó sample 10–20% + bắt buộc 100% các script `recommended=false` hoặc dính gate dữ liệu đáng ngờ. Regen (nội dung đổi) = script mới → theo chính sách trên.
- **[SUPERSEDES trên, Stage 2, user 2026-07-06]** Luồng tự động (nightly, trigger theo worklist-refresh): **bỏ hẳn người duyệt**, kể cả `recommended=false`. Chỉ còn linter máy (phase 01) làm gate. Rủi ro: script sai/nhạy cảm có thể lọt ra cockpit không ai soi trước — chấp nhận theo quyết định user, ghi nhận ở phase-05 § Rủi ro. Luồng thủ công (approach_out/ + load_approach_scripts.py) giữ nguyên cho ai muốn regen tay + soi tay.
- **Completion provider = hexagon, scope hẹp** (phase 04): tách port `ApproachScriptCompletionProvider` (KHÔNG phải LLM abstraction tổng quát cho repo — chỉ phục vụ đúng approach-script), codex CLI là 1 adapter, thêm adapter API-based cho container Dagster tự động (không phụ thuộc OAuth cá nhân/quota subscription khi chạy hàng loạt mỗi đêm).
- **[Đã làm, 2026-07-06, ngoài phase 04]** Cài codex CLI vào `data_platform`: `Dockerfile.dataplatform` thêm Node 20.x + `npm install -g @openai/codex`; auth OAuth sống ở named volume `agent_codex_config:/root/.codex` (`docker-compose.yml`) — cần 1 lần `docker compose exec data_platform codex login` để kích hoạt, chưa login thì lệnh gọi codex sẽ fail (container vẫn chạy bình thường).

## Phases

| # | Phase | Trạng thái |
|---|---|---|
| 01 | [Linter + meta block + sửa docs wh_approach_script](phase-01-linter-meta-docs.md) | ✅ |
| 02 | [Read-back notes/activities từ crm.db](phase-02-readback-crm-history.md) | ✅ |
| 03 | [Generator codex headless](phase-03-codex-generator.md) | ✅ |
| 04 | [Hexagon completion provider cho approach-script (codex CLI + API adapter)](phase-04-llm-provider-hexagon.md) | ✅ |
| 05 | [Trigger theo worklist-refresh + auto-load (bỏ review)](phase-05-worklist-refresh-trigger.md) | ✅ |

## Dependencies
- Template v2: `plans/260624-1917-customer-insight-prompt-template/customer-insight-prompt-template.md`
- Builder hiện có: `scripts/build_approach_prompts.py` (tái dùng cohort/template/fill)
- Loader: `scripts/load_approach_scripts.py`
- CRM data: `crm.db` trong volume container `crm` (`/data/crm.db`) — mapping `crm_party_identity(identity_type='sapo_customer')`, notes `crm_note`, activities `crm_activity_log`
- Roadmap gốc: `plans/260625-1808-s14-approach-script-backend-feed/roadmap-rich-dynamic-script.md` (đây là thực thi WS-A1 + một phần WS-C mức script, Stage 2 thêm phần Dagster)
- Nightly job đích cho phase 05: `pipeline_batch_nightly_job` (`orchestration/definitions.py:238-239`, cron `0 3 * * *` ICT), sau asset `crm_sync.crm_cache_refresh` (`orchestration/assets/crm_sync.py:37`)
- Cohort actionable: `cache.wh_sku_action_queue` (nạp từ `mart_customer_sku_action_queue` qua `crm/sync/duckdb_reader.py:346 fetch_sku_action_queue`)

## Acceptance
- Linter chạy sạch (hoặc chỉ ra lỗi thật) trên 31 script pilot.
- `build_approach_prompts.py` inject notes thật thay `[]` (degrade về `[]` nếu docker/crm.db không truy cập được).
- `generate_approach_scripts.py --dry-run` sinh prompt đủ notes; đường codex thật chạy được trong terminal có codex (user smoke-test).
- `load_approach_scripts.py` từ chối JSON hỏng/vi phạm guardrail, có `--no-lint` escape.
- CRM đọc `meta.model`/`meta.template_version` từ JSON (entity đã có sẵn field); test container crm pass.
- (Stage 2) `generate_approach_scripts.py --provider codex|<api>` chọn được provider qua hexagon, hành vi `--provider codex` mặc định không đổi so với Stage 0+1.
- (Stage 2) Asset nightly tự sinh + tự nạp script cho cohort actionable hôm đó không cần tay người, không cần bước duyệt; script fail lint vẫn rơi vào `_failed/` để soi sau (không chặn asset).

## Ngoài scope (Stage 3+, chưa làm)
- Regen policy tự động theo tuổi/activity mới đo outcome-per-script (Stage 2 chỉ regen khi "chưa có script" hoặc "script cũ hơn N ngày", chưa có auto-tune theo hiệu quả).
- `SQLiteApproachScriptRepository` + thư viện module kết hợp (WS-C đầy đủ).
- `recent_conversations` từ FB messages (giữ `[]`).
