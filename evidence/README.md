# Evidence (static report pages)

Evidence builds the static report pages served at http://evidence.lan.fwg.vn, behind Caddy
basic_auth. The container has no host port: the pages bundle customer data and order economics.
Pages live in `pages/`, SQL sources in `sources/datalake/`, and the image is defined by
`Dockerfile.evidence` at the repository root. The container copies
`app_data/data_lake/serving/olap.duckdb` into `sources/datalake/`, runs `evidence sources` and
`evidence build`, then serves the static build. `docker compose restart evidence` rebuilds the
site from the current serving database; it does not reinstall packages.

## Memory

`evidence build` peaks at about 3.5 GiB, so the container has `mem_limit: 4g` in
`docker-compose.yml`. With 2 GiB it relied on host swap and was killed for lack of memory when the
host swap was full.

## Access

The only way in is the Caddy route `evidence.lan.fwg.vn` (container `caddy-global`), which asks for
a user name and password (`basic_auth`). The credentials are compose variables in the root `.env`
(not `.env.docker`, which only reaches the container): `EVIDENCE_BASIC_AUTH_USER` and
`EVIDENCE_BASIC_AUTH_HASH` (bcrypt). `docker compose` refuses to start any service while either is
missing, so a route without auth never reaches `caddy-global`.

Set or change the password without it appearing on screen or in shell history:

```bash
read -rs -p 'Evidence password: ' P; echo
H=$(printf '%s\n' "$P" | docker exec -i caddy-global caddy hash-password); unset P
sed -i '/^EVIDENCE_BASIC_AUTH_/d' .env
printf "EVIDENCE_BASIC_AUTH_USER=%s\nEVIDENCE_BASIC_AUTH_HASH='%s'\n" "<user name>" "$H" >> .env; unset H
docker compose up -d evidence    # recreate the container so caddy-global reads the new labels
```

Check: `curl -s -o /dev/null -w '%{http_code}' https://evidence.lan.fwg.vn/` answers 401 without
credentials.

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
`legacy` area: unchanged, still built by the container command below until the scheduled builder
(next step of the report plan) replaces it. Nothing serves `areas/` yet.

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

Consequences for the scheduled builder: build each area sequentially with a timeout; give the build
≥ 4 GiB (or verify swap); `npx serve` used by the current container command is not in the locked
`node_modules` (it is fetched at start), so serving should move to Caddy `file_server`.

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
