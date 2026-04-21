---
name: domain-knowledge-doc
description: "Write, rewrite, or review domain knowledge documentation that serves both business users and technical teams. Use when explaining how a business concept is modeled in the data system — classification taxonomies, revenue definitions, channel groupings, metric calculations, reporting conventions, or any topic where business meaning and technical implementation must be aligned. Trigger on requests like: 'document how channels are classified', 'explain revenue calculation', 'write a guide for report creators', 'standardize terminology across teams', or 'make this technical doc accessible to business users'."
---

# Domain Knowledge Documentation

Create documentation that **corrects the reader's mental model** — not just explains concepts, but identifies where the reader's intuition is likely wrong and fixes it before they create a wrong report.

Read bundled resources before drafting:

- Read [`references/principles.md`](references/principles.md) — core quality principles, non-negotiable.
- Read [`references/worked-example.md`](references/worked-example.md) — concrete anchor for what "good" looks like.
- Read [`references/anti-patterns.md`](references/anti-patterns.md) — concrete mistakes to avoid.
- Read [`references/stress-tests.md`](references/stress-tests.md) — scenarios to validate the doc works.
- Read [`references/consistency-checklist.md`](references/consistency-checklist.md) before finalizing.
- Reuse [`assets/template.md`](assets/template.md) as scaffold unless the user asks for a different format.

## Core Insight

Domain knowledge docs fail not because they're inaccurate, but because they don't address **where the reader's existing mental model diverges from reality.**

When a business user asks "doanh thu Ecommerce bao nhiêu?", they already have a mental model of what "Ecommerce" means. The doc's job is not just to define Ecommerce — it's to **show where their model is wrong** (e.g., "Ecommerce includes Social Commerce and Website, not just marketplaces").

This means every section serves one of three purposes:

1. **Build** — give the reader a correct mental model from scratch
2. **Correct** — identify where their intuition is likely wrong and fix it
3. **Equip** — give them the tools (tables, column names, filters) to act on the correct model

## Core Objective

Turn fragmented domain knowledge into one document that:

1. Builds the **minimal correct mental model** a reader needs
2. Identifies the **domain tensions** — places where the same word means different things
3. **Corrects misunderstandings** before they cause wrong reports
4. **Equips readers** with lookup tables and column mappings to act immediately
5. Separates **confirmed reality** from **proposals and open questions**
6. Serves **both audiences** (business + technical) without mixing their needs

## Dual-Audience Design

| Audience | Needs | Reads |
|---|---|---|
| **Business users** (report creators, managers) | Correct mental model → create correct reports | Part A: Business Guide |
| **Technical team** (data engineers, analysts) | Maintain data models, add new sources, debug quality | Part B: Technical Reference |

**Rule:** Part A must be self-contained — a business user should never need to read Part B.

## Domain Tension Analysis

Before drafting, identify **domain tensions** — places where the same word or concept carries different meaning depending on context. These are the root cause of wrong reports.

How to find them:

1. List every key term in the domain (e.g., "discount", "doanh thu", "kênh", "Fine Japan")
2. For each term, ask: "Does this mean the same thing in every context?"
3. If not, you've found a tension. Document both meanings and when each applies.

Example tensions:

| Term | Context A | Context B | Harm if confused |
|---|---|---|---|
| "discount" | Shopee: promotion (giảm giá KM) | Đại Lý: wholesale pricing (giá sỉ) | Discount analysis mixes promotion with wholesale pricing, all averages meaningless |
| "Fine Japan" | Product brand (ai sản xuất) | Channel brand (shop nào bán) | Revenue report off by 30%+ depending on interpretation |
| "doanh thu" | Most channels: net revenue thật | US channel: 0đ (cross-border fulfillment) | Total revenue inflated by 500 tỷ |

**Rule:** Every domain tension found MUST appear in the Common Misunderstandings section. The most damaging tension gets its own dedicated section with full explanation.

## Evidence Model

Categorize every piece of information:

- **Confirmed fact** — verified by business stakeholders. Mark as `ĐÃ XÁC NHẬN (date)`.
- **Current implementation** — how the system works today. State directly (no marker).
- **Proposal** — suggested but not yet confirmed. Mark as `ĐỀ XUẤT`.
- **Open question** — needs business input. Mark as `CẦN XÁC NHẬN`.
- **Historical** — was true before, changed. Mark as `TRƯỚC ĐÂY: ... → HIỆN TẠI: ...`.

**Rule:** Never present a proposal as a confirmed fact. Never flatten contradictions — name them.

## Source Reading Order

1. Existing documentation if rewriting
2. Seed files, configuration, or reference data (the "source of truth")
3. SQL models / transformation logic that implements the concept
4. Existing reports or dashboards that consume this concept
5. Stakeholder conversations, decision logs, or meeting notes
6. Related documentation (other domain docs that reference this concept)

## Output Contract

### Part A: Business Guide
1. **Purpose & TL;DR** — what this doc answers (3-6 questions), minimal correct mental model in 5-8 bullets
2. **Quick Reference Table** — "I want to see X → group by Y" lookup table
3. **Core Concepts** — each concept explained with focus on where intuition breaks
4. **Highest-Impact Tension** — the most confusing concept gets its own section (identify by: which confusion causes the largest financial error in reports?)
5. **Common Misunderstandings** — minimum 3 pairs, each with operational consequence
6. **Practical Examples** — real scenarios combining multiple concepts
7. **Cheat Sheet** — one-screen summary: business term → SQL column → values

### Part B: Technical Reference
8. **Architecture Overview** — data model diagram (Mermaid)
9. **Reference Data** — seed files, schemas, value mappings
10. **Model Logic** — how dimensions/facts are built, derivation rules
11. **Operations** — procedures organized by trigger ("khi X xảy ra, làm Y")
12. **Data Quality Notes** — risks, detection, remediation

### Closing
13. **Decision Log** — key decisions with status, date, confirmer
14. **Open Questions** — unresolved items needing business input
15. **Conclusion** — one quoted sentence (under 200 characters)

## Identifying the Highest-Impact Tension

To decide which concept deserves its own dedicated section:

1. **Financial impact test:** If someone confuses concept A with concept B, how much money does the report get wrong? (e.g., Product Brand vs Channel Brand → 30%+ error)
2. **Frequency test:** How often do people actually make this mistake? (ask stakeholders)
3. **Recoverability test:** Can the reader recover from the mistake without help, or do they need the doc to explain it?

The concept that scores highest on all three gets a dedicated section with:
- Clear definitions for both sides
- Visual showing the difference (tree, table, or diagram)
- Disambiguation table (common question → which interpretation → which filter)

## Writing Rules

### Tables for Scanning, Prose for Understanding
- **Lookup/comparison** → table
- **Why something works a certain way** → prose
- **Never** use prose to list what a table can show more clearly

### Diagrams
Include Mermaid where they show what tables cannot:
- **Hierarchy** (classification tiers)
- **Data model** (entity relationships)
- **Decision flow** (how a value is derived)

Don't add diagrams that repeat tables with less clarity.

### Terminology Consistency
- Define each term once, map to one technical column name
- No unmarked synonyms — if multiple words exist, state the mapping once, then pick one
- Provide mapping table: business term → SQL column → example values

### Reading Paths

Design the document for multiple entry points, not just linear reading:

| Reader type | Entry point | What they skip |
|---|---|---|
| "Quick answer" | Quick Reference Table (section 2) | Everything else |
| "New employee" | Purpose → TL;DR → Core Concepts → Examples | Part B |
| "Debugging a report" | Misunderstandings → Cheat Sheet | Concept explanations |
| "Adding new source" | Part B: Operations | Part A entirely |

**Test:** For each reader type, trace their path through the doc. Can they find their answer without reading sections they don't need?

### Compression Priorities
When too large, cut in order (last = cut first):
1. Keep: concept definitions, tension sections, misunderstandings
2. Keep: quick reference, practical examples, cheat sheet
3. Trim: verbose explanations where a table suffices
4. Trim: edge cases < 1% of data
5. Cut: implementation history (move to decision log)

## Rewrite Mode

When rewriting an existing document:

1. **Identify domain tensions first** — read the existing doc looking for same-word-different-meaning
2. Preserve all data, numbers, confirmed facts
3. Restructure for dual-audience (Part A / Part B) if not already split
4. Add Purpose & TL;DR if missing
5. Add Common Misunderstandings if missing
6. Give the highest-impact tension its own section
7. Replace ASCII diagrams with Mermaid where it improves clarity
8. Normalize terminology across sections
9. Add evidence markers (ĐÃ XÁC NHẬN, ĐỀ XUẤT, CẦN XÁC NHẬN)
10. Move unresolved items to Decision Log / Open Questions

## Final Check

Before finishing:

- [ ] Run stress tests from [`references/stress-tests.md`](references/stress-tests.md)
- [ ] Can a business user read Part A and create a correct report in under 5 minutes?
- [ ] Can a data engineer use Part B to add a new source without asking anyone?
- [ ] Are all domain tensions identified and visible in Misunderstandings?
- [ ] Does the highest-impact tension have its own section?
- [ ] Are confirmed facts and proposals clearly distinguished?
- [ ] Do diagrams and tables tell the same story?
- [ ] Compare against `references/worked-example.md` section-by-section.
- [ ] Verify no trap from `references/anti-patterns.md`.
