# tools/resource-meter — read-only resource meter

A single static binary that runs on the host, outside every container. It shows how much
RAM, CPU and disk each container uses, each process inside `data_platform`, and (from the
Dagster process tree) each run, step and dbt model. It reads numbers the kernel already
keeps (cgroup v2 files and `/proc`), Dagster's own run events (read-only GraphQL on
loopback), and dbt's `run_results.json`. It never writes to a cgroup, sends a signal, calls
the Docker API, opens DuckDB, or writes anywhere except its own output directory.

Commands: `run` (the collector, started by the systemd unit), and `report`, `compare` and
`status` to read the results. Install and uninstall: [Install](#install-and-uninstall).
Operations summary: [docs/operations/resource-meter.md](../../docs/operations/resource-meter.md).

## Reading the results

These commands need no root and nothing else installed. They read the TSV files of
`--dir` (default `/var/lib/resource-meter`) directly, `.gz` included. On a full day, a
command takes about 0.1 s.

```bash
resource-meter status                         # running? own RSS/CPU, unit limits hit, data size
resource-meter report                         # today
resource-meter report --date 2026-10-18 --top 10
resource-meter report --job pipeline_batch_nightly_job
resource-meter report --container data_platform
resource-meter compare --base 2026-10-18 --date 2026-10-25           # what got heavier
resource-meter compare --base 2026-10-18 --job pipeline_batch_nightly_job --threshold-pct 20
```

- **`report`** prints four parts:
  - **Containers**, sorted by peak RAM. RAM means `anon`, the processes' own memory.
    `+CACHE PEAK` is `memory.current`, which includes page cache and is the number
    `memory.peak` reports. The rest are increases over the day: `HIT LIMIT` (times
    `memory.max` was reached), `OOM KILL`, `CPU-S`, `THROTTLED-S` and disk bytes.
  - **Heaviest Dagster steps**, by peak RSS of the step's process tree.
  - **Heaviest dbt models**, by total execute time.
  - **The meter's own cost.**
- **`compare`** takes, for each step (`job / step_key`) and each model, the per-run
  median of time, peak RSS and CPU seconds on each day. It flags a metric that grew by
  more than `--threshold-pct` (default 10%), as long as the absolute growth is at least
  0.5 s or 8 MB, so tiny models are not flagged. It also lists steps and models that
  appear on only one of the two days.
- **`status`** exits 0 when the meter wrote its `self` row in the last 150 s, and exits 3
  otherwise. It also prints the unit's memory peak, how often `MemoryMax` was reached,
  OOM kills, and the share of wall time it was CPU-throttled since it started (`throttled_usec`
  divided by the age of the meter process), all read from the unit's cgroup.

## Build

```bash
cd tools/resource-meter
cargo test && cargo clippy --all-targets -- -D warnings
cargo build --release          # static-pie binary (glibc linked statically, see .cargo/config.toml)
```

The crate has two dependencies: `flate2` (pure-Rust backend) for gzip and `serde_json` (with
`raw_value`) for JSON. HTTP is a small built-in client over `std::net`. The crate is separate
from the Docker builds and uses no async runtime and no threads.

## Run

```bash
resource-meter run [--out-dir DIR] [--track data_platform] [--duration SECS]
                   [--retention-days 90] [--utc-offset-hours 7] [--rss-threshold-mb 256]
                   [--dagster-graphql 127.0.0.1:3000] [--dbt-target-dir DIR]
                   [--cgroup-root /sys/fs/cgroup] [--proc-root /proc] [--docker-root /var/lib/docker]
```

- `--out-dir`: default `/var/lib/resource-meter`. For a manual test, use a scratch directory.
  Never use the repo, `app_data` or the lake.
- `--track`: the containers whose processes are followed, given as names or id prefixes of
  12 or more characters. Names come from `/var/lib/docker/containers/<id>/config.v2.json`,
  which only root can read. Without root, pass the id prefix
  (`docker inspect -f '{{.Id}}' data_platform | cut -c1-12`).
- `--duration`: stop after N seconds. Without it, the meter runs until it is stopped.
  Before stopping, the meter attributes the runs and dbt invocations that have already
  ended. Runs still in progress are dropped.
- `--dagster-graphql`: Dagster's GraphQL endpoint, given as a loopback `IP:PORT[/path]`
  (default `127.0.0.1:3000`, the `data_platform` webserver). Only loopback addresses are
  accepted. Use `off` to write steps without job and step key.
- `--dbt-target-dir`: the host path of the dbt target directory that `data_platform`
  bind-mounts (default: `transformation/` + `target` under the production checkout
  `/home/vantt/app/fg-dataware-house`). Use `off` to skip models.

### Root or not

As root, the meter records everything. As a normal user, everything works except two
things: container names (the `container` column shows the 12-character id instead), and
per-process disk bytes (`read_bytes`/`write_bytes` stay empty, because `/proc/<pid>/io` of a
root process needs root). The meter never reads `/proc/<pid>/environ`.

## What it samples, and how often

| Every | What | Source |
|---|---|---|
| 15 s | every container: one row | `/sys/fs/cgroup/system.slice/docker-<id>.scope/` `memory.current`, `memory.max`, `memory.stat`, `memory.events`, `cpu.stat`, `io.stat`, `{memory,cpu,io}.pressure` |
| 15 s | long-lived processes of tracked containers (webserver, daemon, code server) | `/proc/<pid>/{status,stat,io}` |
| 1 s | new and exited processes of tracked containers | the container's `cgroup.procs` (one small file, no `/proc` scan) |
| 1 s | processes of Dagster runs (run worker, step, children) | `/proc/<pid>/{status,stat,io}` |
| 250 ms | dbt processes, only while one is running | same |
| 60 s | the meter itself (`self` row) | `/proc/self/{status,stat,io}` |

How a process is placed in the Dagster tree (Dagster 1.13, `DefaultRunLauncher`):

- `dagster api grpc` (the code server) spawns one `multiprocessing` child per run. That
  child is the **run worker**.
- Under the multiprocess executor, the run worker spawns one child per step. That child
  is a **step**.
- dbt runs as `.../dbt <subcommand>` under the step, and is named `dbt build`,
  `dbt parse` or `dbt version`.
- Dagster starts `tail -F .../storage/<run_id>/compute_logs/<file_key>.out` under each step
  (or under the run worker, with the in-process executor). The meter takes only `run_id` and
  `file_key` from that path. Every descendant inherits the run id.
- A step that ends before its `tail` is first seen (short asset checks, about 2 s) still gets
  the run id from its run worker. Its `file_key` stays empty. A step is matched to its step
  key later through `ns_pid`, the PID that Dagster's own events report.

When no `tail` was ever seen for a run (all its steps were shorter than one pass, as for a
run that waited in the queue and then finished in seconds), the run id is looked up in
Dagster instead. The candidates are runs updated since the worker started, and one is
accepted only if its "Started process for run (pid: N)" event names this worker's container
PID.

Full command lines are never stored. Processes get a short, path-free name (`dbt build`,
`mp-spawn`, `refresh_rolling.py`, `dagster_webserver`). The dbt `--select` list in
particular is never kept.

## Output files

The output is one TSV file per kind and per local day (`--utc-offset-hours`, default
UTC+7): `<kind>-YYYYMMDD.tsv`, with a header line. Rows are appended and flushed every
tick, so a crash or power loss loses at most one tick. When the day changes, files of past
days are gzipped (`.tsv.gz`; through a `.tmp` file and then a rename). Files older than
`--retention-days` are deleted. Other files in the directory are never touched.

Read the files with `less`, `column -t -s $'\t'`, `zcat`, or any TSV reader. An empty cell
means "not available".

### `containers-YYYYMMDD.tsv`

| Column | Meaning |
|---|---|
| `ts` | Unix seconds (UTC) |
| `container`, `cid` | name (id prefix without root), first 12 characters of the id |
| `mem_current` | `memory.current` in bytes. **Includes page cache.** Use `anon` for the processes' own memory. |
| `anon`, `file`, `kernel`, `shmem` | from `memory.stat`, in bytes |
| `mem_max` | `memory.max` in bytes (empty when there is no limit) |
| `ev_max`, `ev_oom`, `ev_oom_kill` | `memory.events` counters, cumulative since the container started |
| `cpu_usage_usec`, `cpu_throttled_usec`, `nr_throttled` | `cpu.stat`, cumulative |
| `io_rbytes`, `io_wbytes` | `io.stat`, summed over every device, cumulative |
| `psi_mem_some10`, `psi_mem_full10`, `psi_cpu_some10`, `psi_io_some10` | pressure `avg10`, in percent |

Cumulative counters are written raw. Take the difference between two rows of the same
`cid` to get a rate. When a container is recreated, its `cid` changes and the counters
restart.

The `self` row has `container=self` and an empty `cid`. It reuses these columns as follows:
`mem_current` holds the meter's RSS in bytes, `mem_max` its peak RSS (VmHWM) in bytes,
`cpu_usage_usec` its total CPU time, and `io_rbytes`/`io_wbytes` its own disk bytes.

### `processes-YYYYMMDD.tsv` (one row when a process exits)

| Column | Meaning |
|---|---|
| `ts_start`, `ts_end` | process start (from `/proc/<pid>/stat` and boot time), last time it was seen alive (within 1 s, or 250 ms for dbt) |
| `container` | as above |
| `host_pid`, `ns_pid`, `ns_ppid` | PID on the host, and PID and parent PID inside the container (the PIDs Dagster logs) |
| `role` | `run_worker`, `step`, `dbt`, `step_child`, `service`, `helper` |
| `name` | short name, never the command line |
| `run_id`, `file_key` | Dagster run id and compute-log key, when known |
| `rss_hwm_kb` | peak RSS reported by the kernel (`VmHWM`), so short peaks between samples are counted too |
| `rss_max_kb` | highest sampled RSS |
| `cpu_s` | user + system CPU seconds, up to the last sample |
| `read_bytes`, `write_bytes` | from `/proc/<pid>/io` (root only) |

Rows are written for every process of a Dagster run (`run_worker`, `step`, `dbt`,
`step_child`). Other processes get a row only when their RSS reached
`--rss-threshold-mb`. Dagster's log `tail` and orphan-watcher helpers count as `helper`.

Per-second samples of run processes stay in memory (at most 4,096 per process, at most
2,000 tracked processes). They are kept for attribution to steps and dbt models and are
not written to disk.

### `steps-YYYYMMDD.tsv` (rows written when a run ends)

| Column | Meaning |
|---|---|
| `run_id`, `job` | Dagster run id and job name |
| `step_key` | Dagster step key (comma-separated if one process ran several). `*` = the whole run under the in-process executor. `(run_worker)` = the run worker's own process under the multiprocess executor, without its steps. Empty when Dagster could not be asked. |
| `executor` | `multiprocess` or `in_process` |
| `ts_start`, `ts_end` | start of the step process (2–3 s before Dagster's `STEP_START`, because of Python start-up) and last time it was seen alive |
| `ns_pid` | container PID of the step process |
| `rss_peak_tree_kb` | peak of the summed RSS of the step process and its descendants (dbt included), per whole second |
| `cpu_s`, `read_bytes`, `write_bytes` | summed over the same processes |

How the attribution works:

1. Processes of one run are kept in memory under their run worker until the worker exits.
2. Ten seconds later, Dagster GraphQL is asked once for the run (`runOrError`: job name)
   and for its events (`logsForRun`, 1,000 per page). Only queries are sent, never mutations.
3. Each step process is matched to its `LogsCapturedEvent` by container PID, or else by
   compute-log key.
4. If GraphQL fails, the request is retried every 5 minutes. After 12 hours, the rows are
   written without job and step key. A run Dagster does not know is written without keys
   at once.

At most one run is looked up per second, and a lookup costs about 0.1 s.

### `models-YYYYMMDD.tsv` (rows written when a `dbt build` process exits)

| Column | Meaning |
|---|---|
| `run_id` | Dagster run of the build |
| `unique_id`, `status` | from `run_results.json` (`model.`, `seed.` and `snapshot.` nodes whose `execute` took at least 0.1 s; tests, skipped nodes and shorter nodes get no row) |
| `ts_start`, `ts_end` | the node's `execute` timing |
| `exec_s` | `execution_time` from `run_results.json` |
| `rss_peak_kb`, `rss_delta_kb`, `cpu_s` | memory and CPU of the dbt process during `execute`, from its 250 ms samples. `rss_delta_kb` is the peak minus the RSS just before the model started, and can be negative. Empty when the model took less than 1 s. |
| `rows_affected` | `adapter_response.rows_affected` when dbt-duckdb reports it (rarely) |

dagster-dbt runs each invocation in `<target dir>/<op>-<run_id[:7]>-<7 hex>/`, and the
cleanup loop of `data_platform` deletes these directories after about 24 hours. The meter
reads `run_results.json` right after the build exits, retrying for up to one minute. Among
the run's directories, it picks the one whose `generated_at` falls within the process
lifetime. The file is parsed lazily (`serde_json::value::RawValue`): `compiled_code` and
`args` (which holds the full command line) are never decoded or copied.

dbt runs with `threads: 1`, so the process's samples during a model's `execute` window
belong to that model. In the realtime and incremental jobs, every model takes under 1 s,
so only time is recorded for them. Models that run longer, in the nightly or a full
refresh, also get memory and CPU.

## Install and uninstall

The unit [`resource-meter.service`](resource-meter.service) runs `resource-meter run` as
root, with these limits:

- resources: `MemoryMax=32M`, `CPUQuota=2%` with `CPUQuotaPeriodSec=1s` (20 ms per second, so one scan is not throttled), `Nice=19`, `IOSchedulingClass=idle`;
- read-only filesystem except `/var/lib/resource-meter`;
- cgroups read-only;
- only `CAP_SYS_PTRACE` (to read `/proc/<pid>/io`) and `CAP_DAC_READ_SEARCH` (to read
  `run_results.json` under `/home/vantt`);
- network limited to loopback, for the Dagster GraphQL endpoint.

Installing touches no container and restarts nothing else. The script refuses to run
between 02:30 and 04:00 unless `--force` is given.

```bash
# 1. as your user: build (root has no Rust toolchain)
cd tools/resource-meter && cargo build --release
# 2. install or upgrade, then start
sudo tools/resource-meter/install.sh
# 3. check after one minute, and again after 15 minutes
resource-meter status
resource-meter report
```

To uninstall:

```bash
sudo tools/resource-meter/install.sh --uninstall            # keeps /var/lib/resource-meter
sudo tools/resource-meter/install.sh --uninstall --purge    # also deletes the data
```

This is equivalent to `systemctl disable --now resource-meter`, then removing
`/usr/local/bin/resource-meter`, `/etc/systemd/system/resource-meter.service` and (with
`--purge`) `/var/lib/resource-meter`. Logs: `journalctl -u resource-meter`.

If `read_bytes`/`write_bytes` stay empty in `processes-*.tsv` after the install, the
capability set was too narrow for `/proc/<pid>/io` on this kernel. Remove the
`CapabilityBoundingSet=` line from the unit and install again.

## Cost (measured)

A 200-second manual run on the host on 17/10/2026, as a normal user, with 21 containers and
Dagster realtime runs active, measured:

- RSS 1.4 MB;
- CPU 0.10 s in total (0.05% of one core);
- about 49 KB of output.

Projected for one day: about 18 MB raw `containers` plus about 2.4 MB raw `processes`,
which is about 3 MB/day after gzip.

With attribution, a 360-second run (5 runs, 3 dbt builds, 18 GraphQL lookups) measured:

- peak RSS 3.9 MB (`run_results.json`, about 2 MB, is read once per build);
- CPU 0.20 s (0.06% of one core).

Model rows are written only for nodes whose `execute` took at least 0.1 s. In a realtime
or incremental build, that keeps about 25 of the 209 nodes (12%), so `models` adds about
2 MB raw a day. With the other files, the total is about 23 MB raw and **about 3.3 MB
gzipped per day**. Only the current day stays uncompressed.
