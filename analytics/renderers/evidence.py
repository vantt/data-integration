"""Render Evidence projects (one per permission area) from the catalog, report specs and registry.

  python3 -m analytics render evidence --tenant fine_japan [--check]

For every non-legacy area in the tenant profile (`access.areas`) and every catalog report with
`engine: evidence` in that area, it writes under evidence/areas/<area>/:

  evidence.config.yaml                         basePath /<area> (one static build per area)
  sources/datalake/connection.yaml             DuckDB source; the builder copies olap.duckdb next to it
  sources/datalake/<report>__<card>.sql        compiled SQL of one card: the extract holds only its result
  sources/datalake/<report>__meta.sql          as_of, period bounds, freshness
  pages/index.md, pages/<report>/index.md      pages reading only those extracts

Every file is generated (banner + hash of the inputs) and the output is byte-identical for the same
inputs. A card showing costs is left out of areas that cannot view costs (its SQL is not written).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..compiler.cards import comparison_window, compile_card, compile_meta
from ..compiler.loader import REPO_ROOT, Registry, load_spec, spec_file
from ..compiler.spec_validate import card_cost_sensitive, iter_cards, metric_refs, simple_components
from ..compiler.sql import AsOf, Compiler

RENDERER_VERSION = 1
SOURCE = "datalake"
OUT_DIR = REPO_ROOT / "evidence" / "areas"
COMPARISON_TITLE = {"prev_week_full": "tuần trước", "prev_wtd_same_span": "cùng kỳ tuần trước", "prev_month": "tháng trước"}
AXIS_TITLE = {"order_date": "theo ngày đặt đơn", "return_date": "theo ngày hoàn", "settlement_date": "theo ngày đối soát"}
UNIT_FMT = {"currency": "#,##0", "count": "#,##0", "percent": '0.0"%"', "ratio": "0.00", "index": "0.00"}
OUTPUT_FMT = {"currency": "#,##0", "integer": "#,##0", "number": "#,##0.##", "percent": '0.0"%"'}
NO_COST_NOTE = "Cần quyền xem chi phí để xem thẻ này."


@dataclass(frozen=True)
class Rendered:
    files: dict[str, str]  # path relative to evidence/areas -> content
    areas: list[str]


def _attr(text: str) -> str:
    """Safe value for a double-quoted Svelte attribute."""
    return (str(text).replace("&", "&amp;").replace('"', "&quot;").replace("{", "&#123;").replace("}", "&#125;")
            .replace("<", "&lt;"))


def _md(text: str) -> str:
    return str(text).replace("{", "&#123;").replace("}", "&#125;").replace("<", "&lt;")


def _input_hash(reg: Registry, spec_path: Path, report: dict[str, Any], profile_path: Path) -> str:
    h = hashlib.sha256(f"evidence-renderer-v{RENDERER_VERSION}\n".encode())
    paths = sorted(reg.root.glob("semantic/*.yml")) + sorted(reg.root.glob("metrics/*.yml"))
    for path in paths + [spec_path, profile_path]:
        h.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    h.update(json.dumps(report, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()[:16]


def _fmt(reg: Registry, metric_id: str, decimals: int | None) -> str:
    unit = reg.metrics[metric_id]["unit"]
    if decimals is not None:
        base = "0" if decimals == 0 else "0." + "0" * decimals
        if unit in ("currency", "count"):
            base = "#,##" + base
        return base + ('"%"' if unit == "percent" else "")
    return UNIT_FMT[unit]


def _label(reg: Registry, metric_id: str) -> str:
    return reg.metrics[metric_id]["label"]["vi"]


class _Page:
    def __init__(self, reg: Registry, report: dict[str, Any], spec: dict[str, Any], area: dict[str, Any],
                 profile: dict[str, Any], digest: str, source_rel: str):
        self.reg, self.report, self.spec, self.area, self.profile = reg, report, spec, area, profile
        self.digest, self.source_rel = digest, source_rel
        self.queries: list[str] = []
        self.used_metrics: set[str] = set()

    def query(self, name: str, select_extra: str = "") -> None:
        cols = "*" + (f", {select_extra}" if select_extra else "")
        self.queries.append(f"```sql {name}\nselect {cols} from {SOURCE}.{self.report['id']}__{name}\n```")

    # -------------------------------------------------------------- cards
    def card(self, card: dict[str, Any]) -> str:
        kind, cid = card["kind"], card["card_id"]
        title = card["title"]["vi"]
        if kind == "text":
            return _md(card["text"])
        if kind == "meta_period":
            return ('📅 Tuần này: <Value data={meta} column=week_start fmt="dd/mm/yyyy"/> – '
                    '<Value data={meta} column=as_of fmt="dd/mm/yyyy"/> · So với tuần trước: '
                    '<Value data={meta} column=prev_week_start fmt="dd/mm/yyyy"/> – '
                    '<Value data={meta} column=prev_week_end fmt="dd/mm/yyyy"/>')
        if kind == "meta_freshness":
            text = '🕐 Đơn cuối: <Value data={meta} column=last_event_at fmt="dd/mm/yyyy hh:mm"/>'
            if self.has_coverage:
                text += ' · Độ phủ giá vốn 30 ngày: <Value data={meta} column=cost_coverage_30d fmt=\'0.0"%"\'/>'
            return text
        if card_cost_sensitive(self.reg, card) and not self.area["can_view_cost"]:
            return f'<Note>\n**{_md(title)}**: {NO_COST_NOTE}\n</Note>'
        refs = metric_refs(card)
        self.used_metrics.update(refs)
        if kind == "inline_sql":
            return self._inline(card)
        if kind in ("kpi_compare", "derived"):
            return self._kpi(card, refs[0])
        if kind in ("trend", "breakdown", "breakdown_compare", "table"):
            return self._chart(card, refs)
        raise ValueError(f"unknown card kind {kind}")

    def _kpi(self, card: dict[str, Any], mid: str) -> str:
        cid = card["card_id"]
        fmt = _fmt(self.reg, mid, card.get("decimals"))
        desc = self.reg.metrics[mid]["description"]
        base = f'data={{{cid}}} value={mid} title="{_attr(card["title"]["vi"])}" fmt=\'{fmt}\' description="{_attr(desc)}"'
        cmp = comparison_window(card)
        if cmp:
            unit = self.reg.metrics[mid]["unit"]
            if unit == "percent":
                self.query(cid, f"{mid} - {mid}__cmp AS {mid}__delta")
                cfmt = '0.0" đ.%"'
            else:
                self.query(cid, f"({mid} - {mid}__cmp) / NULLIF(ABS({mid}__cmp), 0) AS {mid}__delta")
                cfmt = "+0.0%;-0.0%"
            ctitle = "so với " + COMPARISON_TITLE[card["comparison"]]
            return f"<BigValue {base} comparison={mid}__delta comparisonTitle=\"{ctitle}\" comparisonFmt='{cfmt}'/>"
        if card.get("goal"):
            goal = self.profile["tenant_params"][card["goal"]["param"]]
            self.query(cid, f"{goal} AS goal, {mid} * 100.0 / NULLIF({goal}, 0) AS pct_of_goal")
            gtitle = f"% mục tiêu {goal:,.0f}".replace(",", ".") if isinstance(goal, (int, float)) else "% mục tiêu"
            return (f"<BigValue {base} comparison=pct_of_goal comparisonTitle=\"{_attr(gtitle)}\" "
                    f"comparisonFmt='0.0\"%\"' comparisonDelta=false/>")
        if card.get("bands"):
            cases = " ".join(f"WHEN {mid} <= {b['max']} THEN '{b['label']}'" for b in card["bands"])
            self.query(cid, f"CASE WHEN {mid} IS NULL THEN NULL {cases} ELSE '{card['bands'][-1]['label']}' END AS band")
            return f"<BigValue {base}/>\n\nMức: **<Value data={{{cid}}} column=band/>**"
        self.query(cid)
        return f"<BigValue {base}/>"

    def _chart(self, card: dict[str, Any], refs: list[str]) -> str:
        cid, viz, kind = card["card_id"], card["viz"], card["kind"]
        title = _attr(card["title"]["vi"])
        self.query(cid)
        dims = [d.split(".", 1)[1] for d in card.get("dimensions", [])]
        x = "day" if card.get("grain") == "day" else (card.get("grain") or (dims[0] if dims else None))
        fmt = _fmt(self.reg, refs[0], card.get("decimals"))
        if viz in ("data-table", "data-table-formatted"):
            cols = [f'  <Column id={d} title="{_attr(self._dim_label(card, d))}"/>' for d in dims]
            cols += [f'  <Column id={m} title="{_attr(_label(self.reg, m))}" fmt=\'{_fmt(self.reg, m, None)}\'/>' for m in refs]
            if kind == "breakdown_compare":
                ctitle = COMPARISON_TITLE[card["comparison"]]
                cols += [f'  <Column id={m}__cmp title="{_attr(_label(self.reg, m))} ({ctitle})" fmt=\'{_fmt(self.reg, m, None)}\'/>'
                         for m in refs]
                if card.get("pct_change_of"):
                    p = card["pct_change_of"]
                    dec = card.get("decimals", 1)
                    pfmt = ("0" if dec == 0 else "0." + "0" * dec) + '"%"'
                    cols.append(f'  <Column id={p}__pct_change title="Thay đổi % so với {ctitle}" fmt=\'{pfmt}\' contentType=delta/>')
            return f'<DataTable data={{{cid}}} title="{title}" rows=all>\n' + "\n".join(cols) + "\n</DataTable>"
        if kind == "breakdown_compare":
            ys = [refs[0], f"{refs[0]}__cmp"]
            return (f'<BarChart data={{{cid}}} x={x} y={{{json.dumps(ys)}}} type=grouped title="{title}" '
                    f"yFmt='{fmt}' labels=false/>")
        y = refs[0] if len(refs) == 1 else "{" + json.dumps(refs) + "}"
        if viz in ("area-chart", "stacked-area"):
            return f"<AreaChart data={{{cid}}} x={x} y={y} title=\"{title}\" yFmt='{fmt}'/>"
        if viz in ("line-chart", "multi-line-chart"):
            return f"<LineChart data={{{cid}}} x={x} y={y} title=\"{title}\" yFmt='{fmt}'/>"
        if viz in ("stacked-bar", "stacked-bar-time"):
            return f"<BarChart data={{{cid}}} x={x} y={y} type=stacked title=\"{title}\" yFmt='{fmt}'/>"
        swap = " swapXY=true" if viz in ("horizontal-bar", "donut") else ""
        return f"<BarChart data={{{cid}}} x={x} y={y}{swap} title=\"{title}\" yFmt='{fmt}' labels=true/>"

    def _dim_label(self, card: dict[str, Any], dim_name: str) -> str:
        for ref in card.get("dimensions", []):
            model_id, name = ref.split(".", 1)
            if name == dim_name:
                dim = next(d for d in self.reg.semantic[model_id].get("dimensions", []) if d["name"] == name)
                return (dim.get("label") or {}).get("vi", name)
        return dim_name

    def _inline(self, card: dict[str, Any]) -> str:
        cid = card["card_id"]
        outputs = card["inline_sql"]["outputs"]
        extra = []
        for out in outputs:
            if out.get("link"):
                template = str(self.profile["tenant_params"][out["link"]["param"]])
                sql = "'" + template.replace("'", "''") + "'"
                for col in sorted(set(re.findall(r"{([a-z_][a-z0-9_]*)}", template))):
                    sql = f"replace({sql}, '{{{col}}}', CAST({col} AS VARCHAR))"
                extra.append(f"{sql} AS {out['name']}__url")
        self.query(cid, ", ".join(extra))
        visible = [o for o in outputs if not o.get("hidden")]
        if card["viz"] in ("single-value", "single-value-with-trend") and len(visible) == 1:
            o = visible[0]
            return (f'<BigValue data={{{cid}}} value={o["name"]} title="{_attr(card["title"]["vi"])}" '
                    f"fmt='{OUTPUT_FMT.get(o['type'], '#,##0')}'/>")
        cols = []
        for o in visible:
            label = _attr(o.get("label", o["name"]))
            if o.get("link"):
                cols.append(f'  <Column id={o["name"]}__url title="{label}" contentType=link linkLabel={o["name"]} openInNewTab=true/>')
            elif o["type"] in OUTPUT_FMT:
                cols.append(f"  <Column id={o['name']} title=\"{label}\" fmt='{OUTPUT_FMT[o['type']]}'/>")
            else:
                cols.append(f'  <Column id={o["name"]} title="{label}"/>')
        return (f'<DataTable data={{{cid}}} title="{_attr(card["title"]["vi"])}" rows=20 search=true>\n'
                + "\n".join(cols) + "\n</DataTable>")

    # -------------------------------------------------------------- page
    @property
    def has_coverage(self) -> bool:
        return self.coverage_metric is not None

    @property
    def coverage_metric(self) -> str | None:
        for _, _, card in iter_cards(self.spec):
            for mid in metric_refs(card):
                cov = self.reg.metrics.get(mid, {}).get("coverage_metric")
                if cov:
                    return cov
        return None

    def render(self) -> str:
        body: list[str] = []
        for tab in self.spec["tabs"]:
            body.append(f'<Tab label="{_attr(tab["title"]["vi"])}">\n')
            for block in tab["blocks"]:
                if block.get("title"):
                    body.append(f"### {_md(block['title']['vi'])}\n\n*{AXIS_TITLE[block['time_axis']]}*\n")
                rows: dict[int, list[dict[str, Any]]] = {}
                for card in block["cards"]:
                    rows.setdefault((card.get("position") or {}).get("row", 0), []).append(card)
                for row in sorted(rows):
                    cards = sorted(rows[row], key=lambda c: (c.get("position") or {}).get("col", 0))
                    parts = []
                    for c in cards:
                        part = self.card(c)
                        if c.get("time_axis") and c["time_axis"] != block["time_axis"]:
                            part += f"\n\n*{AXIS_TITLE[c['time_axis']]}*"
                        parts.append(part)
                    if len(parts) > 1:
                        body.append(f"<Grid cols={len(parts)}>\n\n" + "\n\n".join(parts) + "\n\n</Grid>\n")
                    else:
                        body.append(parts[0] + "\n")
            body.append("</Tab>\n")
        header = [
            "---",
            f"title: {self.spec['title']['vi']}",
            "---",
            "",
            f"<!-- GENERATED by `python3 -m analytics render evidence` from {self.source_rel}, analytics/registry/ "
            f"and the tenant profile (inputs sha256 {self.digest}). Do not edit by hand. -->",
            "",
            "```sql meta",
            f"select * from {SOURCE}.{self.report['id']}__meta",
            "```",
            "",
        ]
        page = "\n".join(header) + "\n\n".join(self.queries) + "\n\n"
        page += ('<Alert status="info">\nDữ liệu đến hết ngày <Value data={meta} column=as_of fmt="dd/mm/yyyy"/> '
                 f"· {_md(self.spec['question'])}\n</Alert>\n\n")
        page += "<Tabs>\n\n" + "\n".join(body) + "</Tabs>\n\n" + self.footer()
        return page

    def footer(self) -> str:
        rev = self.profile["revenue"]
        recog = {"order_created": "theo ngày tạo đơn", "delivered": "theo ngày giao thành công"}[rev["recognition_date"]]
        vat = {"excluded": "đã trừ VAT", "included": "gồm VAT", "none": "không có VAT"}[rev["vat"]]
        lines = [
            "## Doanh thu được tính thế nào",
            "",
            f"- Doanh thu ghi nhận {recog}; doanh thu bán hàng tính sau chiết khấu, {vat}, trước hàng hoàn.",
            "- Hàng hoàn trừ vào kỳ hoàn, không sửa lại kỳ của đơn gốc.",
            f"- Không tính đơn ở trạng thái: {', '.join(rev['excluded_statuses'])}.",
        ]
        if self.area["can_view_cost"] and any(self.reg.metrics[m].get("cost_sensitive") for m in self.used_metrics):
            lines.append("- Chỉ tiêu lãi và biên chỉ tính trên đơn có giá vốn; độ phủ giá vốn 30 ngày ở dòng \"Độ tươi dữ liệu\".")
        lines += ["", "### Chỉ tiêu trên trang", ""]
        for mid in sorted(self.used_metrics):
            m = self.reg.metrics[mid]
            lines.append(f"- **{_md(m['label']['vi'])}** (`{mid}`): {_md(m['description'])}")
        return "\n".join(lines) + "\n"


def _sql_banner(digest: str, what: str) -> str:
    return f"-- GENERATED by `python3 -m analytics render evidence` ({what}; inputs sha256 {digest}). Do not edit by hand.\n"


def render_tenant(reg: Registry, profile: dict[str, Any], profile_path: Path, catalog: dict[str, Any],
                  catalog_path: Path) -> Rendered:
    compiler = Compiler(reg, profile)
    as_of = AsOf.runtime(profile["locale"]["timezone"])
    files: dict[str, str] = {}
    areas = [a for a in (profile.get("access") or {}).get("areas", []) if not a.get("legacy")]
    plugins = ('plugins:\n  components:\n    "@evidence-dev/core-components": {}\n'
               '  datasources:\n    "@evidence-dev/duckdb": {}\n')
    for area in areas:
        aid = area["id"]
        reports = [r for r in catalog["reports"] if r["engine"] == "evidence" and r["area"] == aid]
        files[f"{aid}/evidence.config.yaml"] = (
            "# GENERATED by `python3 -m analytics render evidence`. Do not edit by hand.\n"
            f"deployment:\n  basePath: /{aid}\n" + plugins)
        files[f"{aid}/sources/{SOURCE}/connection.yaml"] = (
            "# GENERATED by `python3 -m analytics render evidence`. The builder copies the serving catalog\n"
            "# (data_lake/serving/olap.duckdb) next to this file as olap-serving.duckdb before `evidence sources`.\n"
            f"name: {SOURCE}\ntype: duckdb\noptions:\n  filename: olap-serving.duckdb\n")
        index = ["---", f"title: {area['title']}", "---", "",
                 "<!-- GENERATED by `python3 -m analytics render evidence`. Do not edit by hand. -->", "",
                 f"# {_md(area['title'])}", ""]
        for report in sorted(reports, key=lambda r: r["id"]):
            spath = spec_file(catalog_path, report["spec"])
            spec = load_spec(spath)
            digest = _input_hash(reg, spath, report, profile_path)
            rel = str(spath.resolve().relative_to(REPO_ROOT)) if spath.resolve().is_relative_to(REPO_ROOT) else spath.name
            page = _Page(reg, report, spec, area, profile, digest, rel)
            for _, _, card in iter_cards(spec):
                if card_cost_sensitive(reg, card) and not area["can_view_cost"]:
                    continue
                sql = compile_card(compiler, card, as_of)
                if sql is not None:
                    files[f"{aid}/sources/{SOURCE}/{report['id']}__{card['card_id']}.sql"] = (
                        _sql_banner(digest, f"{rel}#{card['card_id']}") + sql)
            first = next((m for _, _, c in iter_cards(spec) for m in metric_refs(c)
                          if reg.metrics[m]["type"] == "simple"), None)
            comp = simple_components(reg, first)[0] if first else None
            coverage = page.coverage_metric
            meta = compile_meta(compiler, as_of, comp["model"] if comp else "orders",
                                comp.get("filters", []) if comp else [], coverage)
            files[f"{aid}/sources/{SOURCE}/{report['id']}__meta.sql"] = _sql_banner(digest, f"{rel} meta") + meta
            files[f"{aid}/pages/{report['id']}/index.md"] = page.render()
            index.append(f"- [{_md(report['title'])}](/{report['id']}) — {_md(report['question'])}")
        files[f"{aid}/pages/index.md"] = "\n".join(index) + "\n"
    return Rendered(files=dict(sorted(files.items())), areas=[a["id"] for a in areas])


def write(rendered: Rendered, out_dir: Path = OUT_DIR) -> list[str]:
    """Write the files and delete stale generated files of the rendered areas. Returns changed paths."""
    changed = []
    for rel, content in rendered.files.items():
        path = out_dir / rel
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        changed.append(rel)
    for aid in rendered.areas:
        area_dir = out_dir / aid
        for sub in ("pages", "sources"):
            for path in sorted((area_dir / sub).rglob("*")) if (area_dir / sub).exists() else []:
                rel = str(path.relative_to(out_dir))
                if path.is_file() and rel not in rendered.files:
                    path.unlink()
                    changed.append(rel + " (deleted)")
    return changed


def stale(rendered: Rendered, out_dir: Path = OUT_DIR) -> list[str]:
    """Paths whose content differs from a fresh render (for --check)."""
    out = [rel for rel, content in rendered.files.items()
           if not (out_dir / rel).exists() or (out_dir / rel).read_text(encoding="utf-8") != content]
    for aid in rendered.areas:
        for sub in ("pages", "sources"):
            base = out_dir / aid / sub
            for path in sorted(base.rglob("*")) if base.exists() else []:
                if path.is_file() and str(path.relative_to(out_dir)) not in rendered.files:
                    out.append(str(path.relative_to(out_dir)))
    return out
