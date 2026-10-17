# tools/resource-meter — read-only resource meter

A single static binary that runs on the host, outside every container. It shows how much
RAM, CPU and disk each container uses, each process inside `data_platform`, and (from the
Dagster process tree) each run and step. It only reads numbers the kernel already keeps:
cgroup v2 files and `/proc`. It never writes to a cgroup, sends a signal, calls the Docker
API, opens DuckDB, or writes anywhere except its own output directory.

Status: the collector (`run`) is built. Step and dbt-model attribution, `report`,
`compare`, `status`, the systemd unit and the install script come next. Until the unit
exists, run the binary only by hand, as below.

## Build

```bash
cd tools/resource-meter
cargo test && cargo clippy --all-targets -- -D warnings
cargo build --release          # static-pie binary (glibc linked statically, see .cargo/config.toml)
```

The crate has two dependencies: `flate2` (pure-Rust backend) for gzip and `serde_json` for
JSON. It is separate from the Docker builds and uses no async runtime and no threads.

## Run

```bash
resource-meter run [--out-dir DIR] [--track data_platform] [--duration SECS]
                   [--retention-days 90] [--utc-offset-hours 7] [--rss-threshold-mb 256]
                   [--cgroup-root /sys/fs/cgroup] [--proc-root /proc] [--docker-root /var/lib/docker]
```

- `--out-dir`: default `/var/lib/resource-meter`. For a manual test, use a scratch directory.
  Never use the repo, `app_data` or the lake.
- `--track`: the containers whose processes are followed, given as names or id prefixes of
  12 or more characters. Names come from `/var/lib/docker/containers/<id>/config.v2.json`,
  which only root can read. Without root, pass the id prefix
  (`docker inspect -f '{{.Id}}' data_platform | cut -c1-12`).
- `--duration`: stop after N seconds. Without it, the meter runs until it is stopped.

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

## Cost (measured)

A 200-second manual run on the host on 17/10/2026, as a normal user, with 21 containers and
Dagster realtime runs active, measured:

- RSS 1.4 MB;
- CPU 0.10 s in total (0.05% of one core);
- about 49 KB of output.

Projected for one day: about 18 MB raw `containers` plus about 2.4 MB raw `processes`,
which is about 3 MB/day after gzip.
