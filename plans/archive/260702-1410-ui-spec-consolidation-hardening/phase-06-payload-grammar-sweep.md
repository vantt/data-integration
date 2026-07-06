# Phase 06 — Payload grammar sweep

**Effort:** 45m  
**Blocker:** Phase 02 (VR-PAYLOAD-GRAMMAR warn must exist so validate confirms fixes clear the warns)  
**File ownership:** `crm/docs/ui-spec/components/C04-tag-chips.md` (normalization). C03, C05, C06 reviewed but kept as-is (documented below).

---

## Context

VR-PAYLOAD-GRAMMAR (added Phase 02) warns on bare `$<word>` tokens (no dot) in payload objects. After Phase 02, 8 warns are expected. This phase clears the actionable ones and documents why the rest stay.

Payload grammar convention (defined Phase 03 CONVENTION.md §9):
- `$<entity>.<field>` — data context on screens/panels (e.g. `$party.id`)
- `$event.<field>` — listener event field (e.g. `$event.party_id`)
- `$<prop_name>` — bare component prop variable in `emits` blocks (legitimate)

---

## Bare token inventory (from grep `\"\$[a-z_]+\"` across spec)

| File | Action | Token | Assessment | Fix |
|---|---|---|---|---|
| `C04-tag-chips.md` | A-C04-001 | `$party_id` | Component emits `party.id` of the currently-rendered party — should be `$party.id` (entity field). C04 docs say `tags` prop is an array and the component has `party_id` as implicit context. The payload key is `party_id` with value `"$party_id"`. This matches the entity pattern. | **Fix:** `"$party_id"` → `"$party.id"` |
| `C04-tag-chips.md` | A-C04-002 | `$party_id` | Same reasoning. | **Fix:** `"$party_id"` → `"$party.id"` |
| `C04-tag-chips.md` | A-C04-003 | — | No bare token in A-C04-003 payload (`$tag.id`, `$tag.name` — already dotted). | No change |
| `C03-action-queue-card.md` | A-C03-001, A-C03-002, A-C03-003 | `$party_id` | C03 is used exclusively on S01 (worklist) where each card represents a party. But C03's `hosts: [S01]` (→ after Phase 05: `hosted_by: [S01]`) — only one host. The `$party_id` prop is passed from S01's loop context. Could be `$party.id` but C03 is a list-card component where `party_id` is a scalar prop. Accept as legitimate component prop. | **Keep as-is.** Warn remains informational. |
| `C05-filter-bar.md` | emit | `$current_filter_values` | Filter state blob, no entity mapping. Pure component prop. | **Keep as-is.** |
| `C06-freshness-badge.md` | emit | `$table_name`, `$refreshed_at` | Component props for a generic freshness badge. No entity model applies. | **Keep as-is.** |

**Net result after Phase 06:** 5 warns remain (C03 ×3, C05 ×1, C06 ×2) as accepted-informational. C04 ×2 warns cleared.

---

## Changes

### `crm/docs/ui-spec/components/C04-tag-chips.md`

**Line 41** (A-C04-001 payload):
```yaml
    payload: { party_id: "$party_id" }
```
→
```yaml
    payload: { party_id: "$party.id" }
```

**Line 46** (A-C04-002 payload):
```yaml
    payload: { tag_id: "$tag.id", party_id: "$party_id" }
```
→
```yaml
    payload: { tag_id: "$tag.id", party_id: "$party.id" }
```

No other lines in C04 change.

---

## Suppression documentation for accepted warns

Add to `crm/docs/ui-spec/components/C03-action-queue-card.md`, `C05-filter-bar.md`, `C06-freshness-badge.md` — in the **Props / API** section (prose, not contract block), add a one-liner:

> Note: payload uses bare prop variables (`$party_id`, `$current_filter_values`, etc.) — these are component-level props, not entity field paths. VR-PAYLOAD-GRAMMAR warns are accepted (see CONVENTION.md §9).

This makes the warn intentional and discoverable without modifying the contract block.

---

## Implementation steps

1. Edit `C04-tag-chips.md`: apply 2 payload token fixes (lines 41 and 46).
2. Edit `C03-action-queue-card.md`, `C05-filter-bar.md`, `C06-freshness-badge.md`: add Props/API prose note.
3. Run validate+build.

---

## Validation command

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome (final state — all phases complete):**
- 0 errors.
- VR-PAYLOAD-GRAMMAR warns: 5 remaining (C03 ×3, C05 ×1, C06 ×2) — all documented as accepted component-prop pattern.
- VR-HOSTS-BIDIR warns: ~28 (from Phase 05 — accepted informational).
- VR-EFFECT-SURFACE warns: 0 (P01.insight.reload — P01 is known surface, no warn).
- VR-REGION-PARENT warns: 0 (sidebar parent declared in S03 regions[]).
- All other validators: 0 errors, 0 unexpected warns.
- `navigation-graph.yaml` includes 6 `show_panel` display edges from S03.
- Exit 0.

This is the **plan acceptance state** — all 5 acceptance criteria from `plan.md` met.

---

## Risk / Rollback

**Risk (Low×Low):** `$party.id` in C04 emits doesn't match the actual prop name used by host screens in their `listens_to` payloads. S03's A-S03-LSN03 uses `{ party_id: "$event.party_id" }` — it reads `$event.party_id` which comes from the C04 emit payload key `party_id`. The payload key (`party_id`) doesn't change, only the value template (`"$party_id"` → `"$party.id"`). Host screens read the key, not the value template. Zero runtime impact.

**Rollback:** `git checkout HEAD -- crm/docs/ui-spec/components/C04-tag-chips.md crm/docs/ui-spec/components/C03-action-queue-card.md crm/docs/ui-spec/components/C05-filter-bar.md crm/docs/ui-spec/components/C06-freshness-badge.md`
