"""Sales playbook pack (experimental, not standardised yet): nightly approach-script
generation for the customer action queue. Depends on the crm pack (runs after the CRM cache
refresh and loads the scripts into the CRM)."""
from .approach_script_generation import approach_script_autogen

ASSETS = [approach_script_autogen]
NIGHTLY_ASSETS = [approach_script_autogen]
