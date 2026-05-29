# Manage Metabase Resources

Manage Metabase resources (Models, Metrics, Questions, Dashboards) programmatically using the automation library.

## Context

Read these files before proceeding:
- `.skills/metabase-automation/STRATEGY.md` — Strategic planning framework
- `.skills/metabase-automation/SKILL.md` — Full API documentation

## Steps

### Step 1: Verify Design Spec

Before writing code, confirm a Design Spec exists (from Phase 0-6 in `.skills/analytics-design/`):

1. **Archetype**: Specified in Design Spec (Pulse / Cockpit / Tool)
2. **Data Strategy**: Reusable → `Model` + `Metric`. One-off → `Question`.
3. **Visualization**: Mapped from Design Spec using `METABASE_VIZ_CATALOG.md`

### Step 2: Define Scope

- **Semantic Layer** (Models & Metrics): `client.model`, `client.metric`, `client.segment`
- **Ad-hoc Reporting**: `client.collection`, `client.card`, `client.snippet`
- **Full Dashboard**: All resources (Collection -> Models -> Questions -> Dashboard)

### Step 3: Create Implementation Script

Create a script using `.skills/metabase-automation/scripts/metabase_client.js`:

```javascript
const MetabaseClient = require("./.skills/metabase-automation/scripts/metabase_client");
const client = new MetabaseClient(METABASE_URL, API_KEY);
await client.connect();
const dbId = await client.findDatabaseId("Sapo");
// ... resource creation
```

Or use the config-based deployment:
```bash
node .skills/metabase-automation/scripts/deploy_from_config.js <config.js>
```

### Step 4: Execute & Verify

1. Run the script
2. Check logs for success markers
3. Verify in Metabase UI

## User Arguments

$ARGUMENTS
