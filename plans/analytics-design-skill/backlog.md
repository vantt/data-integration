# Analytics Design Skill — Backlog

> Tong hop tu: `deferred-open-items.md`, `deferred-260403-open-items.md`, `deferred-4.3-blueprint-design-spec-ref.md`
> Cap nhat: 2026-04-03

---

## Group 1: Fixes (nho, cu the, co the lam ngay)

### Fix 1 — CEO Weekly Pulse: archetype violation

**Van de:** Dashboard labeled `Executive Pulse` nhung co cau truc Operational Cockpit — 3 views, detail tables, ~26 cards. Vi pham rule Executive Pulse: single view, no tables, max 10 cards.

**Impact:** Agents hoc tu exemplar sai → dashboards "pulse" bam dan thanh cockpit, mat narrative discipline.

**Options:**
- A) Re-label thanh `Operational Cockpit` → update design spec + blueprint + playbook
- B) Re-design lai thanh dung Executive Pulse: 1 view, no tables, max 10 cards
- C) Tach thanh 2 artifact: `ceo_weekly_pulse` (true Pulse) + `ceo_weekly_review` (Cockpit)

**Files lien quan:**
- `docs/analytics-handbook/designs/ceo_weekly_pulse.md`
- `docs/analytics-handbook/blueprints/ceo_weekly_pulse.md`
- `docs/analytics-handbook/playbooks/ceo_weekly_pulse.md`

---

### Fix 2 — Blueprint → Design Spec reference con thieu

**Van de:** 15/17 blueprints khong co link tro ve design spec tuong ung. Khi design spec update, khong biet blueprint da outdated.

**Hien trang (2026-04-03):** Chi co 2/17 blueprints co Design Spec header (`customer_retention_dashboard.md`, `customer_intelligence_monthly.md`).

**Giai phap:** Option A — them convention header vao tung blueprint:
```
> **Design Spec:** `designs/<name>.md`
```

**Files can sua:**
- `.skills/metabase-automation/templates/blueprint_template.md` — them vi du header
- 15 blueprint files con lai trong `docs/analytics-handbook/blueprints/`

**Priority:** Low — hygiene, khong anh huong deploy hay design quality.

---

## Group 2: Large Improvements (can plan rieng, effort cao)

### P2 — Executive-Grade Visual System

**Status:** Planned, not started

**Goal:** Nang thi giac dashboard len cap "intentionally designed" — khong chi "tidy". Tao repeatable visual quality standards.

**Plan chi tiet:** `plans/analytics-design-skill/plan-p2-executive-grade-visual-system.md`

**Estimated effort:** 1-2 weeks
