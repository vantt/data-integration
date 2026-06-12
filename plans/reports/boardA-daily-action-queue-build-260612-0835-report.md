# Board Build Report: Daily · Customer Action Queue [Retail]

**Date:** 2026-06-12 · **Author:** general-purpose agent

---

## Blueprint

`docs/analytics-handbook/blueprints/customer_daily_action_queue.md`

---

## Dashboard

- **Name:** Daily · Customer Action Queue [Retail]
- **ID:** 103
- **URL:** https://bi.lan.fwg.vn/dashboard/103
- **Collection:** ID 99 ("👥 Customer", sub-collection under Marketing & Customers)
- **Deploy method:** `node .skills/metabase-automation/scripts/deploy_from_markdown.js`

> Note: deploy script matched collection by name ("Marketing & Customers", ID 52), then dashboard was moved to ID 99 via direct API PUT after deploy. Future redeploys of this blueprint will also land in 52 and need re-moving — recommend updating the `## 📂 Collection:` line in the blueprint to include the sub-collection path when the parser gains that support, or use the manage-metabase-resources skill post-deploy to re-home.

---

## Tab & Card List

### Tab 1 — 🎯 Hành động hôm nay (11 SQL cards + 4 text cards)

| Card | ID | Type |
|---|---|---|
| Chu ky bao cao | 2167 | scalar |
| CALL_NOW — Goi ngay | 2168 | scalar |
| REORDER_NUDGE — Nhac tai mua | 2169 | scalar |
| REORDER_PREEMPT — Nhac truoc | 2225 | scalar |
| WIN_BACK — Lay lai khach | 2170 | scalar |
| SECOND_ORDER — Push don 2 | 2171 | scalar |
| HIGH_CANCEL_RISK — Rui ro huy | 2172 | scalar |
| Contactable — OVERDUE va DUE_SOON | 2241 | scalar |
| LTV at Stake (Contactable) | 2227 | scalar |
| Value at Stake (Contactable) | 2228 | scalar |
| Queue — Danh sach outreach | 2175 | table |

### Tab 2 — 👀 Watchlists (7 SQL cards + 5 text cards)

| Card | ID | Type |
|---|---|---|
| Chu ky bao cao watchlist | 2242 | scalar |
| VIP Customer Watchlist | 1361 | table |
| At-Risk Reactivation Priority | 1362 | table |
| Churned High-Value Customers | 1363 | table |
| High Cancel Rate Customers | 2158 | bar |
| Next Purchase Signal Breakdown | 2156 | table |
| Reactivation Mine — SILVER GOLD VIP | 2243 | table |

**Total dashcards:** 28 (18 SQL + 10 text)

---

## Deploy Output Tail

```
✅ Synced cards. Dashboard now has 28 cards.
🚀 Deployment Complete.
```

Warnings on 6 action-type scalars: "dashboard filter(s) not matched: action_type, is_contactable, next_purchase_signal" — expected; those scalars only use `{{value_group}}` template tag. Other 3 filters (action_type, is_contactable, next_purchase_signal) correctly wire only to cards that declare those template tags.

---

## Post-Deploy Verification

| Check | Result |
|---|---|
| collection_id | 99 ✅ |
| Tab count | 2 ✅ |
| Queue table rows (card 2175) | **116 rows** ✅ |
| Contactable OVERDUE/DUE_SOON count (card 2241) | **13** ✅ |
| Chu ky bao cao scalar (card 2167) | "📅 Queue hôm nay: 12/06/2026 · Cập nhật lúc: 08:38 12/06/2026" ✅ |
| Card errors | None ✅ |

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Blueprint created, deployed, and verified in collection 99 with 2 tabs + 28 cards. All 3 verification queries return valid data; no Binder errors.
**Concerns:** Deploy script resolves collection by name ("Marketing & Customers" → ID 52), not by the `Collection ID: 99` blockquote. Dashboard was manually moved to ID 99 via API after deploy. On every future redeploy the script will move it back to 52 unless the `## 📂 Collection:` header is updated to the nested path (e.g. `Marketing & Customers > 👥 Customer`) once the parser supports emoji-prefixed sub-collections, or a post-deploy move step is scripted.
