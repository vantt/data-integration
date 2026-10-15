# Evidence (static report pages)

The report site https://evidence.lan.fwg.vn is a set of static Evidence builds, one per
**permission area**, served by the container `report_site` (Caddy) behind a login per area and per
person. It is reachable on the LAN and through Tailscale only, never from the Internet; no
container publishes a host port.

- **Builder** — container `evidence` (image `Dockerfile.evidence`) runs
  [`scripts/build-areas.sh`](scripts/build-areas.sh). It serves nothing. It builds every area into
  `app_data/report_site/<area>/builds/<id>/` and switches the symlink `current` atomically; it builds
  once per request that Dagster writes after the nightly run, and at start only areas without a
  build: **`docker compose restart evidence` no longer rebuilds**.
- **Areas** — generated projects in `areas/<area>/` (product reports, `python3 -m analytics render
  evidence`), plus the `legacy` area: the hand-written `pages/` and `sources/` of this folder,
  served at the root paths (`/`, `/ceo-weekly-pulse/`, `/finance-cashflow/`).
- **Serving and login** — container `report_site` with the generated [`site/Caddyfile`](site/Caddyfile)
  (`python3 -m analytics render site`); accounts in `app_data/secrets/report_site/<area>.caddy`,
  managed with [`site/report-users.sh`](site/report-users.sh).

Runbook: [Report site](#report-site) below and `docs/operations/deployment.md` ("Report site
(Evidence)").

## Memory

`evidence build` peaks at about 3.5 GiB, so the container has `mem_limit: 4g` in
`docker-compose.yml`. With 2 GiB it relied on host swap and was killed for lack of memory when the
host swap was full.

## Access

One account per person and per area (Caddy `basic_auth`, bcrypt). A person who may see two areas has
an account line in both area files. Every request is logged by `report_site` with the user name
(`user_id` in its JSON access log), so you can see who opened what.

Fail-closed: the Caddyfile imports `/etc/caddy/users/<area>.caddy` for every area. A missing file
stops Caddy (caddy-global then answers 502); an empty file (last account removed) answers 401 to
everyone. Nothing is ever served without login. (Until the report site is deployed, the old single
account from `EVIDENCE_BASIC_AUTH_USER`/`EVIDENCE_BASIC_AUTH_HASH` protects the old container; those
variables are no longer used afterwards.)

## Areas and generated pages

Product reports are not written by hand. `python3 -m analytics render evidence --tenant fine_japan`
generates one Evidence project per **permission area** (`access.areas` in
`tenants/<t>/analytics/profile.yml`) under `areas/<area>/`:

| File | Content |
|---|---|
| `areas/<area>/evidence.config.yaml` | `deployment.basePath: /<area>`: the area is served under its own path, so a login per path covers its pages **and** its data files |
| `areas/<area>/sources/datalake/connection.yaml` | DuckDB source `datalake`; the builder copies `data_lake/serving/olap.duckdb` next to it as `olap-serving.duckdb` |
| `areas/<area>/sources/datalake/<report>__<card>.sql` | Compiled SQL of one card, `as_of` = yesterday in the tenant time zone at build time; the extract holds only the card's result |
| `areas/<area>/sources/datalake/<report>__meta.sql` | `as_of`, period bounds, last order time, cost coverage (header and meta cards) |
| `areas/<area>/pages/index.md`, `pages/<report>/index.md` | Pages that read only those extracts; footer "Doanh thu được tính thế nào" generated from the profile and registry |

Every generated file starts with a GENERATED banner (pages and SQL carry a hash of the inputs). Do not
edit them; `python3 -m analytics render evidence --check` (and `pytest analytics/tests`) fails when they
drift from the spec, registry or profile. A card that shows cost, margin or profit is not rendered (and
its SQL not written) in an area with `can_view_cost: false`; the page shows "Cần quyền xem chi phí".

The hand-written pages in `pages/` (`index`, `ceo-weekly-pulse`, `finance-cashflow`, `theme-mvp`) form the
`legacy` area: their content is unchanged; the builder builds them like any area (without base
path) and `report_site` serves them at the root paths behind the `legacy` accounts.

## Report site

### Accounts (one per person)

Run in a terminal on the server, from the repository root. The password is typed twice without
echo, hashed by `caddy hash-password` and only the hash is stored (file mode 600, directory 700);
nothing is printed or written to the shell history.

```bash
evidence/site/report-users.sh add <area> <user>      # create or change a password
evidence/site/report-users.sh remove <area> <user>   # revoke
evidence/site/report-users.sh list                   # who has access to which area (names only)
evidence/site/report-users.sh reload                 # apply: caddy reload in report_site
```

Areas are the paths of `site/Caddyfile` (today `dieu-hanh` and `legacy`). User names are lower case
`[a-z0-9._-]`, passwords at least 12 characters.

### Builds

| Task | Command |
|---|---|
| State of the last build | `cat app_data/data_lake/report_build/status.json` (per area: ok, build id, duration, error) |
| Builder log | `docker compose logs --tail 50 evidence` |
| Build now (after a page or spec change is deployed) | launch `report_site_build_job` in Dagster, or `docker exec evidence bash /app/scripts/build-areas.sh --once` |
| Roll an area back to the previous build | `ls app_data/report_site/<area>/builds/`, then `ln -sfn builds/<older id> app_data/report_site/<area>/current.new && mv -Tf app_data/report_site/<area>/current.new app_data/report_site/<area>/current` (3 builds are kept) |
| Add an area | add it to `access.areas` in the tenant profile, `python3 -m analytics render evidence` and `render site`, create its account file, deploy, `report-users.sh reload` |

A failed area keeps its previous build and Dagster alerts on the Lark alert channel; a build not
finished 2 hours after the request is alerted too. Do not start builds between 02:30 and 04:00 (nightly
window): a build needs about 3.5 GiB.

## Spike results (14/10/2026, test container, Evidence 40.1.8)

Run per "Upgrading deliberately" step 3: current image under the name `evidence-spike`, port 3106,
default bridge network (not `caddy_net`), copies of `pages/` and `sources/`, `data_lake` read-only;
removed afterwards.

| # | Question | Result |
|---|---|---|
| S1 | Build under a sub-path | ✅ `deployment.basePath` exists in 40.1.8 (`@evidence-dev/sdk` config schema, used as SvelteKit `paths.base`). Built with `/dieu-hanh`: HTML, `_app` assets, links and the runtime fetches of `/data/…` and `/api/…` are all prefixed. Served by Caddy (`root /srv`, `try_files {path} {path}.html {path}/index.html`, `file_server`): `/dieu-hanh/`, `/dieu-hanh/ceo_weekly_pulse`, `/dieu-hanh/data/manifest.json` return 200 |
| S2 | Where the extracts live | Under the build root of the area only: `data/datalake/<query>/<hash>/<query>.parquet`, `data/manifest.json`, `api/prerendered_queries/*.arrow`. Nothing outside the area directory, so a path-based login covers the data |
| S3 | Build from another directory sharing `node_modules` | ✅ project dir with `pages/`, `sources/`, `evidence.config.yaml`, a copy of `package.json` and a symlink `node_modules → /app/node_modules`; `npx evidence sources && npx evidence build` |
| S4 | Time and memory | Area `dieu-hanh` (CEO Weekly Pulse): sources 9 s, build 44 s, 25 extracts = **12.6 KB** (legacy build: 9 whole-table extracts ≈ 1.1 MB, `fact_orders` and `dim_customers` included). Peak memory of `evidence build` ≈ 3.5–3.7 GiB for both legacy and the small area (the Vite build, not the data): with `--memory 2g` and no swap the build is **OOM-killed** (2/2 legacy, 1/1 area) |
| S5 | Future of Evidence | npm `@evidence-dev/evidence` latest = 40.1.8 (published 2026-02-06), no release since; `@evidence-dev/duckdb` 2.0.1 same day; docs still document a local DuckDB file source. Whether a newer Evidence product reads a local DuckDB file could not be verified. Decision: stay on the pinned 40.1.8 until there is a reason to move; spec v2 is engine-independent, so a new engine needs only a new renderer |

Consequences, now applied: the builder builds areas sequentially with a timeout (`AREA_TIMEOUT`,
default 1200 s) in a container with 4 GiB, and `report_site` serves the builds with Caddy
`file_server` (the `serve` package is no longer used at run time).

## Why the versions are pinned

`package.json` pins exact versions and `package-lock.json` locks the whole dependency tree
(974 packages). The Dockerfile installs with `npm ci`, which installs exactly the locked tree
and fails when `package.json` and the lock disagree.

Before 14/10/2026 the Evidence packages were declared as `latest`, without a lockfile, so every
image rebuild could pull a different release, including a broken one. The pinned versions are
the ones that were running in production on 14/10/2026, taken from the running container (the
lock is that container's own lockfile):

| Package | Version |
|---|---|
| `@evidence-dev/evidence` | 40.1.8 |
| `@evidence-dev/core-components` | 5.4.2 |
| `@evidence-dev/duckdb` | 2.0.1 |
| `tailwindcss` | 3.4.18 |
| `autoprefixer` | 10.5.4 |
| `serve` | 14.2.6 (serves the static build; installed from the lock, never downloaded at start) |

The base image is pinned too: `Dockerfile.evidence` uses `node:20.20.2-slim` (node 20.20.2,
npm 10.8.2, Debian 12.13), the same versions the production image was built with.

## Upgrading deliberately

Upgrade on a branch, never on the production checkout:

1. Change the version in `package.json` (exact version, no `^`, `~` or `latest`). To upgrade
   node, change the `FROM` tag in `Dockerfile.evidence` to another exact tag.
2. Regenerate the lock without installing, using the same node image as the Dockerfile:
   `docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/evidence":/w -w /w node:20.20.2-slim npm install --package-lock-only --include=dev --ignore-scripts`
3. Build an image under a test tag (`docker build -f Dockerfile.evidence -t evidence-test .`)
   and run it under another container name, without the production ports or network. Mount
   copies of `pages/`, `sources/` and `scripts/`, and mount `app_data/data_lake` read-only.
4. Check that the build finishes (the container turns healthy) and that every page renders,
   for example `ceo-weekly-pulse` and `finance-cashflow`.
5. Commit `package.json` and `package-lock.json` together. The new versions reach production
   at the next `docker compose build evidence`.
