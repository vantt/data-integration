# Research Report: Code-First / AI-Codegen-Friendly Dashboard & Report Frameworks
**Date:** 2026-06-05 | **Author:** researcher

---

## Context

User's stack: DuckDB (`olap.duckdb`) + dbt marts, Metabase v0.60 deployed via AI-generated markdown blueprints (NOT drag-drop), Rill already running. Internal reporting, Vietnamese audience.

Pain points driving this research:
1. Richer chart types than Metabase offers
2. Fully code-first so AI can gen dashboard code from a spec
3. Inject provenance/metadata narrative next to each chart ("which model/SQL built this")
4. Version-controlled

---

## Tool-by-Tool Analysis

### 1. Evidence.dev

**DuckDB support**
- Native DuckDB connector: reads `.duckdb` files placed in `sources/[name]/` directory; also queries across CSV, Parquet, JSON via DuckDB WASM in-browser. Sources: [docs](https://docs.evidence.dev/core-concepts/data-sources/duckdb), [blog](https://myblog.evidence.app/duckdb-and-BI/).
- At build time: runs queries against local DuckDB file, extracts results to Parquet cache; at runtime: DuckDB-WASM in browser queries those Parquet files. So it reads `olap.duckdb` directly — file must be inside the Evidence project tree (can symlink).

**Code-first & AI-codegen story**
- Authoring: plain `.md` files with fenced SQL blocks and `<Chart>` component tags. Format is trivially LLM-generatable: "given this schema, write Evidence markdown" maps directly. Official docs note Evidence includes "an AI agent that looks up docs, checks schema, debugs errors, writes Evidence markdown." Every dashboard is git-trackable text.
- VSCode extension available. Build via `npm run build` → static HTML bundle → CI/CD-able.

**Chart variety**
- Built-in: Line, Area, Bar, Scatter, Bubble, Funnel, Sankey, Heatmap, Calendar Heatmap, Histogram, Box Plot, Mixed-Type, Candlestick (added Dec 2025), Maps (Area/Point/Bubble/US). Source: [all-components page](https://docs.evidence.dev/components/all-components).
- Ceiling: `<ECharts>` component exposes full ECharts config for any chart type ECharts supports (treemap, sunburst, gauge, radar, etc.). Custom Svelte components can wrap any JS viz library. This is a high ceiling.

**Narrative + provenance injection**
- Native capability: prose markdown wraps every chart. A pattern like `## Source: mart_name — see transformation/models/marts/sales/fact_order_economics.sql` is just text. Can be templated with SQL query results inline (e.g., `Last built: {last_refreshed_at}`).
- No built-in "model lineage" widget, but nothing prevents injecting dbt manifest-derived metadata as markdown text or a small table component alongside charts.

**Output / hosting / auth**
- Static site output (HTML/JS). Self-host anywhere (Nginx, S3+CDN, GitHub/GitLab Pages). No server needed for static builds.
- Auth: open-source build has none; [Evidence Studio](https://evidence.dev/blog/evidence-studio) (commercial SaaS) adds page-level/row-level access control + SSO (Okta, Google, Azure). Self-hosted auth requires Cloudflare Access or similar reverse-proxy solution. $500/mo/dev seat for enterprise self-hosted support.

**Maturity / license / momentum**
- OSS core: MIT. GitHub: ~5k stars, active releases. Jan 2026 release added Delta Lake/S3, Dec 2025 added candlestick, customer management in Studio. Weekly releases visible on changelog. MotherDuck partnership = ongoing investment signal.
- Abandonment risk: LOW — DuckDB Labs / MotherDuck-adjacent, active community, commercial tier sustains dev.

**Fit score: 5/5**
*Best match: SQL+Markdown authoring is the ideal AI codegen target, native DuckDB, rich chart ceiling via ECharts, free-form prose is exactly how provenance narrative works, 100% version-controlled.*

---

### 2. Observable Framework

**DuckDB support**
- First-class: built-in `DuckDBClient` from `npm:@observablehq/duckdb`. Loads `.duckdb` files, Parquet, CSV from `src/data/` directory. Uses DuckDB-WASM 1.29.0 (aligned with DuckDB 1.1.1) client-side. Source: [Observable Framework DuckDB docs](https://observablehq.com/framework/lib/duckdb).
- Data loaders (server-side, run at build time): Python, R, shell, Node — can call `dbt run` or query DuckDB server-side and emit Arrow/Parquet for browser consumption.

**Code-first & AI-codegen story**
- Authoring: `.md` files with fenced JS code blocks. Reactive notebook semantics (cells recompute when dependencies change). Full JavaScript/TypeScript, `import` from npm, Observable Plot, D3, Vega-Lite all available.
- More code than Evidence — requires JS comfort. For AI codegen: generatable but the output is more verbose JS than Evidence's component tags. An LLM writing `Plot.barY(data, {x: "month", y: "revenue"})` is easy; full custom D3 layouts are harder to reliably generate.
- Static site generator: `npm run build`. Git-native. 100% version-controlled.

**Chart variety**
- Observable Plot (grammar-of-graphics): any mark type (bar, line, area, dot, rect, hexbin, contour, etc.) + layering. D3 integration for anything custom. Essentially unlimited ceiling — the highest of all tools reviewed.
- Downside: more code per chart vs Evidence's declarative components.

**Narrative + provenance injection**
- Excellent: it's a document-first format. Prose, tables, footnotes, custom HTML, and reactive chart cells coexist freely. Provenance blocks are just markdown paragraphs or JS expressions referencing build-time metadata.

**Output / hosting / auth**
- Static site output. Self-host anywhere. **Observable Cloud deprecated April 2025, shutdown Oct 15 2025** — means you must self-host. Source: [deprecation notice](https://observablehq.com/release-notes/2025-04-15-deprecating-observable-cloud).
- Auth: NONE built-in — handled at hosting layer (Nginx basic auth, Cloudflare Access, etc.). For internal audiences this is acceptable but requires setup.

**Maturity / license / momentum**
- OSS: ISC license. Created by Mike Bostock (D3 author). GitHub: ~4.5k stars. Active releases (v1.13.0 recent). Backed by Observable Inc. (profitable, enterprise notebook product funds OSS).
- Risk note: cloud shutdown shows business pivots happen; Framework OSS appears stable but Observable's revenue focus is the notebook product, not Framework. Medium abandonment risk long-term.

**Fit score: 4/5**
*Second-best: highest chart customization ceiling, excellent narrative-first format, DuckDB-native. Loses one point vs Evidence because authoring is more verbose JS (harder to reliably AI-gen), no built-in auth story, and Observable Cloud shutting down signals uncertain hosting path.*

---

### 3. Rill Data (already in stack)

**DuckDB support**
- Rill is built on DuckDB internally. "External DuckDB" connector available: reads `.duckdb` files or Parquet/CSV. Cloud deployment has 100MB size limit for DuckDB files. Source: [external DuckDB docs](https://docs.rilldata.com/developers/build/connectors/data-source/duckdb).
- Caveat: PIVOT without IN filter unsupported due to DuckDB/view constraints.

**Code-first & AI-codegen story**
- Fully YAML/SQL code-first: `rill/models/*.sql` + `rill/metrics/*.yaml` + dashboard YAML files. 100% version-controlled. Authoring format is highly structured YAML — LLM can generate it but requires understanding Rill's specific schema.
- 2025 Canvas dashboards allow visual OR code editing; code wins for AI-gen.
- Already on the stack — zero adoption cost for exploration dashboards.

**Chart variety**
- Explore dashboards: pivot tables, leaderboards, time-series — optimized for metric slicing. NOT a general-purpose viz tool.
- Canvas dashboards (2025): bar, line charts live; donut, heatmap in beta/coming. Custom viz via code snippets (beta). Very limited chart palette vs Evidence/Observable.
- Critical gap: no free-form chart composition.

**Narrative + provenance injection**
- Major gap. Rill is built for metric exploration, not narrative reporting. No mechanism to inject prose provenance text next to a chart. The YAML config is metrics-centric, not document-centric. The team already noticed this (they hand-build Flask/Jinja reports for narrative).

**Output / hosting / auth**
- Local dev server or Rill Cloud (SaaS). Self-hosted on-prem available but requires Rill infrastructure. Auth via Rill Cloud SSO or local dev mode (no auth). Not a pure static site.

**Maturity / license / momentum**
- OSS: Apache 2.0. GitHub: ~5k stars. Active, well-funded (Series A). DuckCon6 presence. "Fastest BI tool for humans and agents" current tagline.
- Abandonment risk: LOW — but product is moving toward enterprise SaaS; self-hosted story less prominent.

**Fit score: 2/5**
*Already on stack so free to use for metric exploration dashboards, but fails on narrative injection (core pain point) and chart variety. Use it for what it's good at (slice/dice explore) — don't stretch it for provenance reports.*

---

### 4. Streamlit

**DuckDB support**
- Native: `import duckdb; conn = duckdb.connect("olap.duckdb")`. Official DuckDB blog post (March 2025) covers Streamlit+DuckDB patterns. Source: [DuckDB blog](https://duckdb.org/2025/03/28/using-duckdb-in-streamlit). Reads any DuckDB file or Parquet directly.

**Code-first & AI-codegen story**
- Pure Python scripts. Highest AI-codegen friendliness for Python — LLMs (GPT-4, Claude) are extremely good at Streamlit code. "Describe a dashboard → get working Python" works well in practice.
- Version-controlled trivially (`.py` files).

**Chart variety**
- Built-in: Plotly, Altair, Matplotlib, Bokeh, Vega-Lite all supported. Plotly alone covers 40+ chart types. With `st.components.v1.html()` you can embed any custom JS/D3. Ceiling: very high.
- Downside: each chart is a Python function call — more code per chart than Evidence's declarative components.

**Narrative + provenance injection**
- Excellent: `st.markdown()`, `st.caption()`, `st.expander()` allow injecting arbitrary prose, metadata tables, SQL snippets alongside charts. Closer to the Flask/Jinja pattern the user already knows. Very natural for "show the SQL that built this."

**Output / hosting / auth**
- Server-side Python process (NOT static). Requires running a server. Self-hosted via Docker easily. Auth: `st.secrets`, or Streamlit Community Cloud free tier, or custom auth libraries (`streamlit-authenticator`). Per-connection Python thread = RAM grows with users (not a problem for internal low-traffic reporting).
- Not static: every pageview hits the server. Minor ops overhead vs static tools.

**Maturity / license / momentum**
- Apache 2.0. GitHub: ~40k stars, massive community. Acquired by Snowflake 2022 but remains OSS and independent product. Extremely stable. Zero abandonment risk.

**Fit score: 3/5**
*Strong Python/LLM codegen story and excellent narrative injection, but server-required (vs static), and the existing Flask/Jinja work the user already does is essentially the same paradigm — adding Streamlit is additive, not transformative. Best if Python team wants richer charts without learning JS.*

---

### 5. Plotly Dash

**DuckDB support**
- Via Python `duckdb` library; same as Streamlit. Dash Enterprise embeds DuckDB. No production-DuckDB gotchas beyond Streamlit.

**Code-first & AI-codegen story**
- Python with callback decorators. More verbose than Streamlit — explicit `@app.callback` for every interaction. AI can generate it but the code is denser and more error-prone to generate reliably.
- Version-controlled (Python files).

**Chart variety**
- Plotly (50+ chart types) + custom React components (Dash DAQ, Dash Bio, custom). Highest production-grade chart control in Python ecosystem.

**Narrative + provenance injection**
- Possible via `html.Div`, `dcc.Markdown` components but more verbose than Streamlit's `st.markdown()`. Not document-first.

**Output / hosting / auth**
- Server-side (Flask/WSGI). Docker-deployable. Better multi-user scaling than Streamlit (WSGI vs one-thread-per-user). Dash Enterprise (paid) adds auth, row-level security.

**Maturity / license / momentum**
- MIT (open-source core). GitHub: ~22k stars. Well-maintained by Plotly Inc. 2025 added Narwhals support (DuckDB DataFrames), GenAI capabilities in Enterprise tier. Stable, low abandonment risk.

**Fit score: 3/5**
*Production-ready Python option with great chart library, but more complex to author than Streamlit and no advantage over Streamlit for this team's narrative+provenance goal. Slight edge over Streamlit for multi-user production load, but overkill for internal reporting.*

---

### 6. Quarto Dashboards (brief)

**DuckDB support:** Via OJS + DuckDB-WASM in static builds, or Python/R code blocks querying DuckDB at render time. Source: [Posit community thread](https://forum.posit.co/t/using-quarto-with-ojs-and-duckdb/190311). Works but setup is non-trivial.

**Code-first:** `.qmd` markdown files — excellent for documents, awkward for interactive dashboards. Layout via `##` headings and `layout` YAML. Not the primary use case for Quarto (it's really for reports/papers/presentations).

**Chart variety:** Whatever Python/R/OJS library you use. Same ceiling as Observable but without Observable's polished integration.

**Narrative:** First-class — Quarto is a document publishing tool. Provenance text lives naturally alongside code outputs.

**Fit score: 2/5**
*Good fit for one-off analytical documents/papers, but awkward for dashboard-style interactive reports. Low momentum for the dashboard use case specifically. Skip unless the team already knows R/Python scientific workflows.*

---

### 7. Apache Superset (brief)

**DuckDB support:** Official connector via SQLAlchemy `duckdb:///path`. But multiple concurrent connections cause errors (DuckDB read-write lock); must use `READ_ONLY` mode. Superset 6.0 broke DuckDB extension installs (open GitHub issue). Source: [Superset DuckDB docs](https://superset.apache.org/docs/databases/supported/duckdb/), [issue #34984](https://github.com/apache/superset/issues/34984).

**Code-first:** Dashboard-as-code support via Superset CLI import/export YAML, but dashboard creation is primarily GUI. Not code-first by design.

**Fit score: 1/5**
*Primarily a GUI BI tool with GUI-first philosophy — antithetical to the user's explicit "no drag-drop" requirement. DuckDB integration is fragile. Eliminate.*

---

## Comparison Matrix

| Dimension | Evidence.dev | Observable Framework | Rill (existing) | Streamlit | Plotly Dash |
|---|---|---|---|---|---|
| DuckDB native read | YES (.duckdb + parquet) | YES (WASM + data loaders) | YES (with size limits) | YES (Python lib) | YES (Python lib) |
| Authoring format | SQL + Markdown | Markdown + JS | YAML + SQL | Python | Python |
| AI codegen ease | **VERY HIGH** (spec→MD) | HIGH (verbose JS) | MEDIUM (Rill YAML schema) | HIGH (Python) | MEDIUM (callback boilerplate) |
| Chart variety | HIGH (ECharts ceiling) | **HIGHEST** (D3/Plot) | LOW (metric-explore only) | HIGH (Plotly) | HIGH (Plotly) |
| Provenance narrative | **NATIVE** (prose MD) | **NATIVE** (prose MD) | **ABSENT** | GOOD (st.markdown) | OK (dcc.Markdown) |
| Static output | YES | YES | NO (server) | NO (server) | NO (server) |
| Auth (built-in) | Studio (paid) / proxy | None / proxy | Rill Cloud | Library/proxy | Enterprise (paid) |
| Version-control | YES (text files) | YES (text files) | YES (YAML/SQL) | YES (.py) | YES (.py) |
| Maturity | HIGH (2022+, active) | HIGH (2024+, active) | MEDIUM (2023+) | VERY HIGH | VERY HIGH |
| Abandonment risk | LOW | MEDIUM (cloud pivot) | LOW-MED | VERY LOW | VERY LOW |
| Fit score | **5/5** | 4/5 | 2/5 | 3/5 | 3/5 |

---

## Ranked Shortlist

### #1 — Evidence.dev *(primary recommendation)*

Reasons:
- Authoring format (SQL + Markdown) is the simplest possible target for AI codegen — a spec like "show monthly GMV by category with this SQL" maps almost directly to an Evidence page file.
- DuckDB is a first-class connector; reads local `.duckdb` file or Parquet; the DuckDB-WASM in-browser engine means dashboards work without a running server.
- ECharts escape hatch covers any chart type gap beyond built-ins; chart set already exceeds Metabase substantially.
- Free-form prose markdown IS the provenance narrative — you literally write it next to the chart tag. No special feature needed.
- Static site → git, CI/CD, deploy anywhere (Nginx container alongside data_platform).
- Jan/Dec 2025 releases show healthy velocity; MotherDuck partnership = DuckDB compatibility guaranteed.
- Migration story: Evidence dashboard = an `.md` file. AI can generate these from the same blueprints used for Metabase today, just with different syntax.

Weaknesses: Auth requires Evidence Studio (paid) or a reverse proxy layer. DuckDB file must live inside the project (symlink or mount).

### #2 — Observable Framework *(for complex bespoke reports)*

Use when: a specific report needs chart types impossible in ECharts (complex force-directed graphs, custom geo projections, animated scrollytelling). The D3/Observable Plot power is unmatched.

Tradeoff: more JS knowledge required, AI codegen output is more verbose and harder to validate. Observable Cloud gone — must self-host from day 1. Best suited for one or two high-value "showcase" reports rather than the bulk of dashboards.

### #3 — Streamlit *(if team prefers Python over SQL+Markdown)*

Use when: the report requires complex Python logic at render time (e.g., running dbt programmatically, loading ML model outputs, dynamic provenance from dbt manifest JSON). Essentially a better-productionized version of the existing Flask/Jinja pattern.

Tradeoff: requires a running Python server; no static output; adds another server process to manage.

---

## Architectural Recommendation

**Evidence.dev as the primary new dashboard layer, complementing Metabase.**

- Keep Metabase for ad-hoc exploration (its strength).
- Migrate narrative / provenance-rich reports to Evidence.dev pages (`.md` files in a new `reporting/` project, connected to `olap.duckdb`).
- Keep Rill for metric explore/slice-and-dice — don't stretch it for narrative.
- Use Observable Framework selectively for one-off high-design reports.
- Do NOT adopt Superset (GUI-first, DuckDB fragile).

The Evidence project can be built via `npm run build` in CI (same Dagster pipeline that runs dbt) so dashboards are always in sync with the latest mart refresh. Static output deploys to any Nginx container — no new server process.

---

## Source Credibility Notes

- DuckDB connector behavior: [official Evidence docs](https://docs.evidence.dev/core-concepts/data-sources/duckdb) + [MotherDuck integration page](https://motherduck.com/docs/integrations/bi-tools/evidence/) (high credibility — maintainer sources)
- Chart components: [official Evidence all-components page](https://docs.evidence.dev/components/all-components)
- Observable Cloud shutdown: [official Observable deprecation notice](https://observablehq.com/release-notes/2025-04-15-deprecating-observable-cloud)
- Rill 2025 features: [Rill docs external DuckDB](https://docs.rilldata.com/developers/build/connectors/data-source/duckdb), [Rill vs Evidence comparison](https://visivo.io/comparisons/evidence-dev-rill-data)
- Superset DuckDB issues: [official Superset docs](https://superset.apache.org/docs/databases/supported/duckdb/) + [GitHub issue #34984](https://github.com/apache/superset/issues/34984)
- Streamlit+DuckDB: [official DuckDB blog March 2025](https://duckdb.org/2025/03/28/using-duckdb-in-streamlit)

---

## Limitations of This Research

- Did not benchmark actual DuckDB file read performance for each tool against user's `olap.duckdb` size (unknown).
- Evidence.dev auth story on self-hosted (without Studio) not fully validated — options like Cloudflare Access or Nginx basic auth work but add operational complexity that wasn't measured.
- Rill Canvas dashboard custom viz is in beta as of 2025 — actual chart extensibility ceiling not verified against production builds.
- Did not evaluate Visivo (YAML-native BI-as-code), Lightdash (dbt-native semantic layer), or Hex (collaborative notebooks) — all 2025-viable alternatives worth a follow-up pass if Evidence doesn't fit.

---

## Unresolved Questions

1. **Evidence.dev `.duckdb` file path**: Does Evidence support a symlink from `sources/sapo/olap.duckdb → ../../../olap.duckdb` on Windows (NTFS junctions)? Or must the file be copied at build time?
2. **Auth requirement**: Is page-level auth required for internal reporting, or is network-level isolation (VPN/internal network only) sufficient? Determines whether Evidence Studio cost is justified.
3. **dbt manifest provenance**: Is there appetite to write a build step that reads `target/manifest.json` and injects model lineage metadata into Evidence pages automatically? This would make provenance injection truly systematic vs manual.
4. **Rill retention**: If Evidence replaces Rill's narrative report use case, does Rill still earn its keep for explore/slice-dice? Team already invested in Rill YAML — answer determines migration vs complement strategy.
