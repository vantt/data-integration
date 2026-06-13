# METHODOLOGY — Why this system exists and how to use it

---

## The core tension

Humans think in **flows** ("user clicks X, then Y happens"). Machines need **graphs** (nodes, edges, typed transitions). Most spec formats pick one:

- Gherkin / user stories → great for humans, terrible for graph traversal
- XState / state machines → great for machines, requires deep upfront modeling
- Figma prototypes → great for visuals, no semantic structure, drifts from code

The ui-spec system resolves this by holding **both in the same file**:
- Prose (purpose, layout, edge cases) → for humans
- One fenced `yaml {project}-contract` block → for machines

Compiler ignores prose entirely. Prose can drift, get verbose, or change format — the contract stays machine-stable.

---

## Why dual-content in one file (not two files)

Alternative: keep surface prose in `screens/S05.md`, contracts in `contracts/S05.yaml`.

Problems with split files:
1. **Synchronization burden** — two files to update per change, always risk of divergence
2. **Context loss** — when reading the contract, you lose the "why" that's in the prose
3. **LLM consumption** — agent needs to load two files per surface; one file is simpler

Dual-content in one file means: open `S05-product-list.md`, read the prose for context, read the contract for behavior. One source of truth per surface.

---

## Why compiler ignores prose

Parsing free Markdown is fragile. Any rule that depends on prose structure breaks when authors write differently. Instead:

- Prose is a first-class **comment layer** — always present, never parsed
- Contract is a **typed, schema-validated YAML block** — always parseable
- The fenced block info-string (`yaml crm-contract`) is the delimiter — unambiguous even if the file has 40 other code blocks

This means authors can restructure, reformat, translate, or expand prose without any compiler impact.

---

## Why cross-surface validation matters

A spec written by humans + LLMs across multiple sessions accumulates drift:
- Surface A says it navigates to M05 — M05 was renamed or deleted
- Rule R4 lists surface S09 — S09 never declared R4 in its frontmatter
- A modal has no close path — user can never exit

These are **silent errors** in prose specs. In this system, `validate` catches all three:
- Target resolution: every `target` must exist in surface registry
- Rule drift: bidirectional check between `20-domain-rules.md` and surface frontmatter
- Modal exit: every modal must have ≥1 `close_overlay` and ≥1 `return_to_invoker`

The validator is the trust gate. Spec is trusted only after it passes.

---

## Comparison to alternatives

| Tool | Best when | Weakness |
|---|---|---|
| Gherkin / BDD | QA acceptance criteria, behavior-driven teams | Not a graph; no navigation model |
| XState | State machine IS the core domain (wizard, canvas editor) | Over-engineered for simple navigation |
| Figma prototypes | Visual design review, stakeholder demos | No semantic actions; drifts from implementation |
| OpenAPI / schema-first | Backend API contracts | UI interaction model is out of scope |
| **ui-spec** | ≥20 surfaces, domain rules, LLM-authored | Overkill for small/fast-iterating apps |

Use XState for canvas-level statecharts (e.g. idle → dragging → conflict). Use ui-spec for the surface layer above it.

---

## The 3-layer model

```
Layer 1 — Framework (generic)
  SKILL.md + CONVENTION.md + compiler tools
  Applies to any project; no domain knowledge

Layer 2 — Convention (configurable per project)
  spec.config.yaml → contract_tag, ID prefixes, entry_surface
  Adapts framework to project naming conventions

Layer 3 — Domain (app-specific)
  20-domain-rules.md, surface files, flow files
  Encodes business rules, navigation graph, interaction contracts
```

The framework and convention layers are stable; domain layer is where authoring happens. LLMs write Layer 3, guided by Layer 1+2.

---

## LLM consumption protocol

When using the spec for codegen, load context in this order:

1. `spec.config.yaml` — understand project name, contract tag, ID prefixes
2. `generated/surface-registry.yaml` — get full surface inventory (IDs, types, names)
3. `20-domain-rules.md` — load domain rules relevant to the target surface
4. Target surface file — read prose for intent, read contract for interactions
5. Connected surfaces — load any `target` surfaces referenced in the contract
6. `30-states-and-errors.md` — load state/error definitions referenced in the surface

Use `/ui-spec context <surface-id>` to get a pre-assembled context bundle for a specific surface.

**For flow implementation:** load the flow file + all surfaces in `flow.steps`.

**For design generation:** surface prose (Layout section) + `design_ref` path + contract (element names map to design components).

---

## The authoring model for LLMs

The 2-pass generate pipeline exists because writing prose and contracts simultaneously is harder and less reliable:

- **Pass 1 (skeleton):** LLM writes freely — purpose, layout, edge cases, user journey. No contract pressure. Good prose emerges when unconstrained.
- **Pass 2 (contracts):** LLM reads the registry + each surface → fills contracts. With the full surface graph already established, target resolution is reliable.

This mirrors how humans write specs: sketch the surfaces first, then formalize the interactions.
