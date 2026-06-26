# Backup & Restore Completeness Runbook

**Purpose:** the standard method for guaranteeing a backup is a *complete, restorable version* — not just a file that got written. Proven on the CRM pilot (live, zero downtime); **Part 2 generalizes it to the warehouse pipeline.**

**Core principle:** *A backup is not a dump — it is a **gate**. A backup is "complete" only when a restore has been **proven** to boot a working system with provably-correct data, not when the file finishes writing.*

---

## 1. What "complete" means — four properties

Every backup must satisfy all four. Each is guaranteed by a specific technique; missing any one is a distinct failure mode.

| # | Property | Question it answers | Failure mode if absent |
|---|---|---|---|
| 1 | **Consistent** | Was the file captured mid-write? | torn copy — DB won't open |
| 2 | **Self-contained** | Is everything needed to rebuild the system present, with no external source? | restore yields an empty / partial system |
| 3 | **Faithful** | Does the snapshot exactly equal the *live source* at capture time? | **silent** data loss during copy |
| 4 | **Restorable** | Does it actually boot a working system with correct data? | "looks fine", dies on restore |

The method is a **gate chain**: each gate closes exactly one failure mode. Any backup that fails a gate is a hard **FAIL** — never recorded as success.

---

## 2. Capture-time gate chain (proven: `crm/ops/backup_crm.py`)

```
1. quiesce writers / checkpoint   → no in-flight writes captured
2. profile the LIVE source        → per-table row counts + content checksums
3. take a CONSISTENT snapshot      → engine-native API, NOT a raw file copy
4. profile the SNAPSHOT
5. integrity_check the snapshot
6. ASSERT source == snapshot       → delta of 1 row / 1 cell ⇒ FAIL
7. write manifest.json             → the fidelity fingerprint
8. rotate (keep-N) + alert on any partial/failure
```

Why each step maps to a property:

- **Steps 1 + 3 → Consistent.** Never raw-copy a live database file. CRM uses SQLite's online-backup API (`Connection.backup()`) after `wal_checkpoint(PASSIVE)`, so the snapshot is a single consistent transaction, not a half-written WAL. (Lessons **L56/L68**.)
- **Self-contained.** Back up *every* store the system needs to boot. CRM backs up both `crm.db` (source of truth) **and** `cache.db` (regenerable reverse-ETL cache) so restore needs **no warehouse**.
- **Steps 2 + 4 + 6 → Faithful (the crux).** This is what makes a backup a *gate*, not a dump: profile the **live source** before and the **snapshot** after, then require **delta == 0**. A manifest computed only from the snapshot cannot detect a copy that silently dropped rows — so we compare against the *source*, not against itself. (Closes red-team **H1**.)
- **Content checksums, not just row counts.** Row count + file `sha256` catch added/removed rows but **miss a mutated cell** when the count is unchanged. Each table also carries `hash(group_concat(pk || updated_at ORDER BY pk))` to catch value mutation. (Closes **H5**.)

---

## 3. The manifest — the "fidelity contract" (`manifest.json`)

The fingerprint of a complete state; the restore step verifies against it. Per backup it records:

- per-store **`sha256`**
- per-table **row count + content checksum**
- **`migration_head`** (schema version)
- **`integrity_check`** result
- (optional) image digest of the producing build

No manifest ⇒ no definition of "correct" ⇒ no provable restore.

---

## 4. Restore-verify drill — the real proof (`crm/ops/restore_verify_crm.py`)

A backup asserting "I'm fine" is not enough. **Completeness is proven only by an actual restore.** Runs after every backup:

```
Gate A — File integrity (PRE-boot)
   restore the stores → re-profile → compare to the manifest
   (sha256 + checksums + row counts + integrity)   → exact match or FAIL

Gate B — Functional (boot the real system)
   spin an EPHEMERAL, isolated instance from the backup
   health-ready → serves reads → a REAL write (create/insert/delete/drop)

Production untouched
   fingerprint prod store (size+mtime) before/after → must be identical (hard isolation)
```

**Isolation is hard-asserted** (this is non-negotiable for a drill that touches prod infra): distinct name/port, **no prod data mount, no prod network route, no prod-routing label**; the ephemeral runs the same image the system runs; prod is fingerprinted before/after and asserted unchanged.

---

## 5. What makes the method *trustworthy* (not theatre)

1. **Negative / tamper tests — defeat vacuous checks.** Deliberately corrupt the backup (delete a row / mutate one cell / truncate a table / truncate the file) and run the drill; it **must FAIL**. If a tampered backup still PASSes, the checks are vacuous. Verified: a single-cell mutation is caught at Gate A via `sha256` mismatch. (Lesson **L147**.)
2. **Automated + fail-loud.** The drill runs on **every** backup (chained immediately after it); a failure reds the orchestration run → the failure sensor alerts. Silent backup rot is the zombie-run lesson repeating — never let it be silent.

### CRM wiring (reference implementation)
- **Schedule:** `crm_backup_job` (daily 02:00 ICT, `definitions.py`) runs `crm_backup → crm_restore_verify` (deps-chained, both fail-loud).
- **Socket isolation:** the drill must spin a container, so the Docker socket is confined to a single-purpose, token-gated, no-route **`crm_drill_runner`** sidecar (`Dockerfile.drillrunner`, `crm/ops/drill_runner_server.py`) — **never** granted to the orchestrator (`data_platform`). (Lesson **L150**: a drill inside a socket-mounted sidecar reaches the ephemeral by network name on a shared network, not via a host-published port.)

### Property → mechanism summary
| Property | Guaranteed by |
|---|---|
| Consistent | engine-native online backup + checkpoint + `integrity_check` |
| Self-contained | back up every store needed to boot (CRM: `crm.db` + `cache.db`) |
| Faithful | **live-source vs snapshot gate, delta==0** + content checksums |
| Restorable | **restore drill**: Gate A (file) + Gate B (boot + real write) + prod-untouched |
| *Trustworthy* | tamper tests (non-vacuous) + automated, fail-loud |

---

# Part 2 — Applying the method to the warehouse pipeline

The five properties and the gate chain are **identical**. What changes is *what is the source of truth* and *what "restore" + "verify" mean*, because the warehouse is a **derived** system: most of it is rebuildable from immutable inputs.

## 2.1 Source-of-truth analysis (do this first, for any system)

| Class | Warehouse artifacts | Backup treatment |
|---|---|---|
| **Irreplaceable** (source of truth) | raw **Parquet data lake** (append-only; holds 2021–2025 Sapo history — see memory `project_sapo_history_log_truncation`), `dagster_home` instance state (`dagster.yaml`, schedules, run/event storage), **dbt seeds** | **MUST back up** with the full gate chain |
| **Regenerable** (derived) | `sapo_warehouse.duckdb`, serving `olap.duckdb`, standalone export, all marts | do **not** treat as source of truth — rebuild them |

**Implication:** warehouse *backup* centers on **raw parquet + `dagster_home` + seeds**. Warehouse *restore* = restore those, then **re-run `dbt` + serving build** to reconstruct everything derived. This is the key difference from CRM (where `crm.db` itself is irreplaceable).

## 2.2 The same gate chain, adapted

| Stage | CRM (SQLite) | Warehouse |
|---|---|---|
| **Consistent capture** | online-backup API + `wal_checkpoint` | parquet is **immutable/append-only** ⇒ consistency is largely a non-issue; back it up by content addressing (per-file hashes + manifest of the file set). For any DuckDB file that *must* be captured, copy under the `duckdb_lock` (pause writers) or use `EXPORT DATABASE` — but prefer parquet-as-truth so DuckDB files are disposable. |
| **Faithful gate** | source-vs-snapshot row/checksum, delta==0 | manifest of the parquet file set: per-file `sha256` + partition row counts; assert the captured set == the live lake (no missing partitions / no truncation). |
| **Manifest** | per-table checksums + migration head | parquet file inventory + hashes; `dagster_home` schema/version; dbt **manifest hash** (`target/manifest.json`) + seed checksums to pin the code version that rebuilds. |
| **Restorable — Gate A** | restored DB matches manifest | restored parquet set + `dagster_home` + seeds match the manifest (hashes + inventory). |
| **Restorable — Gate B** | boot ephemeral app + read + write | **rebuild-from-source**: in an isolated env, restore raw → `dbt run` → serving build → assert the rebuilt marts are correct by **invariants** (row counts within tolerance, reuse the existing **recon checks** + **KPI closure** invariant), **not** byte-identical DB files. This is also the realistic *cross-version* recovery path (old data + current code). |
| **Tamper test** | corrupt a cell → caught | drop a parquet partition / mutate a row group → the rebuild's recon/KPI invariant must FAIL. |
| **Isolation** | no prod mounts/route | rebuild in a scratch warehouse dir + scratch `dagster_home`; never write prod `data_lake`, `sapo_warehouse.duckdb`, or `olap.duckdb`; fingerprint prod unchanged. |

## 2.3 What to reuse vs build
- **Reuse:** manifest+checksum verification, ephemeral isolated env, fail-loud Dagster wiring, the socket-isolated sidecar pattern, exit-code contract.
- **Existing assets to fold in:** `scripts/backup/backup.sh` (already copies `data_lake`/`dagster_home`/`crm_data` — but raw, **WAL-unsafe**: replace its DB legs with gated snapshots), the `system_backup.py` Dagster op, lessons **L50/L51/L56/L58/L68**.
- **Detailed plan:** `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (source-of-truth + parquet-first strategy). Coordinate backup **security/encryption** with `plans/260624-1958-pipeline-hardening-followups/` (out of scope here).

---

# Part 3 — Operations

## Run the CRM drill manually
- **Via the sidecar (prod path):** `POST http://crm_drill_runner:9000/run-drill` with header `X-Drill-Token: <DRILL_TOKEN>` (from inside `caddy_net`, e.g. `docker exec data_platform …`). 200 = PASS; 500 = FAIL (body carries the log tail).
- **Negative check:** add `?negative=value` (or `row` / `truncate` / `file`) — expect the drill to **catch** the tamper.
- **Host/dev mode:** run `crm/ops/restore_verify_crm.py` directly (uses a host temp dir + published port; `--negative <mode>` supported).

## Trigger the scheduled job
Dagster → `crm_backup_job` (materializes `crm_backup` then `crm_restore_verify`). A red run ⇒ the failure sensor alerts.

## Honest limits (state these, don't hide them)
- **RPO:** daily (02:00). A loss between backups loses up to ~24h. Tighten cadence if the data justifies it.
- **DR scope:** backups are **local-only** (Docker named volumes) — this is **not** real DR against host loss. A minimal **offsite copy** + a **backup-age SLA alert** are the next gaps to close (tracked in the warehouse-DR plan).
- **Drill cost:** each drill spins an ephemeral instance; warehouse rebuild-and-verify is heavier (full `dbt run`) — schedule accordingly (CRM: daily; warehouse: match to its RPO).

---

## Reference index
- **CRM code:** `crm/ops/backup_crm.py`, `crm/ops/restore_verify_crm.py`, `crm/ops/drill_runner_server.py`, `Dockerfile.drillrunner`; `orchestration/assets/crm_sync.py` (`crm_backup`, `crm_restore_verify`); `orchestration/definitions.py` (`crm_backup_job`).
- **Plans:** `plans/260624-2010-crm-backup-checkpoint-restore-verify/` (CRM pilot, done), `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (warehouse, to implement).
- **Lessons:** L50 (always-run rotation cleanup), L56/L68 (never raw-copy a live WAL DB), L58 (2× disk pre-flight), L147 (vacuous-probe ⇒ tamper tests), L148 (CRLF in shell scripts), L150 (socket-sidecar reaches siblings by network name) — `.skills/data-pipeline/references/lessons-learned.md`.
