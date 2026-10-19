"""Fine Japan configuration read by shared orchestration code through
`orchestration.tenants.setting(name)`. An environment variable of the same name overrides a
value here. Shared code has no default for any of these: removing one makes the code that needs
it fail with TenantConfigError.

Values are the ones the shared code carried as defaults before the tenant overlay existed.
"""

# Google Sheet URLs are not here: each sheet is configured once, by the environment variable
# SOURCES__SPREADSHEET_URL__<NAME> (names in .env.docker.example), read by the ingestion readers
# (ingestion/src/gsheet_*.py) and by orchestration/sensors/sheets_modified_sensor.py.

# CRM app endpoints used by the crm pack (orchestration/packs/crm/crm_sync.py). `crm` and
# `crm_drill_runner` are container names on this deployment's docker network (caddy_net).
CRM_REFRESH_URL = "http://crm:8090/admin/refresh"
CRM_BACKUP_URL = "http://crm:8090/admin/backup"
CRM_DRILL_URL = "http://crm_drill_runner:9000/run-drill"

# Where the sales_playbook pack loads generated approach scripts
# (orchestration/packs/sales_playbook/approach_script_generation.py).
APPROACH_SCRIPT_LOAD_URL = "http://crm:8090/admin/approach-scripts/load"

# Whether the nightly approach_script_autogen asset calls the completion provider at all
# ("true"/"false"). Off for Fine Japan: the asset returns "disabled" without running the
# generator. The rest of the sales_playbook pack (the action queues the CRM reads) is unaffected.
APPROACH_SCRIPT_AUTOGEN_ENABLED = "false"
