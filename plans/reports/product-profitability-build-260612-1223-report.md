# Product Profitability & Cost [Cross] — Build Report

**Date:** 2026-06-12

## Blueprint

`docs/analytics-handbook/blueprints/product_profitability_cost.md`

## Dashboard

- **ID:** 108
- **URL:** https://bi.lan.fwg.vn/dashboard/108
- **Name:** Product Profitability & Cost [Cross]
- **collection_id:** 100 (`Merchandising & Product` — confirmed)
- **Tabs:** Margin Ranking · Cost & Variance
- **Total cards deployed:** 30 (17 questions + 13 text/heading cards)

## What Was Merged / Deduped

| From | Cards taken |
|------|-------------|
| **#36 product_profitability.md** | Chu ky bao cao scalar · Top Products by Profit (bar) · Bottom Margin Products (bar) · SKU Margin by Channel (grouped bar) · Product Detail Table · hero scalars (highest/lowest margin product) |
| **#76 finance_product_cost_margin.md** | COGS Variance Alert Count scalar · COGS Variance Alert Table · Top 50 SKU Detail Table (with COGS variance %) · SKU Margin vs Revenue Scatter · Margin Distribution Histogram |

**Deduped (single copy kept):**
- `Chu ky bao cao` — both sources had identical SQL; one per tab (required for tab-scoped display)
- `Avg Margin %` scalar — both sources had identical SQL; one per tab
- `Total SKUs` scalar — #36 used `product_name`, #76 used `product_code`; unified to `product_code` (more precise) as "Tong SKU" in Tab 2; Tab 1 uses "SKU co COGS" label

**Coverage note card** added to Tab 1 explaining ~42 COGS-mapped SKUs out of total.

## Deploy Tail (key lines)

```
✅ Collection 'Merchandising & Product' exists (ID: 100)
✅ Created Dashboard 'Product Profitability & Cost [Cross]' (ID: 108)
✅ Synced cards. Dashboard now has 30 cards.
⚠️  'SKU Margin vs Revenue Scatter': dashboard filter date_range not matched
    (expected — scatter uses hardcoded 30-day window, no {{date_range}} tag)
🚀 Deployment Complete.
```

## Verification

| Check | Result |
|-------|--------|
| collection_id | 100 ✅ |
| Tabs | Margin Ranking, Cost & Variance ✅ |
| Total SKUs with COGS (card 2330) | 186 rows ✅ |
| Avg Margin % (card 2331) | 43.7% ✅ |
| COGS Variance Alert Count (card 2341) | 0 (no spikes in current window) ✅ |
| Top Products by Profit (card 2335) | 20 rows, top profit = 4,200,475,517 VND ✅ |

No query errors on any tested card.

---

**Status:** DONE
**Summary:** New dashboard #108 deployed to collection 100 merging #36 (margin ranking, cross-channel) and #76 (COGS variance, scatter, distribution). 30 cards across 2 tabs. Old #36 and #76 untouched.
**Concerns:** Scatter card (SKU Margin vs Revenue) uses a hardcoded `current_date - 30 days` window — the `date_range` filter does not apply to it by design (inherited from source #76). Expected behavior, documented in deploy warning.
