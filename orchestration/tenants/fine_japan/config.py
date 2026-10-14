"""Fine Japan configuration read by shared orchestration code through
`orchestration.tenants.setting(name)`. An environment variable of the same name overrides a
value here. Shared code has no default for any of these: removing one makes the code that needs
it fail with TenantConfigError.

Values are the ones the shared code carried as defaults before the tenant overlay existed.
"""

# Public CSV exports of the Google Sheets the `sheets` connector ingests, polled by
# orchestration/sensors/sheets_modified_sensor.py (content hash). The ingestion readers
# (ingestion/src/gsheet_*.py) resolve their own URL from SOURCES__SPREADSHEET_URL__<NAME> with a
# fallback in the script; if a sheet URL changes, update both places.
SHEETS_SENSOR_TARGETS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/export?format=csv"
)
SHEETS_SENSOR_MARKETING_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/export?format=csv"
)
SHEETS_SENSOR_US_SHIPMENT_PRICES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1PWPQzzML_-i9yUrjGyhUcW0ABkrGEtXE2k49EaW4gwc/export?format=csv&gid=304875363"
)

# CRM app endpoints used by the crm pack (orchestration/packs/crm/crm_sync.py). `crm` and
# `crm_drill_runner` are container names on this deployment's docker network (caddy_net).
CRM_REFRESH_URL = "http://crm:8090/admin/refresh"
CRM_BACKUP_URL = "http://crm:8090/admin/backup"
CRM_DRILL_URL = "http://crm_drill_runner:9000/run-drill"

# Where the sales_playbook pack loads generated approach scripts
# (orchestration/packs/sales_playbook/approach_script_generation.py).
APPROACH_SCRIPT_LOAD_URL = "http://crm:8090/admin/approach-scripts/load"
