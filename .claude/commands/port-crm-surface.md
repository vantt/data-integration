# Port CRM Surface

Port a retailCRM surface (screen / panel / modal / component) from the React prototype to the Python Jinja2 + HTMX stack with pixel-faithful fidelity.

## Skill

Read `.skills/crm-ui-port/SKILL.md` in full before doing anything else.

## Usage

```
/port-crm-surface S01
/port-crm-surface P01
/port-crm-surface M05
/port-crm-surface C03
```

## Steps

1. **Read the skill** — `.skills/crm-ui-port/SKILL.md` (mandatory, non-negotiable)
2. **Execute the 5-step reading protocol** from the skill before writing any template code
3. **Implement** the Jinja2 template(s) following all fidelity + translation rules
4. **Verify** against the checklist in the skill §6 before reporting done

## Output locations

| Artifact | Path |
|----------|------|
| Full-page template | `crm/python/adapters/inbound/web/templates/{surface}.html` |
| HTMX fragment | `crm/python/adapters/inbound/web/templates/fragments/{surface}_{tab}.html` |
| New CSS (if any) | `crm/app/internal/adapters/inbound/web/static/app.css` (append only) |

## Constraints

- Never invent CSS class names — copy verbatim from the prototype JSX
- Never hardcode colors or sizes — use design tokens (`var(--)`)
- Never use harness-only CSS classes (`.theme-panel`, `.harness-*`, `.reg-*`, `.clean-*`)
- All Vietnamese copy must match the prototype exactly
- All domain rules (R1–R12) referenced in the spec must be enforced
