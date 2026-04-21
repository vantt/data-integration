# Worked Example

Concrete anchor for what "good" looks like — not just rules, but judgment.

## Gold Example

**File:** `docs/context/sales-segmentation-guide.md` (in the data-integration project).

Compare your draft against this document section-by-section.

## What This Example Does Right

### Mental Model Correction, Not Just Definition

The TL;DR doesn't list facts — it builds the **minimal correct mental model**:
- "4 chiều độc lập" corrects the assumption that there's one way to group revenue
- "Hai loại thương hiệu khác nhau" immediately signals the biggest trap
- "Seed files là dữ liệu tham chiếu" tells the data team where truth lives

A reader who only reads the TL;DR already avoids the top 3 mistakes.

### Domain Tension Given Dedicated Section

"Thương hiệu sản phẩm vs Thương hiệu kênh" gets a full section — not because it's complex, but because **confusing them causes the largest financial error** (~30% revenue misattribution).

The section works because it:
1. Defines both sides clearly
2. Shows a concrete tree: JPC shop selling Fine Japan + FG Care products
3. Provides a disambiguation table: 4 common questions → exact filter for each
4. Includes a brand reference table with checkmarks

This is the "highest-impact tension" pattern from the skill applied correctly. The author identified the tension, measured its damage, and gave it proportional space.

### Quick Reference Table as Primary Entry Point

Section 2 is a lookup table: "Tôi muốn xem X → Gom nhóm theo Y"

This single table answers 80% of report creator questions. A business user can screenshot this table and never read the rest of the doc. That's the design intent — not everyone needs the full explanation.

### Dual-Audience Split

- **Part A** (sections 1-7): No SQL, no file paths, pure concepts
- **Part B** (sections 8-13): Schema, seed files, model logic, operations
- Boundary marked explicitly with `PHẦN A` / `PHẦN B` headers

A marketing manager reads Part A. A data engineer reads Part B. Neither wastes time on the other's content.

### Common Misunderstandings With Consequences

5 pairs, each with operational harm:
1. Ecommerce ≠ Marketplace → "báo cáo Ecommerce thiếu 25% nếu chỉ tính sàn"
2. channel_category ≠ channel_format → "filter sai tầng, kết quả sai"
3. channel_brand ≠ brand_name → "nhầm thương hiệu sản phẩm với thương hiệu kênh"
4. Chi nhánh ≠ Kênh → "nhầm nơi xử lý với nơi bán"
5. is_sales_channel=false ≠ doanh thu=0 → "US có gross 514 tỷ nhưng thật = 0đ"

Each pair names the **concrete harm**, not just the conceptual difference.

### Operations Organized by Trigger

Part B doesn't just list schemas — it provides procedures:
- "Khi thêm nguồn đơn hàng mới" → numbered steps
- "Khi phát hiện vendor mới" → numbered steps
- "Khi thay đổi cơ cấu tổ chức" → numbered steps

A data engineer knows exactly what to do when each event happens.

### Business-to-Technical Mapping Table

One table maps every business term to its SQL column name and example values. This is the bridge between Part A and Part B — report creators on Metabase can look up exactly which column to use.

## What This Example Could Improve

- Missing Decision Log table (which classifications were confirmed, by whom, when)
- No explicit TRƯỚC ĐÂY → HIỆN TẠI markers for historical changes (Telesale reclassification is mentioned but not in evidence model format)
- Quick Reference Cheat Sheet could be more compact for screenshotting
- Some Mermaid diagrams use emoji in node labels which may not render in all tools
- Dual-dimension topic (CS/Telesale) is explained inline rather than in a dedicated "Future Considerations" section
- Doesn't explicitly call out reading paths for different reader types

## How to Use This Reference

1. Before drafting, read this file.
2. After drafting, compare section-by-section:
   - Purpose questions listed? TL;DR as minimal correct mental model?
   - Quick reference lookup table as primary entry point?
   - Highest-impact domain tension with dedicated section?
   - Common misunderstandings ≥ 3 with concrete consequences?
   - Part A self-contained without SQL?
   - Business-to-technical mapping table?
   - Operations organized by trigger?
   - One-sentence conclusion?
3. If missing any, add before finalizing.

## Why a Worked Example Matters

Principles describe intent. Anti-patterns describe failure. A worked example shows **judgment** — which tension deserves a full section, how much space a misunderstanding needs, when a table is better than prose, how to phrase a correction without condescending. LLMs without a concrete anchor regress to generic structure even when following all stated rules.
