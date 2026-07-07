# Phase 01 — Linter + meta block + sửa docs wh_approach_script

## Yêu cầu
1. Module lint `scripts/approach_script_lint.py` — validate 1 script JSON, trả list lỗi (rỗng = pass).
2. `load_approach_scripts.py` lint trước khi copy; file fail → skip + log lỗi; flag `--no-lint`.
3. `FileApproachScriptRepository` đọc `meta.model` / `meta.template_version` từ JSON → truyền vào entity (field có sẵn, đang bỏ trống).
4. Sửa docs nói dối: `cache.wh_approach_script` không tồn tại — thực tế đọc file JSON qua `ApproachScriptRepository`.

## Rule lint (máy check được — KISS)
- JSON parse được, object.
- Key bắt buộc: `profile_read`, `value_assessment`, `opportunity`, `risk`, `approach`, `confidence`, `data_gaps`.
- `approach.recommended` là bool; nếu `false` → `reason_if_not_recommended` non-empty.
- `primary_channel` ∈ {phone,zalo,sms,in_store}; `fallback_channel` ∈ {phone,zalo,sms,in_store,none}.
- `confidence` ∈ {high,medium,low}.
- Chống lộ số thô: mọi string không chứa decimal dài (regex `\d\.\d{4,}`).
- Guardrail margin (chỉ khi có `meta.customer`): `is_margin_negative=true` → talking_points/opening/cross_sell không chứa "giảm giá|khuyến mãi|ưu đãi|discount|sale off" (case-insensitive).
- Branching v3 (nếu có `nodes`): `entry_node` tồn tại trong `nodes`; mọi `options[].next` null hoặc trỏ node tồn tại; mỗi node có `say` + `options` non-empty; ≥1 đường terminal (next=null).

## Files
- Tạo: `scripts/approach_script_lint.py`
- Sửa: `scripts/load_approach_scripts.py`, `crm/src/adapters/outbound/file/approach_script_file_repository.py`
- Docs fix: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (comment dòng 18 + empty-state dòng ~318), `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`, `crm/docs/ui-spec/screens/S03-customer-360-detail.md`, `crm/docs/ui-spec/30-states-and-errors.md` (prototype jsx/data.js giữ nguyên — mock design)

## Validate
- Lint 31 file `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/` — báo cáo kết quả.
- Test crm container: `test_approach_script_file_repository.py` pass (+ case meta).
- `docker compose restart crm` sau khi sửa repo (bind-mount, không rebuild).

## Rủi ro
- Lint quá gắt fail cả 31 pilot đã duyệt → chỉnh rule theo thực tế (pilot là ground truth đã duyệt), không nới với script mới.
