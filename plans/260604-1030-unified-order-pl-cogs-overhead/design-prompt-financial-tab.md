# Design Prompt — Redesign Order detail "Financial" tab (main-section)

> Paste this as the brief for a Claude design pass. **Scope = the Financial tab MAIN-SECTION of the ORDER detail page only.** Visual target = the right column of the mockup `plans/260604-1030-unified-order-pl-cogs-overhead/mockups/financial-tab-current-vs-proposed.html`.

## 0. Goal
Reorganize the Order → Financial tab so a non-finance user can answer, at a glance and with trust: **"Did this order make money, how much, where did the money go, and can I trust the numbers?"** — professional, calm, decision-oriented, good UX. Enhance the existing screen; do NOT rebuild from scratch.

## 1. Scope (hard boundaries)
- **EDIT ONLY:** `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` and `_cost_ledger.html`; ADD a small composition-bar block + a collapsed COGS-reconciliation block (new partials or inline). Update CSS in the app's stylesheet for any new components.
- **DO NOT touch:** the sidebar money-headline (`order_detail.html` aside), the tab mechanism/routes, other tabs, domain models, application services, or any SQL/adapter. (Backend fields are provided by the plan's phases 02–06; this is a presentation pass.)
- **Out of scope (separate companion change):** per-line COGS + margin columns belong on the **Items tab** (`_line_items.html`), NOT in Financial. Mention only.
- **Tech:** FastAPI + Jinja2 + HTMX, hexagonal. The tab renders as an HTMX partial. Keep it light.

## 2. Reuse the design system (do NOT invent new visual language)
- Reuse macros (FREEZE CONTRACT — names/signatures fixed): `waterfall_row(op, label, amount, total, result, neg, pct_val)`, `panel_head(title, source, right)`, `badge(label, tone, dot, kind)`, `caveat(label, severity, rule)`, `kpi_stat`. New rows = more `waterfall_row` calls.
- Tones: `neutral | good | warn | bad | accent`. Filters: `|vnd`, `|pct`, `|dt`, `|dateonly`. The new screen must feel like the same app.
- Color is NEVER the only signal — always a text label (accessibility).

## 3. Layout — zones, top → bottom (match mockup right column)

**Zone 1 — Verdict bar** (keep existing pattern):
- Word (Lãi/Lỗ/Chưa xác định) + dot, plain-VN sentence, right figs: **Channel net profit (the hero/decision number)** + its margin% + "· gộp {gross_margin}".
- ADD a **COGS source badge** next to the verdict word: `Sapo-MAC` (good) / `MISA` / `both` / `No COGS` (warn). This REPLACES the noisy "Margin unverified" logic — show the warn only when `cogs_source == 'none'`.
- ADD a muted **fully-loaded footnote** below (conditional, only when overhead allocated): "ⓘ Sau phân bổ chi phí vận hành (ước tính): Fully-loaded net profit +{x} · {pct}". It is a quiet REPORT figure, NOT a competing tier.

**Zone 2 — Composition bar** (NEW, "trình bày đẹp"):
- A single horizontal 100% stacked bar of **Net Revenue** split into: COGS / Promo / Platform fees / Overhead / **Profit (fully-loaded)**. Segment colors distinct + a small legend with VN labels. Pure visual "where the money goes." Conditional segments (skip zero). Place between Verdict and Waterfall.

**Zone 3 — P&L Waterfall** (keep current structure + VAT bridge intact; EN labels; % column BEFORE amount):
1. `Gross Revenue` `[gồm VAT]`
2. − `Discount` `[bundle]`
3. = `Total Collected` `[gồm VAT]` (total)
4. − `Tax Amount` `[VAT nhúng trong giá]` (neg)
5. = `Net Revenue` `[trừ VAT]` (total)
6. − `COGS` + **source badge** (pct = cogs/net)
7. = `Gross Profit` (result, pct = gross_margin_pct) ◄ tier 1
8. − `Promo goods cost` **(only render if > 0)**
9. − `Platform fees` `[{platform}]` `[▸ chi tiết]` (pct)
10. = **`Channel net profit`** (result, **visually emphasized = decision tier**, pct) ◄ END of main waterfall (same as today)
- THEN, below the table, two muted "report" lines (conditional, only when overhead exists): `＋ Allocated overhead [ước tính]  −{x}` and `= Fully-loaded net profit [để báo cáo]  +{x}  {pct}`.
- Keep the **US CrossBorder variant** (swap revenue block to `us_revenue_excl/incl_vat`) and the **returns reference note**.

**Zone 4 — Cost breakdown** (KEEP the grouped traceable ledger — its strength is provenance):
- Groups by `cost_category` with subtotal, collapsible; each row: `cost_type · source_system · source_record · fee_source (actual/estimated badge) · amount`.
- ADD two categories + tones: `PROMO_GOODS` (accent), `OVERHEAD` (accent; show `(allocated)` + `estimated` badge). Keep COGS/PLATFORM_FEE/TAX/SHIPPING/DISCOUNT.

**Zone 5 — COGS reconciliation** (NEW, COLLAPSED by default, advanced/audit):
- One expandable line: `Sapo-MAC {x} vs MISA-632 {y} · variance {±z} ({±pct})`. Conditional: render only when both sources exist (`cogs_source == 'both'`). Minimal — do not make it prominent.

## 4. Labels (EN) + tooltips (VN name + definition) — align with `docs/analytics-handbook/guides/revenue_terminology.md`
Every P&L line label is **English**; attach a tooltip (hover + focus/keyboard, `aria-describedby`/`title`) showing **Vietnamese name — short definition**:

| EN label | VN name | Tooltip definition |
|---|---|---|
| Gross Revenue | Doanh thu gộp | Giá bán × SL, trước chiết khấu, **đã gồm VAT**. |
| Discount | Chiết khấu | Coupon, khuyến mãi, combo, giảm giá nhân viên… |
| Total Collected | Tổng thu từ khách | Số tiền khách thực trả (= $.total), **VAT đã nhúng**. |
| Tax Amount | VAT nhúng trong giá bán | Sapo tính sẵn 8/108 hoặc 10/110; 0 cho xuất khẩu/không chịu thuế. |
| Net Revenue | Doanh thu thuần | Sau chiết khấu, **đã trừ VAT** — con số P&L. |
| COGS | Giá vốn hàng bán | Giá vốn hàng đã bán (Sapo-MAC bình quân gia quyền lúc xuất; đối chiếu MISA TK632). Cơ sở không-VAT. |
| Gross Profit | Lãi gộp | Net Revenue − COGS. |
| Promo goods cost | Chi phí hàng tặng | Giá vốn hàng KM/biếu tặng (doanh thu = 0) — chi phí marketing, **không phải** COGS hàng bán. |
| Platform fees | Phí sàn | Phí sàn TMĐT (Shopee: hạ tầng, voucher Xtra, phí xử lý giao dịch…). |
| Channel net profit | Lãi đóng góp (theo kênh) | Lãi gộp − chi phí trực tiếp (phí sàn, chiết khấu shop). **Số để ra quyết định** nhận/đẩy đơn — chưa trừ bộ máy. |
| Allocated overhead | Chi phí vận hành phân bổ | Chi phí quản lý DN (TK642/635/641-chung) phân bổ xuống đơn; ước tính trong tháng, true-up sau khi MISA chốt sổ. |
| Fully-loaded net profit | Lãi ròng đầy đủ | Lãi đóng góp − chi phí vận hành phân bổ. **Để báo cáo**, KHÔNG dùng để quyết định nhận/từ chối đơn. |

COGS source badge tooltips: `Sapo-MAC` = giá vốn từ tồn kho Sapo (phủ ~100% đơn đã giao); `MISA` = giá vốn kế toán TK632; `both` = có cả hai (đối chiếu được); `none` = chưa có giá vốn → margin chưa xác định.

## 5. UX principles (embed these)
1. **Decision-first:** Channel net profit (lãi đóng góp) is the hero; fully-loaded is a muted footnote/report line — never let it compete (avoid the "đơn lỗ-sau-phân-bổ nên bỏ" trap).
2. **Progressive disclosure:** verdict → composition bar → waterfall → cost breakdown → reconciliation (collapsed). Advanced/audit content collapsed.
3. **Plain-language + exact numbers** together (VN verdict sentence + precise figures).
4. **Confidence, never hide uncertainty:** COGS source badge; `estimated` badge for overhead; "unverified" only when `cogs_source == 'none'`.
5. **Domain-faithful (VAT-inclusive):** keep the full VAT bridge visible; all margins on net (VAT-excluded) basis.
6. **Traceability:** keep every cost row traceable to source + actual/estimated.
7. **Visual discipline:** costs red/−, profit green/+, subtotals bold, **decision tier emphasized, fully-loaded/recon muted**; calm palette (no alarm-everywhere). Numbers right-aligned, tabular, **% before amount**, aligned across rows.
8. **Conditional rendering / graceful degradation:** render only zones/rows with data (promo only if >0; overhead/fully-loaded only when allocated; recon only when both sources; US variant for US orders). No zero clutter. When new fields are null (backend phases pending), the screen must degrade to today's behavior (verdict + VAT-bridge waterfall ending at channel net + cost ledger).
9. **Consistency & scope:** reuse macros/tokens; change only the main-section; respect hexagonal boundaries; accessible (text+color, focusable tooltips, contrast).

## 6. Data fields rendered (domain `order.financial` / `order.cost_ledger`)
Existing: gross_revenue, discount_amount, total_collected, vat_amount, net_revenue, cogs_amount, gross_profit, gross_margin_pct, channel_net_profit, channel_net_margin_pct, shopee_platform_fees (+ shopee_infra_fee/voucher_xtra/taxes/settlement), has_cogs/has_platform_fees/has_returns, return_amount, US fields, cost_ledger rows.
New (phases 02–06; render conditionally, may be null now): `cogs_source`, `promo_goods_cost`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, COGS-recon (`sapo_mac_cogs`, `misa_cogs_632`, `cogs_variance`, `cogs_variance_pct`), new cost_category rows (PROMO_GOODS, OVERHEAD).

## 7. Acceptance
- Matches the mockup's right column in structure & feel; reuses existing macros (no new macro names).
- VAT bridge intact; EN labels + working VN tooltips; % before amount; decision tier emphasized; fully-loaded muted.
- All new bits conditional → page renders correctly TODAY with only current fields (degrades gracefully) and lights up new zones when backend data lands.
- Only the Financial main-section changed; sidebar/tabs/other untouched. Renders correctly in the detailView Docker service.

## 8. References
- Visual target: `mockups/financial-tab-current-vs-proposed.html` (right column).
- Terminology: `docs/analytics-handbook/guides/revenue_terminology.md` (NOTE: its §4 lists COGS/Gross Profit as "not available" — now outdated; update separately).
- Data model & rationale: `docs/architecture/order-pl/` (cogs-reconciliation-design, overhead-cost-allocation-design, order-pl-schema-design) + plan `phase-06-detailview-pl.md`.
- Current code: `_financial.html`, `_cost_ledger.html`, `macros.html`.
- **Coordination:** detailView is being edited by a concurrent stream → do this AFTER that work merges (phase-06 gate).
