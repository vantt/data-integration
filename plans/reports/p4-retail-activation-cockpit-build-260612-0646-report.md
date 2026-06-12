# Retail Activation Cockpit — Build Report

**Date:** 2026-06-12 · **Dashboard ID:** 102 · **Collection:** Marketing & Customers (ID 52)
**URL:** https://bi.lan.fwg.vn/dashboard/102

---

## Design Summary

3-tab Operational Cockpit for Marketing/CSKH. Marries contribution margin × activation signals × retention-by-channel.

### Tab A — Activation Now
Call list for this week. Cards: contactable OVERDUE/DUE_SOON scalar, LTV at Stake, Value at Stake; full action queue table (priority-sorted, margin-negative rows highlighted red); SILVER/GOLD/VIP At-Risk/Churned reactivation mine. Filters: action_type, value_group (CategoryDrop, field_ids 773 + 758).

### Tab B — Channel × Retention × Margin
Shopee-negative story. Cards: horizontal bar of channel net margin % (bottom → top), horizontal bar of repeat rate by channel, combined table (channel × order_share × repeat% × margin% × net profit). Conditional formatting: margin < 0 = red, ≥ 20% = green; repeat < 15% = red, ≥ 30% = green.

### Tab C — Discount-Dependency × Margin
Offer-redesign signal. Cards: discount sensitivity donut (PROMO_DEPENDENT dominates), avg contribution margin by sensitivity (horizontal bar), 3 scalars (discount% of gross, margin-negative customer count, PROMO_DEPENDENT count), full sensitivity × tier × margin detail table.

**Freshness/trust note:** present on each tab as text card (source, scope, caveats).

---

## Artifacts Created

- Design spec: `docs/analytics-handbook/designs/retail_activation_cockpit.md`
- Blueprint: `docs/analytics-handbook/blueprints/retail_activation_cockpit.md`

---

## Deploy Output (tail)

```
✅ Created Dashboard 'Retail Activation Cockpit [Retail]' (ID: 102)
✅ 14 questions created, 3 "Chu kỳ báo cáo" reused/updated
📝 11 text cards (section headers + 3 Source & Freshness)
✅ Synced cards. Dashboard now has 28 cards.
🚀 Deployment Complete.
```

---

## Post-Deploy Verification

| Check | Result |
|-------|--------|
| Dashboard exists | ✅ ID 102, name correct |
| Tab count | ✅ 3 tabs: Activation Now / Channel × Retention × Margin / Discount-Dependency × Margin |
| Total dashcards | ✅ 28 |
| Tab A — Contactable OVERDUE/DUE_SOON count | **13** customers |
| Tab B — Bottom channel margins | Shopee-JPC 12.7%, Shopee-thehealthyus 14.2%, Shopee-FJV 27.3% — all Shopee lowest |
| Tab C — PROMO_DEPENDENT discount % of gross | **55.4%** (matches verified anchor from analysis) |

---

## Notes / Caveats

1. **channel_net_margin vs fully_loaded_margin:** Blueprint uses `channel_net_margin_pct` (not `fully_loaded`) for Tab B. Fully-loaded penalizes large orders via overhead allocation — channel_net is more stable for channel comparison. Shopee is still bottom-3 on channel_net.
2. **has_cogs ~65% coverage:** Tab B queries filter `has_cogs=true`. Coverage note added to Source & Freshness card.
3. **Tab B channel margin values show positive for all Shopee** (12–27% channel_net, not negative). The originally-reported negative values (-18% to -47%) were `fully_loaded_margin_pct`. The dashboard uses `channel_net_margin_pct` which is less punishing but still shows Shopee at the bottom. Switching to `fully_loaded_margin_pct` in the horizontal bar would show Shopee negative — can do if that stronger framing is preferred.
4. **discount_sensitivity NULL for ~78% of base** (single-purchase customers have no purchase pattern). Added to Tab C Source & Freshness. PROMO_MIXED is 1 customer only — noted in freshness card.
5. **Pre-deploy warning** (non-blocking): Tab C SQL uses `customer_type='RETAIL'` on `dim_customers` directly (not via fact_orders, which is correct for a customer-grain dim query). Warning is a false positive for dim-table queries.

---

## Unresolved Questions

1. Overhead allocation key for VIP/GOLD? — if fixed, `fully_loaded_margin_pct` may be usable for tier-level margin. Currently caveat #3 in Tab B.
2. Prefer `fully_loaded_margin_pct` in Tab B bar chart to show Shopee as negative? Requires 1-field change in blueprint.
3. is_contactable filter not added as dashboard-level parameter (no field_id looked up). If user wants to toggle contactable/all from dashboard level, need to add field_id for `is_contactable` boolean column (id 1661) and add as a filter.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Dashboard 102 deployed with 3 tabs, 28 cards. All post-deploy queries return expected data. Key story verified: 13 contactable OVERDUE/DUE_SOON, Shopee bottom-of-channel on margin, PROMO_DEPENDENT eating 55.4% of gross.
**Concerns:** Tab B shows Shopee channel_net_margin positive (12–27%) not negative — because `fully_loaded_margin_pct` was used in the original analysis but `channel_net_margin_pct` was chosen for the dashboard as more stable. The Shopee-negative story still holds directionally (bottom of pack) but the dramatic negative numbers (-18% to -47%) only appear with fully_loaded. Recommend confirming which metric to use before sharing with stakeholders.
