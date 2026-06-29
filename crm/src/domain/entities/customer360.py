# Compatibility shim — entities live in profile.py; imported here for ports
# that use the old module name 'customer360'.
from domain.entities.profile import (  # noqa: F401
    CustomerProfile,
    CustomFieldDef,
    Party360,
)
