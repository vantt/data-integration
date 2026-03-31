# Capture Metabase Dashboard

Capture a live Metabase dashboard (layout, SQL, viz settings, positions) and save as a deployable blueprint markdown.

## Prerequisites

1. Metabase container must be running
2. Environment variables set: `METABASE_URL`, `METABASE_API_KEY`

## Steps

1. **Identify the dashboard** to capture (by ID or name)
2. **Run capture**:
   ```bash
   node .skills/metabase-automation/scripts/capture_dashboard.js <dashboard_id> [output_file.md]
   ```
3. **Review and clean up** the generated blueprint:
   - Fix collection path if needed (remove root "Các phân tích của chúng ta" prefix)
   - Add playbook link, role, archetype metadata
   - Add domain references and descriptions
   - Verify viz settings look correct

## Examples

```bash
# Capture to stdout (preview)
node .skills/metabase-automation/scripts/capture_dashboard.js 11

# Capture to file
node .skills/metabase-automation/scripts/capture_dashboard.js 11 docs/analytics-handbook/blueprints/ceo_weekly_pulse.md
```

## User Arguments

$ARGUMENTS
