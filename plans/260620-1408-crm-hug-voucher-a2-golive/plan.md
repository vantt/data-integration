---
title: "M5 — A2 Go-Live: Hug Voucher Issuance/Redeem + A2 Campaign"
description: "Closes the voucher loop (issuance ledger + redeem matcher) and launches A2 to 364 MASKED_REPEAT customers (683M VND CM)."
status: pending
# (updated 2026-07-10: 5/5 quyết định kiến trúc/ops chốt — HUG_ZALO_OA_URL set + Worker deployed (Version 5225dc64), xem Quyết định chốt section below. Phases P1-P5 vẫn pending — chưa có implementation report nào trong plan dir này.)
priority: P1
effort: 6h
branch: main
tags: [hug, voucher, crm, a2, campaign]
created: 2026-06-20
---

## Context

- Design rationale: `plans/260619-1030-crm-nba-resell-engine/discussion-hug.md` §9, §12
- Build order: `plans/260619-1030-crm-nba-resell-engine/build-order.md` M5
- Coupon/Zalo verify: `plans/reports/hug-verify-sapo-coupon-zalo-deeplink-260619-1432-report.md`
- Completed prereqs: M0 (tier mart) · M2 (edge schema + Worker) · M3 (token mint/claim) · M4 (capture loop + identity resolution + C2 campaign UI)

## Phases

| # | Name | Status | Effort | Blocks |
|---|------|--------|--------|--------|
| P1 | [crm.db migration `crm_hug_voucher`](phase-01-crm-hug-voucher-migration.md) | pending | 45m | P3, P4 |
| P2 | [Edge landing: reveal offer + carry campaign_id](phase-02-edge-landing-campaign-id.md) | pending | 60m | P3 |
| P3 | [Issuance writer in /admin/refresh](phase-03-issuance-writer.md) | pending | 90m | P1, P2 |
| P4 | [Redeem matcher in /admin/refresh](phase-04-redeem-matcher.md) | pending | 60m | P1 |
| P5 | [A2 go-live runbook + attribution readout](phase-05-a2-golive-runbook.md) | pending | 45m | P3, P4 |

## Key Architecture Decisions (flag for user)

1. **Ledger LOCAL** (`crm_hug_voucher` in crm.db, not edge D1): redeem matching needs `fact_orders` (local/warehouse); §11 "Local là brain; D1 dựng lại được từ local". Alt: edge-only ledger — requires edge write + D1 read-back for matching. **→ See Open Questions #1.**
2. **Issuance triggered locally in /admin/refresh** (not at edge landing time): resolver runs first → customer_id known → single transaction. No NULL-customer rows ever written. **→ See Open Questions #2.**
3. **Redeem matcher is a local CRM job** (not a dbt model): needs crm_hug_voucher write-back; dbt is read-only. **→ See Open Questions #3.**
4. **Flavor C+** (shared-per-campaign code "HUG50", created manually in Sapo admin with `once_per_customer` + min-order): no Sapo write-API needed. Match key = `(customer_id, order_coupon_code)`.
5. **Edge D1 `hug_voucher` push deferred** (P6, not in this plan): not needed for the issuance/redeem loop. **→ See Open Questions #4.**

## Open Questions

1. **Local vs edge ledger**: plan bakes in local-master. Confirm or redirect to edge-only (requires more Worker logic + D1 read-back at match time).
2. **Issuance trigger latency**: 15-min /admin/refresh cycle means voucher shows up in ledger ~15 min after opt-in. Is that acceptable for the landing page "show code immediately" UX? (If not, consider a lightweight direct-write path at opt-in ingest time.)
3. **Redeem matcher as CRM job vs dbt model**: plan uses local job (needs write-back to crm.db). Confirm — alternative is a dbt model that reads fact_orders and outputs a mart, but dbt cannot write back to crm.db.
4. **Push ledger to edge D1 in v1?**: deferred to optional P6. Confirm deferral is acceptable (edge `hug_voucher` empty for now; quota enforcement stays local/Sapo).
5. ~~**A2 campaign HUG_ZALO_OA_URL**: is the env var already set in production `.env`? Needed for the landing page follow-CTA. Confirm value.~~ **RESOLVED 2026-07-10** — see Quyết định chốt #5.

## Quyết định chốt 2026-07-10 (mở khóa go-live)

1. **Ledger: giữ local-master** như plan hiện tại. Edge D1 = P6, không đổi hướng.
2. **Issuance latency: chấp nhận chu kỳ 15 phút, ĐỔI UX landing** — landing KHÔNG hiện mã ngay; hiển thị "Mã ưu đãi sẽ được gửi qua Zalo OA trong ít phút" → vừa gỡ ràng buộc direct-write, vừa ép khách follow Zalo OA (mục tiêu thật của capture là kênh liên hệ trọn đời, voucher chỉ là token). ⚠ P3/P5 phải sync copy landing theo quyết định này.
3. **Redeem matcher: CRM job local** (write-back crm.db) — dbt không ghi ngược crm.db, không có phương án thay thế khả thi.
4. **Edge D1 push: defer P6** — quota enforcement giữ local/Sapo trong v1.
5. **HUG_ZALO_OA_URL: ✅ chốt + deploy 2026-07-10** — `https://zalo.me/4578048148495215534`, set trong `webhook_receiver/cloudflareD1/wrangler.toml` `[vars]`, Worker live trên `hug.fjp.vn` (Version `5225dc64-c763-47bf-839a-a9d045192e05`, commit `6b049e49`). 5/5 M5 decisions resolved — không còn ops check nào chặn go-live ở mức kiến trúc/config. **Phases P1-P5 (migration, edge landing, issuance writer, redeem matcher, runbook) vẫn ở trạng thái `pending` — chưa implement, chỉ mới xong phần config.**

Nguồn: thảo luận strategy 2026-07-10 (user chốt "theo default đề xuất"); trích xuất câu hỏi từ audit cùng ngày.
