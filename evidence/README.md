# Evidence (static report pages)

Evidence builds the static report pages served at http://evidence.lan.fwg.vn (port 3006 locally).
Pages live in `pages/`, SQL sources in `sources/datalake/`, and the image is defined by
`Dockerfile.evidence` at the repository root. The container copies
`app_data/data_lake/serving/olap.duckdb` into `sources/datalake/`, runs `evidence sources` and
`evidence build`, then serves the static build. `docker compose restart evidence` rebuilds the
site from the current serving database; it does not reinstall packages.

## Why the versions are pinned

`package.json` pins exact versions and `package-lock.json` locks the whole dependency tree
(919 packages). The Dockerfile installs with `npm ci`, which installs exactly the locked tree
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

These were built with node 20.20.2 and npm 10.8.2 (`node:20-slim` base image).

## Upgrading deliberately

Upgrade on a branch, never on the production checkout:

1. Change the version in `package.json` (exact version, no `^`, `~` or `latest`).
2. Regenerate the lock without installing, using the same node image as the Dockerfile:
   `docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/evidence":/w -w /w node:20-slim npm install --package-lock-only --include=dev --ignore-scripts`
3. Build an image under a test tag (`docker build -f Dockerfile.evidence -t evidence-test .`)
   and run it under another container name, without the production ports or network. Mount
   copies of `pages/`, `sources/` and `scripts/`, and mount `app_data/data_lake` read-only.
4. Check that the build finishes (the container turns healthy) and that every page renders,
   for example `ceo-weekly-pulse` and `finance-cashflow`.
5. Commit `package.json` and `package-lock.json` together. The new versions reach production
   at the next `docker compose build evidence`.
