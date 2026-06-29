from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.profile import CustomFieldDef


class CustomFieldRepository(Protocol):
    """Outbound port for crm_custom_field_def persistence."""

    def list_active_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]:
        """Return all active custom field definitions, optionally filtered by entity_type."""
        ...

    def list_all_defs(self, entity_type: str) -> list[CustomFieldDef]:
        """Return active + inactive definitions for entity_type."""
        ...

    def get_def(self, field_id: str) -> Optional[CustomFieldDef]:
        """Return a single definition by field_id, or None if not found."""
        ...

    def create_def(self, defn: CustomFieldDef) -> CustomFieldDef:
        """Insert a new custom field definition; returns the same object."""
        ...

    def update_def(self, defn: CustomFieldDef) -> None:
        """Persist changes to label, options, is_required, is_active, sort_order."""
        ...
