// wireframe/client/region-model.js
// BROWSER pure functions: surface data model helpers.
// All renderers consume interactionsOf() as the single adapter (DRY).
// Ported/adapted from mockup s01-regionbox-mockup.html lines 168-195.
// Real data shape: contract.interactions[] + contract.emits[] (no flat interactions on surface).

/** HTML-escape a value for text content. */
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Escape a value for use in HTML attribute (double-quote context). */
function escAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

/**
 * isReaction: true when the interaction is a system/listener reaction, not a user click.
 * Rule: !!ix.listens_to || ix.trigger === 'system_event'
 * Verified: A-S01-007 has BOTH trigger:system_event AND listens_to → reaction chip.
 */
function isReaction(ix) {
  return !!ix.listens_to || ix.trigger === "system_event";
}

/**
 * Human-readable description of an interaction's outcome.
 * Used in button/chip meta line.
 */
function actionDesc(ix) {
  if (ix.action === "navigate")      return "navigate · " + (ix.target || "?");
  if (ix.action === "open_overlay")  return "open · " + (ix.target || "?");
  if (ix.action === "mutate")        return (ix.effects || []).join(" + ") || "mutate";
  if (ix.action === "emit_event")    return "emit · " + (ix.event || "?");
  if (ix.action === "close_overlay") return "close → " + (ix.target || "invoker");
  return ix.action || "?";
}

/**
 * Merge contract.interactions[] and contract.emits[] into a unified list.
 * Emits are normalised into reaction-shaped objects (they have no action field → 'emit_event').
 * All renderers call this — never read contract.interactions directly.
 */
function interactionsOf(surface) {
  const c = surface.contract || {};
  const ix = [...(c.interactions || [])];
  for (const e of (c.emits || [])) {
    // Emits are reactions by construction (fired by the component, not by user).
    // Normalise: add listens_to=event so isReaction() returns true; add action='emit_event'.
    ix.push({ ...e, listens_to: e.event, action: e.action || "emit_event" });
  }
  return ix;
}

/**
 * Ordered list of region names for this surface.
 * 1. meta.regions (declared, ordered)
 * 2. any ix.region not already in declared
 * 3. "(unassigned)" if any interaction lacks a region
 */
function regionOrder(surface) {
  const declared = surface.meta?.regions || [];
  const all = interactionsOf(surface);
  const used = [...new Set(all.map((i) => i.region).filter(Boolean))];
  const order =
    declared.length
      ? [...declared, ...used.filter((r) => !declared.includes(r))]
      : used;
  if (all.some((i) => !i.region)) order.push("(unassigned)");
  return order;
}

/**
 * Bucket interactions by region → {actions:[], listeners:[]} per region.
 * isReaction(ix) → listeners bucket; else → actions bucket.
 */
function groupByRegion(surface, order) {
  const buckets = Object.fromEntries(
    order.map((r) => [r, { actions: [], listeners: [] }])
  );
  for (const ix of interactionsOf(surface)) {
    const r = ix.region || "(unassigned)";
    if (!buckets[r]) buckets[r] = { actions: [], listeners: [] };
    (isReaction(ix) ? buckets[r].listeners : buckets[r].actions).push(ix);
  }
  return buckets;
}

// ── Phase 2: Edge index + narration ───────────────────────────────────────────

/**
 * Build a flat map { [actionId]: enrichedEdge } from all SURFACES.
 * Covers contract.interactions[] + contract.emits[] (via interactionsOf).
 * Called once at init; cached via edgeById().
 * @param {object[]} surfaces - SURFACES array
 * @returns {{ [id: string]: object }}
 */
function buildEdgeIndex(surfaces) {
  const m = {};
  for (const s of surfaces) {
    for (const ix of interactionsOf(s)) {
      if (!ix.id) continue;
      m[ix.id] = {
        id: ix.id,
        from: s.id,
        fromName: s.meta?.name || s.id,
        element: ix.element,
        region: ix.region,
        trigger: ix.trigger,
        listens_to: ix.listens_to,
        action: ix.action,
        target: ix.target,
        effects: ix.effects,
        guard: ix.guard,
        event: ix.event,
        isReaction: isReaction(ix),
      };
    }
  }
  return m;
}

/** Lazy singleton edge index — built once from SURFACES on first access. */
let _edges = null;
function edgeById(id) {
  if (!_edges) _edges = buildEdgeIndex(SURFACES);
  return _edges[id] || null;
}

/**
 * Human-readable narration for a flow step action ID.
 * Format: "{surfaceId} · {element} [{trigger | on listens_to}] → {actionDesc}" [+ guard clause]
 * Falls back to "{stepId} (unknown)" if ID not in edge index.
 * @param {string} stepId - action ID like A-S04-001
 * @returns {string}
 */
function narrate(stepId) {
  const e = edgeById(stepId);
  if (!e) return stepId + " (unknown)";
  const trig = e.isReaction
    ? "on " + (e.listens_to || "event")
    : (e.trigger || "?");
  let s = e.from + " · " + (e.element || "?") + " [" + trig + "] → " + actionDesc(e);
  if (e.guard) s += " (chỉ khi " + e.guard + ")";
  return s;
}
