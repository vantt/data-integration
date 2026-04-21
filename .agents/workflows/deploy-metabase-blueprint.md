---
description: Deploy a Metabase Blueprint (Markdown) to the Metabase instance.
---

# Deploy Metabase Blueprint

> **Preferred entrypoint:** Use `/deploy-metabase-blueprint` slash command for the full guided experience.

## Prerequisites

1. **Metabase Container**: Must be running (`docker ps` to check)
2. **Blueprint File**: A valid Markdown file in `docs/analytics-handbook/blueprints/`
3. **Environment**: `METABASE_URL` and `METABASE_API_KEY` (or `METABASE_SESSION_ID`) set

## Steps

1. **Verify blueprint syntax**: Headers (`## 📂 Collection:`, `### 🖥️ Dashboard:`, `### 📑 Tab:`, `#### ❓ Question:`, `#### 📝 Text:`) and code blocks (`sql`, `json metabase-viz`, `json metabase-pos`)

2. **Deploy**:
   ```bash
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/<name>.md
   ```

3. **Verify in UI**: Open Metabase and check the target collection

## References

- Blueprint Template: `.skills/metabase-automation/templates/blueprint_template.md`
- Strategy & Limitations: `.skills/metabase-automation/STRATEGY.md`
