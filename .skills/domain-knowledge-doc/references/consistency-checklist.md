# Consistency Checklist

Use this before finalizing a domain knowledge document.

## Mental Model & Purpose

- [ ] Opens with "Tài liệu này trả lời những câu hỏi nào?" (3-6 questions)
- [ ] TL;DR builds the **minimal correct mental model** (not a section summary)
- [ ] TL;DR addresses the top 3 assumptions a reader likely has wrong
- [ ] A newcomer reading only the TL;DR avoids the most common mistakes

## Domain Tensions

- [ ] Domain tensions identified (same word, different meaning depending on context)
- [ ] Every tension appears in Common Misunderstandings section
- [ ] The highest-impact tension has its own dedicated section
- [ ] Dedicated section includes: definitions, visual, disambiguation table

## Dual-Audience Structure

- [ ] Part A (Business Guide) is self-contained — no SQL, no file paths
- [ ] Part B (Technical Reference) is operationally useful — not just schema dumps
- [ ] Boundary between Part A and Part B is explicitly marked
- [ ] Business user never needs Part B to create a correct report

## Evidence Discipline

- [ ] Confirmed decisions marked with `ĐÃ XÁC NHẬN (date)`
- [ ] Proposals marked with `ĐỀ XUẤT`
- [ ] Open questions marked with `CẦN XÁC NHẬN`
- [ ] Historical changes marked with `TRƯỚC ĐÂY → HIỆN TẠI`
- [ ] No proposal presented as confirmed fact
- [ ] Contradictions between business understanding and implementation named explicitly

## Terminology

- [ ] Each business term defined once
- [ ] Each term mapped to one technical column name
- [ ] No unmarked synonyms
- [ ] Mapping table present: business term → SQL column → example values

## Quick Reference & Reading Paths

- [ ] Lookup table present ("I want X → group by Y")
- [ ] Cheat sheet is self-contained (usable without reading the full doc)
- [ ] Document supports multiple entry points (quick answer, new employee, debugging, operations)
- [ ] Each reader type can find their answer without reading irrelevant sections

## Common Misunderstandings

- [ ] Contains at least 3 entries
- [ ] Each entry is a pair of concepts that look similar but differ
- [ ] Each entry states the **concrete operational consequence** of confusing them
- [ ] All domain tensions from analysis are represented

## Diagrams & Tables

- [ ] Hierarchies shown as tree diagrams or tiered tables (not flat lists)
- [ ] Data model shown as Mermaid ER or relationship diagram (Part B)
- [ ] No diagram that only repeats a table with less precision
- [ ] Tables for lookup/comparison; prose for explanation

## Technical Reference (Part B)

- [ ] Seed file schemas documented with all columns
- [ ] Derivation logic explained step-by-step
- [ ] Operations organized by trigger ("khi X xảy ra, làm Y")
- [ ] Data quality risks documented with detection and remediation

## Decision Tracking

- [ ] Decision Log table present (decision, status, date, confirmer)
- [ ] Open Questions table separates answered from unanswered

## Conclusion

- [ ] Single quoted sentence, under 200 characters
- [ ] Captures the most important mental model shift (not a section recap)

## Stress Tests (from stress-tests.md)

- [ ] Test 1: New Employee — can find answer using only Part A
- [ ] Test 2: Ambiguous Question — recognizes ambiguity, finds both interpretations
- [ ] Test 3: Cross-Department Disagreement — can diagnose why numbers differ
- [ ] Test 4: Edge Case — can identify mixed wholesale/retail as cause of anomaly
- [ ] Test 5: Data Engineer Onboarding — can add new source from Part B alone
- [ ] Test 6: Historical Confusion — returning reader notices what changed
- [ ] Test 7: Proposal Trap — engineer can tell proposal from implementation
