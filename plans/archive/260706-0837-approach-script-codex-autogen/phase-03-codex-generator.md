# Phase 03 — Generator codex headless

## Yêu cầu
`scripts/generate_approach_scripts.py`: thay bước "dán tay vào GPT" bằng gọi `codex` non-interactive per khách. Người vẫn duyệt output trước khi `load_approach_scripts.py`.

## Flow
1. Cohort: tái dùng `GATE`/`COLS`/`load_template`/`fill` import từ `build_approach_prompts` (cùng flags `--recency/--limit/--ids/--mask-phone`).
2. Prompt: như builder + notes thật (phase 02).
3. Gọi codex: prompt ghi ra file tạm, chạy lệnh configurable — mặc định `codex exec --skip-git-repo-check -` (prompt qua stdin). Override: `--codex-cmd` hoặc env `CODEX_CMD` (codex không có trong PATH mọi shell — user chạy trong terminal có codex).
4. Extract JSON: lấy khối `{...}` cân bằng ngoặc cuối cùng trong stdout (codex có thể in text quanh JSON).
5. Gắn `meta`: `{model, template_version: "v2", generated_at, snapshot_date, generator: "codex-exec", customer: {is_margin_negative, avg_order_contribution_margin_pct, customer_type}}`.
6. Lint (phase 01). Pass → `approach_out/{customer_id}.json` (chờ duyệt). Fail → `approach_out/_failed/{customer_id}.stdout.txt` + lỗi lint để soi tay.
7. Tuần tự, in tiến độ; `--dry-run` = chỉ ghi prompt (không gọi codex).

## Chính sách duyệt (chốt với user)
- Linter: 100% tự động.
- Người duyệt: lô codex đầu 100%; ổn định → sample 10–20% + LUÔN 100% script `recommended=false`/dính gate.
- 31 pilot đã duyệt: không duyệt lại nếu không regen.

## Files
- Tạo: `scripts/generate_approach_scripts.py`
- Không sửa loader/CRM (contract giữ nguyên).

## Validate
- `--dry-run --ids <2 khách>` → 2 prompt đúng, có notes.
- Smoke test codex thật: user chạy trong terminal có codex (`--ids 1 khách`), verify JSON pass lint. (Máy build không thấy codex trong PATH → không tự smoke được.)

## Rủi ro
- Codex output không phải JSON thuần → extractor + _failed dir đỡ; nếu tỷ lệ fail cao, thêm system-instruction ép "output only JSON" vào cuối prompt (đã có trong template RÀNG BUỘC #3).
- Chi phí/giới hạn subscription codex: chạy `--limit` nhỏ trước.
