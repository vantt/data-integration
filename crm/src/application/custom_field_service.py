"""CustomFieldService — business logic for custom field definitions.

Also exports the module-level validators (_validate_custom_field,
_validate_custom_map) which are reused by ProfileService.update_custom.

Depends only on domain entities and port protocols; no adapter imports.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

from domain.entities.profile import CustomFieldDef
from domain.ports.custom_field_repository import CustomFieldRepository
from domain.result import CustomFieldError


# ---------------------------------------------------------------------------
# Validators (ported from domain/custom_field_validator.go)
# ---------------------------------------------------------------------------

def _validate_custom_field(defn: CustomFieldDef, raw_value: str) -> Optional[CustomFieldError]:
    """Validate one (def, raw_value) pair. Returns error or None."""
    if defn.is_required and not raw_value.strip():
        return CustomFieldError(defn.field_key, "required field is missing or empty")
    if not raw_value:
        return None  # allow clearing optional fields

    dt = defn.data_type
    if dt == "text":
        return None
    if dt == "number":
        try:
            float(raw_value)
        except ValueError:
            return CustomFieldError(defn.field_key, f"expected a number, got {raw_value!r}")
    elif dt == "date":
        try:
            datetime.strptime(raw_value, "%Y-%m-%d")
        except ValueError:
            return CustomFieldError(defn.field_key, f"expected date YYYY-MM-DD, got {raw_value!r}")
    elif dt == "bool":
        if raw_value.lower() not in ("true", "false"):
            return CustomFieldError(defn.field_key, f"expected true or false, got {raw_value!r}")
    elif dt == "select":
        opts = defn.options or []
        if raw_value.strip() not in opts:
            return CustomFieldError(defn.field_key, f"value {raw_value!r} not in allowed options {opts}")
    elif dt == "multiselect":
        opts = defn.options or []
        for item in (p.strip() for p in raw_value.split(",") if p.strip()):
            if item not in opts:
                return CustomFieldError(defn.field_key, f"value {item!r} not in allowed options {opts}")
    # unknown data_type: skip (forward-compatible)
    return None


def _validate_custom_map(
    defs: list[CustomFieldDef], custom_map: dict[str, str]
) -> list[CustomFieldError]:
    """Validate a full key→value map against active defs. Returns all errors (non-short-circuit)."""
    defs_by_key = {d.field_key: d for d in defs if d.is_active}
    errors: list[CustomFieldError] = []

    for key, val in custom_map.items():
        defn = defs_by_key.get(key)
        if defn is None:
            continue  # unknown key — allowed, not validated
        err = _validate_custom_field(defn, val)
        if err:
            errors.append(err)

    # Check required active fields absent from the map entirely.
    for key, defn in defs_by_key.items():
        if not defn.is_required:
            continue
        if key in custom_map:
            continue
        errors.append(CustomFieldError(key, "required field is missing or empty"))

    return errors


# ---------------------------------------------------------------------------
# CustomFieldService
# ---------------------------------------------------------------------------

class CustomFieldService:
    """Manages custom field definition lifecycle."""

    def __init__(
        self,
        custom_field_repo: CustomFieldRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._cfs = custom_field_repo
        self._db = db

    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]:
        return self._cfs.list_active_defs(entity_type or "party")

    def get_custom_field_def(self, field_id: str) -> Optional[CustomFieldDef]:
        return self._cfs.get_def(field_id)

    def create_custom_field_def(self, def_data: CustomFieldDef) -> CustomFieldDef:
        if not def_data.field_id:
            def_data.field_id = str(uuid.uuid4())
        if not def_data.entity_type:
            def_data.entity_type = "party"
        self._cfs.create_def(def_data)
        if self._db:
            self._db.commit()
        return def_data

    def update_custom_field_def(self, field_id: str, **kwargs) -> None:
        defn = self._cfs.get_def(field_id)
        if defn is None:
            raise ValueError(f"custom field service: def {field_id!r} not found")
        for k, v in kwargs.items():
            if hasattr(defn, k):
                setattr(defn, k, v)
        self._cfs.update_def(defn)
        if self._db:
            self._db.commit()
