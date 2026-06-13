---
id: domain-rules
type: cross-cutting
name: "Domain Rules"
status: active
---

# Domain Rules

## Purpose
Cross-cutting business rules that apply across multiple surfaces. Each rule maps to the surfaces
that must enforce or display it. Compiler validates that referenced surface IDs exist.

## How to Use
- Add a rule entry per business constraint.
- List every surface where this rule is visible or enforced in `surfaces`.
- Use rule IDs (R001, R002, …) in surface frontmatter `rules:` arrays to link back.

## Rules

```yaml {project}-contract
rules:
  # Each rule maps a business constraint to the surfaces it affects.
  #
  # - id: R001
  #   name: "Unique email per account"
  #   surfaces: [S01, S03, M02]
  #
  # - id: R002
  #   name: "Order total must be positive before checkout"
  #   surfaces: [S05, M04]
  #
  # - id: R003
  #   name: "Admin-only: delete is permanent and cannot be undone"
  #   surfaces: [S07, M06]
```

## Rule Descriptions

### R001 — Unique email per account
<!-- Explain the business context, validation logic, and user-facing messaging. -->

### R002 — ...
<!-- Add one section per rule. -->
