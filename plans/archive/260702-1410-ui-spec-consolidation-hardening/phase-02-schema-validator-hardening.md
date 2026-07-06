# Phase 02 — Schema + validator hardening

**Effort:** 2h  
**Blocker:** Phase 01 (centralized tools must exist)  
**File ownership:** `.agents/skills/ui-spec/tools/validate.mjs`; `.agents/skills/ui-spec/tools/build.mjs`; `.agents/skills/ui-spec/templates/schema/surface-contract.schema.json`; `crm/docs/ui-spec/schema/surface-contract.schema.json`

---

## Context

Five D3 hardening items touch tooling. All must land before the crm spec migration phases (04–06) so the new rules validate the migrated spec. The crm spec `schema/` is kept in-place per D2; it must stay in sync with the template schema.

---

## Change set

### A. Schema — add `show_panel` action enum (D3-2)

**Both files** (template schema + crm schema):
- `.agents/skills/ui-spec/templates/schema/surface-contract.schema.json`
- `crm/docs/ui-spec/schema/surface-contract.schema.json`

Current `action` enum (line ~44 in both files):
```json
"enum": ["navigate", "open_overlay", "close_overlay", "mutate", "emit_event", "external", "system_event"]
```

New value: add `"show_panel"` to the enum array.

```json
"enum": ["navigate", "open_overlay", "close_overlay", "mutate", "emit_event", "external", "system_event", "show_panel"]
```

Note: `show_panel` requires `target` (a panel ID). The existing `allOf` conditional already enforces `target` when action is `navigate` or `open_overlay`; extend it to also require `target` when action is `show_panel`:

```json
{
  "comment": "navigate/open_overlay/show_panel require a target",
  "if": { "properties": { "action": { "enum": ["navigate", "open_overlay", "show_panel"] } }, "required": ["action"] },
  "then": { "required": ["target"] }
}
```

---

### B. validate.mjs — add VR-SHOW-PANEL rule (D3-2)

**File:** `.agents/skills/ui-spec/tools/validate.mjs`

After the VR-TARGET block (current line ~107), add a new pass-2 check:

```js
// VR-SHOW-PANEL: show_panel target must be a known surface with type=panel
const surfaceTypeById = new Map();
for (const f of files) {
  if (f.meta?.id && f.meta?.type) surfaceTypeById.set(f.meta.id, f.meta.type);
}
for (const it of allInteractions) {
  if (it.action !== "show_panel") continue;
  const t = String(it.target ?? "");
  if (!knownSurfaceIds.has(t)) {
    err(it.file, `show_panel target \`${t}\` (action ${it.id ?? "?"}) is not a known surface`);
  } else if (surfaceTypeById.get(t) !== "panel") {
    err(it.file, `show_panel target \`${t}\` (action ${it.id ?? "?"}) must be type=panel`);
  }
}
```

Also update **VR-TARGET** to let `show_panel` pass through (currently it checks `SURFACE_ID_RE` against knownSurfaceIds for any target; `show_panel` targets are surface IDs so VR-TARGET already covers existence — VR-SHOW-PANEL adds the type constraint on top).

---

### C. validate.mjs — VR-REGION: dotted region parent warn (D3-1)

After the existing VR-REGION block (line ~147), add:

```js
// VR-REGION-PARENT: if regions[] contains a dotted path (e.g. sidebar.core_info),
// warn if the parent segment (e.g. sidebar) is not also declared in regions[].
for (const [surfaceId, regions] of surfaceRegions) {
  for (const r of regions) {
    const dotIdx = r.indexOf(".");
    if (dotIdx === -1) continue;
    const parent = r.slice(0, dotIdx);
    if (!regions.includes(parent)) {
      warn(surfaceId, `region \`${r}\` declared but parent segment \`${parent}\` not in regions[] (add it for layout reference)`);
    }
  }
}
```

Severity: **warn** (non-blocking).

---

### D. validate.mjs — VR-EFFECT-SURFACE: effect token surface reference (D3-2 complement)

Any effect string token matching `^[A-Z]{1,2}\d+\.` (starts with surface ID prefix + dot) must reference a known surface. This catches stale `P01.insight.reload` refs if P01 is renamed.

After VR-SHOW-PANEL, add:

```js
// VR-EFFECT-SURFACE: effect tokens starting with a surface-like prefix must reference known surfaces
const EFFECT_SURFACE_RE = /^([A-Z]{1,2}\d+)\./;
for (const it of allInteractions) {
  for (const eff of it.effects ?? []) {
    const m = String(eff).match(EFFECT_SURFACE_RE);
    if (m && !knownSurfaceIds.has(m[1])) {
      warn(it.file, `effect \`${eff}\` (action ${it.id ?? "?"}) references unknown surface \`${m[1]}\``);
    }
  }
}
```

Severity: **warn** (effects are advisory strings; some may be intentionally forward-declaring).

---

### E. validate.mjs — hosted_by support + bidirectional check (D3-3)

Build.mjs already records `hosts` from frontmatter. For validation, add two new checks after VR-HOSTS:

```js
// VR-HOSTED-BY: hosted_by[] entries must reference known surfaces
for (const f of files) {
  if (!Array.isArray(f.meta?.hosted_by)) continue;
  for (const h of f.meta.hosted_by) {
    if (!knownSurfaceIds.has(h)) {
      err(f.file, `hosted_by[] references \`${h}\` — not a known surface`);
    }
  }
}

// VR-HOSTS-BIDIR: if X.hosted_by lists Y, then Y.hosts must include X (and vice versa)
const hostsByFile   = new Map(); // surfaceId -> hosts[]
const hostedByFile  = new Map(); // surfaceId -> hosted_by[]
for (const f of files) {
  if (!f.meta?.id) continue;
  if (Array.isArray(f.meta.hosts))     hostsByFile.set(f.meta.id, f.meta.hosts);
  if (Array.isArray(f.meta.hosted_by)) hostedByFile.set(f.meta.id, f.meta.hosted_by);
}
for (const [childId, parents] of hostedByFile) {
  for (const parentId of parents) {
    const parentHosts = hostsByFile.get(parentId) ?? [];
    if (!parentHosts.includes(childId)) {
      warn(null, `bidirectional hosting gap: ${childId}.hosted_by lists ${parentId} but ${parentId}.hosts does not include ${childId} (VR-HOSTS-BIDIR)`);
    }
  }
}
```

Severity: `VR-HOSTED-BY` = **error** (wrong surface ref). `VR-HOSTS-BIDIR` = **warn** (migration may be in progress).

Note: `surfaceTypeById` is already built in change B above; move it to pass-1 scope so all pass-2 rules can use it.

---

### F. validate.mjs — payload grammar warn (D3-4)

Scan payload values for bare `$<word>` tokens (no dot, no `$event.`). Warn only — component props may legitimately use bare names.

```js
// VR-PAYLOAD-GRAMMAR: payload tokens should follow $entity.field or $event.field convention
const BARE_TOKEN_RE = /"\$([a-z_]+)"/g;
for (const it of allInteractions) {
  if (!it.payload) continue;
  const payloadStr = JSON.stringify(it.payload);
  for (const m of payloadStr.matchAll(BARE_TOKEN_RE)) {
    // Allow $event.* (caught by the dot check) — this regex already excludes dotted
    warn(it.file, `payload token \`$${m[1]}\` (action ${it.id ?? "?"}) is a bare variable — prefer $entity.field or $event.field (VR-PAYLOAD-GRAMMAR)`);
  }
}
```

Severity: **warn**. After Phase 06 normalization, only legitimate component prop usages will remain.

---

### G. validate.mjs — minor fixes (D3-5)

**G1. Modal detection — type-only, no heuristic** (D3-5-c)

Current (line ~121-124):
```js
const modalIds = [...knownSurfaceIds].filter((s) => {
  const f = files.find((f) => f.meta?.id === s);
  return f?.meta?.type === "modal" || s.startsWith("M");
});
```

Replace with:
```js
const modalIds = [...knownSurfaceIds].filter((s) => {
  const f = files.find((f) => f.meta?.id === s);
  return f?.meta?.type === "modal";
});
```

**G2. VR-MODAL-EXIT-001 message fix + submit acceptance** (D3-5-a)

Current (line ~127-129):
```js
if (!acts.some((a) => a.action === "close_overlay")) {
  err(mid, `modal ${mid} has no close_overlay/submit exit (VR-MODAL-EXIT-001)`);
}
```

Replace with:
```js
const hasExit = acts.some((a) => a.action === "close_overlay" || a.action === "submit");
if (!hasExit) {
  err(mid, `modal ${mid} has no close_overlay or submit exit action (VR-MODAL-EXIT-001)`);
}
```

**G3. Element name uniqueness warn** (D3-5-b)

After VR-ID-UNIQUE block, add:
```js
// VR-ELEMENT-UNIQUE: warn if the same element name appears >1 time in same surface+region
const elementSeen = new Map(); // `${surfaceId}::${region}::${element}` -> first actionId
for (const it of allInteractions) {
  if (!it.element || !it.surfaceId) continue;
  const key = `${it.surfaceId}::${it.region ?? ""}::${it.element}`;
  if (elementSeen.has(key)) {
    warn(it.file, `element \`${it.element}\` in ${it.surfaceId}${it.region ? "/" + it.region : ""} appears in multiple interactions (action ${it.id ?? "?"}); first seen at ${elementSeen.get(key)}`);
  } else {
    elementSeen.set(key, it.id ?? "?");
  }
}
```

Severity: **warn**.

**G4. Listener ID convention** (D3-5-e)

No code change needed. The existing `actionId` JSON schema pattern `^A-[A-Z0-9]+-[A-Za-z0-9]+$` accepts both `A-S03-LSN-01` and `A-S03-LSN01`. Document only (Phase 03).

---

### H. build.mjs — emit display edges for show_panel (D3-2)

In `build.mjs`, after the `pushEdge` loop for `c.interactions`, add a comment noting that `show_panel` edges are already emitted (same `pushEdge` logic). Verify: `pushEdge` captures `action: show_panel` and `target: Pxx` into `navigation-graph.yaml` edges. No code change needed — the existing loop handles all interactions including show_panel. Just verify the output after Phase 04 migration.

---

## Implementation steps

1. Edit both schema files: add `"show_panel"` to action enum; extend `allOf[0]` condition to include `show_panel`.
2. Edit `validate.mjs`:
   - Move/add `surfaceTypeById` map build into pass-1 scope.
   - Add VR-SHOW-PANEL (B).
   - Add VR-REGION-PARENT (C).
   - Add VR-EFFECT-SURFACE (D).
   - Add VR-HOSTED-BY + VR-HOSTS-BIDIR (E).
   - Add VR-PAYLOAD-GRAMMAR (F).
   - Apply G1, G2, G3 minor fixes.
3. Verify `build.mjs` already captures `show_panel` edges (no change needed).
4. Run validate+build against crm spec.

---

## Validation command

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome after Phase 02 (before crm spec migration):**
- No new **errors** (existing spec doesn't use `show_panel` as action yet — it's still in `effects`, which doesn't trigger VR-SHOW-PANEL).
- New **warns** expected:
  - VR-PAYLOAD-GRAMMAR: ~8 warnings from C04 (`$party_id`), C03 (`$party_id` ×3), C05 (`$current_filter_values`), C06 (`$table_name`, `$refreshed_at`).
  - VR-EFFECT-SURFACE: 0 (current effects like `main_col.show_panel_P01` start with `main_col`, not a surface ID pattern `[A-Z]{1,2}\d+`). However `P01.insight.reload` in A-S03-LSN01 starts with `P01.` — this WILL fire 1 warn. Acceptable.
  - VR-HOSTS-BIDIR: ~31 warns (all non-screen files have `hosts:` not `hosted_by:` yet; bidirectional check will note S03.hosts has P01 but P01 has no `hosted_by` listing S03). These are expected pre-migration warns.
  - VR-ELEMENT-UNIQUE: 0 expected.
  - VR-REGION-PARENT: 0 expected (no dotted regions yet).
- Exit 0 (warns do not fail the build).

---

## Risk / Rollback

**Risk (Low×High):** `surfaceTypeById` map built after `knownSurfaceIds` — ordering matters in pass-1 loop. Mitigation: build both in same pass-1 loop.

**Risk (Med×Med):** VR-HOSTS-BIDIR generates too many warns before Phase 05, cluttering output.  
Mitigation: tag the warn clearly with phase context; implementer can grep-filter. Alternatively, gate VR-HOSTS-BIDIR behind an env flag `UI_SPEC_STRICT=1` — plan both and pick at implementation time.

**Rollback:** `git checkout HEAD -- .agents/skills/ui-spec/tools/validate.mjs .agents/skills/ui-spec/tools/build.mjs .agents/skills/ui-spec/templates/schema/ crm/docs/ui-spec/schema/`
