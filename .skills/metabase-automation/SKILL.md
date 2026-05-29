---
name: Metabase Automation (Modular Node.js)
description: A robust, modular skill for programmatically managing Metabase Collections, Questions, Dashboards, Metrics, and Models. Shared by Claude Code and Antigravity.
---

# Metabase Automation Skill

> **Location**: `.skills/metabase-automation/` — agent-agnostic shared tooling.
> Both Claude Code (`.claude/commands/`) and Antigravity (`.agents/skills/`) reference this directory.

## 🧠 How This Skill Fits

This skill **implements** analytics configurations designed by `.skills/analytics-design/` (Phase 0-6).
It assumes you have a **Design Spec** with archetype, viz selections, and composition already decided.

**Input**: Design Spec → **Output**: Metabase resources (Collections, Cards, Dashboards, Metrics, Models)

- **Strategy**: `.skills/metabase-automation/STRATEGY.md` — translation workflow, semantic layer, deploy mechanics
- **Viz Catalog**: `.skills/metabase-automation/METABASE_VIZ_CATALOG.md` — standard vocab → Metabase settings

## 📂 Structure

- `.skills/metabase-automation/scripts/metabase_client.js`: Main entry point.
- `.skills/metabase-automation/lib/metabase_core.js`: Low-level API client.
- `.skills/metabase-automation/lib/resources/`: Resource managers.

## 🚀 Usage

### 1. Import the Client

```javascript
const MetabaseClient = require("./.skills/metabase-automation/scripts/metabase_client");

// Option A: API Key (Standard)
const client = new MetabaseClient(METABASE_URL, API_KEY);

// Option B: Session Token (Custom Header)
const client = new MetabaseClient(METABASE_URL, SESSION_TOKEN, {
  authHeader: "X-Metabase-Session",
});

await client.connect();
const dbId = await client.findDatabaseId("My Database");
```

### 2. Manage Resources

#### Collections

```javascript
const col = await client.collection.ensure("Analytics");
```

#### Questions (Cards)

Use `client.card` to create Native SQL questions.
**Variables**: Pass `template_tags` in options to support SQL variables.

```javascript
const q = await client.card.ensure(
  "Revenue by Date",
  "SELECT sum(gmv) FROM fact_orders WHERE {{date}}",
  2,
  col.id,
  {
    display: "scalar",
    template_tags: {
      date: {
        id: "uuid...",
        name: "date",
        "display-name": "Date",
        type: "dimension",
        dimension: ["field-id", 123], // Use client.table.getFields(id) to find this
        "widget-type": "date/all-options",
      },
    },
  },
);
```

#### Dashboards & Filters

Create dashboards with filters and map them to cards.

```javascript
// 1. Create Dashboard with Filter Definition
const dash = await client.dashboard.ensure("KPIs", "Desc", col.id, [
  {
    name: "Date Range",
    slug: "date_range",
    id: "filter-uuid",
    type: "date/all-options",
  },
]);

// 2. Sync Cards & Map Filters
await client.dashboard.syncCards(dash.id, [
  {
    id: q.id,
    row: 0,
    col: 0,
    size_x: 6,
    size_y: 4,
    parameter_mappings: [
      {
        parameter_id: "filter-uuid", // Dashboard Filter ID
        card_id: q.id,
        target: ["dimension", ["template-tag", "date"]], // SQL Variable Name
      },
    ],
  },
]);
```

#### Dashboard Tabs

Organize cards into tabs. Tabs and cards must be sent in a **single PUT** request.

```javascript
// Sync cards with tabs — tab names are resolved to IDs automatically
await client.dashboard.syncCards(dash.id, [
  { id: q1.id, row: 0, col: 0, size_x: 6, size_y: 4, tab: "Overview" },
  { id: q2.id, row: 0, col: 0, size_x: 6, size_y: 4, tab: "Details" },
], ["Overview", "Details"]); // tab names array as 3rd argument
```

**Key points:**
- New tabs use negative temp IDs; existing tabs are reused by name.
- Each card's `tab` field is a tab name string, resolved internally to `dashboard_tab_id`.
- Metabase requires all tabs + all dashcards in one `PUT /api/dashboard/:id` payload.

#### Models & Metrics

Manage semantic layer.

```javascript
const model = await client.model.ensure("Curated Orders", "SELECT *...", 2, col.id);
const table = await client.table.find("fact_orders");
await client.metric.ensure("Revenue", "Sum GMV", table.id, { ... });
```

### 3. Advanced Features

#### Segments

Define subsets of data (e.g., "Active Users").

```javascript
await client.segment.ensure("VIP Customers", "Spent > 1k", table.id, { ... });
```

#### SQL Snippets

Share code fragments across questions.

```javascript
await client.snippet.ensure("fy2024_filter", "date(timestamp) >= '2024-01-01'");
```

#### Pulses (Alerts/Reports)

Send dashboards via Email or Slack.

```javascript
await client.pulse.ensure(
  "Daily Report",
  [{ id: card_id }],
  [{ channel_type: "email", recipients: [{ email: "boss@company.com" }] }],
);
```

### 4. Generic Deployment (Zero-Code Script)

Instead of writing a custom script for every dashboard, define your resources in a config file and run the generic helper.

**1. Create a Config File (e.g., `dashboard_config.js`)**

```javascript
module.exports = {
  database: "Sapo",
  collection: "Sales Analytics",
  dashboard: { name: "Daily Sales" },
  questions: [
    {
      name: "Total Revenue",
      display: "scalar",
      sql: "SELECT sum(gmv) FROM fact_orders",
      pos: { row: 0, col: 0, size_x: 4, size_y: 4 },
    },
  ],
};
```

**2. Run the Helper**

````bash
```bash
node .skills/metabase-automation/scripts/deploy_from_config.js ./dashboard_config.js
````

### 5. Literate Configuration (Markdown Blueprints)

Define your analytics in Markdown and deploy them directly.

**Template**: `.skills/metabase-automation/templates/blueprint_template.md`

**1. Create a Blueprint**

```bash
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
# Example: node .skills/metabase-automation/scripts/create_blueprint.js sales daily
```

**2. Deploy a Blueprint**

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/my_metrics.md
```

## 🛠️ API Details

- **Tables**: Use `client.table.find("name")` and `client.table.getFields(id)` to discover metadata.

## ⚠️ Troubleshooting & Compatibility (v0.60+)

### 1. Dashboard Cards Not Syncing

**Symptoms**: Deployment success log but empty dashboard.
**Cause**: Metabase v0.60+ requires `PUT /api/dashboard/:id` with `dashcards` payload (legacy `POST /api/dashboard/:id/cards` and `ordered_cards` no longer supported).
**Solution**:

- Use `PUT /api/dashboard/:id` with `dashcards` payload.
- **CRITICAL**: New cards must have a **negative integer ID** (e.g., `-1`, `-2`) in the payload. Creating a card without an ID causing the request to be rejected or ignored.

### 2. "The object has been archived" Error

**Symptoms**: API returns 400/404 with archive error message.
**Cause**: Dashboards or Cards interactively "Archived" (Soft Deleted) in UI block API updates.
**Solution**:

- The Skill (`Dashboard.js`, `Card.js`) automatically checks for `archived: true` and unarchives resources before update.
- Manually check "Archive" in Metabase Collection to restore items if needed.

### 3. API Payload Differences

- **Legacy**: `ordered_cards` (ignored in new versions).
- **Modern**: `dashcards` (requires `id`).

### 4. Tabs Not Appearing After Deployment

**Symptoms**: Cards deployed but all on one flat view, no tabs.
**Cause**: Tabs and dashcards must be sent in a **single PUT** request. Sending tabs separately is silently ignored by Metabase v0.60+.
**Solution**: Use `dashboard.syncCards(id, cardConfigs, tabNames)` which combines both in one payload. The `deploy_from_markdown.js` script handles this automatically when `### 📑 Tab:` headers are present in the blueprint.
