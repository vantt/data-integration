# Core Principles

These principles are non-negotiable for every domain knowledge document.

## 1. Mental Model Correction (Not Just Explanation)

The document's job is not to explain concepts — it's to **correct the reader's existing mental model** where it diverges from reality.

Every reader arrives with assumptions. A business user hearing "Ecommerce" thinks "Shopee + Lazada." The doc must show them it also includes Social Commerce and Website — not as trivia, but because missing those means their report is 25% short.

**How to apply:**
- For each concept, ask: "What does the reader probably assume? Where is that assumption wrong?"
- Lead with the correction, not the definition. "Ecommerce bao gồm cả MXH và Website, không chỉ sàn TMDT" is better than "Ecommerce là tất cả kênh online."
- If the reader's intuition is correct, don't over-explain — a table row suffices.

## 2. Domain Tension Mapping

**Domain tension** = same word or concept carries different meaning depending on context. This is the #1 root cause of wrong reports.

Before drafting, scan for tensions:

| Pattern | Example | Harm |
|---|---|---|
| Same word, different meaning | "discount" = promotion (Shopee) vs wholesale pricing (Đại Lý) | Discount analysis mixes incomparable numbers |
| Same entity, dual identity | "Fine Japan" = product brand AND channel brand | Revenue off 30%+ depending on interpretation |
| Looks like revenue, isn't | US channel gross = 514 tỷ but real = 0đ | Total revenue inflated by half a trillion |
| Looks internal, isn't | Telesale/CS look like internal ops but are real sales | Missing 0.2% revenue + wrong channel classification |

**Rule:** Every tension found MUST appear in Common Misunderstandings. The most damaging tension gets its own dedicated section.

**How to identify the most damaging tension:** Which confusion, if uncorrected, causes the largest financial error? That one gets a full section.

## 3. Purpose-First Opening

Every document opens with:
- "Tài liệu này trả lời những câu hỏi nào?" — list 3-6 concrete questions
- TL;DR — 5-8 bullets capturing the **minimal correct mental model**

The TL;DR is not a summary of what's in the doc. It's the smallest set of facts a reader needs to avoid the most common mistakes.

**Why:** Readers self-route. A business user who sees their question listed reads on. One who doesn't asks for a different doc instead of misinterpreting this one.

## 4. Evidence Model

Categorize every claim:

| Marker | Meaning | Example |
|---|---|---|
| *(no marker)* | Current implementation, directly observable | "Ecommerce bao gồm Marketplace, Social, Web" |
| **ĐÃ XÁC NHẬN (date)** | Confirmed by business stakeholder | "US = cross-border fulfillment (2026-04-13)" |
| **ĐỀ XUẤT** | Proposed, not yet confirmed | "Thêm order_nature dimension" |
| **CẦN XÁC NHẬN** | Needs business input | "Discount 50% Zalo/FB: giá sỉ hay promotion?" |
| **TRƯỚC ĐÂY → HIỆN TẠI** | Changed — old readers need to know | "Telesale: Internal → Offline/Direct Sales (2026-04-13)" |

**Why:** Without markers, readers can't tell what's decided vs under discussion. The TRƯỚC ĐÂY marker prevents distrust from people who learned the old classification.

## 5. Dual-Audience Layer Separation

Split the document into:
- **Part A: Business Guide** — concepts, quick reference, examples. No SQL, no file paths.
- **Part B: Technical Reference** — data model, seed files, derivation logic, operations.

**Rule:** Part A must be self-contained. A report creator should never need Part B.

**Why:** Business users stop reading when they hit SQL. Data engineers skip concept prose. Mixing audiences means neither reads efficiently.

## 6. Tables for Scanning, Prose for Understanding

- **Lookup/comparison** → table
- **Explanation of *why*** → prose
- **Never** use prose to enumerate what a table shows more clearly

**Why:** Business users scan. 10 seconds to find an answer, not 3 paragraphs.

## 7. Common Misunderstandings (Minimum 3)

Format per entry:
```
**"Concept A ≠ Concept B"** — Difference. Operational consequence if confused.
```

Every domain tension from Principle 2 must appear here. Additional misunderstandings from stakeholder experience are welcome.

**Why:** The most damaging gaps aren't missing information — they're correct information that readers misinterpret.

## 8. Reading Paths

Design for multiple entry points, not just linear reading:

| Reader | Enters at | Skips |
|---|---|---|
| Quick answer | Quick Reference Table | Everything else |
| New employee | TL;DR → Concepts → Examples | Part B |
| Debugging wrong report | Misunderstandings → Cheat Sheet | Concept prose |
| Adding new data source | Part B: Operations | Part A |

**Why:** A doc that only works top-to-bottom fails 3 of 4 reader types. Design sections to be independently useful.

## 9. Diagrams That Add Insight

Include Mermaid only when it shows what tables cannot:
- Hierarchies (classification tiers — tree structure)
- Entity relationships (how tables connect)
- Decision flows (how a value is derived)

**Anti-pattern:** A diagram that repeats a table with less precision is decoration. Remove it.

## 10. Terminology Consistency

- Define each business term once, map to one technical column name
- No unmarked synonyms
- Provide mapping table: business term → SQL column → example values

**Why:** The root cause of conflicting reports is different people using different words for the same concept, or the same word for different concepts. (This overlaps with Domain Tension — terminology consistency is the solution, domain tension mapping is the diagnostic.)

## 11. One-Sentence Conclusion

End with a single quoted sentence (under 200 characters) that captures the most important mental model shift this document teaches.

Not a summary. Not a recap. The one thing a reader should remember if they forget everything else.
