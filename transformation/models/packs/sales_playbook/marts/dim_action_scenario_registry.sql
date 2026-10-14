{{ config(
    tags=['mart', 'customer', 'crm_sync'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Canonical opportunity-type taxonomy. Passthrough of the scenario registry seed so the
-- CRM app can read the same enable flags + Vietnamese labels the marts filter on.
SELECT
    action_type,
    mart,
    enabled,
    scenario_group,
    description_vi
FROM {{ ref('seed_action_scenario_registry') }}
