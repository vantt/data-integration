"""test_check_taxonomy_rules.py — the rule validator rejects every kind of invalid rule before load.

Run:
  python -m pytest scripts/tests/test_check_taxonomy_rules.py -q
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import check_taxonomy_rules as ctr  # noqa: E402

REAL_REPO = Path(__file__).resolve().parents[2]

REGISTRY = {
    "features": {
        "feat_customer_profile": {
            "subject": "customer", "key": "customer_key",
            "columns": {"group_code": "varchar", "total_spend": "double", "order_count": "integer",
                        "first_order_at": "date", "is_staff": "boolean", "tags": "varchar[]"},
        },
        "feat_customer_orders": {
            "subject": "customer", "key": "customer_key",
            "columns": {"channels_ordered_on": "varchar[]"},
        },
    },
    "domains": {
        "customer_type": {
            "subject": "customer", "cardinality": "single", "hit_policy": "FIRST",
            "features": ["feat_customer_profile", "feat_customer_orders"],
            "label_set": "customer_type", "required_features": [], "matched_flags": ["CROSSBORDER"],
            "survey": {"features": ["group_code"]}, "selftest": False,
        },
        "customer_tag": {
            "subject": "customer", "cardinality": "multi", "hit_policy": "COLLECT",
            "features": ["feat_customer_profile"], "label_set": "customer_tag",
        },
        "customer_band": {
            "subject": "customer", "cardinality": "single", "hit_policy": "UNIQUE",
            "features": ["feat_customer_profile"], "label_set": "customer_type",
        },
    },
}
LABELS = [("customer_type", "RETAIL"), ("customer_type", "WHOLESALE"), ("customer_type", "CROSSBORDER"),
          ("customer_tag", "VIP")]


def rule(rule_id, domain="customer_type", priority="10", label="WHOLESALE", feature="group_code",
         op="like", value="%CTN%", value_to="", enabled="true", note="") -> dict:
    return dict(rule_id=rule_id, domain=domain, priority=priority, label=label, feature=feature, op=op,
                value=value, value_to=value_to, enabled=enabled, note=note)


def _csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def make_repo(root: Path, product: list[dict] | None = None, tenant: list[dict] | None = None,
              registry: dict | None = None, tenant_id: str = "acme", default_rows: list[dict] | None = None) -> Path:
    project = {"name": "x", "vars": {"tenant": tenant_id, "taxonomy": registry if registry is not None else REGISTRY}}
    (root / "transformation").mkdir(parents=True, exist_ok=True)
    (root / "transformation" / "dbt_project.yml").write_text(yaml.safe_dump(project), encoding="utf-8")
    seeds = root / "transformation" / "seeds"
    _csv(seeds / "taxonomy" / "taxonomy_rule_product.csv", ctr.COLUMNS, product or [])
    _csv(seeds / "defaults" / "taxonomy_rule_tenant__default.csv", ctr.COLUMNS, default_rows or [])
    label_cols = ["domain", "label", "label_std", "note"]
    _csv(seeds / "defaults" / "taxonomy_label__default.csv", label_cols, [])
    if tenant_id:
        _csv(seeds / "tenants" / tenant_id / "taxonomy_rule_tenant.csv", ctr.COLUMNS, tenant or [])
        _csv(seeds / "tenants" / tenant_id / "taxonomy_label.csv", label_cols,
             [dict(domain=d, label=l, label_std="X", note="") for d, l in LABELS])
    return root


VALID_TENANT = [
    rule("fj_wholesale", priority="10", label="WHOLESALE", feature="group_code", op="like", value="%CTN00014%"),
    rule("fj_us", priority="20", label="CROSSBORDER", feature="channels_ordered_on", op="has", value="US"),
    rule("fj_spend", priority="30", label="WHOLESALE", feature="total_spend", op="between", value="1000", value_to=""),
    rule("fj_spend", priority="30", label="WHOLESALE", feature="order_count", op="in", value="1|2|3"),
    rule("fj_date", priority="40", label="RETAIL", feature="first_order_at", op="between",
         value="2026-01-01", value_to="2026-07-01"),
    rule("fj_staff", priority="50", label="RETAIL", feature="is_staff", op="eq", value="true"),
    rule("fj_nogroup", priority="60", label="RETAIL", feature="group_code", op="is_null", value=""),
    rule("fj_hasgroup", priority="61", label="RETAIL", feature="group_code", op="is_null", value="false"),
    rule("fj_re", priority="70", label="RETAIL", feature="group_code", op="regex", value="^CTN[0-9]+$"),
    rule("fj_default", priority="999", label="RETAIL", feature="", op="", value=""),
    rule("prod_band", domain="customer_band", enabled="false", label="", priority="", feature="", op="", value=""),
    rule("fj_vip", domain="customer_tag", priority="10", label="VIP", feature="tags", op="has", value="vip"),
    rule("fj_vip2", domain="customer_tag", priority="10", label="VIP", feature="total_spend", op="eq", value="5"),
]
VALID_PRODUCT = [
    rule("prod_band", domain="customer_band", priority="10", label="RETAIL", feature="order_count", op="eq", value="1"),
]


def errors_of(repo: Path) -> list[str]:
    errors, _ = ctr.validate(repo)
    return errors


def test_committed_seeds_pass():
    errors, summary = ctr.validate(REAL_REPO)
    assert errors == [], errors
    assert "tenant" in summary


def test_main_exit_codes(tmp_path, capsys):
    good = make_repo(tmp_path / "good", VALID_PRODUCT, VALID_TENANT)
    assert ctr.main(["--repo", str(good)]) == 0
    assert "TAXONOMY RULES: OK" in capsys.readouterr().out
    bad = make_repo(tmp_path / "bad", [], [rule("r1", domain="nope")])
    assert ctr.main(["--repo", str(bad)]) == 1
    assert "TAXONOMY RULES: FAIL" in capsys.readouterr().out


def test_valid_rules_pass(tmp_path):
    assert errors_of(make_repo(tmp_path, VALID_PRODUCT, VALID_TENANT)) == []


def test_empty_registry_and_header_only_seeds_pass(tmp_path):
    assert errors_of(make_repo(tmp_path, registry={"features": {}, "domains": {}})) == []


def test_no_tenant_reads_default_layer(tmp_path):
    repo = make_repo(tmp_path, [], None, tenant_id="", default_rows=[rule("x", domain="nope")])
    errs = errors_of(repo)
    assert any("defaults/taxonomy_rule_tenant__default.csv" in e and "not in vars.taxonomy.domains" in e
               for e in errs), errs


@pytest.mark.parametrize("layer,rows,expected", [
    # domain not in registry
    ("tenant", [rule("r1", domain="nope")], "domain 'nope' not in vars.taxonomy.domains"),
    # feature not declared for the domain
    ("tenant", [rule("r1", feature="loyalty_points")], "feature 'loyalty_points' not declared"),
    # feature of another domain's feature model
    ("tenant", [rule("r1", domain="customer_band", label="RETAIL", feature="channels_ordered_on", op="has",
                     value="US")], "feature 'channels_ordered_on' not declared for domain 'customer_band'"),
    # op not allowed for the type
    ("tenant", [rule("r1", feature="tags", op="like", value="%x%")], "op 'like' not allowed on feature 'tags'"),
    ("tenant", [rule("r1", feature="group_code", op="has", value="x")], "op 'has' not allowed on feature 'group_code'"),
    ("tenant", [rule("r1", feature="group_code", op="between", value="a", value_to="b")],
     "op 'between' not allowed on feature 'group_code'"),
    ("tenant", [rule("r1", feature="group_code", op="matches", value="x")], "op 'matches' not in"),
    # value not castable
    ("tenant", [rule("r1", feature="total_spend", op="eq", value="abc")], "value 'abc' is not double"),
    ("tenant", [rule("r1", feature="order_count", op="in", value="1|two")], "value 'two' is not integer"),
    ("tenant", [rule("r1", feature="first_order_at", op="between", value="2026-13-01")], "is not date"),
    ("tenant", [rule("r1", feature="is_staff", op="eq", value="yes")], "is not boolean"),
    ("tenant", [rule("r1", feature="group_code", op="regex", value="(")], "invalid regex"),
    ("tenant", [rule("r1", feature="group_code", op="in", value="a||b")], "empty item in in list"),
    ("tenant", [rule("r1", feature="group_code", op="eq", value="")], "op 'eq' needs a value"),
    ("tenant", [rule("r1", feature="group_code", op="is_null", value="maybe")], "is_null takes an empty value"),
    ("tenant", [rule("r1", feature="group_code", op="eq", value="a", value_to="b")], "value_to is only used by between"),
    # between without either bound, or bounds in the wrong order
    ("tenant", [rule("r1", feature="total_spend", op="between", value="", value_to="")], "between needs value, value_to or both"),
    ("tenant", [rule("r1", feature="total_spend", op="between", value="10", value_to="5")], "between needs value < value_to"),
    # label not in the label set
    ("tenant", [rule("r1", label="KOL")], "label 'KOL' not in taxonomy_label for label_set 'customer_type'"),
    ("tenant", [rule("r1", label="")], "label is empty"),
    # attributes differ between rows of one rule_id
    ("tenant", [rule("r1", priority="10"), rule("r1", priority="20", feature="total_spend", op="eq", value="1")],
     "priority '20' differs from '10'"),
    ("tenant", [rule("r1", label="WHOLESALE"), rule("r1", label="RETAIL", feature="total_spend", op="eq", value="1")],
     "label 'RETAIL' differs"),
    ("tenant", [rule("r1", enabled="true"), rule("r1", enabled="false", feature="total_spend", op="eq", value="1")],
     "enabled 'false' differs"),
    ("tenant", [rule("r1", priority="ten")], "priority 'ten' is not an integer"),
    ("tenant", [rule("r1", enabled="")], "enabled must be true or false"),
    ("tenant", [rule("", label="RETAIL")], "rule_id is empty"),
    # two rule_ids with the same (domain, layer, priority) in FIRST and UNIQUE domains
    ("tenant", [rule("r1", priority="10"), rule("r2", priority="10", value="%X%")],
     "priority 10 already used by rule 'r1' in domain 'customer_type', layer tenant"),
    ("product", [rule("b1", domain="customer_band", label="RETAIL", feature="order_count", op="eq", value="1"),
                 rule("b2", domain="customer_band", label="RETAIL", feature="order_count", op="eq", value="2")],
     "already used by rule 'b1' in domain 'customer_band', layer product (UNIQUE"),
    # unconditional rule in a COLLECT domain
    ("tenant", [rule("t1", domain="customer_tag", label="VIP", feature="", op="", value="")],
     "unconditional rule in COLLECT domain 'customer_tag'"),
    # unconditional row mixed with conditions
    ("tenant", [rule("r1", feature="", op="", value=""), rule("r1")], "must be the only row of its rule"),
    ("tenant", [rule("r1", feature="", op="eq", value="x")], "op/value without feature"),
    # disable row pointing to no rule
    ("tenant", [rule("ghost", label="", priority="", feature="", op="", value="", enabled="false")],
     "disable row for rule 'ghost': no layer defines this rule_id"),
    ("tenant", [rule("p1", domain="customer_band", label="", priority="", feature="group_code", op="eq",
                     value="x", enabled="false")], "a disable row (enabled=false, no label) takes no feature"),
])
def test_invalid_rule_is_rejected(tmp_path, layer, rows, expected):
    repo = make_repo(tmp_path, rows if layer == "product" else [], rows if layer == "tenant" else [])
    errs = errors_of(repo)
    assert any(expected in e for e in errs), errs


def test_disable_row_with_wrong_domain(tmp_path):
    product = [rule("p1", domain="customer_band", label="RETAIL", feature="order_count", op="eq", value="1")]
    tenant = [rule("p1", domain="customer_type", label="", priority="", feature="", op="", value="", enabled="false")]
    errs = errors_of(make_repo(tmp_path, product, tenant))
    assert any("domain 'customer_type' != 'customer_band'" in e for e in errs), errs


def test_disabled_rule_frees_its_priority(tmp_path):
    product = [rule("p1", priority="10", label="RETAIL"), rule("p2", priority="10", label="RETAIL", value="%Y%")]
    tenant = [rule("p2", label="", priority="", feature="", op="", value="", enabled="false")]
    assert errors_of(make_repo(tmp_path, product, tenant)) == []


def test_same_rule_id_defined_in_two_layers(tmp_path):
    errs = errors_of(make_repo(tmp_path, [rule("r1")], [rule("r1")]))
    assert any("defined in layers ['product', 'tenant']" in e for e in errs), errs


def test_same_priority_in_different_layers_is_fine(tmp_path):
    assert errors_of(make_repo(tmp_path, [rule("p1", priority="10")], [rule("t1", priority="10")])) == []


def test_wrong_header(tmp_path):
    repo = make_repo(tmp_path)
    p = repo / "transformation" / "seeds" / "taxonomy" / "taxonomy_rule_product.csv"
    p.write_text("rule_id,domain\n", encoding="utf-8")
    assert any("header" in e for e in errors_of(repo))


def test_default_seed_must_stay_empty(tmp_path):
    repo = make_repo(tmp_path, default_rows=[rule("r1")])
    assert any("a core default seed has a header only" in e for e in errors_of(repo))


@pytest.mark.parametrize("mutate,expected", [
    (lambda r: r["domains"]["customer_type"].update(hit_policy="PRIORITY"), "hit_policy 'PRIORITY'"),
    (lambda r: r["domains"]["customer_tag"].update(cardinality="single"), "COLLECT goes with cardinality multi"),
    (lambda r: r["domains"]["customer_type"].update(features=["feat_missing"]), "'feat_missing' not declared"),
    (lambda r: r["domains"]["customer_type"].update(label_set=""), "`label_set` is required"),
    (lambda r: r["domains"]["customer_type"].update(required_features=["zzz"]), "required_features 'zzz'"),
    (lambda r: r["domains"]["customer_type"].update(matched_flags=["KOL"]), "matched_flags 'KOL'"),
    (lambda r: r["domains"]["customer_type"].update(survey={"features": ["zzz"]}), "survey feature 'zzz'"),
    (lambda r: r["features"]["feat_customer_profile"]["columns"].update(x="geometry"), "unsupported type 'geometry'"),
    (lambda r: r["features"]["feat_customer_orders"]["columns"].update(group_code="varchar"),
     "feature column 'group_code' declared by two feature models"),
    (lambda r: r["features"]["feat_customer_orders"].update(subject="order"), "has subject 'order'"),
    (lambda r: r["features"]["feat_customer_orders"].update(key="order_key"), "must share one key column"),
    (lambda r: r["features"]["feat_customer_orders"]["columns"].update(x="LIST(VARCHAR)"), "unsupported type 'LIST(VARCHAR)'"),
])
def test_invalid_registry_is_rejected(tmp_path, mutate, expected):
    import copy
    reg = copy.deepcopy(REGISTRY)
    mutate(reg)
    errs = errors_of(make_repo(tmp_path, registry=reg))
    assert any(expected in e for e in errs), errs


def test_selftest_domain(tmp_path):
    import copy
    reg = copy.deepcopy(REGISTRY)
    reg["domains"]["selftest_x"] = dict(reg["domains"]["customer_band"], selftest=True, matched_flags=["NOT_A_LABEL"])
    assert errors_of(make_repo(tmp_path / "ok", registry=reg)) == []  # fixture labels: no label-set check
    errs = errors_of(make_repo(tmp_path / "bad", tenant=[rule("s1", domain="selftest_x", label="RETAIL",
                                                                 feature="order_count", op="eq", value="1")],
                               registry=reg))
    assert any("is a selftest domain" in e for e in errs), errs


def test_missing_registry_fails(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "transformation" / "dbt_project.yml").write_text("vars: {tenant: acme}\n", encoding="utf-8")
    assert any("vars.taxonomy is missing" in e for e in errors_of(repo))


def test_cast_value_types():
    assert ctr.cast_value("3", "BIGINT") == 3
    assert ctr.cast_value("1.5", "decimal(18, 2)") is not None
    assert ctr.cast_value("US", "VARCHAR[]") == "US"
    assert ctr.type_family("TIMESTAMP WITH TIME ZONE") == "temporal"
    with pytest.raises(ValueError):
        ctr.cast_value("x", "INTEGER")
