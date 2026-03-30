---
name: Metabase Automation
description: Programmatic management of Metabase resources. Full documentation and code lives in .skills/metabase-automation/.
---

# Metabase Automation Skill

This skill's code and documentation have been moved to a **shared, agent-agnostic location** so that both Antigravity and Claude Code can use them.

## Shared Resources

| Resource | Location |
| --- | --- |
| **Full Documentation** | `.skills/metabase-automation/SKILL.md` |
| **Strategy Guide** | `.skills/metabase-automation/STRATEGY.md` |
| **JS Library** | `.skills/metabase-automation/lib/` |
| **Scripts** | `.skills/metabase-automation/scripts/` |
| **Templates** | `.skills/metabase-automation/templates/` |

## Quick Reference

### Deploy from Blueprint (Markdown)

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js <path-to-blueprint.md>
```

### Deploy from Config (JS)

```bash
node .skills/metabase-automation/scripts/deploy_from_config.js <path-to-config.js>
```

### Create Blueprint

```bash
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
```

## Instructions

1. **READ** `.skills/metabase-automation/SKILL.md` for full API documentation.
2. **READ** `.skills/metabase-automation/STRATEGY.md` before designing any dashboard.
3. Use the workflows in `.agents/workflows/` for guided step-by-step processes.
