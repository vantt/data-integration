//! Per-process tracking for the processes of watched containers.
//!
//! Discovery reads the container's `cgroup.procs` (cheap: one small file) instead of
//! scanning `/proc`. Each process is classified once from its arguments, placed in the
//! Dagster tree (run worker, step, dbt, ...) through its parent, and sampled at a rate
//! that depends on its role. When it disappears, the tracker returns its summary.

use std::collections::{HashMap, HashSet, VecDeque};

use crate::procfs::{classify, Io, Kind, ProcFs, Status, CLK_TCK};

/// Role of a process in the Dagster process tree.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Role {
    /// Long-lived or unrelated process (webserver, daemon, code server, shell).
    Service,
    /// Spawn child of `dagster api grpc`: executes one run.
    RunWorker,
    /// Spawn child of a run worker: executes one step (multiprocess executor).
    Step,
    /// dbt CLI process.
    Dbt,
    /// Any other descendant of a run worker or step.
    StepChild,
    /// Log tailing and orphan watching that only mirror a step.
    Helper,
}

impl Role {
    pub fn as_str(self) -> &'static str {
        match self {
            Role::Service => "service",
            Role::RunWorker => "run_worker",
            Role::Step => "step",
            Role::Dbt => "dbt",
            Role::StepChild => "step_child",
            Role::Helper => "helper",
        }
    }

    /// Roles sampled every second (and written on exit regardless of size).
    pub fn is_run_related(self) -> bool {
        matches!(self, Role::RunWorker | Role::Step | Role::Dbt | Role::StepChild)
    }
}

/// One in-memory sample, kept for later attribution to steps and dbt models.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Sample {
    pub ts: f64,
    pub rss_kb: u64,
    pub cpu_ticks: u64,
}

#[derive(Debug, Clone)]
pub struct Proc {
    pub host_pid: u32,
    pub ns_pid: Option<u32>,
    pub ppid: u32,
    pub ns_ppid: Option<u32>,
    pub container_id: String,
    pub start_ticks: u64,
    /// Process start, seconds since the epoch.
    pub start_epoch: f64,
    /// Last time the process was seen alive.
    pub last_seen: f64,
    pub comm: String,
    pub kind: Kind,
    pub role: Role,
    pub name: String,
    pub run_id: Option<String>,
    pub file_key: Option<String>,
    /// Host PID of the run worker this process belongs to (itself for a run worker).
    pub worker_pid: Option<u32>,
    /// Host PID of the step this process belongs to (itself for a step).
    pub step_pid: Option<u32>,
    pub hwm_kb: Option<u64>,
    pub rss_max_kb: u64,
    pub cpu_ticks: u64,
    pub read_bytes: Option<u64>,
    pub write_bytes: Option<u64>,
    pub samples: VecDeque<Sample>,
}

impl Proc {
    pub fn cpu_seconds(&self) -> f64 {
        self.cpu_ticks as f64 / CLK_TCK as f64
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Limits {
    /// Samples kept per process (ring buffer).
    pub max_samples: usize,
    /// Processes tracked at once; new ones beyond this are ignored.
    pub max_procs: usize,
}

impl Default for Limits {
    fn default() -> Self {
        // 4096 samples cover 17 minutes at 250 ms or 68 minutes at 1 s.
        Self {
            max_samples: 4096,
            max_procs: 2000,
        }
    }
}

pub struct Tracker {
    procfs: ProcFs,
    btime: u64,
    limits: Limits,
    procs: HashMap<u32, Proc>,
    dropped_new: u64,
}

impl Tracker {
    pub fn new(procfs: ProcFs, btime: u64, limits: Limits) -> Self {
        Self {
            procfs,
            btime,
            limits,
            procs: HashMap::new(),
            dropped_new: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.procs.len()
    }

    pub fn is_empty(&self) -> bool {
        self.procs.is_empty()
    }

    pub fn get(&self, pid: u32) -> Option<&Proc> {
        self.procs.get(&pid)
    }

    /// New processes ignored because `max_procs` was reached (cumulative).
    pub fn dropped_new(&self) -> u64 {
        self.dropped_new
    }

    pub fn any_dbt(&self) -> bool {
        self.procs.values().any(|p| p.role == Role::Dbt)
    }

    /// Reconciles the tracked set of one container with its current PID list.
    /// Returns the processes that are gone.
    pub fn discover(&mut self, container_id: &str, pids: &[u32], now: f64) -> Vec<Proc> {
        let current: HashSet<u32> = pids.iter().copied().collect();
        let gone: Vec<u32> = self
            .procs
            .values()
            .filter(|p| p.container_id == container_id && !current.contains(&p.host_pid))
            .map(|p| p.host_pid)
            .collect();
        let exited = self.remove_all(&gone);

        let mut fresh: Vec<(Proc, Option<u64>)> = Vec::new();
        for &pid in pids {
            if self.procs.contains_key(&pid) {
                continue;
            }
            if self.procs.len() + fresh.len() >= self.limits.max_procs {
                self.dropped_new += 1;
                continue;
            }
            if let Some(found) = self.read_new(pid, container_id, now) {
                fresh.push(found);
            }
        }
        // Parents start before their children: resolving in start order lets each new
        // process see its parent's role, including parents discovered in this pass.
        fresh.sort_by_key(|(p, _)| p.start_ticks);
        for (mut p, first_rss) in fresh {
            let pid = p.host_pid;
            p.role = self.resolve_role(&p.kind, p.ppid);
            (p.worker_pid, p.step_pid) = self.owners(pid, p.role, p.ppid);
            push_sample(&mut p, first_rss, now, self.limits.max_samples);
            p.ns_ppid = self.procs.get(&p.ppid).and_then(|parent| parent.ns_pid);
            if p.run_id.is_none() {
                p.run_id = self.inherited_run_id(p.ppid);
            }
            let tail_ids = match &p.kind {
                Kind::ComputeLogTail { run_id, file_key } => Some((run_id.clone(), file_key.clone())),
                _ => None,
            };
            let ppid = p.ppid;
            self.procs.insert(pid, p);
            if let Some((run_id, file_key)) = tail_ids {
                self.attach_run_ids(ppid, &run_id, &file_key);
            }
        }
        exited
    }

    /// Removes every tracked process of a container that no longer exists.
    pub fn forget_container(&mut self, container_id: &str) -> Vec<Proc> {
        let pids: Vec<u32> = self
            .procs
            .values()
            .filter(|p| p.container_id == container_id)
            .map(|p| p.host_pid)
            .collect();
        self.remove_all(&pids)
    }

    /// Samples every tracked process whose role passes `want`. Processes that vanished
    /// or whose PID now belongs to a different process are removed and returned.
    pub fn sample(&mut self, now: f64, want: impl Fn(Role) -> bool) -> Vec<Proc> {
        let pids: Vec<u32> = self
            .procs
            .values()
            .filter(|p| want(p.role))
            .map(|p| p.host_pid)
            .collect();
        let mut gone = Vec::new();
        for pid in pids {
            if !self.sample_one(pid, now) {
                gone.push(pid);
            }
        }
        self.remove_all(&gone)
    }

    fn remove_all(&mut self, pids: &[u32]) -> Vec<Proc> {
        let mut out: Vec<Proc> = pids.iter().filter_map(|pid| self.procs.get(pid).cloned()).collect();
        // Resolve run ids through ancestors while they are still tracked.
        for p in &mut out {
            if p.run_id.is_none() {
                p.run_id = self.inherited_run_id(p.ppid);
            }
        }
        for pid in pids {
            self.procs.remove(pid);
        }
        out
    }

    fn read_new(&self, pid: u32, container_id: &str, now: f64) -> Option<(Proc, Option<u64>)> {
        let stat = self.procfs.stat(pid)?;
        let status = self.procfs.status(pid)?;
        let argv = self.procfs.argv(pid);
        let classified = classify(&argv, &status.name);
        let start_epoch = self.btime as f64 + stat.start_ticks as f64 / CLK_TCK as f64;
        let mut p = Proc {
            host_pid: pid,
            ns_pid: status.ns_pid,
            ppid: stat.ppid,
            ns_ppid: None,
            container_id: container_id.to_string(),
            start_ticks: stat.start_ticks,
            start_epoch,
            last_seen: now,
            comm: status.name.clone(),
            kind: classified.kind,
            role: Role::Service,
            name: classified.name,
            run_id: None,
            file_key: None,
            worker_pid: None,
            step_pid: None,
            hwm_kb: None,
            rss_max_kb: 0,
            cpu_ticks: 0,
            read_bytes: None,
            write_bytes: None,
            samples: VecDeque::new(),
        };
        if let Kind::ComputeLogTail { run_id, .. } = &p.kind {
            p.run_id = Some(run_id.clone());
        }
        apply_reading(&mut p, &status, stat.utime + stat.stime, self.procfs.io(pid), now);
        Some((p, status.rss_kb))
    }

    /// Returns false when the process is gone or its PID was reused.
    fn sample_one(&mut self, pid: u32, now: f64) -> bool {
        let Some(stat) = self.procfs.stat(pid) else {
            return false;
        };
        let Some(status) = self.procfs.status(pid) else {
            return false;
        };
        let io = self.procfs.io(pid);
        let max_samples = self.limits.max_samples;

        let reclassify = match self.procs.get(&pid) {
            None => return true,
            Some(p) if p.start_ticks != stat.start_ticks => return false,
            Some(p) => p.comm != status.name,
        };
        if reclassify {
            // The process exec'd after discovery (fork, then exec): classify again.
            let classified = classify(&self.procfs.argv(pid), &status.name);
            let role = self.resolve_role(&classified.kind, stat.ppid);
            if let Some(p) = self.procs.get_mut(&pid) {
                p.comm = status.name.clone();
                p.kind = classified.kind;
                p.name = classified.name;
                p.role = role;
            }
            let owners = self.owners(pid, role, stat.ppid);
            if let Some(p) = self.procs.get_mut(&pid) {
                (p.worker_pid, p.step_pid) = owners;
            }
        }
        if let Some(p) = self.procs.get_mut(&pid) {
            apply_reading(p, &status, stat.utime + stat.stime, io, now);
            push_sample(p, status.rss_kb, now, max_samples);
        }
        true
    }

    fn resolve_role(&self, kind: &Kind, ppid: u32) -> Role {
        let parent_role = self.procs.get(&ppid).map(|q| (q.kind.clone(), q.role));
        match kind {
            Kind::ComputeLogTail { .. } | Kind::Helper => Role::Helper,
            Kind::Dbt => Role::Dbt,
            Kind::MpFork => match parent_role {
                Some((Kind::DagsterGrpc, _)) => Role::RunWorker,
                Some((_, Role::RunWorker)) => Role::Step,
                _ if self.has_run_ancestor(ppid) => Role::StepChild,
                _ => Role::Service,
            },
            Kind::DagsterGrpc => Role::Service,
            Kind::Other if self.has_run_ancestor(ppid) => Role::StepChild,
            Kind::Other => Role::Service,
        }
    }

    fn ancestors(&self, start: u32) -> impl Iterator<Item = &Proc> {
        let mut next = Some(start);
        let mut depth = 0;
        std::iter::from_fn(move || {
            let pid = next?;
            depth += 1;
            if depth > 64 {
                return None;
            }
            let p = self.procs.get(&pid)?;
            next = (p.ppid != pid).then_some(p.ppid);
            Some(p)
        })
    }

    /// Run worker and step that own a process with this role and parent.
    fn owners(&self, pid: u32, role: Role, ppid: u32) -> (Option<u32>, Option<u32>) {
        let find = |want: Role| {
            if role == want {
                Some(pid)
            } else {
                self.ancestors(ppid).find(|a| a.role == want).map(|a| a.host_pid)
            }
        };
        (find(Role::RunWorker), find(Role::Step))
    }

    fn has_run_ancestor(&self, ppid: u32) -> bool {
        self.ancestors(ppid)
            .any(|a| matches!(a.role, Role::RunWorker | Role::Step))
    }

    fn inherited_run_id(&self, ppid: u32) -> Option<String> {
        self.ancestors(ppid).find_map(|a| a.run_id.clone())
    }

    /// A compute-log `tail` names the run and log key of its parent (a step, or the run
    /// worker itself under the in-process executor). The run id also belongs to the
    /// run worker and to every tracked descendant that does not have one yet.
    fn attach_run_ids(&mut self, owner: u32, run_id: &str, file_key: &str) {
        let Some(owner_role) = self.procs.get(&owner).map(|p| p.role) else {
            return;
        };
        if !matches!(owner_role, Role::Step | Role::RunWorker) {
            return;
        }
        let worker = if owner_role == Role::Step {
            self.procs.get(&owner).map(|p| p.ppid)
        } else {
            None
        };
        if let Some(p) = self.procs.get_mut(&owner) {
            p.run_id.get_or_insert_with(|| run_id.to_string());
            p.file_key.get_or_insert_with(|| file_key.to_string());
        }
        if let Some(w) = worker.and_then(|w| self.procs.get_mut(&w)) {
            if w.role == Role::RunWorker {
                w.run_id.get_or_insert_with(|| run_id.to_string());
            }
        }
        let missing: Vec<u32> = self
            .procs
            .values()
            .filter(|p| p.run_id.is_none() && self.ancestors(p.ppid).any(|a| a.host_pid == owner))
            .map(|p| p.host_pid)
            .collect();
        for pid in missing {
            if let Some(p) = self.procs.get_mut(&pid) {
                p.run_id = Some(run_id.to_string());
            }
        }
    }
}

fn apply_reading(p: &mut Proc, status: &Status, cpu_ticks: u64, io: Option<Io>, now: f64) {
    p.last_seen = now;
    p.ns_pid = status.ns_pid.or(p.ns_pid);
    p.cpu_ticks = cpu_ticks.max(p.cpu_ticks);
    if let Some(h) = status.hwm_kb {
        p.hwm_kb = Some(h.max(p.hwm_kb.unwrap_or(0)));
    }
    if let Some(io) = io {
        p.read_bytes = Some(io.read_bytes);
        p.write_bytes = Some(io.write_bytes);
    }
    if let Some(rss) = status.rss_kb {
        p.rss_max_kb = p.rss_max_kb.max(rss);
    }
}

/// Appends a sample to the ring buffer of a run-related process.
fn push_sample(p: &mut Proc, rss_kb: Option<u64>, now: f64, max_samples: usize) {
    let Some(rss_kb) = rss_kb else { return };
    if !p.role.is_run_related() || max_samples == 0 {
        return;
    }
    if p.samples.len() >= max_samples {
        p.samples.pop_front();
    }
    p.samples.push_back(Sample {
        ts: now,
        rss_kb,
        cpu_ticks: p.cpu_ticks,
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{fake_proc, TempTree};

    const CID: &str = "c7ba6271e6e554ed72810197daa437be348f05af93a2c54385316e497a15c8de";
    const RUN: &str = "0a1b2c3d-0000-4111-8222-123456789abc";
    const FORK: &[&str] = &[
        "/usr/local/bin/python3.10",
        "-c",
        "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=5, pipe_handle=7)",
        "--multiprocessing-fork",
    ];

    fn tail_argv(key: &str) -> Vec<String> {
        ["tail", "-F", "-c", "+0"]
            .iter()
            .map(|s| s.to_string())
            .chain([format!("/app/var/dagster_home/storage/{RUN}/compute_logs/{key}.out")])
            .collect()
    }

    /// grpc(10) -> run worker(20) -> step(30) -> {tail(31), dbt build(40)}; webserver(11).
    fn dagster_tree(t: &TempTree) {
        t.file("stat", "cpu 1 2 3\nbtime 1000\n");
        fake_proc(
            t,
            10,
            1,
            202,
            "python3.10",
            &[
                "/usr/local/bin/python3.10",
                "-m",
                "dagster",
                "api",
                "grpc",
                "--lazy-load-user-code",
            ],
            100,
            300_000,
            500,
            None,
        );
        fake_proc(
            t,
            11,
            1,
            203,
            "python3.10",
            &["/usr/local/bin/python3.10", "-m", "dagster_webserver", "--port", "3001"],
            101,
            400_000,
            900,
            None,
        );
        fake_proc(t, 20, 10, 900, "python3.10", FORK, 5000, 200_000, 50, Some((1, 2)));
        fake_proc(t, 30, 20, 901, "python3.10", FORK, 5100, 250_000, 70, Some((10, 20)));
        let tail = tail_argv("qbiabrcl");
        let tail_refs: Vec<&str> = tail.iter().map(String::as_str).collect();
        fake_proc(t, 31, 30, 902, "tail", &tail_refs, 5110, 1_000, 0, None);
        fake_proc(
            t,
            40,
            30,
            903,
            "dbt",
            &[
                "/usr/local/bin/python3.10",
                "/usr/local/bin/dbt",
                "build",
                "--select",
                "a b c",
            ],
            5200,
            600_000,
            300,
            Some((4096, 8192)),
        );
    }

    fn tracker(t: &TempTree) -> Tracker {
        let procfs = ProcFs::new(t.path());
        let btime = procfs.btime().unwrap();
        Tracker::new(
            procfs,
            btime,
            Limits {
                max_samples: 3,
                max_procs: 100,
            },
        )
    }

    #[test]
    fn builds_dagster_roles_and_run_ids() {
        let t = TempTree::new();
        dagster_tree(&t);
        let mut tr = tracker(&t);
        // Deliberately unordered: roles must not depend on cgroup.procs order.
        let exited = tr.discover(CID, &[40, 31, 30, 20, 11, 10], 6000.0);
        assert!(exited.is_empty());
        assert_eq!(tr.len(), 6);

        let role = |pid| tr.get(pid).unwrap().role;
        assert_eq!(role(10), Role::Service);
        assert_eq!(role(11), Role::Service);
        assert_eq!(role(20), Role::RunWorker);
        assert_eq!(role(30), Role::Step);
        assert_eq!(role(31), Role::Helper);
        assert_eq!(role(40), Role::Dbt);
        assert!(tr.any_dbt());

        let step = tr.get(30).unwrap();
        assert_eq!(step.run_id.as_deref(), Some(RUN));
        assert_eq!(step.file_key.as_deref(), Some("qbiabrcl"));
        assert_eq!(step.ns_pid, Some(901));
        assert_eq!(step.ns_ppid, Some(900));
        assert_eq!(tr.get(20).unwrap().run_id.as_deref(), Some(RUN));
        assert_eq!(tr.get(20).unwrap().file_key, None);
        assert_eq!(tr.get(40).unwrap().run_id.as_deref(), Some(RUN));
        assert_eq!(tr.get(40).unwrap().name, "dbt build");
        assert_eq!(tr.get(11).unwrap().run_id, None);
        let owners = |pid| {
            let p = tr.get(pid).unwrap();
            (p.worker_pid, p.step_pid)
        };
        assert_eq!(owners(20), (Some(20), None));
        assert_eq!(owners(30), (Some(20), Some(30)));
        assert_eq!(owners(40), (Some(20), Some(30)));
        assert_eq!(owners(11), (None, None));
        // Start time comes from btime + start ticks / CLK_TCK.
        assert!((tr.get(30).unwrap().start_epoch - 1051.0).abs() < 1e-9);
    }

    #[test]
    fn samples_and_reports_exit_summary() {
        let t = TempTree::new();
        dagster_tree(&t);
        let mut tr = tracker(&t);
        tr.discover(CID, &[10, 11, 20, 30, 31, 40], 6000.0);

        // dbt grows, then shrinks: the summary keeps the maximum seen.
        fake_proc(
            &t,
            40,
            30,
            903,
            "dbt",
            &["/usr/local/bin/python3.10", "/usr/local/bin/dbt", "build"],
            5200,
            900_000,
            450,
            Some((8192, 9000)),
        );
        assert!(tr.sample(6000.25, |r| r == Role::Dbt).is_empty());
        fake_proc(
            &t,
            40,
            30,
            903,
            "dbt",
            &["/usr/local/bin/python3.10", "/usr/local/bin/dbt", "build"],
            5200,
            700_000,
            500,
            Some((9000, 9500)),
        );
        assert!(tr.sample(6000.5, |r| r == Role::Dbt).is_empty());
        fake_proc(
            &t,
            40,
            30,
            903,
            "dbt",
            &["/usr/local/bin/python3.10", "/usr/local/bin/dbt", "build"],
            5200,
            650_000,
            520,
            Some((9100, 9600)),
        );
        assert!(tr.sample(6000.75, |r| r == Role::Dbt).is_empty());

        // Ring buffer keeps the newest `max_samples` (3) samples.
        let samples: Vec<f64> = tr.get(40).unwrap().samples.iter().map(|s| s.ts).collect();
        assert_eq!(samples, vec![6000.25, 6000.5, 6000.75]);
        // Services and helpers keep no samples.
        assert!(tr.get(11).unwrap().samples.is_empty());
        assert!(tr.get(31).unwrap().samples.is_empty());

        // dbt leaves the cgroup.
        t.remove("40");
        let exited = tr.discover(CID, &[10, 11, 20, 30, 31], 6001.0);
        assert_eq!(exited.len(), 1);
        let dbt = &exited[0];
        assert_eq!(dbt.host_pid, 40);
        assert_eq!(dbt.rss_max_kb, 900_000);
        assert_eq!(dbt.hwm_kb, Some(900_100));
        assert!((dbt.cpu_seconds() - 5.2).abs() < 1e-9);
        assert_eq!((dbt.read_bytes, dbt.write_bytes), (Some(9100), Some(9600)));
        assert_eq!(dbt.last_seen, 6000.75);
        assert_eq!(dbt.run_id.as_deref(), Some(RUN));
        assert!(!tr.any_dbt());
    }

    #[test]
    fn pid_reuse_and_vanished_process() {
        let t = TempTree::new();
        dagster_tree(&t);
        let mut tr = tracker(&t);
        tr.discover(CID, &[10, 20, 30, 31, 40], 6000.0);

        // PID 30 now belongs to a different process (other start time).
        fake_proc(&t, 30, 1, 999, "sh", &["sh", "-c", "x"], 7000, 10, 1, None);
        // PID 40 vanished between discovery passes.
        t.remove("40");
        let gone = tr.sample(6001.0, Role::is_run_related);
        let mut pids: Vec<u32> = gone.iter().map(|p| p.host_pid).collect();
        pids.sort();
        assert_eq!(pids, vec![30, 40]);
        assert_eq!(gone.iter().find(|p| p.host_pid == 30).unwrap().role, Role::Step);

        // The next discovery sees the new owner of PID 30 as a fresh process.
        tr.discover(CID, &[10, 20, 30, 31], 6002.0);
        assert_eq!(tr.get(30).unwrap().role, Role::Service);
        assert_eq!(tr.get(30).unwrap().name, "sh");
    }

    #[test]
    fn exec_after_discovery_is_reclassified() {
        let t = TempTree::new();
        dagster_tree(&t);
        // PID 41 seen between fork and exec: still the step's command line.
        fake_proc(&t, 41, 30, 904, "python3.10", FORK, 5300, 100, 1, None);
        let mut tr = tracker(&t);
        tr.discover(CID, &[10, 20, 30, 31, 41], 6000.0);
        assert_eq!(tr.get(41).unwrap().role, Role::StepChild);
        fake_proc(
            &t,
            41,
            30,
            904,
            "dbt",
            &["/usr/local/bin/python3.10", "/usr/local/bin/dbt", "parse"],
            5300,
            100,
            1,
            None,
        );
        tr.sample(6001.0, Role::is_run_related);
        let p = tr.get(41).unwrap();
        assert_eq!((p.role, p.name.as_str()), (Role::Dbt, "dbt parse"));
    }

    #[test]
    fn in_process_run_worker_gets_file_key() {
        let t = TempTree::new();
        dagster_tree(&t);
        let tail = tail_argv("inhqwukv");
        let tail_refs: Vec<&str> = tail.iter().map(String::as_str).collect();
        fake_proc(&t, 21, 20, 905, "tail", &tail_refs, 5050, 1_000, 0, None);
        let mut tr = tracker(&t);
        tr.discover(CID, &[10, 20, 21], 6000.0);
        let w = tr.get(20).unwrap();
        assert_eq!(w.role, Role::RunWorker);
        assert_eq!(w.run_id.as_deref(), Some(RUN));
        assert_eq!(w.file_key.as_deref(), Some("inhqwukv"));
    }

    #[test]
    fn other_containers_and_limits() {
        let t = TempTree::new();
        dagster_tree(&t);
        let procfs = ProcFs::new(t.path());
        let mut tr = Tracker::new(
            procfs,
            1000,
            Limits {
                max_samples: 3,
                max_procs: 2,
            },
        );
        tr.discover(CID, &[10, 11, 20], 6000.0);
        assert_eq!(tr.len(), 2);
        assert_eq!(tr.dropped_new(), 1);
        // Discovery of another container never ends this container's processes.
        assert!(tr.discover("other", &[], 6001.0).is_empty());
        assert_eq!(tr.forget_container(CID).len(), 2);
        assert!(tr.is_empty());
        // A PID listed but already gone from /proc is skipped.
        assert!(tr.discover(CID, &[12345], 6002.0).is_empty());
        assert!(tr.is_empty());
    }
}
