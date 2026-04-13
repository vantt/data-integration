# Anti-Patterns

Concrete mistakes that produce low-value domain knowledge docs. Check your draft against each one.

## 1. Starting with the Data Model

**Symptom:** Doc opens with ER diagram, table schemas, or "dim_channels has these columns..."

**Why it's bad:** Business users close the doc. They came to understand a concept, not a schema.

**Fix:** Part A first (concepts, examples). Part B second (schemas, models). Always.

## 2. Mixing Audiences in One Section

**Symptom:** Paragraph explains a business concept, then drops SQL, file paths, or column names mid-sentence.

**Why it's bad:** Business users get lost at SQL. Data engineers skip concept prose. Neither reads efficiently.

**Fix:** Strict Part A / Part B split. Reference Part B from Part A if needed, but never inline technical details.

## 3. Synonyms Without Warning

**Symptom:** "kênh bán hàng", "channel", "nguồn đơn hàng", "source" used interchangeably.

**Why it's bad:** Reader can't tell if these are the same concept or different concepts. This is the #1 cause of conflicting reports.

**Fix:** Define once. Map to one technical name. Use consistently. If synonyms exist in the wild, state the mapping explicitly, then pick one.

## 4. Defining Without Correcting

**Symptom:** "Ecommerce là tất cả kênh bán hàng trực tuyến bao gồm sàn TMDT, mạng xã hội, và website."

**Why it's bad:** Technically correct, but doesn't address the reader's likely assumption that Ecommerce = Shopee + Lazada. The definition passes through their mental model without correcting it.

**Fix:** Lead with the correction: "Ecommerce bao gồm cả MXH (Facebook, Zalo) và Website — không chỉ các sàn TMDT. Nếu chỉ tính sàn, báo cáo thiếu ~25%."

## 5. Flattening Domain Tensions

**Symptom:** "Fine Japan" appears throughout the doc sometimes meaning the product brand, sometimes the channel brand, without acknowledging the ambiguity.

**Why it's bad:** The reader doesn't realize "doanh thu Fine Japan" has two valid interpretations that produce different numbers. They pick one randomly.

**Fix:** Identify the tension explicitly. Give it a dedicated section if it's high-impact. Provide a disambiguation table.

## 6. Proposal Presented as Fact

**Symptom:** "order_nature có 7 giá trị: retail_sale, wholesale..." in present tense, no marker.

**Why it's bad:** Data engineer thinks the column exists, tries to use it, wastes hours debugging. Or skips implementing it because they think it's done.

**Fix:** Mark clearly: **ĐỀ XUẤT** — chưa implement. Separate current reality from desired state.

## 7. Ignoring Historical Changes

**Symptom:** "Telesale thuộc Offline / Direct Sales" stated as if it was always this way.

**Why it's bad:** Anyone who learned the old classification (Telesale = Internal) will distrust the doc — or worse, won't notice the change and continue using the old model.

**Fix:** **TRƯỚC ĐÂY:** Internal → **HIỆN TẠI:** Offline/Direct Sales (ĐÃ XÁC NHẬN 2026-04-13). Make the change visible enough that returning readers notice it.

## 8. Quick Reference That Requires Context

**Symptom:** Quick reference says "Gom nhóm theo Phân loại kênh" without listing what values exist or which SQL column to use.

**Why it's bad:** Quick reference exists so readers DON'T need to read the full doc. If it requires context from earlier sections, it fails its purpose.

**Fix:** Self-contained: business term → SQL column → possible values → example result. Usable by a reader who lands directly on this table.

## 9. Mega-Table Without Hierarchy

**Symptom:** One 30-row flat table listing every channel source, brand, and branch together.

**Why it's bad:** Reader can't see the structure. A taxonomy's value IS its hierarchy — flat tables destroy it.

**Fix:** Show hierarchy first (tree diagram or tiered table). Then provide flat detail table as reference. Two representations serve different needs.

## 10. Operations Without Triggers

**Symptom:** Part B lists seed file schemas and SQL logic but doesn't say "when you add a new shop, do steps 1-2-3."

**Why it's bad:** Engineer knows the schema but not the procedure. They reverse-engineer it, waste time, miss steps.

**Fix:** Organize by trigger: "Khi thêm nguồn mới → steps", "Khi phát hiện vendor mới → steps". Each trigger = numbered procedure.

## 11. Technically Correct But Doesn't Change Behavior

**Symptom:** Doc accurately defines every concept. Reports are still wrong.

**Why it's bad:** This is the most insidious failure. The doc is correct. The reader understood it. But they didn't connect the concept to their actual workflow (opening Metabase, choosing columns, applying filters). Knowledge didn't become action.

**Fix:** Add practical examples that walk through real report creation scenarios. The Cheat Sheet must map business terms to concrete columns. Stress-test with "new employee" and "debugging wrong report" scenarios.

## 12. Conclusion That Summarizes Everything

**Symptom:** Conclusion re-lists all sections in 2-3 sentences each.

**Why it's bad:** Reader already read the doc. They need a take-home message, not a recap.

**Fix:** One quoted sentence, under 200 characters. The single most important mental model shift. Nothing more.
