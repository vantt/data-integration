#!/usr/bin/env python3
"""generate_approach_scripts.py — Sinh approach-script bằng LLM completion provider.

Thay bước "dán tay từng prompt vào GPT" bằng gọi provider per khách:
  cohort SQL → prompt (template v2 + data khách + notes thật) → provider.complete() →
  extract JSON → lint guardrail → approach_out/{customer_id}.json (CHỜ DUYỆT).

Người vẫn duyệt output trước khi nạp:
  python scripts/load_approach_scripts.py --src approach_out/

Provider mặc định là codex CLI headless (--provider codex, cần codex trong PATH
của terminal chạy lệnh này). --provider anthropic gọi thẳng Anthropic API (cần
ANTHROPIC_API_KEY) — dùng cho luồng tự động không phụ thuộc OAuth cá nhân.

Luồng tự động (phase 05, `--auto-load-url`): bỏ hẳn bước chờ duyệt tay — script
pass lint POST thẳng sang CRM (`POST /admin/approach-scripts/load`), không ghi
`approach_out/{cid}.json`. Kèm regen-guard (`--cohort-from-queue` + state file)
để không gọi provider lại cho khách vừa auto-load gần đây.

Ví dụ:
  python scripts/generate_approach_scripts.py --ids 895489673
  python scripts/generate_approach_scripts.py --recency 270 --limit 20
  python scripts/generate_approach_scripts.py --dry-run --limit 5
  python scripts/generate_approach_scripts.py --provider anthropic --ids 895489673
  CODEX_CMD="codex exec --model gpt-5.5 -" python scripts/generate_approach_scripts.py ...
  python scripts/generate_approach_scripts.py --cohort-from-queue --provider codex \\
      --auto-load-url http://crm:8090/admin/approach-scripts/load --crm-db /app/var/crm_data/crm.db

Lưu ý chi phí: `--provider codex` với ChatGPT-subscription login KHÔNG chọn được
model khác (khoá cứng gpt-5.5, mọi `-m` khác bị 400 "not supported"). Đòn bẩy
chi phí duy nhất là `--reasoning-effort` (mặc định "low").
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from approach_script_autoload import post_batch  # noqa: E402
from approach_script_completion.codex_cli_provider import DEFAULT_CODEX_CMD  # noqa: E402
from approach_script_completion.errors import ApproachScriptCompletionError  # noqa: E402
from approach_script_completion.factory import get_completion_provider  # noqa: E402
from approach_script_lint import lint_script  # noqa: E402
from approach_script_regen_state import load_state, save_state, should_skip  # noqa: E402
from build_approach_prompts import ROOT, add_cohort_args, fetch_cohort, fetch_history, fill, load_template  # noqa: E402

TEMPLATE_VERSION = "v2"
DEFAULT_STATE_FILE = ROOT / "approach_out" / ".generated_state.json"


def extract_json_block(text: str) -> dict | None:
    """Lấy object JSON cuối cùng trong stdout (codex có thể in text quanh JSON).

    Quét ngược tìm '{' mở của khối cân bằng ngoặc kết thúc gần cuối nhất,
    bỏ qua ngoặc nằm trong string literal.
    """
    end = text.rfind("}")
    while end != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(end, -1, -1):
            ch = text[i]
            # Quét ngược nên xử lý string đơn giản: chỉ đếm ngoặc ngoài dấu "
            if ch == '"' and not escape:
                in_str = not in_str
            if not in_str:
                if ch == "}":
                    depth += 1
                elif ch == "{":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[i:end + 1])
                        except json.JSONDecodeError:
                            break  # khối này hỏng → thử '}' trước đó
            escape = ch == "\\" and not escape
        end = text.rfind("}", 0, end)
    return None


def build_meta(customer: dict, provider) -> dict:
    """Provenance + snapshot vài field khách để linter check guardrail margin."""
    return {
        "model": provider.model_label,
        "template_version": TEMPLATE_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": provider.name,
        "customer": {
            "is_margin_negative": customer.get("is_margin_negative"),
            "avg_order_contribution_margin_pct": customer.get("avg_order_contribution_margin_pct"),
            "customer_type": customer.get("customer_type"),
        },
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Sinh approach-script bằng completion provider (codex/anthropic).")
    ap.add_argument("--out", default="approach_out", help="thư mục output (chờ duyệt)")
    add_cohort_args(ap)
    ap.add_argument("--provider", default=os.getenv("APPROACH_SCRIPT_PROVIDER", "codex"),
                    choices=["codex", "anthropic"], help="completion provider (default: codex)")
    ap.add_argument("--codex-cmd", default=os.getenv("CODEX_CMD", DEFAULT_CODEX_CMD),
                    help=f"lệnh codex headless, chỉ áp dụng khi --provider codex (default: {DEFAULT_CODEX_CMD!r})")
    ap.add_argument("--reasoning-effort", default=os.getenv("APPROACH_SCRIPT_REASONING_EFFORT", "low"),
                    choices=["minimal", "low", "medium", "high"],
                    help="chỉ áp dụng khi --provider codex — model KHÔNG chọn được (khoá cứng gpt-5.5 "
                         "với ChatGPT-subscription login, verified 2026-07-07); đây là đòn bẩy chi phí "
                         "duy nhất còn lại (default: low)")
    ap.add_argument("--timeout", type=int, default=300, help="giây timeout mỗi lần gọi provider")
    ap.add_argument("--dry-run", action="store_true", help="chỉ ghi prompt, không gọi provider")
    ap.add_argument("--auto-load-url", default=os.getenv("APPROACH_SCRIPT_LOAD_URL", ""),
                    help="POST batch script pass-lint tới URL này (vd http://crm:8090/admin/approach-scripts/load) "
                         "thay vì ghi approach_out/ chờ duyệt tay — luồng tự động phase 05")
    ap.add_argument("--auto-load-timeout", type=int, default=60, help="giây timeout cho POST auto-load")
    ap.add_argument("--state-file", default=str(DEFAULT_STATE_FILE),
                    help="file state regen-guard (mặc định approach_out/.generated_state.json)")
    ap.add_argument("--regen-after-days", type=int, default=None,
                    help="ép flat N ngày cho mọi khách (mặc định: tiered theo next_purchase_signal, xem approach_script_regen_state.py)")
    ap.add_argument("--force-regen", action="store_true",
                    help="bỏ qua regen-guard, sinh lại dù chưa tới ngưỡng")
    args = ap.parse_args()

    if args.dry_run:
        provider = None
    else:
        try:
            provider = (get_completion_provider("codex", codex_cmd=args.codex_cmd, reasoning_effort=args.reasoning_effort)
                        if args.provider == "codex" else get_completion_provider(args.provider))
        except ApproachScriptCompletionError as exc:
            sys.exit(str(exc))

    customers = fetch_cohort(args)
    if not customers:
        sys.exit("Cohort rỗng — kiểm tra gating/--ids.")
    print(f"Cohort: {len(customers)} khách")

    today_date = date.today()
    state_path = Path(args.state_file)
    state = load_state(state_path)
    # Regen-guard chỉ áp dụng cho cohort GATE/queue — --ids tường minh luôn bypass
    # (giữ đúng ngữ nghĩa "tôi muốn khách này" như GATE cũng bypass).
    if not args.force_regen and not args.ids.strip():
        before = len(customers)
        customers = [c for c in customers if not should_skip(c, state, args.regen_after_days, today_date)]
        if before - len(customers):
            print(f"Regen-guard: bỏ qua {before - len(customers)} khách (script còn mới)")
    if not customers:
        sys.exit("Cohort rỗng sau regen-guard — không còn khách cần sinh.")

    history = fetch_history(customers, args)

    template = load_template()
    out = ROOT / args.out
    failed_dir = out / "_failed"
    out.mkdir(parents=True, exist_ok=True)
    today = today_date.isoformat()

    ok = failed = 0
    to_load: list[dict] = []  # {"customer_id", "script"} — gom khi --auto-load-url
    for i, customer in enumerate(customers, 1):
        cid = customer["customer_id"]
        prompt = fill(template, customer, today, recent_notes=history.get(int(cid)))

        if args.dry_run:
            (out / f"{cid}.prompt.txt").write_text(prompt, encoding="utf-8")
            print(f"[{i}/{len(customers)}] {cid} dry-run → prompt ghi xong")
            continue

        print(f"[{i}/{len(customers)}] {cid} gọi {provider.name}...", flush=True)
        completion = ""
        try:
            completion = provider.complete(prompt, args.timeout)
            data = extract_json_block(completion)
            errors = [] if data else ["không extract được JSON từ completion"]
        except ApproachScriptCompletionError as exc:
            data = None
            errors = [str(exc)]

        if data:
            data["meta"] = build_meta(customer, provider)
            errors = lint_script(data)

        if errors:
            failed += 1
            failed_dir.mkdir(exist_ok=True)
            (failed_dir / f"{cid}.stdout.txt").write_text(
                completion + "\n\n--- ERRORS ---\n" + "\n".join(errors), encoding="utf-8")
            print(f"    FAIL → {failed_dir.name}/{cid}.stdout.txt")
            for e in errors[:3]:
                print(f"      - {e}")
        else:
            ok += 1
            if args.auto_load_url:
                to_load.append({"customer_id": int(cid), "script": data})
                print(f"    OK → gom auto-load (cid={cid}, recommended={data.get('approach', {}).get('recommended')})")
            else:
                (out / f"{cid}.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"    OK → {cid}.json (recommended={data.get('approach', {}).get('recommended')})")

    if args.dry_run:
        print(f"\nDry-run xong: {len(customers)} prompt trong {out}/")
    elif args.auto_load_url:
        if to_load:
            result = post_batch(args.auto_load_url, to_load, args.auto_load_timeout)
            if result is not None:
                skipped_cids = {s.get("customer_id") for s in result.get("skipped", [])}
                loaded_cids = {item["customer_id"] for item in to_load} - skipped_cids
                for customer in customers:
                    if int(customer["customer_id"]) in loaded_cids:
                        state[str(customer["customer_id"])] = today
                save_state(state_path, state)
                print(f"\nAuto-load: {result.get('written', 0)} written, {len(skipped_cids)} skipped bởi CRM.")
            else:
                print("\nAuto-load: POST fail — state KHÔNG cập nhật, sẽ thử lại lần sau.")
        else:
            print("\nKhông có script pass lint để auto-load.")
        print(f"Xong: {ok} OK, {failed} fail.")
    else:
        print(f"\nXong: {ok} OK, {failed} fail. DUYỆT output trong {out}/ rồi chạy:\n"
              f"  python scripts/load_approach_scripts.py --src {args.out}/")


if __name__ == "__main__":
    main()
