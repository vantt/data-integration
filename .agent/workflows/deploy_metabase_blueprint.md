---
description: Deploy a Metabase Blueprint (Markdown) to the Metabase instance.
---

# Deploy Metabase Blueprint

This workflow deploys analytics configurations (Dashboards, Questions, Models) from a Markdown blueprint file to Metabase.

## Prerequisites

1.  **Metabase Container**: Must be running (`docker ps` to check).
2.  **Blueprint File**: A valid Markdown file in `docs/metabase-workspace/` (e.g., `docs/metabase-workspace/sales-blueprint-daily.md`).

## Steps

1.  **Verify Configuration**
    Check that the blueprint follows the literate configuration syntax.
    - Headers: `## 📂`, `### 🖥️`, `#### ❓`
    - Code: `sql`, `json metabase-viz`

2.  **Run Deployment**
    Replace `<file_path>` with your blueprint path.

    ```bash
    node .agent/skills/metabase-automation/scripts/deploy_from_markdown.js docs/metabase-workspace/sales-blueprint-daily.md
    ```

    _Tip: To deploy a different file, just change the path argument._

3.  **Verify in UI**
    Open Metabase (http://localhost:3000) and check the "Collections" to see your new dashboards.
