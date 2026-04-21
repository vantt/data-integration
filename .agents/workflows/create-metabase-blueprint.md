---
description: Create a new Metabase Blueprint using the 2-skill pipeline (Design → Implementation).
---

# Create Metabase Blueprint

This workflow uses the 2-skill architecture to create analytics blueprints.

> **Preferred entrypoint:** Use `/create-metabase-blueprint` slash command instead of this workflow for the full guided experience.

## Pipeline

1. **Phase 0-6 (Analytics Design):** Design dashboard using `.skills/analytics-design/` knowledge
   - Output: Design Spec at `docs/analytics-handbook/designs/<name>.md`
2. **Phase 7-10 (Metabase Automation):** Translate design to Metabase blueprint
   - Output: Blueprint at `docs/analytics-handbook/blueprints/<name>.md`
3. **Deploy:** `node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint.md>`

## References

- Analytics Design Skill: `.skills/analytics-design/SKILL.md`
- Metabase Automation Skill: `.skills/metabase-automation/SKILL.md`
- Blueprint Template: `.skills/metabase-automation/templates/blueprint_template.md`
