# {PROJECT} UI Spec

Machine-readable UI specification using the **ui-spec** format. Each surface file contains a
fenced YAML contract block validated by the compiler.

## Quick Start

```bash
# Copy config and customise
cp spec.config.yaml my-app/spec.config.yaml

# Copy surface templates as needed
cp templates/surfaces/screen.md   screens/S01-dashboard.md
cp templates/surfaces/modal.md    modals/M01-confirm-delete.md
cp templates/surfaces/component.md components/C01-data-table.md

# Validate all contracts
node compiler/validate.js
```

## Surface Types

| Type | Template | Contract Block | When to Use |
|------|----------|---------------|-------------|
| `screen` | `screen.md` | `interactions:` | Full-page views |
| `modal` | `modal.md` | `interactions:` | Blocking dialogs |
| `panel` | `panel.md` | `interactions:` | Reusable panel regions |
| `overlay` | `overlay.md` | `interactions:` | Popovers, drawers, menus |
| `component` | `component.md` | `emits:` | Reusable UI components |
| `flow` | `flow.md` | `flow:` | End-to-end user journeys |
| cross-cutting | `domain-rules.md` | `rules:` | Business rules across surfaces |
| cross-cutting | `system-events.md` | `interactions:` | System-initiated events |

## Contract Block Format

Every surface file contains exactly one fenced block tagged with the project contract tag:

````markdown
```yaml {project}-contract
interactions:
  - element: btn_save
    trigger: click
    action: navigate
    target: S02
```
````

The compiler extracts and validates all contract blocks against `schema/surface-contract.schema.json`.

## ID Conventions

| Surface Type | Prefix | Example |
|-------------|--------|---------|
| Screen | `S` | `S01`, `S12` |
| Modal | `M` | `M01`, `M03` |
| Panel | `P` | `P01` |
| Component | `C` | `C01` |
| Flow | `F` | `F01` |
| Overlay | `O` | `O01` |
| Action ID | `A-{SURFACE}-{Name}` | `A-S01-SaveDraft` |
| Rule ID | `R{NNN}` | `R001`, `R012` |

## Compiler Checks

- All `target` values in `navigate`/`open_overlay` resolve to a known surface ID
- All `steps` in `flow:` resolve to defined action IDs
- All surface IDs in `rules[].surfaces` exist
- `navigate`/`open_overlay` always have a `target`
- Non-listener interactions always have a `trigger`
- `emit` entries always have an explicit `id` (required for cross-reference)

## File Naming

```
screens/   S01-login.md  S02-dashboard.md  S03-settings.md
modals/    M01-confirm-delete.md  M02-edit-profile.md
panels/    P01-activity-feed.md
components/C01-data-table.md  C02-tag-picker.md
flows/     F01-onboarding.md  F02-checkout.md
overlays/  O01-card-context-menu.md
```
