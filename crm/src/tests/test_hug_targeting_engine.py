"""test_hug_targeting_engine.py — parity tests for the Python port of matchesTargeting.

Each test case is cross-checked against the TypeScript source:
  webhook_receiver/cloudflareD1/src/hug-handler.ts  matchesTargeting

Parity citations are embedded per test so the mapping stays auditable.

Coverage matrix:
  M01  empty targeting {}           → always True  (TS empty-dict check)
  M02  list OR — value in list      → True          (TS array rule branch)
  M03  list OR — value not in list  → False
  M04  AND across keys — both match → True          (TS: all keys must pass)
  M05  AND across keys — one fails  → False
  M06  range gte boundary: exact    → True          (TS range branch)
  M07  range gte boundary: below    → False
  M08  range lte boundary: exact    → True
  M09  range lte boundary: above    → False
  M10  range gt strict              → True/False
  M11  range lt strict              → True/False
  M12  range: multiple bounds       → both checked
  M13  scalar equality: match       → True          (TS scalar branch)
  M14  scalar equality: no match    → False
  M15  missing key in targeting     → no constraint, True (TS: key absent = pass)
  M16  constrained key ctx None     → False         (TS list/null check)
  M17  malformed targeting (raises) → True           (TS graceful degradation)
  M18  list with str/int coercion   → True           (TS String() coercion)
  M19  not_in: value absent from excluded list → True
  M20  not_in: value in excluded list → False
  M21  not_in: None ctx value → True (unknown is not in the excluded set)
  M22  not_in: str coercion — int rule, int ctx
  M23  not_in combined with positive list rule (AND semantics)

Validate coverage:
  V01  valid catalog attribute + list rule         → no errors
  V02  valid range rule                            → no errors
  V03  unknown attribute key                       → error
  V04  unknown range operator                      → error
  V05  out-of-domain value for is_contactable      → error
  V06  empty list rule                             → error
  V07  range with no operators                     → error
  V08  range operator value non-numeric            → error
  V09  all 6 original catalog attrs accept valid rules → no errors
  V10  all 7 catalog attrs (including sku) accept valid rules → no errors
  V11  not_in accepted for list attr with domain   → no errors
  V12  not_in rejected when extra keys present     → error
  V13  not_in rejected on range-type attr          → error
  V14  not_in rejected with empty list             → error
  V15  not_in sku open domain (no domain check)    → no errors

Preview coverage:
  P01  all-match targeting {} → matched == total
  P02  tier filter → only matching rows counted
  P03  unavailable cache.db  → error dict, no raise
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

import pytest

# Ensure crm/src is importable without installing the package.
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.targeting_catalog import TARGETING_CATALOG, validate_targeting  # noqa: E402
from hug.targeting_engine import matches_targeting, preview_match_customers  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache_db(tmp_dir: str, rows: list[dict]) -> str:
    """Create a minimal cache.db with wh_customer_tier and return its path."""
    path = str(pathlib.Path(tmp_dir) / "cache.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE wh_customer_tier (
            customer_key   TEXT PRIMARY KEY,
            customer_id    INTEGER,
            strategic_tier TEXT,
            recency_days   INTEGER,
            value_group    TEXT,
            is_contactable INTEGER
        )
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO wh_customer_tier "
            "(customer_key, customer_id, strategic_tier, recency_days, value_group, is_contactable) "
            "VALUES (:customer_key, :customer_id, :strategic_tier, :recency_days, :value_group, :is_contactable)",
            r,
        )
    conn.commit()
    conn.close()
    return path


# ---------------------------------------------------------------------------
# M01–M18 : matches_targeting parity tests
# ---------------------------------------------------------------------------

def test_empty_targeting_matches_any_context():
    """M01: {} → True for any context (DEFAULT campaign). TS line 159."""
    assert matches_targeting({}, {}) is True
    assert matches_targeting({}, {"tier": "VIP", "recency_days": 45}) is True


def test_list_or_value_in_list_matches():
    """M02: list rule — context value inside list → True. TS lines 165–172."""
    # Parity: TS `rule.some(v => String(v) === String(ctxValue))`
    assert matches_targeting({"tier": ["VIP", "CORE"]}, {"tier": "VIP"}) is True
    assert matches_targeting({"tier": ["VIP", "CORE"]}, {"tier": "CORE"}) is True


def test_list_or_value_not_in_list_no_match():
    """M03: list rule — context value absent from list → False."""
    assert matches_targeting({"tier": ["VIP", "CORE"]}, {"tier": "CASUAL"}) is False


def test_and_across_keys_both_match():
    """M04: multiple keys — all must match → True. TS: every key must pass."""
    targeting = {"tier": ["VIP"], "op_type": ["package_insert"]}
    ctx = {"tier": "VIP", "op_type": "package_insert"}
    assert matches_targeting(targeting, ctx) is True


def test_and_across_keys_one_fails():
    """M05: multiple keys — one fails → False."""
    targeting = {"tier": ["VIP"], "op_type": ["package_insert"]}
    ctx = {"tier": "VIP", "op_type": "loyalty_card"}
    assert matches_targeting(targeting, ctx) is False


def test_range_gte_boundary_exact_matches():
    """M06: recency_days gte — exact boundary → True. TS line 178: numCtx >= r.gte."""
    assert matches_targeting({"recency_days": {"gte": 30}}, {"recency_days": 30}) is True


def test_range_gte_boundary_below_no_match():
    """M07: recency_days gte — one below boundary → False."""
    assert matches_targeting({"recency_days": {"gte": 30}}, {"recency_days": 29}) is False


def test_range_lte_boundary_exact_matches():
    """M08: recency_days lte — exact boundary → True. TS line 179: numCtx <= r.lte."""
    assert matches_targeting({"recency_days": {"lte": 90}}, {"recency_days": 90}) is True


def test_range_lte_boundary_above_no_match():
    """M09: recency_days lte — one above boundary → False."""
    assert matches_targeting({"recency_days": {"lte": 90}}, {"recency_days": 91}) is False


def test_range_gt_strict_boundary():
    """M10: gt is strict (not >=). TS line 180: numCtx > r.gt."""
    assert matches_targeting({"recency_days": {"gt": 30}}, {"recency_days": 31}) is True
    assert matches_targeting({"recency_days": {"gt": 30}}, {"recency_days": 30}) is False


def test_range_lt_strict_boundary():
    """M11: lt is strict (not <=). TS line 181: numCtx < r.lt."""
    assert matches_targeting({"recency_days": {"lt": 90}}, {"recency_days": 89}) is True
    assert matches_targeting({"recency_days": {"lt": 90}}, {"recency_days": 90}) is False


def test_range_multiple_bounds_all_checked():
    """M12: gte+lte window — value inside matches, outside fails."""
    rule = {"recency_days": {"gte": 30, "lte": 90}}
    assert matches_targeting(rule, {"recency_days": 60}) is True
    assert matches_targeting(rule, {"recency_days": 20}) is False
    assert matches_targeting(rule, {"recency_days": 100}) is False


def test_scalar_equality_match():
    """M13: scalar rule — string equality. TS lines 182–186: String(rule)==String(ctxValue)."""
    # Scalar rules are less common (UI produces lists), but the engine handles them.
    assert matches_targeting({"tier": "VIP"}, {"tier": "VIP"}) is True


def test_scalar_equality_no_match():
    """M14: scalar rule — different value → False."""
    assert matches_targeting({"tier": "VIP"}, {"tier": "CORE"}) is False


def test_missing_targeting_key_is_no_constraint():
    """M15: key absent from targeting → no constraint on that attr → pass.
    TS: loop only iterates keys present in targeting."""
    # targeting has no 'tier' key — tier is unconstrained, any tier passes.
    assert matches_targeting({"op_type": ["package_insert"]},
                              {"op_type": "package_insert", "tier": "CASUAL"}) is True


def test_constrained_key_with_none_ctx_value_no_match():
    """M16: targeting constrains a key but ctx value is None → False.
    TS line 168: if (ctxValue === null || ctxValue === undefined) return false."""
    # tier is constrained but missing from ctx → ctx.get("tier") = None → False
    assert matches_targeting({"tier": ["VIP"]}, {}) is False
    assert matches_targeting({"tier": ["VIP"]}, {"tier": None}) is False


def test_malformed_targeting_raises_internally_returns_true():
    """M17: malformed targeting that throws during eval → True (graceful degradation).
    TS lines 153–155: catch JSON.parse error → return true.
    Python: pre-parsed dict arrives; "malformed" means a rule value that throws
    during the evaluation loop (e.g. a list-like whose __iter__ raises, or a
    dict whose __contains__ raises).  We inject via a list subclass whose
    __iter__ raises so the `any(...)` inside the list branch throws.
    """
    class _ExplodingList(list):
        """A list that raises when iterated — simulates corrupted rule data."""
        def __iter__(self):
            raise RuntimeError("corrupted rule data")

    bad_targeting = {"tier": _ExplodingList(["VIP"])}
    # Engine must not raise, must return True (graceful degradation).
    result = matches_targeting(bad_targeting, {"tier": "VIP"})
    assert result is True


def test_list_rule_uses_string_coercion_for_int_values():
    """M18: is_contactable=[1] with ctx int 1 → True. TS: String(1)==String(1).
    Confirms str() coercion on both sides: str(1)=='1', str('1')=='1'."""
    # int rule value, int ctx value
    assert matches_targeting({"is_contactable": [1]}, {"is_contactable": 1}) is True
    # int rule value, string ctx value (cross-type coercion)
    assert matches_targeting({"is_contactable": [1]}, {"is_contactable": "1"}) is True
    # int rule 0 does not match int ctx 1
    assert matches_targeting({"is_contactable": [0]}, {"is_contactable": 1}) is False


# ---------------------------------------------------------------------------
# Validate coverage
# ---------------------------------------------------------------------------

def test_validate_accepts_valid_list_attr():
    """V01: valid list attr + list rule → no errors."""
    assert validate_targeting({"tier": ["VIP", "CORE"]}) == []


def test_validate_accepts_valid_range_attr():
    """V02: valid range rule → no errors."""
    assert validate_targeting({"recency_days": {"gte": 30, "lte": 90}}) == []


def test_validate_rejects_unknown_attribute():
    """V03: unknown attr key → error."""
    errors = validate_targeting({"order_value": [100]})
    assert any("unknown attribute" in e for e in errors)


def test_validate_rejects_unknown_range_operator():
    """V04: range with an unsupported operator → error."""
    errors = validate_targeting({"recency_days": {"eq": 30}})
    assert any("unknown range operator" in e for e in errors)


def test_validate_rejects_out_of_domain_is_contactable():
    """V05: is_contactable=2 is outside domain {0,1} → error."""
    errors = validate_targeting({"is_contactable": [2]})
    assert any("is_contactable" in e and "domain" in e for e in errors)


def test_validate_rejects_empty_list():
    """V06: empty list is meaningless as a rule → error."""
    errors = validate_targeting({"tier": []})
    assert any("must not be empty" in e for e in errors)


def test_validate_rejects_range_with_no_operators():
    """V07: range dict with no gte/gt/lte/lt → error."""
    errors = validate_targeting({"recency_days": {}})
    assert any("at least one" in e for e in errors)


def test_validate_rejects_non_numeric_range_value():
    """V08: range operator value must be numeric → error."""
    errors = validate_targeting({"recency_days": {"gte": "thirty"}})
    assert any("numeric" in e for e in errors)


def test_validate_accepts_all_six_catalog_attrs():
    """V09: all 6 v1 attrs with valid rules → no errors."""
    valid = {
        "op_type":       ["package_insert"],
        "tier":          ["VIP"],
        "channel":       ["shopee"],
        "value_group":   ["HIGH"],
        "is_contactable": [1],
        "recency_days":  {"gte": 0},
    }
    assert validate_targeting(valid) == []


# ---------------------------------------------------------------------------
# Preview coverage
# ---------------------------------------------------------------------------

def test_preview_empty_targeting_matches_all_customers():
    """P01: {} targeting → matched == total (every customer passes DEFAULT)."""
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_cache_db(tmp, [
            {"customer_key": "a", "customer_id": 1, "strategic_tier": "VIP",
             "recency_days": 10, "value_group": "HIGH", "is_contactable": 1},
            {"customer_key": "b", "customer_id": 2, "strategic_tier": "CORE",
             "recency_days": 50, "value_group": "MID",  "is_contactable": 0},
        ])
        result = preview_match_customers({}, db)
    assert result["total"] == 2
    assert result["matched"] == 2
    assert len(result["sample"]) == 2


def test_preview_tier_filter_counts_only_matching_customers():
    """P02: tier=["VIP"] → only VIP rows counted."""
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_cache_db(tmp, [
            {"customer_key": "a", "customer_id": 1, "strategic_tier": "VIP",
             "recency_days": 5,  "value_group": "HIGH", "is_contactable": 1},
            {"customer_key": "b", "customer_id": 2, "strategic_tier": "CORE",
             "recency_days": 30, "value_group": "MID",  "is_contactable": 0},
            {"customer_key": "c", "customer_id": 3, "strategic_tier": "VIP",
             "recency_days": 15, "value_group": "HIGH", "is_contactable": 1},
        ])
        result = preview_match_customers({"tier": ["VIP"]}, db)
    assert result["total"] == 3
    assert result["matched"] == 2
    assert all(s["tier"] == "VIP" for s in result["sample"])


def test_preview_unavailable_cache_db_returns_error_dict_no_raise():
    """P03: non-existent cache.db → error dict (never raises)."""
    result = preview_match_customers({}, "/tmp/does_not_exist_xyz.db")
    assert "error" in result
    assert result["matched"] == 0
    assert result["total"] == 0
    assert result["sample"] == []


# ---------------------------------------------------------------------------
# M19–M23 : not_in operator parity tests (mirrors TS index.test.ts)
# ---------------------------------------------------------------------------

def test_not_in_value_absent_from_excluded_list_passes():
    """M19: {"tier": {"not_in": ["WHOLESALE","STAFF"]}} + ctx tier="VIP" → True.
    Parity: TS matchesTargeting not_in branch — value not in list → passes."""
    assert matches_targeting(
        {"tier": {"not_in": ["WHOLESALE", "STAFF"]}},
        {"tier": "VIP"},
    ) is True


def test_not_in_value_in_excluded_list_fails():
    """M20: {"tier": {"not_in": ["WHOLESALE"]}} + ctx tier="WHOLESALE" → False.
    Parity: TS — value is in excluded list → campaign does not match."""
    assert matches_targeting(
        {"tier": {"not_in": ["WHOLESALE", "STAFF"]}},
        {"tier": "WHOLESALE"},
    ) is False


def test_not_in_none_ctx_value_passes():
    """M21: not_in rule + ctx value None → True (unknown is not in the excluded set).
    Parity: TS — ctxValue null/undefined → passes not_in check (exclusion rule
    should not block customers whose attr is simply unknown)."""
    assert matches_targeting(
        {"tier": {"not_in": ["WHOLESALE", "STAFF"]}},
        {"tier": None},
    ) is True
    # Also when key is absent entirely from ctx dict
    assert matches_targeting(
        {"tier": {"not_in": ["WHOLESALE", "STAFF"]}},
        {},
    ) is True


def test_not_in_str_coercion_int_rule_int_ctx():
    """M22: int values in not_in list matched via str() coercion.
    Parity: TS String(v) === String(ctxValue) — same as list-membership branch."""
    # is_contactable 0 is in [0] → fails
    assert matches_targeting(
        {"is_contactable": {"not_in": [0]}},
        {"is_contactable": 0},
    ) is False
    # is_contactable 1 is not in [0] → passes
    assert matches_targeting(
        {"is_contactable": {"not_in": [0]}},
        {"is_contactable": 1},
    ) is True


def test_not_in_combined_with_positive_list_rule_and_semantics():
    """M23: {"tier": {"not_in": [...]}, "op_type": [...]} — AND semantics.
    Both rules must pass; one failure in either → overall False."""
    targeting = {
        "tier": {"not_in": ["WHOLESALE", "STAFF"]},
        "op_type": ["package_insert"],
    }
    # Both pass
    assert matches_targeting(targeting, {"tier": "VIP", "op_type": "package_insert"}) is True
    # op_type fails
    assert matches_targeting(targeting, {"tier": "VIP", "op_type": "loyalty_card"}) is False
    # tier excluded
    assert matches_targeting(targeting, {"tier": "WHOLESALE", "op_type": "package_insert"}) is False


# ---------------------------------------------------------------------------
# V10–V15 : validate_targeting — not_in and sku tests
# ---------------------------------------------------------------------------

def test_validate_accepts_all_seven_catalog_attrs_including_sku():
    """V10: all 7 v1 attrs (sku added) with valid rules → no errors."""
    valid = {
        "op_type":       ["package_insert"],
        "tier":          ["VIP"],
        "channel":       ["shopee"],
        "sku":           ["FJ-OMEGA3-60"],
        "value_group":   ["HIGH"],
        "is_contactable": [1],
        "recency_days":  {"gte": 0},
    }
    assert validate_targeting(valid) == []


def test_validate_accepts_not_in_for_list_attr():
    """V11: not_in with domain-valid tier values → no errors."""
    # Use domain-valid values (DORMANT_VALUABLE, LAPSED_VALUABLE are in tier domain).
    assert validate_targeting({"tier": {"not_in": ["DORMANT_VALUABLE", "LAPSED_VALUABLE"]}}) == []


def test_validate_rejects_not_in_with_extra_keys():
    """V12: {"not_in": [...], "gte": 1} in same dict → error (mixed shape)."""
    errors = validate_targeting({"tier": {"not_in": ["WHOLESALE"], "gte": 1}})
    assert any("unexpected keys" in e for e in errors)


def test_validate_rejects_not_in_on_range_attr():
    """V13: range-type attr (recency_days) cannot use not_in → error."""
    errors = validate_targeting({"recency_days": {"not_in": [30]}})
    # range-type branch expects gte/gt/lte/lt; not_in is an unknown operator
    assert len(errors) > 0


def test_validate_rejects_empty_not_in_list():
    """V14: {"tier": {"not_in": []}} → error (empty list meaningless)."""
    errors = validate_targeting({"tier": {"not_in": []}})
    assert any("non-empty" in e for e in errors)


def test_validate_not_in_sku_open_domain_no_domain_check():
    """V15: sku has no 'values' domain → not_in accepts any string, no domain error."""
    assert validate_targeting({"sku": {"not_in": ["ANY-SKU-CODE-XYZ"]}}) == []
    assert validate_targeting({"sku": ["FJ-COLLAGEN-90"]}) == []
