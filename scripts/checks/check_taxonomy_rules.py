"""Classification rule validator (stdlib + PyYAML). Run before the rule seeds are loaded.

  python3 scripts/checks/check_taxonomy_rules.py            # exit 0 when every rule is valid, 1 otherwise
  python3 scripts/checks/check_taxonomy_rules.py --repo DIR # check another checkout or worktree

Reads, from the repository:
  transformation/dbt_project.yml        vars.taxonomy (registry: features, domains) and vars.tenant
  seeds/taxonomy/taxonomy_rule_product.csv                   product default layer
  seeds/tenants/<tenant>/taxonomy_rule_tenant.csv            tenant layer (vars.tenant set)
  seeds/defaults/taxonomy_rule_tenant__default.csv           tenant layer when vars.tenant is ""
  seeds/tenants/<tenant>/taxonomy_label.csv                  label sets (or defaults/taxonomy_label__default.csv)
  seeds/taxonomy/taxonomy_canonical.csv                      canonical codes per domain

A tenant rule's label is a tenant label: it must be in taxonomy_label for the domain's label_set.
A product rule's label is a canonical code: it must be a code of taxonomy_canonical whose domain is
the label_set (its *_std is the code itself), other than UNMAPPED and UNKNOWN, which only the engine
assigns. Tenants override product rules with their own labels.

One CSV row is one condition. Rows sharing a rule_id inside a layer form one rule (conditions
joined by AND). A rule whose rows all have enabled=false and no label is a *disable marker*: it
turns off the rule with that rule_id defined in the other layer. Semantics and the registry
schema: docs/architecture/taxonomy-engine.md "Hiện thực MVP".

Errors (exit 1): wrong header; registry inconsistent; domain not in the registry or a selftest
domain (its rules live in unit tests); feature not
declared for the domain; operator not allowed for the feature type; value not castable to the
feature type; between without either bound; label not in the domain's label set; rule attributes
differing between the rows of one rule_id; a product-rule label that is not a canonical code; two rule_ids with the same (domain, layer, priority) in
a FIRST/UNIQUE domain; an unconditional rule in a COLLECT domain; a disable marker pointing to a
rule_id defined in no layer.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COLUMNS = ["rule_id", "domain", "priority", "label", "feature", "op", "value", "value_to", "enabled", "note"]
LAYERS = ("tenant", "product")  # evaluation order: tenant layer first
ENGINE_RESERVED = {"UNMAPPED", "UNKNOWN"}  # assigned by the engine itself, never by a rule
HIT_POLICIES = {"FIRST", "UNIQUE", "COLLECT"}
CARDINALITIES = {"single", "multi"}

# Operators per feature type family. `is_null` is allowed on every type.
OPS_BY_FAMILY = {
    "string": {"like", "eq", "in", "not_in", "starts_with", "contains", "regex", "is_null"},
    "number": {"eq", "in", "not_in", "between", "is_null"},
    "temporal": {"eq", "in", "not_in", "between", "is_null"},
    "boolean": {"eq", "is_null"},
    "list": {"has", "is_null"},
}
ALL_OPS = set().union(*OPS_BY_FAMILY.values())

_INT = {"TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT",
        "UINTEGER", "UBIGINT"}
_FLOAT = {"DOUBLE", "FLOAT", "REAL"}
_STRING = {"VARCHAR", "TEXT", "STRING"}
_DECIMAL = re.compile(r"^(DECIMAL|NUMERIC)(\(\s*\d+\s*(,\s*\d+\s*)?\))?$")


class RegistryError(Exception):
    """vars.taxonomy cannot be read at all."""


def _norm_type(t: str) -> str:
    return re.sub(r"\s+", " ", str(t).strip().upper())


def type_family(duckdb_type: str) -> str | None:
    """Family of a DuckDB type name, or None when the type is not supported for features."""
    t = _norm_type(duckdb_type)
    if t.endswith("[]"):
        return "list"
    if t in _INT or t in _FLOAT or _DECIMAL.match(t):
        return "number"
    if t in {"DATE", "TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"}:
        return "temporal"
    if t == "BOOLEAN":
        return "boolean"
    if t in _STRING:
        return "string"
    return None


def element_type(list_type: str) -> str:
    return _norm_type(list_type)[:-2]


def cast_value(raw: str, duckdb_type: str) -> object:
    """Cast a rule operand to the feature type; raise ValueError when it does not fit."""
    t = _norm_type(duckdb_type)
    fam = type_family(t)
    if fam == "list":
        return cast_value(raw, element_type(t))
    if fam == "string":
        return raw
    if fam == "boolean":
        low = raw.strip().lower()
        if low not in {"true", "false"}:
            raise ValueError("expected true or false")
        return low == "true"
    if fam == "number":
        if t in _INT:
            return int(raw.strip())
        if t in _FLOAT:
            return float(raw.strip())
        try:
            return Decimal(raw.strip())
        except InvalidOperation as e:
            raise ValueError("not a decimal") from e
    if fam == "temporal":
        if t == "DATE":
            return date.fromisoformat(raw.strip())
        return datetime.fromisoformat(raw.strip())
    raise ValueError(f"unsupported type {duckdb_type}")


@dataclass
class Row:
    layer: str
    file: str
    line: int
    values: dict[str, str]

    def get(self, col: str) -> str:
        return (self.values.get(col) or "").strip()

    @property
    def where(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class Inputs:
    registry: dict
    tenant: str
    rule_files: dict[str, Path]                 # layer -> csv
    label_file: Path
    canonical_file: Path
    default_rule_file: Path | None = None       # header-only default, checked when a tenant is set
    errors: list[str] = field(default_factory=list)


def load_inputs(repo: Path) -> Inputs:
    project = repo / "transformation" / "dbt_project.yml"
    try:
        doc = yaml.safe_load(project.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise RegistryError(f"cannot read {project}: {e}") from e
    vars_ = doc.get("vars") or {}
    if "taxonomy" not in vars_:
        raise RegistryError(f"{project}: vars.taxonomy is missing")
    registry = vars_.get("taxonomy") or {}
    tenant = str(vars_.get("tenant") or "")
    seeds = repo / "transformation" / "seeds"
    default_rules = seeds / "defaults" / "taxonomy_rule_tenant__default.csv"
    if tenant:
        tenant_rules = seeds / "tenants" / tenant / "taxonomy_rule_tenant.csv"
        labels = seeds / "tenants" / tenant / "taxonomy_label.csv"
    else:
        tenant_rules = default_rules
        labels = seeds / "defaults" / "taxonomy_label__default.csv"
    return Inputs(
        registry=registry,
        tenant=tenant,
        rule_files={"product": seeds / "taxonomy" / "taxonomy_rule_product.csv", "tenant": tenant_rules},
        label_file=labels,
        canonical_file=seeds / "taxonomy" / "taxonomy_canonical.csv",
        default_rule_file=default_rules if tenant else None,
    )


def _rel(repo: Path, p: Path) -> str:
    try:
        return str(p.relative_to(repo))
    except ValueError:
        return str(p)


def read_rules(path: Path, layer: str, display: str, errors: list[str]) -> list[Row]:
    if not path.is_file():
        errors.append(f"{display}: file not found")
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        if header != COLUMNS:
            errors.append(f"{display}: header {header} != {COLUMNS}")
            return []
        rows = []
        for rec in reader:
            if None in rec:  # more cells than columns
                errors.append(f"{display}:{reader.line_num}: more cells than the {len(COLUMNS)} columns")
                continue
            if not any((v or "").strip() for v in rec.values()):
                continue
            rows.append(Row(layer, display, reader.line_num, rec))
        return rows


def read_labels(path: Path, display: str, errors: list[str]) -> dict[str, set[str]]:
    """label_set (taxonomy_label.domain) -> labels."""
    if not path.is_file():
        errors.append(f"{display}: file not found")
        return {}
    out: dict[str, set[str]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"domain", "label"} - set(reader.fieldnames or [])
        if missing:
            errors.append(f"{display}: missing columns {sorted(missing)}")
            return {}
        for rec in reader:
            out.setdefault((rec["domain"] or "").strip(), set()).add(rec["label"] or "")
    return out


def read_canonical(path: Path, display: str, errors: list[str]) -> dict[str, set[str]]:
    """Canonical domain -> codes a product rule may assign (UNMAPPED and UNKNOWN excluded)."""
    if not path.is_file():
        errors.append(f"{display}: file not found")
        return {}
    out: dict[str, set[str]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"domain", "code"} - set(reader.fieldnames or [])
        if missing:
            errors.append(f"{display}: missing columns {sorted(missing)}")
            return {}
        for rec in reader:
            code = (rec["code"] or "").strip()
            if code and code not in ENGINE_RESERVED:
                out.setdefault((rec["domain"] or "").strip(), set()).add(code)
    return out


def check_registry(registry: dict, label_sets: dict[str, set[str]],
                   canonical: dict[str, set[str]] | None = None) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Validate vars.taxonomy. Returns (errors, domain -> {feature column: duckdb type})."""
    errors: list[str] = []
    features = registry.get("features")
    domains = registry.get("domains")
    if not isinstance(features, dict) or not isinstance(domains, dict):
        return ["vars.taxonomy: `features` and `domains` must be mappings ({} when empty)"], {}

    for model, spec in features.items():
        where = f"vars.taxonomy.features.{model}"
        if not isinstance(spec, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        for key in ("subject", "key"):
            if not spec.get(key):
                errors.append(f"{where}: `{key}` is required")
        cols = spec.get("columns")
        if not isinstance(cols, dict) or not cols:
            errors.append(f"{where}: `columns` must map column -> DuckDB type")
            continue
        for col, typ in cols.items():
            if type_family(str(typ)) is None:
                errors.append(f"{where}.columns.{col}: unsupported type {typ!r}")
            elif type_family(str(typ)) == "list" and type_family(element_type(str(typ))) in (None, "list"):
                errors.append(f"{where}.columns.{col}: unsupported list element type {typ!r}")

    domain_columns: dict[str, dict[str, str]] = {}
    for name, spec in domains.items():
        where = f"vars.taxonomy.domains.{name}"
        if not isinstance(spec, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        hit = spec.get("hit_policy")
        card = spec.get("cardinality")
        if hit not in HIT_POLICIES:
            errors.append(f"{where}: hit_policy {hit!r} not in {sorted(HIT_POLICIES)}")
        if card not in CARDINALITIES:
            errors.append(f"{where}: cardinality {card!r} not in {sorted(CARDINALITIES)}")
        elif hit in HIT_POLICIES and (hit == "COLLECT") != (card == "multi"):
            errors.append(f"{where}: hit_policy COLLECT goes with cardinality multi, FIRST/UNIQUE with single")
        if not spec.get("subject"):
            errors.append(f"{where}: `subject` is required")
        label_set = spec.get("label_set")
        if not label_set:
            errors.append(f"{where}: `label_set` is required")
        fmodels = spec.get("features")
        if not isinstance(fmodels, list) or not fmodels:
            errors.append(f"{where}: `features` must list at least one feature model")
            fmodels = []
        cols: dict[str, str] = {}
        keys = {(features.get(fm) or {}).get("key") for fm in fmodels if isinstance(features.get(fm), dict)}
        if len(keys) > 1:
            errors.append(f"{where}: feature models must share one key column (found {sorted(map(str, keys))})")
        for fm in fmodels:
            fspec = features.get(fm)
            if not isinstance(fspec, dict):
                errors.append(f"{where}: feature model {fm!r} not declared in vars.taxonomy.features")
                continue
            if fspec.get("subject") != spec.get("subject"):
                errors.append(f"{where}: feature model {fm!r} has subject {fspec.get('subject')!r}, "
                              f"domain has {spec.get('subject')!r}")
            for col, typ in (fspec.get("columns") or {}).items():
                if col in cols:
                    errors.append(f"{where}: feature column {col!r} declared by two feature models")
                cols[col] = str(typ)
        domain_columns[name] = cols
        for col in spec.get("required_features") or []:
            if col not in cols:
                errors.append(f"{where}: required_features {col!r} is not a feature of the domain")
        # Selftest domains take their labels from unit test fixtures, not from taxonomy_label.
        # A flag may name a tenant label or a canonical code (the label of a product rule).
        allowed_flags = label_sets.get(label_set, set()) | (canonical or {}).get(label_set, set())
        for lab in spec.get("matched_flags") or []:
            if label_set and not spec.get("selftest") and lab not in allowed_flags:
                errors.append(f"{where}: matched_flags {lab!r} neither in label set {label_set!r} "
                              "nor a canonical code of it")
        survey = spec.get("survey")
        if survey is not None:
            if not isinstance(survey, dict):
                errors.append(f"{where}: `survey` must be a mapping")
            else:
                for col in survey.get("features") or []:
                    if col not in cols:
                        errors.append(f"{where}: survey feature {col!r} is not a feature of the domain")
        if "selftest" in spec and not isinstance(spec.get("selftest"), bool):
            errors.append(f"{where}: `selftest` must be true or false")
    return errors, domain_columns


def _check_condition(row: Row, ftype: str, errors: list[str]) -> None:
    op, value, value_to = row.get("op"), row.get("value"), row.get("value_to")
    fam = type_family(ftype)
    feature = row.get("feature")
    prefix = f"{row.where}: rule {row.get('rule_id')!r}"
    if op not in ALL_OPS:
        errors.append(f"{prefix}: op {op!r} not in {sorted(ALL_OPS)}")
        return
    if op not in OPS_BY_FAMILY.get(fam or "", set()):
        errors.append(f"{prefix}: op {op!r} not allowed on feature {feature!r} of type {ftype}")
        return
    if op != "between" and value_to:
        errors.append(f"{prefix}: value_to is only used by between")
    if op == "is_null":
        if value and value.lower() not in {"true", "false"}:
            errors.append(f"{prefix}: is_null takes an empty value (IS NULL) or true/false")
        return
    if op == "between":
        if not value and not value_to:
            errors.append(f"{prefix}: between needs value, value_to or both")
            return
        bounds = []
        for raw in (value, value_to):
            if not raw:
                continue
            try:
                bounds.append(cast_value(raw, ftype))
            except ValueError as e:
                errors.append(f"{prefix}: value {raw!r} is not {ftype} ({e})")
                return
        if len(bounds) == 2 and not bounds[0] < bounds[1]:  # type: ignore[operator]  # same family, comparable
            errors.append(f"{prefix}: between needs value < value_to ([value, value_to))")
        return
    if not value:
        errors.append(f"{prefix}: op {op!r} needs a value")
        return
    parts = value.split("|") if op in {"in", "not_in"} else [value]
    for part in parts:
        if op in {"in", "not_in"} and part == "":
            errors.append(f"{prefix}: empty item in {op} list {value!r}")
            continue
        try:
            cast_value(part, ftype)
        except ValueError as e:
            errors.append(f"{prefix}: value {part!r} is not {ftype} ({e})")
    if op == "regex":
        try:
            re.compile(value)
        except re.error as e:
            errors.append(f"{prefix}: invalid regex {value!r} ({e})")


def _bool(raw: str) -> bool | None:
    low = raw.strip().lower()
    return {"true": True, "false": False}.get(low)


def check_rules(rows: list[Row], registry: dict, domain_columns: dict[str, dict[str, str]],
                label_sets: dict[str, set[str]], canonical: dict[str, set[str]] | None = None) -> list[str]:
    errors: list[str] = []
    domains = registry.get("domains") or {}

    # Row-level checks.
    groups: dict[tuple[str, str], list[Row]] = {}
    for row in rows:
        rid, dom = row.get("rule_id"), row.get("domain")
        if not rid:
            errors.append(f"{row.where}: rule_id is empty")
            continue
        if _bool(row.get("enabled")) is None:
            errors.append(f"{row.where}: rule {rid!r}: enabled must be true or false, got {row.get('enabled')!r}")
        if not dom:
            errors.append(f"{row.where}: rule {rid!r}: domain is empty")
        elif dom not in domains:
            errors.append(f"{row.where}: rule {rid!r}: domain {dom!r} not in vars.taxonomy.domains")
        elif isinstance(domains[dom], dict) and domains[dom].get("selftest"):
            errors.append(f"{row.where}: rule {rid!r}: domain {dom!r} is a selftest domain (rules live in its unit tests)")
        groups.setdefault((row.layer, rid), []).append(row)

    # Rule-level checks: definitions and disable markers.
    definitions: dict[tuple[str, str], dict] = {}   # (layer, rule_id) -> attrs
    markers: list[tuple[str, str, Row]] = []
    for (layer, rid), grp in groups.items():
        first = grp[0]
        is_marker = all(_bool(r.get("enabled")) is False and not r.get("label") for r in grp)
        if is_marker:
            for r in grp:
                if r.get("feature") or r.get("op") or r.get("value") or r.get("value_to"):
                    errors.append(f"{r.where}: rule {rid!r}: a disable row (enabled=false, no label) "
                                  "takes no feature, op or value")
            markers.append((layer, rid, first))
            continue
        attrs = {c: first.get(c) for c in ("domain", "priority", "label", "enabled")}
        for r in grp[1:]:
            for c, v in attrs.items():
                if r.get(c) != v:
                    errors.append(f"{r.where}: rule {rid!r}: {c} {r.get(c)!r} differs from {v!r} "
                                  f"on line {first.line} (rows of one rule_id must agree)")
        if not attrs["label"]:
            errors.append(f"{first.where}: rule {rid!r}: label is empty")
        if not re.fullmatch(r"-?\d+", attrs["priority"]):
            errors.append(f"{first.where}: rule {rid!r}: priority {attrs['priority']!r} is not an integer")
        unconditional = [r for r in grp if not r.get("feature")]
        if unconditional and len(grp) > 1:
            errors.append(f"{unconditional[0].where}: rule {rid!r}: a row without feature (unconditional) "
                          "must be the only row of its rule")
        definitions[(layer, rid)] = dict(attrs, rows=grp, unconditional=bool(unconditional))

        dom = attrs["domain"]
        spec = domains.get(dom)
        if not isinstance(spec, dict):
            continue  # domain error already reported
        label_set = spec.get("label_set")
        if attrs["label"] and label_set and layer == "product":
            if attrs["label"] not in (canonical or {}).get(label_set, set()):
                errors.append(f"{first.where}: rule {rid!r}: product rule label {attrs['label']!r} is not a "
                              f"canonical code of {label_set!r} in taxonomy_canonical (UNMAPPED/UNKNOWN excluded); "
                              "product rules assign canonical codes, tenants override with their own labels")
        elif attrs["label"] and label_set and attrs["label"] not in label_sets.get(label_set, set()):
            errors.append(f"{first.where}: rule {rid!r}: label {attrs['label']!r} not in taxonomy_label "
                          f"for label_set {label_set!r}")
        if unconditional and spec.get("hit_policy") == "COLLECT":
            errors.append(f"{first.where}: rule {rid!r}: unconditional rule in COLLECT domain {dom!r} "
                          "(it would add its label to every subject)")
        cols = domain_columns.get(dom, {})
        for r in grp:
            feat = r.get("feature")
            if not feat:
                if r.get("op") or r.get("value") or r.get("value_to"):
                    errors.append(f"{r.where}: rule {rid!r}: op/value without feature")
                continue
            if feat not in cols:
                errors.append(f"{r.where}: rule {rid!r}: feature {feat!r} not declared for domain {dom!r}")
                continue
            _check_condition(r, cols[feat], errors)

    # A rule_id names one rule: defined in at most one layer.
    by_id: dict[str, list[str]] = {}
    for layer, rid in definitions:
        by_id.setdefault(rid, []).append(layer)
    for rid, layers in sorted(by_id.items()):
        if len(layers) > 1:
            errors.append(f"rule {rid!r} is defined in layers {sorted(layers)}; a rule_id names one rule "
                          "(disable an inherited rule with an enabled=false row, then add a new rule_id)")

    # Disable markers must point at a defined rule of the same domain.
    disabled: set[str] = set()
    for layer, rid, row in markers:
        targets = [(l, a) for (l, r), a in definitions.items() if r == rid]
        if not targets:
            errors.append(f"{row.where}: disable row for rule {rid!r}: no layer defines this rule_id")
            continue
        for _, a in targets:
            if a["domain"] != row.get("domain"):
                errors.append(f"{row.where}: disable row for rule {rid!r}: domain {row.get('domain')!r} "
                              f"!= {a['domain']!r} of the rule")
        disabled.add(rid)

    # FIRST/UNIQUE need a deterministic order: no two effective rules share (domain, layer, priority).
    seen: dict[tuple[str, str, str], str] = {}
    for (layer, rid), a in sorted(definitions.items()):
        spec = domains.get(a["domain"])
        if not isinstance(spec, dict) or spec.get("hit_policy") not in {"FIRST", "UNIQUE"}:
            continue
        if _bool(a["enabled"]) is not True or rid in disabled:
            continue
        key = (a["domain"], layer, a["priority"])
        if key in seen:
            errors.append(f"{a['rows'][0].where}: rule {rid!r}: priority {a['priority']} already used by "
                          f"rule {seen[key]!r} in domain {a['domain']!r}, layer {layer} "
                          f"({spec.get('hit_policy')} needs a strict order)")
        else:
            seen[key] = rid
    return errors


def validate(repo: Path) -> tuple[list[str], str]:
    """Return (errors, summary)."""
    try:
        inp = load_inputs(repo)
    except RegistryError as e:
        return [str(e)], ""
    errors: list[str] = []
    label_sets = read_labels(inp.label_file, _rel(repo, inp.label_file), errors)
    canonical = read_canonical(inp.canonical_file, _rel(repo, inp.canonical_file), errors)
    reg_errors, domain_columns = check_registry(inp.registry, label_sets, canonical)
    errors += reg_errors
    rows: list[Row] = []
    for layer in LAYERS:
        path = inp.rule_files[layer]
        rows += read_rules(path, layer, _rel(repo, path), errors)
    if inp.default_rule_file is not None:
        display = _rel(repo, inp.default_rule_file)
        if read_rules(inp.default_rule_file, "tenant", display, errors):
            errors.append(f"{display}: a core default seed has a header only (no rows)")
    errors += check_rules(rows, inp.registry, domain_columns, label_sets, canonical)
    n_rules = len({(r.layer, r.get("rule_id")) for r in rows})
    summary = (f"{n_rules} rule(s) in {len(rows)} row(s), {len(domain_columns)} domain(s), "
               f"tenant {inp.tenant or '(none)'}")
    return errors, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=REPO, help="checkout to check (default: this one)")
    args = ap.parse_args(argv)
    errors, summary = validate(args.repo.resolve())
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"TAXONOMY RULES: FAIL ({len(errors)} error(s))")
        return 1
    print(f"TAXONOMY RULES: OK ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
