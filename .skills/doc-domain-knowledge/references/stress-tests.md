# Stress Tests

Scenarios to validate a domain knowledge document actually works. Run these before finalizing.

## How to Use

For each test, mentally simulate (or actually test with a colleague) whether the document helps the person reach the correct answer. If they can't, the doc has a gap.

---

## Test 1: The New Employee

**Persona:** Marketing manager, joined yesterday. No context about the company's data system.

**Question:** "Ecommerce bán bao nhiêu tháng trước?"

**Pass criteria:**
- [ ] Can find the answer using only Part A (no SQL knowledge needed)
- [ ] Understands that Ecommerce includes Social Commerce and Website, not just marketplaces
- [ ] Knows to filter `is_sales_channel = true` (or understands why Internal/CrossBorder are excluded)
- [ ] Can identify which Metabase column to use from the Cheat Sheet

**Common failure:** Doc defines Ecommerce correctly but doesn't connect it to a concrete column name or filter. Reader creates report using wrong grouping.

---

## Test 2: The Ambiguous Question

**Persona:** CEO asks a question where the same word has multiple meanings.

**Question:** "Doanh thu Fine Japan bao nhiêu?"

**Pass criteria:**
- [ ] Reader immediately recognizes this question is ambiguous (product brand vs channel brand)
- [ ] Can find both interpretations and their correct filters in under 60 seconds
- [ ] Understands the numbers will be different and why

**Common failure:** Doc explains the distinction but doesn't provide a disambiguation table with concrete filters. Reader picks one interpretation randomly.

---

## Test 3: The Cross-Department Disagreement

**Persona:** Two managers from different departments produce different revenue numbers for the same period.

**Scenario:** Marketing says "Ecommerce = 38 tỷ". Sales says "Ecommerce = 45 tỷ". They both think they're right.

**Pass criteria:**
- [ ] Doc makes it possible to diagnose why the numbers differ (one included wholesale customers on Zalo/Facebook, the other didn't; or one included US channel, the other didn't)
- [ ] Common Misunderstandings section covers this specific confusion
- [ ] The report grouping recommendations in the doc prevent this by defining standard filters

**Common failure:** Doc defines concepts correctly but doesn't address what happens when people use different filters. No standard report definitions.

---

## Test 4: The Edge Case

**Persona:** Data analyst investigating an anomaly.

**Scenario:** "Tại sao discount trung bình tháng này tăng từ 30% lên 45%?"

**Pass criteria:**
- [ ] Doc explains that wholesale discount (giá sỉ ~46%) is fundamentally different from promotion discount (~29%)
- [ ] Reader can identify that mixing wholesale and retail in the same analysis is the cause
- [ ] Doc provides the correct filter to separate them

**Common failure:** Doc mentions the distinction between wholesale and retail discount but doesn't connect it to the specific scenario of mixed averages. Reader knows the concept but can't apply it to debug.

---

## Test 5: The Data Engineer Onboarding

**Persona:** New data engineer, first week. Needs to add a new Shopee shop to the system.

**Task:** "Thêm shop 'Shopee - New Brand' vào hệ thống."

**Pass criteria:**
- [ ] Part B Operations section has a step-by-step procedure for this exact task
- [ ] Engineer knows which file to edit, which columns to fill, which values are valid
- [ ] Engineer knows which dbt command to run afterward
- [ ] Engineer can verify the new source appears correctly in dim_channels

**Common failure:** Schema is documented but the procedure isn't. Engineer has to reverse-engineer the process from the schema.

---

## Test 6: The Historical Confusion

**Persona:** Someone who learned the old classification 3 months ago.

**Scenario:** They remember "Telesale = Internal" and create a report excluding Telesale from sales revenue.

**Pass criteria:**
- [ ] Doc explicitly marks the change: "TRƯỚC ĐÂY: Internal → HIỆN TẠI: Offline/Direct Sales (2026-04-13)"
- [ ] The change is visible enough that a returning reader notices it (not buried in a footnote)
- [ ] Evidence model markers make it clear this was a confirmed decision, not a proposal

**Common failure:** Doc shows the current state correctly but doesn't acknowledge the historical change. Returning readers trust their outdated mental model because the doc doesn't signal that something changed.

---

## Test 7: The Proposal Trap

**Persona:** Data engineer reads the doc and sees "order_nature dimension."

**Task:** Implement order_nature in the data model.

**Pass criteria:**
- [ ] Engineer can clearly tell whether order_nature is already implemented or still a proposal
- [ ] If proposal: marked as ĐỀ XUẤT, engineer knows not to implement without confirmation
- [ ] If implemented: engineer can find the derivation logic in Part B

**Common failure:** Doc describes order_nature in present tense ("order_nature có 7 giá trị...") without marking it as ĐỀ XUẤT. Engineer assumes it exists, tries to use it, wastes hours debugging why the column doesn't exist.

---

## Scoring

| Score | Meaning | Action |
|---|---|---|
| 7/7 pass | Doc is operationally excellent | Ship it |
| 5-6/7 pass | Doc has minor gaps | Fix failing tests, re-check |
| 3-4/7 pass | Doc has structural problems | Revisit Part A structure or evidence model |
| < 3/7 pass | Doc needs major rewrite | Start from template, apply principles from scratch |
