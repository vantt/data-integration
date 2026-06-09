# Semantic Layer & BI Debuggability on DuckDB + dbt
**Date:** 2026-06-05 | **Scope:** Trustworthy, debuggable BI numbers for this stack

---

## The Core Problem, Stated Precisely

When a Metabase dashboard shows a wrong number there are two distinct failure modes:

| Failure mode | Root cause | How to detect |
|---|---|---|
| **Definition wrong** | Metric SQL/filter incorrect in Metabase card | Trace chart → metric SQL → dbt model; unit-test the metric formula |
| **Data wrong** | Upstream model produced bad rows | dbt data tests, freshness checks, dbt-expectations |

The current stack has no clean path for either. Metabase native-SQL cards embed the definition inside Metabase's UI — no git history, no tests, no link back to dbt. Rill has definitions in YAML (already better) but no formal test harness. The fix requires: (1) canonical metric definitions that live in code + version control, (2) explicit data tests on those definitions, (3) a lineage chain from chart → metric → SQL model → source.

---

## Tool Evaluation

### 1. dbt MetricFlow / dbt Semantic Layer

**What it is:** Define metrics once in `_metrics.yml` inside your dbt project. MetricFlow compiles them to engine-specific SQL at query time.

**DuckDB support:** Native DuckDB SQL renderer confirmed; dbt-duckdb adapter tested. CLI queries work locally via `dbt sl query --metrics gross_revenue`. **Critical caveat:** the hosted Semantic Layer API (which lets BI tools consume metrics dynamically) requires **dbt Cloud Team/Enterprise** ($100+/mo). dbt Core users get the engine + CLI only — no API, no BI tool integration without Cloud.

**Lineage:** Metrics point to dbt models; `dbt docs generate` includes metrics in the DAG. Column-level lineage visible in dbt Explorer (Cloud only).

**Testing:** MetricFlow itself has no test commands. But metrics compile to SQL that can be used in `dbt-expectations` `expect_table_aggregation_to_equal_other_table` tests. `dbt test` catches upstream model failures that break a metric.

**Debuggability score:** High for definition provenance (metric YAML → model YAML → SQL), but the runtime query path is invisible unless you run `dbt sl query --explain` in CLI. BI integration (Metabase consuming metrics by name) is gated behind dbt Cloud.

**Fit for this stack:** Medium. Best value today is using MetricFlow YAML as the canonical definition document even without the hosted API — enforce "no new metric lives only in Metabase." The CLI explain output is the best debugging tool you can have for free.

**Adoption effort:** Low (already use dbt; add `packages: dbt-semantic-interfaces`). Effort is high if you want BI consumption — that requires dbt Cloud or a proxy layer.

**License:** dbt Core + MetricFlow = Apache 2.0. Semantic Layer API = proprietary, Cloud only.

---

### 2. Lightdash

**What it is:** Open-source BI that reads dbt project YAML directly. Metrics defined as `meta.metrics` on columns. No separate semantic layer — dbt is the layer.

**DuckDB support:** **BLOCKED.** Issue [#11112](https://github.com/lightdash/lightdash/issues/11112) open since Aug 2024; PR #19866 referenced but unresolved. Lightdash supports DuckDB only via **MotherDuck** (cloud), not local `.duckdb` files. This is a hard blocker for this stack.

**Lineage:** Excellent — every chart shows the dbt model it queries, dimensions/metrics link to YAML definitions. Full upstream DAG visible. Closest to the "chart → metric definition → SQL model → source" dream.

**Testing:** No metric test framework of its own. Relies on dbt tests passing for trust. `dbt test` failures surface as freshness warnings in Lightdash.

**Debuggability score:** Highest of all options *if DuckDB were supported* — definition and chart are the same artifact.

**Fit for this stack:** Currently **not viable** for local DuckDB serving. If/when DuckDB file support lands this would be the strongest fit. MotherDuck route adds cost + architecture change.

**Adoption effort:** High (blocked by DB constraint) → potentially low if DuckDB support ships.

**License:** MIT (self-host via Docker Compose).

---

### 3. Cube (cube.dev)

**What it is:** Standalone semantic layer + API layer. Defines cubes/measures in JS/YAML schema files. Exposes REST, GraphQL, and SQL APIs. Has pre-aggregation caching.

**DuckDB support:** Full. Can connect to local `.duckdb` file via `CUBEJS_DB_DUCKDB_DATABASE_PATH`. Pre-aggregations work (batching strategy; no export buckets). Memory limit configurable. Actively maintained.

**Lineage:** Cube schema (cube YAML/JS) defines measures referencing SQL expressions. No automatic trace back to dbt models — you must manually reference the same column names. No integration with dbt DAG or dbt `sources.yml`. The lineage chain is: Metabase chart → Cube measure → Cube cube SQL → (manually) DuckDB mart.

**Testing:** No native test framework. You can validate by querying Cube's REST API and asserting expected values in a shell script, but there is no CI-native test runner.

**Debuggability score:** Medium. Measures have a single canonical definition (better than Metabase native SQL), but it's a second YAML system parallel to dbt — drift risk is real. The `explain` endpoint shows generated SQL which helps.

**Fit for this stack:** Low-Medium. Cube is optimized for embedded analytics + customer-facing APIs. For internal BI debugging it adds substantial operational weight (Node.js service, Redis for caching, separate schema files). It solves metric definition consistency but doesn't connect to the dbt model graph.

**Adoption effort:** High. New service to deploy + maintain. Schema files must stay in sync with dbt marts manually. Overkill for a single-team internal BI stack.

**License:** Apache 2.0 (Cube Core). Cloud tier separate.

---

### 4. Rill (already in use)

**What it is:** Code-first BI powered by DuckDB. Metrics defined in `metrics/*.yaml` as `measures` + `dimensions`. Already deployed.

**DuckDB support:** Native — DuckDB is Rill's runtime engine. Zero friction.

**Lineage:** Partial. `model:` in metrics YAML points to a Rill SQL model (e.g., `orders_enriched`). That SQL model references DuckDB views (the serving layer). The chain is: Rill dashboard → metrics YAML → `model:` → Rill SQL model → DuckDB view → dbt mart. But this chain is only traceable by reading files; there is no UI that surfaces it. Rill has no concept of "show me the dbt model this came from."

**Testing:** No test framework. No way to assert `gross_revenue = X` for a known time window. Metric correctness is validated by eyeball. This is the biggest gap.

**Validation / "definition correct":** Rill's YAML definitions are version-controlled — that's the best thing about them. The `description:` fields (as seen in this repo's `orders_core_metrics.yaml`) provide semantic documentation. But definitions can silently diverge from dbt mart columns without any error (a renamed column just returns NULL or 0).

**Debuggability score:** Low-Medium. Better than Metabase native SQL because definitions are in git, but no formal test layer and no UI lineage to dbt.

**Fit for this stack:** Already deployed. Incremental improvements (add `dbt-expectations` tests on the mart models Rill consumes, add exposures in dbt YAML referencing Rill metrics) give 70% of the value with zero new tooling.

**Adoption effort:** Already adopted. Improvements are additive.

---

### 5. dbt Tests + dbt-expectations for Metric Correctness

**What it is:** Two-layer testing:
- **dbt unit tests** (dbt ≥1.8): static input → expected output. Tests transformation logic, not aggregates. dbt docs explicitly say *do not unit-test built-in aggregates* like `SUM()`, `COUNT()` — test the surrounding logic instead.
- **dbt-expectations `expect_table_aggregation_to_equal_other_table`**: production data test. Asserts an aggregate on a model matches an expected value or another model. DuckDB fully supported.

**DuckDB support:** Both confirmed working on dbt-duckdb adapter.

**What it actually solves:**
- Unit tests: "Is the formula/case-logic correct?" (tests the SQL in the mart, not the number in the chart)
- dbt-expectations aggregation test: "Does `SUM(net_revenue)` on `fact_orders` for 2026-01 match our golden reference?" — can catch data drift

**What it doesn't solve:** The chart-level definition problem. A Metabase card with a wrong WHERE clause will fail independently of dbt tests passing.

**Fit for this stack:** High. This is the testing backbone regardless of which semantic layer you choose. `dbt-expectations` is already DuckDB-compatible, freely composable with existing `packages.yml`.

**Adoption effort:** Low. Add to `packages.yml`, write tests in mart `schema.yml`.

---

### 6. Column-Level Lineage Tooling

**dbt-column-lineage (open source):** [github.com/Fszta/dbt-column-lineage](https://github.com/Fszta/dbt-column-lineage) — last release v0.8.0, Nov 2025. DuckDB adapter tested. Interactive UI showing column dependencies across models. Useful for "which upstream column contributes to `net_revenue`?" Does not trace to Metabase/Rill charts.

**dbt exposures:** Define `exposures:` in YAML pointing to Metabase dashboards / Rill metrics. Provides DAG visibility: "these models are consumed by Dashboard X." No validation — purely documentation. Low effort, high value for making lineage visible in `dbt docs`.

**dbt-metabase:** [github.com/gouline/dbt-metabase](https://github.com/gouline/dbt-metabase) — v1.7.5 (May 2026), actively maintained. Syncs dbt model/column descriptions + relationships to Metabase's data model. Critically: `dbt-metabase exposures` reverse-syncs Metabase questions/dashboards back into dbt as `exposures:` YAML. This closes the loop: Metabase card → exposure → dbt model. Does **not** sync metric definitions or prevent wrong SQL.

---

## Trade-Off Matrix

| Tool | DuckDB fit | Definition in code | Lineage to dbt | Metric tests | Self-host | Effort | Blocker |
|---|---|---|---|---|---|---|---|
| dbt MetricFlow | ✅ CLI only | ✅ YAML | ✅ native | ⚠ indirect via dbt-expectations | ✅ | Low | No BI API without Cloud |
| Lightdash | ❌ local DuckDB | ✅ reuses dbt YAML | ✅ best-in-class | ⚠ inherits dbt tests | ✅ MIT | Low*blocked* | DuckDB file support not shipped |
| Cube | ✅ local .duckdb | ✅ cube YAML | ❌ manual only | ❌ none native | ✅ Apache 2.0 | High | Parallel schema system |
| Rill (existing) | ✅ native | ✅ metrics YAML | ⚠ file-level only | ❌ none | ✅ | 0 (already live) | No test framework |
| dbt-expectations | ✅ | N/A | N/A | ✅ strong | ✅ | Low | Tests mart data, not chart SQL |
| dbt-metabase | ✅ (pass-through) | ❌ Metabase SQL unchanged | ✅ exposure sync | ❌ | ✅ | Low | Doesn't fix wrong metric SQL |
| dbt-column-lineage | ✅ | N/A | ✅ column level | N/A | ✅ | Low | Dev tool only, no prod UI |

---

## Recommended Layering for This Stack

**Ranked recommendation: don't add a new tool. Instrument the existing stack.**

### Tier 1 — Do now (zero new dependencies)

1. **Formalize metric definitions in Rill YAML as the canonical source.** Every measure needs a `description:` citing the business rule (already partially done: `orders_core_metrics.yaml` has good descriptions linking to `domains/sales.md`). Extend to all metrics views. This makes "definition correct?" answerable by reading one file.

2. **Add dbt exposures for Rill metrics views.** In `transformation/models/marts/schema.yml` (or a dedicated `exposures.yml`):
   ```yaml
   exposures:
     - name: rill_orders_dashboard
       type: dashboard
       url: "rill://orders_core"
       depends_on:
         - ref('fact_orders')
         - ref('dim_channels')
   ```
   Now `dbt docs` shows which mart models feed Rill. When a mart model fails a test, you immediately know which Rill dashboard is at risk.

3. **Add dbt-metabase exposures sync.** Run `dbt-metabase exposures` to pull Metabase questions into dbt `exposures:`. Combined with step 2 above, you now have full lineage: Metabase card → exposure → dbt mart → upstream models.

### Tier 2 — Do in next sprint (one new package)

4. **Add dbt-expectations to `packages.yml`.** Write `expect_table_aggregation_to_equal_other_table` tests on the most critical mart metrics (e.g., assert monthly `SUM(net_revenue)` on `fact_orders` doesn't deviate >1% from prior run). This answers "is the DATA wrong?" systematically. Fully DuckDB-compatible.

5. **Add dbt unit tests for non-trivial mart logic** (e.g., the VAT-strip formula, `cogs_source` flag logic, the overhead allocation in `fact_order_economics`). These catch definition bugs introduced by refactors.

### Tier 3 — Evaluate later

6. **Lightdash:** watch [issue #11112](https://github.com/lightdash/lightdash/issues/11112). If DuckDB file support ships, it becomes the strongest option: single YAML defines both dbt models and charts, lineage is automatic, and you can deprecate Metabase native SQL cards. Until then: do not adopt.

7. **dbt MetricFlow YAML (without Cloud API):** optionally migrate Rill metric definitions to MetricFlow format so they're co-located in the dbt project. `mf query` CLI gives explain output for debugging. No BI tool benefit without dbt Cloud, but the definitions become dbt-native and testable inline.

8. **Cube:** not recommended for this stack. Adds a second service, a second schema system, and no dbt DAG integration. Solves a different problem (embedded customer-facing analytics + caching). YAGNI.

---

## Self-Debuggable Chart Pattern (Best Practice)

The ideal state — attainable with Tier 1+2 above:

```
Metabase card (or Rill dashboard)
  → dbt exposure (git-tracked YAML)
  → dbt mart model (schema.yml description + column tests)
  → dbt test (dbt-expectations aggregation assertion)
  → intermediate model (dbt lineage graph)
  → staging model
  → source (sources.yml freshness check)
```

When a number looks wrong:
1. Find the exposure in git → know which mart model the chart queries
2. Check dbt test results → pass = data is fine, suspect the chart SQL
3. Run `dbt sl query --explain` (or read Rill YAML) → see exact SQL generated
4. Compare chart SQL to YAML definition → find divergence

This requires NO new tools. It requires discipline: every chart must have a corresponding dbt exposure, every mart metric must have a dbt-expectations test.

---

## Source Credibility Notes

- MetricFlow DuckDB support: confirmed in [MotherDuck examples](https://www.mintlify.com/motherduckdb/motherduck-examples/dbt/metricflow) and [dbt docs](https://docs.getdbt.com/docs/build/about-metricflow)
- dbt Semantic Layer API requires Cloud: [official FAQ](https://docs.getdbt.com/docs/use-dbt-semantic-layer/sl-faqs) confirmed
- Lightdash DuckDB blocked: [GitHub issue #11112](https://github.com/lightdash/lightdash/issues/11112) open, no resolution as of this research
- Cube DuckDB local file: [official docs](https://docs.cube.dev/admin/connect-to-data/data-sources/duckdb) confirmed via `CUBEJS_DB_DUCKDB_DATABASE_PATH`
- dbt-metabase v1.7.5 (May 2026): [GitHub](https://github.com/gouline/dbt-metabase), actively maintained
- dbt-column-lineage v0.8.0 (Nov 2025): [GitHub](https://github.com/Fszta/dbt-column-lineage), DuckDB-tested
- dbt-expectations DuckDB support: [calogica/dbt-expectations](https://github.com/calogica/dbt-expectations) README confirmed
- Semantic layer comparison: [StackFYI 2026 guide](https://www.stackfyi.com/guides/semantic-layer-tools-dbt-cube-metricflow-lightdash-2026), [Semantic Layers Buyer's Guide](https://davidsj.substack.com/p/semantic-layers-a-buyers-guide)

---

## Unresolved Questions

1. **dbt-metabase + Metabase v0.60 compatibility:** tool claims Metabase ≥49 for API key auth; v0.60 uses pMBQL query format — need to verify that `dbt-metabase models` sync still works against v0.60 API endpoints before adopting.

2. **Lightdash DuckDB PR #19866 status:** unclear if this is actively in development or stalled. Worth a direct GitHub ping to maintainers.

3. **Rill metric test gap:** no known solution for asserting a Rill measure equals an expected value in CI. The only workaround is testing the underlying dbt mart (which catches data errors but not Rill YAML definition errors like a wrong filter expression).

4. **dbt MetricFlow vs Rill YAML — dual-definition maintenance cost:** if MetricFlow measures are added in dbt and Rill metrics YAML continues to exist separately, they will diverge. Need an owner decision: is Rill the canonical layer, or is dbt?

5. **Column-level lineage between dbt mart → Rill model → Rill dashboard:** no tool traces this end-to-end. dbt-column-lineage stops at the mart; Rill has no lineage UI. Gap remains open until Lightdash DuckDB support ships.
