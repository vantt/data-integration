//! The sampling loop: one thread, sleeping between ticks.
//!
//! - every 15 s: every container scope -> `containers-*.tsv`; long-lived processes sampled;
//! - every 1 s: `cgroup.procs` of watched containers (new and gone processes) and
//!   run-related processes sampled;
//! - every 250 ms while a dbt process is alive: dbt processes sampled;
//! - every 60 s: a `self` row with the meter's own RSS, CPU and disk use.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::{Duration, Instant};

use crate::clock::{day_stamp, local_day, now_epoch};
use crate::containers::{self, Scope};
use crate::procfs::{ProcFs, CLK_TCK};
use crate::tracker::{Limits, Proc, Role, Tracker};
use crate::tsv::{housekeeping, DailyWriter, Row};

pub const CONTAINER_EVERY: Duration = Duration::from_secs(15);
pub const PROCESS_EVERY: Duration = Duration::from_secs(1);
pub const DBT_EVERY: Duration = Duration::from_millis(250);
pub const SELF_EVERY: Duration = Duration::from_secs(60);
const ERROR_REPEAT_EVERY: Duration = Duration::from_secs(300);

pub const CONTAINERS_HEADER: &str = "ts\tcontainer\tcid\tmem_current\tanon\tfile\tkernel\tshmem\tmem_max\tev_max\tev_oom\tev_oom_kill\tcpu_usage_usec\tcpu_throttled_usec\tnr_throttled\tio_rbytes\tio_wbytes\tpsi_mem_some10\tpsi_mem_full10\tpsi_cpu_some10\tpsi_io_some10";
pub const PROCESSES_HEADER: &str = "ts_start\tts_end\tcontainer\thost_pid\tns_pid\tns_ppid\trole\tname\trun_id\tfile_key\trss_hwm_kb\trss_max_kb\tcpu_s\tread_bytes\twrite_bytes";

#[derive(Debug, Clone)]
pub struct Config {
    pub out_dir: PathBuf,
    pub cgroup_root: PathBuf,
    pub proc_root: PathBuf,
    pub docker_root: PathBuf,
    /// Containers whose processes are tracked: names, or id prefixes of 12+ characters.
    pub track: Vec<String>,
    pub duration: Option<Duration>,
    pub retention_days: u32,
    pub utc_offset_hours: i32,
    /// Processes outside a Dagster run are written only when their RSS reached this.
    pub rss_threshold_kb: u64,
}

/// Prints an error, but the same message at most once per `ERROR_REPEAT_EVERY`.
#[derive(Default)]
struct ErrorLog {
    last: HashMap<String, Instant>,
}

impl ErrorLog {
    fn report(&mut self, msg: String) {
        let now = Instant::now();
        let due = self
            .last
            .get(&msg)
            .is_none_or(|t| now.duration_since(*t) >= ERROR_REPEAT_EVERY);
        if due {
            eprintln!("resource-meter: {msg}");
            // Messages can carry counters; keep the map bounded.
            if self.last.len() >= 256 {
                self.last.retain(|_, t| now.duration_since(*t) < ERROR_REPEAT_EVERY);
            }
            self.last.insert(msg, now);
        }
    }
}

fn advance(next: &mut Instant, every: Duration, now: Instant) {
    *next += every;
    if *next <= now {
        *next = now + every;
    }
}

struct Collector {
    cfg: Config,
    procfs: ProcFs,
    tracker: Tracker,
    names: HashMap<String, String>,
    watched: Vec<Scope>,
    containers_out: DailyWriter,
    processes_out: DailyWriter,
    day: i64,
    errors: ErrorLog,
    dropped_reported: u64,
}

pub fn run(cfg: Config) -> Result<(), String> {
    let mut c = Collector::new(cfg)?;
    eprintln!(
        "resource-meter: writing to {} (day {}), tracking processes of: {}",
        c.cfg.out_dir.display(),
        day_stamp(c.day),
        c.cfg.track.join(",")
    );
    c.run_loop();
    c.close_writers();
    Ok(())
}

impl Collector {
    fn new(cfg: Config) -> Result<Self, String> {
        fs::create_dir_all(&cfg.out_dir).map_err(|e| format!("create {}: {e}", cfg.out_dir.display()))?;
        let procfs = ProcFs::new(&cfg.proc_root);
        let btime = procfs
            .btime()
            .ok_or_else(|| format!("cannot read btime from {}/stat", cfg.proc_root.display()))?;
        let mut c = Collector {
            tracker: Tracker::new(procfs.clone(), btime, Limits::default()),
            procfs,
            names: HashMap::new(),
            watched: Vec::new(),
            containers_out: DailyWriter::new(&cfg.out_dir, "containers", CONTAINERS_HEADER),
            processes_out: DailyWriter::new(&cfg.out_dir, "processes", PROCESSES_HEADER),
            day: local_day(now_epoch(), cfg.utc_offset_hours),
            errors: ErrorLog::default(),
            dropped_reported: 0,
            cfg,
        };
        c.housekeep();
        Ok(c)
    }

    fn run_loop(&mut self) {
        let start = Instant::now();
        let end = self.cfg.duration.map(|d| start + d);
        let (mut next_container, mut next_process, mut next_dbt) = (start, start, start);
        let mut next_self = start + SELF_EVERY;

        loop {
            let now = Instant::now();
            if end.is_some_and(|e| now >= e) {
                self.write_self_row(now_epoch());
                break;
            }
            let epoch = now_epoch();
            self.roll_day(epoch);

            let mut exited = Vec::new();
            if now >= next_container {
                exited.extend(self.container_tick(epoch));
                advance(&mut next_container, CONTAINER_EVERY, now);
            }
            if now >= next_process {
                exited.extend(self.process_tick(epoch));
                advance(&mut next_process, PROCESS_EVERY, now);
                next_dbt = now + DBT_EVERY;
            } else if now >= next_dbt {
                exited.extend(self.tracker.sample(epoch, |r| r == Role::Dbt));
                advance(&mut next_dbt, DBT_EVERY, now);
            }
            if now >= next_self {
                self.write_self_row(epoch);
                advance(&mut next_self, SELF_EVERY, now);
            }
            self.write_exits(&exited);
            self.flush_writers();

            let mut wake = next_container.min(next_process).min(next_self);
            if self.tracker.any_dbt() {
                wake = wake.min(next_dbt);
            }
            if let Some(e) = end {
                wake = wake.min(e);
            }
            thread::sleep(wake.saturating_duration_since(Instant::now()));
        }
    }

    fn roll_day(&mut self, epoch: f64) {
        let today = local_day(epoch, self.cfg.utc_offset_hours);
        if today != self.day {
            self.close_writers();
            self.day = today;
            self.housekeep();
        }
    }

    fn housekeep(&mut self) {
        let r = housekeeping(&self.cfg.out_dir, self.day, self.cfg.retention_days);
        for e in r.errors {
            self.errors.report(e);
        }
    }

    fn display_name(&self, id: &str) -> String {
        self.names
            .get(id)
            .cloned()
            .unwrap_or_else(|| id[..12.min(id.len())].to_string())
    }

    fn is_tracked(&self, scope: &Scope) -> bool {
        let name = self.names.get(&scope.id);
        self.cfg
            .track
            .iter()
            .any(|t| name.is_some_and(|n| n == t) || (t.len() >= 12 && scope.id.starts_with(t.as_str())))
    }

    /// Writes one row per container, refreshes the watched set and samples services.
    fn container_tick(&mut self, epoch: f64) -> Vec<Proc> {
        let scopes = containers::list_scopes(&self.cfg.cgroup_root);
        if scopes.is_empty() {
            self.errors.report(format!(
                "no docker scopes under {}/system.slice",
                self.cfg.cgroup_root.display()
            ));
        }
        let ts = epoch.floor() as u64;
        let day = self.day;
        for scope in &scopes {
            if !self.names.contains_key(&scope.id) {
                if let Some(n) = containers::container_name(&self.cfg.docker_root, &scope.id) {
                    self.names.insert(scope.id.clone(), n);
                }
            }
            let Some(s) = containers::read_sample(&scope.dir) else {
                continue;
            };
            let line = Row::new()
                .int(ts)
                .text(&self.display_name(&scope.id))
                .text(scope.short_id())
                .int(s.mem_current)
                .int(s.mem.anon)
                .int(s.mem.file)
                .int(s.mem.kernel)
                .int(s.mem.shmem)
                .int(s.mem_max)
                .int(s.events.max)
                .int(s.events.oom)
                .int(s.events.oom_kill)
                .int(s.cpu.usage_usec)
                .int(s.cpu.throttled_usec)
                .int(s.cpu.nr_throttled)
                .int(s.io.as_ref().map(|i| i.rbytes))
                .int(s.io.as_ref().map(|i| i.wbytes))
                .dec(s.psi_mem.some_avg10, 2)
                .dec(s.psi_mem.full_avg10, 2)
                .dec(s.psi_cpu.some_avg10, 2)
                .dec(s.psi_io.some_avg10, 2)
                .finish();
            if let Err(e) = self.containers_out.write_row(day, &line) {
                self.errors.report(format!("write containers: {e}"));
            }
        }
        // Drop names of containers that no longer exist, so the cache stays bounded.
        self.names.retain(|id, _| scopes.iter().any(|s| &s.id == id));

        let watched: Vec<Scope> = scopes.iter().filter(|s| self.is_tracked(s)).cloned().collect();
        let mut exited = Vec::new();
        for old in &self.watched {
            if !watched.iter().any(|s| s.id == old.id) {
                exited.extend(self.tracker.forget_container(&old.id));
            }
        }
        if watched.is_empty() && !self.cfg.track.is_empty() {
            self.errors.report(format!(
                "no running container matches --track {}",
                self.cfg.track.join(",")
            ));
        }
        self.watched = watched;
        exited.extend(self.tracker.sample(epoch, |r| r == Role::Service));
        exited
    }

    /// New and gone processes of watched containers; samples run-related processes.
    fn process_tick(&mut self, epoch: f64) -> Vec<Proc> {
        let mut exited = Vec::new();
        for scope in self.watched.clone() {
            // An unreadable list means the container just went away: all its processes are gone.
            let pids = fs::read_to_string(scope.procs_file())
                .map(|t| crate::cgroup::parse_procs(&t))
                .unwrap_or_default();
            exited.extend(self.tracker.discover(&scope.id, &pids, epoch));
        }
        exited.extend(self.tracker.sample(epoch, Role::is_run_related));
        let dropped = self.tracker.dropped_new();
        if dropped > self.dropped_reported {
            self.errors
                .report(format!("process limit reached, {dropped} new processes not tracked"));
            self.dropped_reported = dropped;
        }
        exited
    }

    fn write_exits(&mut self, exited: &[Proc]) {
        for p in exited {
            if !(p.role.is_run_related() || p.rss_max_kb >= self.cfg.rss_threshold_kb) {
                continue;
            }
            let day = local_day(p.last_seen, self.cfg.utc_offset_hours);
            let line = Row::new()
                .dec(p.start_epoch, 3)
                .dec(p.last_seen, 3)
                .text(&self.display_name(&p.container_id))
                .int(u64::from(p.host_pid))
                .int(p.ns_pid.map(u64::from))
                .int(p.ns_ppid.map(u64::from))
                .text(p.role.as_str())
                .text(&p.name)
                .opt_text(p.run_id.as_deref())
                .opt_text(p.file_key.as_deref())
                .int(p.hwm_kb)
                .int(p.rss_max_kb)
                .dec(p.cpu_seconds(), 2)
                .int(p.read_bytes)
                .int(p.write_bytes)
                .finish();
            if let Err(e) = self.processes_out.write_row(day, &line) {
                self.errors.report(format!("write processes: {e}"));
            }
        }
    }

    fn write_self_row(&mut self, epoch: f64) {
        let status = self.procfs.self_status();
        let stat = self.procfs.self_stat();
        let io = self.procfs.self_io();
        let line = Row::new()
            .int(epoch.floor() as u64)
            .text("self")
            .text("")
            .int(status.as_ref().and_then(|s| s.rss_kb).map(|kb| kb * 1024))
            .int(None)
            .int(None)
            .int(None)
            .int(None)
            .int(status.as_ref().and_then(|s| s.hwm_kb).map(|kb| kb * 1024))
            .int(None)
            .int(None)
            .int(None)
            .int(stat.map(|s| (s.utime + s.stime) * (1_000_000 / CLK_TCK)))
            .int(None)
            .int(None)
            .int(io.map(|i| i.read_bytes))
            .int(io.map(|i| i.write_bytes))
            .dec(None, 2)
            .dec(None, 2)
            .dec(None, 2)
            .dec(None, 2)
            .finish();
        if let Err(e) = self.containers_out.write_row(self.day, &line) {
            self.errors.report(format!("write containers: {e}"));
        }
    }

    fn flush_writers(&mut self) {
        for (name, w) in [
            ("containers", &mut self.containers_out),
            ("processes", &mut self.processes_out),
        ] {
            if let Err(e) = w.flush() {
                self.errors.report(format!("flush {name}: {e}"));
            }
        }
    }

    fn close_writers(&mut self) {
        for (name, w) in [
            ("containers", &mut self.containers_out),
            ("processes", &mut self.processes_out),
        ] {
            if let Err(e) = w.close() {
                self.errors.report(format!("close {name}: {e}"));
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{fake_proc, TempTree};

    const DP: &str = "c7ba6271e6e554ed72810197daa437be348f05af93a2c54385316e497a15c8de";
    const OTHER: &str = "043102d9bd91caab91a078fedcc1d743aadde3c26f1d8fa516d8659f39e46c30";
    const RUN: &str = "0a1b2c3d-0000-4111-8222-123456789abc";
    const FORK: &[&str] = &[
        "/usr/local/bin/python3.10",
        "-c",
        "spawn_main()",
        "--multiprocessing-fork",
    ];

    fn scope(t: &TempTree, id: &str, procs: &str) {
        let d = format!("cg/system.slice/docker-{id}.scope");
        t.file(&format!("{d}/memory.current"), "1000\n");
        t.file(&format!("{d}/memory.stat"), "anon 600\nfile 300\nkernel 90\nshmem 10\n");
        t.file(&format!("{d}/memory.events"), "max 5\noom 0\noom_kill 0\n");
        t.file(
            &format!("{d}/cpu.stat"),
            "usage_usec 77\nnr_throttled 2\nthrottled_usec 9\n",
        );
        t.file(&format!("{d}/memory.max"), "max\n");
        t.file(&format!("{d}/cgroup.procs"), procs);
    }

    fn config(t: &TempTree) -> Config {
        Config {
            out_dir: t.path().join("out"),
            cgroup_root: t.path().join("cg"),
            proc_root: t.path().join("proc"),
            docker_root: t.path().join("docker"),
            track: vec!["data_platform".into()],
            duration: None,
            retention_days: 90,
            utc_offset_hours: 7,
            rss_threshold_kb: 256 * 1024,
        }
    }

    fn proc_tree(t: &TempTree) {
        let p = TempTree::sub(t, "proc");
        p.file("stat", "btime 1000\n");
        fake_proc(
            &p,
            10,
            1,
            202,
            "python3.10",
            &["/usr/local/bin/python3.10", "-m", "dagster", "api", "grpc"],
            100,
            300_000,
            500,
            None,
        );
        fake_proc(
            &p,
            11,
            1,
            203,
            "python3.10",
            &["/usr/local/bin/python3.10", "-m", "dagster_webserver"],
            100,
            400_000,
            500,
            None,
        );
        fake_proc(&p, 20, 10, 900, "python3.10", FORK, 5000, 200_000, 50, None);
        fake_proc(&p, 30, 20, 901, "python3.10", FORK, 5100, 250_000, 70, None);
        let log = format!("/app/var/dagster_home/storage/{RUN}/compute_logs/qbiabrcl.out");
        fake_proc(
            &p,
            31,
            30,
            902,
            "tail",
            &["tail", "-F", "-c", "+0", &log],
            5110,
            1_000,
            0,
            None,
        );
        fake_proc(
            &p,
            40,
            30,
            903,
            "dbt",
            &[
                "/usr/local/bin/python3.10",
                "/usr/local/bin/dbt",
                "build",
                "--select",
                "secret_model_list",
            ],
            5200,
            600_000,
            300,
            None,
        );
    }

    fn read_out(t: &TempTree, kind: &str, day: i64) -> String {
        fs::read_to_string(t.path().join("out").join(format!("{kind}-{}.tsv", day_stamp(day)))).unwrap_or_default()
    }

    #[test]
    fn writes_container_rows_and_process_exits() {
        let t = TempTree::new();
        scope(&t, DP, "10\n11\n20\n30\n31\n40\n");
        scope(&t, OTHER, "");
        t.file(
            &format!("docker/containers/{DP}/config.v2.json"),
            r#"{"Name":"/data_platform","Config":{"Env":["PASSWORD=hunter2"]}}"#,
        );
        proc_tree(&t);
        let mut c = Collector::new(config(&t)).unwrap();
        let day = c.day;

        let now = 1_792_195_300.0;
        assert!(c.container_tick(now).is_empty());
        assert_eq!(c.watched.len(), 1);
        assert!(c.process_tick(now).is_empty());

        // dbt and the step end; the tail ends too (helper rows are not written).
        t.file(
            &format!("cg/system.slice/docker-{DP}.scope/cgroup.procs"),
            "10\n11\n20\n",
        );
        let exited = c.process_tick(now + 1.0);
        assert_eq!(exited.len(), 3);
        c.write_exits(&exited);
        c.write_self_row(now + 1.0);
        c.flush_writers();

        let containers = read_out(&t, "containers", day);
        let lines: Vec<&str> = containers.lines().collect();
        assert_eq!(lines[0], CONTAINERS_HEADER);
        assert_eq!(lines.len(), 4, "{containers}");
        let dp: Vec<&str> = lines
            .iter()
            .find(|l| l.contains("data_platform"))
            .unwrap()
            .split('\t')
            .collect();
        assert_eq!(dp.len(), CONTAINERS_HEADER.split('\t').count());
        assert_eq!(
            &dp[..9],
            &[
                "1792195300",
                "data_platform",
                "c7ba6271e6e5",
                "1000",
                "600",
                "300",
                "90",
                "10",
                ""
            ]
        );
        assert!(lines
            .iter()
            .any(|l| l.starts_with("1792195300\t043102d9bd91\t043102d9bd91")));
        assert!(lines[3].split('\t').nth(1) == Some("self"));

        let processes = read_out(&t, "processes", day);
        let rows: Vec<Vec<&str>> = processes.lines().skip(1).map(|l| l.split('\t').collect()).collect();
        assert_eq!(processes.lines().next(), Some(PROCESSES_HEADER));
        assert_eq!(rows.len(), 2, "{processes}");
        let dbt = rows.iter().find(|r| r[6] == "dbt").unwrap();
        assert_eq!(dbt.len(), PROCESSES_HEADER.split('\t').count());
        assert_eq!(
            &dbt[2..10],
            &["data_platform", "40", "903", "901", "dbt", "dbt build", RUN, ""]
        );
        assert_eq!(dbt[11], "600000");
        let step = rows.iter().find(|r| r[6] == "step").unwrap();
        assert_eq!(&step[8..10], &[RUN, "qbiabrcl"]);
        assert!(!processes.contains("secret_model_list") && !containers.contains("hunter2"));
    }

    #[test]
    fn untracked_container_disappearing_ends_its_processes() {
        let t = TempTree::new();
        scope(&t, DP, "10\n20\n30\n");
        proc_tree(&t);
        let mut cfg = config(&t);
        cfg.track = vec![DP[..12].to_string()];
        let mut c = Collector::new(cfg).unwrap();
        c.container_tick(1_792_195_300.0);
        c.process_tick(1_792_195_300.0);
        assert_eq!(c.tracker.len(), 3);
        t.remove(&format!("cg/system.slice/docker-{DP}.scope"));
        let exited = c.container_tick(1_792_195_315.0);
        assert_eq!(exited.len(), 3);
        assert!(c.tracker.is_empty());
    }

    #[test]
    fn rejects_missing_proc_root() {
        let t = TempTree::new();
        assert!(Collector::new(config(&t)).is_err());
    }
}
