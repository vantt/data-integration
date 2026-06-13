---
id: overview
type: meta
name: "{PROJECT} UI Spec — Overview"
status: active
version: "0.1.0"
---

# {PROJECT} UI Spec

## What Is This?
This directory contains the UI specification for **{PROJECT}**. Each surface (screen, modal,
panel, component, overlay, flow) has its own markdown file with a fenced YAML contract block
that the compiler validates for structural correctness and cross-reference integrity.

## Structure

```
spec/
├── 00-overview.md              ← this file
├── 05-shared-states.md         ← shared state definitions
├── 10-shared-components.md     ← reusable component inventory
├── 15-system-events.md         ← system-initiated events
├── 20-domain-rules.md          ← cross-cutting business rules
├── spec.config.yaml            ← compiler config
├── screens/
│   ├── S01-*.md
│   └── ...
├── modals/
│   ├── M01-*.md
│   └── ...
├── panels/
│   ├── P01-*.md
│   └── ...
├── components/
│   ├── C01-*.md
│   └── ...
├── flows/
│   ├── F01-*.md
│   └── ...
└── overlays/
    ├── O01-*.md
    └── ...
```

## Surface Index

### Screens
| ID | Name | Status | Notes |
|----|------|--------|-------|
| S01 | ... | active | entry point |

### Modals
| ID | Name | Status | Hosts |
|----|------|--------|-------|
| M01 | ... | active | S01 |

### Panels
| ID | Name | Status | Hosts |
|----|------|--------|-------|

### Components
| ID | Name | Status | Used By |
|----|------|--------|---------|

### Flows
| ID | Name | Status | Entry |
|----|------|--------|-------|

### Overlays
| ID | Name | Status | Hosts |
|----|------|--------|-------|

## Key Flows
<!-- List the 3-5 most important user journeys and the flow IDs that describe them. -->
1. **Onboarding** — F01
2. **Core action** — F02

## Entry Surface
`S01` — see `screens/S01-*.md`

## Contract Tag
All fenced contract blocks use: ` ```yaml {project}-contract `

## Running the Compiler
```bash
# Validate all contracts
node compiler/validate.js

# Or via the ui-spec skill
# /ui-spec validate
```
