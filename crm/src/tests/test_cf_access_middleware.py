"""Tests for cf_access_middleware role-resolution helpers:
array-valued departments/functional_roles claims → CRM role priority pick.
"""
from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.inbound.http.cf_access_middleware import (
    _get_claim_values,
    _resolve_crm_role,
)


class TestGetClaimValues:
    def test_reads_array_claim(self):
        payload = {"custom": {"departments": ["Sales", "Care"]}}
        assert _get_claim_values(payload, "custom.departments") == ["Sales", "Care"]

    def test_tolerates_scalar_string(self):
        payload = {"custom": {"departments": "Sales"}}
        assert _get_claim_values(payload, "custom.departments") == ["Sales"]

    def test_missing_claim_returns_empty(self):
        assert _get_claim_values({"custom": {}}, "custom.departments") == []

    def test_non_dict_path_segment_returns_empty(self):
        assert _get_claim_values({"custom": "not-a-dict"}, "custom.departments") == []


class TestResolveCrmRole:
    ROLE_MAP = {"Admin Team": "admin", "Managers": "manager", "Sales": "sales", "Care": "care"}

    def test_single_match(self):
        assert _resolve_crm_role(["Sales"], self.ROLE_MAP) == "sales"

    def test_highest_privilege_wins_across_multiple_departments(self):
        assert _resolve_crm_role(["Sales", "Managers"], self.ROLE_MAP) == "manager"

    def test_admin_beats_everything(self):
        assert _resolve_crm_role(["Sales", "Managers", "Admin Team"], self.ROLE_MAP) == "admin"

    def test_no_match_falls_back_to_sales(self):
        assert _resolve_crm_role(["Unknown Dept"], self.ROLE_MAP) == "sales"

    def test_empty_values_falls_back_to_sales(self):
        assert _resolve_crm_role([], self.ROLE_MAP) == "sales"


class TestResolveCrmRoleManagerPrefixes:
    PREFIXES = ("truong-phong-", "head-of-")

    def test_prefixed_value_maps_to_manager(self):
        assert _resolve_crm_role(["truong-phong-tai-chinh"], {}, self.PREFIXES) == "manager"

    def test_english_prefix_also_matches(self):
        assert _resolve_crm_role(["head-of-sales"], {}, self.PREFIXES) == "manager"

    def test_unmapped_value_alongside_prefix_still_yields_manager(self):
        assert _resolve_crm_role(["finance", "truong-phong-tai-chinh"], {}, self.PREFIXES) == "manager"

    def test_admin_still_beats_manager_prefix(self):
        assert _resolve_crm_role(["bod", "truong-phong-tai-chinh"], {"bod": "admin"}, self.PREFIXES) == "admin"

    def test_no_prefixes_configured_ignores_rule(self):
        assert _resolve_crm_role(["truong-phong-tai-chinh"], {}, ()) == "sales"
