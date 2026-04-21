---
description: Manage Metabase resources (Models, Metrics, Questions, Dashboards) programmatically using the Automation Skill.
---

# Workflow: Manage Metabase Resources

This workflow provides a standardized process for managing Metabase content as code. It is not limited to dashboards; use it for any resource creation.

## Prerequisites

- **Metabase Automation Skill**: `.skills/metabase-automation/`
- **Node.js Environment**: Available to run scripts.

## Step 1: Strategic Planning (The "Think" Phase)

**STOP**: Before writing code, consult `.skills/metabase-automation/STRATEGY.md`.

1.  **classify Archetype**:
    - _Pulse_ (High-level)? _Cockpit_ (Action-oriented)? _Tool_ (Exploratory)?
2.  **Select Data Strategy**:
    - **Reusable?** -> Create `Model` + `Metric`.
    - **One-off?** -> Create `Question`.
3.  **Choose Visualization**:
    - Use the heuristics in `STRATEGY.md` (e.g., Donut for <5 categories).

## Step 2: Define Your Scope

- **Scenario A: Semantic Layer (Models & Metrics)**
  - Goal: Create official datasets and metrics for business users.
  - Resources: `client.model`, `client.metric`, `client.segment`.
- **Scenario B: Ad-hoc Reporting**
  - Goal: Create specific questions or collections without a full dashboard.
  - Resources: `client.collection`, `client.card`, `client.snippet`.

- **Scenario C: Full Dashboard**
  - Goal: End-to-end delivery of a dashboard.
  - Resources: All (Collection -> Models -> Questions -> Dashboard).

## Step 3: Create Implementation Script

Create a script file (e.g., `scripts/manage_resources.js`) using the appropriate template.

### Template A: Semantic Layer

```javascript
const MetabaseClient = require("./.skills/metabase-automation/scripts/metabase_client");
const client = new MetabaseClient(URL, KEY);
await client.connect();

const col = await client.collection.ensure("Official Data");

// 1. Create a Model (Dataset)
const model = await client.model.ensure("Clean Orders", "SELECT ...", DB_ID, col.id);

// 2. Add Metrics/Segments
await client.metric.ensure("Revenue", "Sum GMV", model.id, { ... });
await client.segment.ensure("VIP", "Spent > 1k", model.id, { ... });
```

### Template B: Ad-hoc Question

```javascript
// Quick question creation
const q = await client.card.ensure(
  "Ad-hoc Analysis",
  "SELECT ...",
  DB_ID,
  col.id,
);
console.log(`Question created: ${q.id}`);
```

### Template C: Full Dashboard

```javascript
// See usage_example.js in the skill folder for full flow
const dash = await client.dashboard.ensure("Main Dashboard", "Desc", col.id);
await client.dashboard.syncCards(dash.id, [
  { id: q.id, row: 0, col: 0, size_x: 6, size_y: 4 },
]);
```

## Step 4: Execute & Verify

1. Run the script: `node scripts/manage_resources.js`
2. Check the logs for `✅ Created/Updated`.
3. Verify in Metabase UI.

## Why use this workflow?

- **Code-as-Infrastructure**: Version control your analytics logic.
- **Reproducibility**: Easily recreate environments.
- **Capabilities**: Access advanced features (Permissions, Pulses) not easily done in bulk.
