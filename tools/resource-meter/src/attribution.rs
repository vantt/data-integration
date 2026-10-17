//! Turns exited processes into rows per Dagster step and per dbt model.
//!
//! Processes of one run are buffered under their run worker. When the run worker exits,
//! the run is attributed through Dagster GraphQL (read-only): each step process is matched
//! to its `LogsCapturedEvent` by container PID, or by compute-log key. dbt models are
//! attributed as soon as a `dbt build` process exits, from its `run_results.json`.

use std::collections::{HashMap, VecDeque};
use std::path::PathBuf;

use crate::dagster::{self, Capture, Executor, FetchError, RunInfo};
use crate::dbt;
use crate::http::Endpoint;
use crate::tracker::{Proc, Role, Sample};
use crate::tsv::Row;

pub const STEPS_HEADER: &str =
    "run_id\tjob\tstep_key\texecutor\tts_start\tts_end\tns_pid\trss_peak_tree_kb\tcpu_s\tread_bytes\twrite_bytes";
pub const MODELS_HEADER: &str =
    "run_id\tunique_id\tstatus\tts_start\tts_end\texec_s\trss_peak_kb\trss_delta_kb\tcpu_s\trows_affected";

/// Step key of the row for a whole in-process run.
pub const JOB_LEVEL_KEY: &str = "*";
/// Step key of the row for a multiprocess run worker's own process (its steps excluded).
pub const RUN_WORKER_KEY: &str = "(run_worker)";

/// Wait after the run worker exits before asking Dagster (its last events are written).
const SETTLE_SECONDS: f64 = 10.0;
const RETRY_SECONDS: f64 = 300.0;
/// Give up on GraphQL after this long; rows are then written without job and step key.
const GIVE_UP_SECONDS: f64 = 12.0 * 3600.0;
/// A run whose worker was never seen to exit is attributed after this much quiet.
const STALE_RUN_SECONDS: f64 = 6.0 * 3600.0;
const MAX_BUFFERED_RUNS: usize = 1000;
const DBT_RETRY_SECONDS: f64 = 10.0;
const DBT_ATTEMPTS: u32 = 6;

#[derive(Debug, Clone)]
pub struct Settings {
    /// `None` disables GraphQL: steps are written without job or step key.
    pub graphql: Option<Endpoint>,
    /// `None` disables model rows.
    pub dbt_target_dir: Option<PathBuf>,
}

/// A finished row: `ts` decides the day file.
#[derive(Debug, Clone, PartialEq)]
pub struct Line {
    pub ts: f64,
    pub text: String,
}

#[derive(Debug, Default)]
pub struct Output {
    pub steps: Vec<Line>,
    pub models: Vec<Line>,
    pub errors: Vec<String>,
}

struct RunBuffer {
    procs: Vec<Proc>,
    last_activity: f64,
    queued: bool,
}

struct PendingRun {
    worker_pid: u32,
    due: f64,
    first_try: f64,
}

struct PendingDbt {
    run_id: String,
    started: f64,
    ended: f64,
    samples: Vec<Sample>,
    due: f64,
    attempts: u32,
}

pub struct Attributor {
    settings: Settings,
    runs: HashMap<u32, RunBuffer>,
    pending_runs: VecDeque<PendingRun>,
    pending_dbt: Vec<PendingDbt>,
}

impl Attributor {
    pub fn new(settings: Settings) -> Self {
        Self {
            settings,
            runs: HashMap::new(),
            pending_runs: VecDeque::new(),
            pending_dbt: Vec::new(),
        }
    }

    pub fn buffered_runs(&self) -> usize {
        self.runs.len()
    }

    /// Takes an exited process. Only processes of a Dagster run are kept.
    pub fn on_exit(&mut self, p: Proc, now: f64) {
        if !p.role.is_run_related() {
            return;
        }
        if p.role == Role::Dbt && p.name == "dbt build" && self.settings.dbt_target_dir.is_some() {
            if let Some(run_id) = &p.run_id {
                self.pending_dbt.push(PendingDbt {
                    run_id: run_id.clone(),
                    started: p.start_epoch,
                    ended: p.last_seen,
                    samples: p.samples.iter().copied().collect(),
                    due: now + 1.0,
                    attempts: 0,
                });
            }
        }
        let Some(worker) = p.worker_pid else { return };
        let is_worker = p.role == Role::RunWorker;
        let buf = self.runs.entry(worker).or_insert_with(|| RunBuffer {
            procs: Vec::new(),
            last_activity: now,
            queued: false,
        });
        buf.procs.push(p);
        buf.last_activity = now;
        if is_worker && !buf.queued {
            buf.queued = true;
            self.pending_runs.push_back(PendingRun {
                worker_pid: worker,
                due: now + SETTLE_SECONDS,
                first_try: now,
            });
        }
    }

    /// Does the work that is due. At most one run is fetched from GraphQL per call, so
    /// one call blocks the sampling loop for at most one short HTTP exchange.
    pub fn poll(&mut self, now: f64) -> Output {
        let mut out = Output::default();
        self.poll_dbt(now, &mut out);
        self.queue_stale_runs(now, &mut out);
        if let Some(i) = self.pending_runs.iter().position(|p| p.due <= now) {
            let pending = self.pending_runs.remove(i).expect("index from position");
            self.attribute_run(pending, now, &mut out);
        }
        out
    }

    /// At shutdown: attributes every queued run and dbt invocation once, without waiting.
    pub fn drain(&mut self, now: f64) -> Output {
        let mut out = Output::default();
        for d in &mut self.pending_dbt {
            d.due = now;
            d.attempts = DBT_ATTEMPTS - 1;
        }
        self.poll_dbt(now, &mut out);
        while let Some(mut pending) = self.pending_runs.pop_front() {
            pending.first_try = now - GIVE_UP_SECONDS;
            self.attribute_run(pending, now, &mut out);
        }
        out
    }

    fn poll_dbt(&mut self, now: f64, out: &mut Output) {
        let Some(dir) = self.settings.dbt_target_dir.clone() else {
            return;
        };
        let mut keep = Vec::new();
        for mut d in std::mem::take(&mut self.pending_dbt) {
            if d.due > now {
                keep.push(d);
                continue;
            }
            match dbt::find_run_results(&dir, &d.run_id, d.started, d.ended) {
                Ok(results) => out.models.extend(model_lines(&d.run_id, &results, &d.samples)),
                Err(e) => {
                    d.attempts += 1;
                    if d.attempts >= DBT_ATTEMPTS {
                        out.errors.push(format!("dbt models of run {}: {e}", d.run_id));
                    } else {
                        d.due = now + DBT_RETRY_SECONDS;
                        keep.push(d);
                    }
                }
            }
        }
        self.pending_dbt = keep;
    }

    fn queue_stale_runs(&mut self, now: f64, out: &mut Output) {
        let mut stale: Vec<(f64, u32)> = self
            .runs
            .iter()
            .filter(|(_, b)| !b.queued && now - b.last_activity >= STALE_RUN_SECONDS)
            .map(|(w, b)| (b.last_activity, *w))
            .collect();
        // Bound memory: past the limit, the oldest runs are attributed right away.
        if self.runs.len() > MAX_BUFFERED_RUNS {
            let mut by_age: Vec<(f64, u32)> = self
                .runs
                .iter()
                .filter(|(_, b)| !b.queued)
                .map(|(w, b)| (b.last_activity, *w))
                .collect();
            by_age.sort_by(|a, b| a.0.total_cmp(&b.0));
            stale.extend(by_age.into_iter().take(self.runs.len() - MAX_BUFFERED_RUNS));
            out.errors.push(format!(
                "more than {MAX_BUFFERED_RUNS} runs buffered; attributing the oldest early"
            ));
        }
        for (_, worker) in stale {
            if let Some(b) = self.runs.get_mut(&worker) {
                if !b.queued {
                    b.queued = true;
                    self.pending_runs.push_back(PendingRun {
                        worker_pid: worker,
                        due: now,
                        first_try: now,
                    });
                }
            }
        }
    }

    fn attribute_run(&mut self, pending: PendingRun, now: f64, out: &mut Output) {
        let Some(buf) = self.runs.get(&pending.worker_pid) else {
            return;
        };
        let mut run_id = buf.procs.iter().find_map(|p| p.run_id.clone());
        let worker = buf.procs.iter().find(|p| p.role == Role::RunWorker);
        let worker_key = worker.and_then(|w| w.ns_pid.map(|ns| (ns, w.start_epoch, w.last_seen)));
        let label = run_id
            .clone()
            .unwrap_or_else(|| format!("of worker pid {}", pending.worker_pid));

        let fetched = match (&self.settings.graphql, &run_id, worker_key) {
            (Some(endpoint), Some(id), _) => Some(dagster::fetch_run(endpoint, id).map(Some)),
            (Some(endpoint), None, Some((ns, started, ended))) => {
                Some(dagster::find_run_by_worker(endpoint, ns, started, ended).map(|found| {
                    found.map(|(id, info)| {
                        run_id = Some(id);
                        info
                    })
                }))
            }
            _ => None,
        };
        let info = match fetched {
            None => None,
            Some(Ok(Some(info))) => Some(info),
            Some(Ok(None)) => {
                out.errors.push(format!(
                    "run {label} not identified in Dagster; steps written without keys"
                ));
                None
            }
            Some(Err(FetchError::NotFound)) => {
                out.errors
                    .push(format!("run {label} not found in Dagster; steps written without keys"));
                None
            }
            Some(Err(FetchError::Retry(e))) => {
                if now - pending.first_try < GIVE_UP_SECONDS {
                    self.pending_runs.push_back(PendingRun {
                        due: now + RETRY_SECONDS,
                        ..pending
                    });
                    out.errors
                        .push(format!("Dagster GraphQL for run {label}: {e}; retrying"));
                    return;
                }
                out.errors
                    .push(format!("Dagster GraphQL for run {label}: {e}; giving up"));
                None
            }
        };
        if let Some(buf) = self.runs.remove(&pending.worker_pid) {
            out.steps
                .extend(step_lines(run_id.as_deref(), info.as_ref(), &buf.procs));
        }
    }
}

/// Peak of the summed RSS of several processes, aligned on whole seconds (each process
/// contributes its highest sample within a second).
pub fn tree_rss_peak(procs: &[&Proc]) -> Option<u64> {
    let mut per_second: HashMap<i64, u64> = HashMap::new();
    for p in procs {
        let mut own: HashMap<i64, u64> = HashMap::new();
        for s in &p.samples {
            let slot = own.entry(s.ts.floor() as i64).or_insert(0);
            *slot = (*slot).max(s.rss_kb);
        }
        for (sec, rss) in own {
            *per_second.entry(sec).or_insert(0) += rss;
        }
    }
    per_second.into_values().max()
}

fn sum_opt(values: impl Iterator<Item = Option<u64>>) -> Option<u64> {
    values.fold(None, |acc, v| match (acc, v) {
        (None, None) => None,
        (a, b) => Some(a.unwrap_or(0).saturating_add(b.unwrap_or(0))),
    })
}

fn step_line(
    run_id: Option<&str>,
    job: Option<&str>,
    step_key: &str,
    executor: Option<Executor>,
    owner: &Proc,
    tree: &[&Proc],
) -> Line {
    let text = Row::new()
        .opt_text(run_id)
        .opt_text(job)
        .text(step_key)
        .opt_text(executor.map(Executor::as_str))
        .dec(owner.start_epoch, 3)
        .dec(owner.last_seen, 3)
        .int(owner.ns_pid.map(u64::from))
        .int(tree_rss_peak(tree))
        .dec(tree.iter().map(|p| p.cpu_seconds()).sum::<f64>(), 2)
        .int(sum_opt(tree.iter().map(|p| p.read_bytes)))
        .int(sum_opt(tree.iter().map(|p| p.write_bytes)))
        .finish();
    Line {
        ts: owner.last_seen,
        text,
    }
}

/// Rows for one run: one per step process (with its descendants), and one for the run
/// worker's own process tree (`*` under the in-process executor, where it runs every step).
pub fn step_lines(run_id: Option<&str>, info: Option<&RunInfo>, procs: &[Proc]) -> Vec<Line> {
    let job = info.and_then(|i| i.job.as_deref());
    let steps: Vec<&Proc> = procs.iter().filter(|p| p.role == Role::Step).collect();
    let executor = info.and_then(|i| i.executor).or(if steps.is_empty() {
        None
    } else {
        Some(Executor::Multiprocess)
    });
    let captures: &[Capture] = info.map(|i| i.captures.as_slice()).unwrap_or(&[]);
    let find_capture = |p: &Proc| {
        p.ns_pid
            .and_then(|pid| captures.iter().find(|c| c.pid == Some(pid)))
            .or_else(|| {
                p.file_key
                    .as_ref()
                    .and_then(|k| captures.iter().find(|c| &c.file_key == k))
            })
    };

    let mut lines = Vec::new();
    for step in &steps {
        let key = find_capture(step).map(|c| c.step_keys.join(",")).unwrap_or_default();
        let tree: Vec<&Proc> = procs.iter().filter(|p| p.step_pid == Some(step.host_pid)).collect();
        lines.push(step_line(run_id, job, &key, executor, step, &tree));
    }
    if let Some(worker) = procs.iter().find(|p| p.role == Role::RunWorker) {
        let key = if executor == Some(Executor::InProcess) {
            JOB_LEVEL_KEY
        } else {
            RUN_WORKER_KEY
        };
        let tree: Vec<&Proc> = procs.iter().filter(|p| p.step_pid.is_none()).collect();
        lines.push(step_line(run_id, job, key, executor, worker, &tree));
    }
    lines
}

/// One row per model-like node of a `dbt build` whose `execute` took at least
/// [`dbt::MIN_WRITTEN_SECONDS`].
pub fn model_lines(run_id: &str, results: &dbt::RunResults, samples: &[Sample]) -> Vec<Line> {
    results
        .nodes
        .iter()
        .filter(|n| n.execute.is_some_and(|(s, e)| e - s >= dbt::MIN_WRITTEN_SECONDS))
        .map(|n| {
            let usage = n.execute.and_then(|(s, e)| dbt::model_usage(samples, s, e));
            let text = Row::new()
                .text(run_id)
                .text(&n.unique_id)
                .text(&n.status)
                .dec(n.execute.map(|w| w.0), 3)
                .dec(n.execute.map(|w| w.1), 3)
                .dec(n.execution_time, 3)
                .int(usage.as_ref().map(|u| u.rss_peak_kb))
                .signed(usage.as_ref().map(|u| u.rss_delta_kb))
                .dec(usage.as_ref().map(|u| u.cpu_s), 2)
                .int(n.rows_affected)
                .finish();
            let ts = n.execute.map(|w| w.1).or(results.generated_at).unwrap_or(0.0);
            Line { ts, text }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::procfs::Kind;
    use crate::test_support::TempTree;
    use std::collections::VecDeque;

    const RUN: &str = "0a1b2c3d-0000-4111-8222-123456789abc";
    const T0: f64 = 1_792_195_200.0;

    fn proc(pid: u32, ns: u32, role: Role, worker: u32, step: Option<u32>, start: f64, end: f64) -> Proc {
        Proc {
            host_pid: pid,
            ns_pid: Some(ns),
            ppid: 1,
            ns_ppid: None,
            container_id: "c".into(),
            start_ticks: 0,
            start_epoch: T0 + start,
            last_seen: T0 + end,
            comm: "python3.10".into(),
            kind: Kind::Other,
            role,
            name: "mp-spawn".into(),
            run_id: Some(RUN.into()),
            file_key: None,
            worker_pid: Some(worker),
            step_pid: step,
            hwm_kb: None,
            rss_max_kb: 0,
            cpu_ticks: 100,
            read_bytes: None,
            write_bytes: None,
            samples: VecDeque::new(),
        }
    }

    fn with_samples(mut p: Proc, points: &[(f64, u64)]) -> Proc {
        p.samples = points
            .iter()
            .map(|&(ts, rss)| Sample {
                ts: T0 + ts,
                rss_kb: rss,
                cpu_ticks: 0,
            })
            .collect();
        p
    }

    fn info(executor: Executor) -> RunInfo {
        RunInfo {
            job: Some("pipeline_sapo_v2_realtime_job".into()),
            status: Some("SUCCESS".into()),
            executor: Some(executor),
            worker_pid: Some(900),
            captures: vec![
                Capture {
                    file_key: "qbiabrcl".into(),
                    step_keys: vec!["sapo_dbt_assets".into()],
                    pid: Some(901),
                },
                Capture {
                    file_key: "pnageyhi".into(),
                    step_keys: vec!["ingest".into()],
                    pid: Some(999),
                },
            ],
        }
    }

    fn cells(line: &Line) -> Vec<String> {
        line.text.trim_end_matches('\n').split('\t').map(String::from).collect()
    }

    #[test]
    fn tree_peak_sums_per_second() {
        let a = with_samples(
            proc(30, 901, Role::Step, 20, Some(30), 0.0, 3.0),
            &[(0.1, 100), (1.2, 300), (2.5, 50)],
        );
        let b = with_samples(
            proc(40, 903, Role::Dbt, 20, Some(30), 1.0, 3.0),
            &[(1.0, 500), (1.25, 700), (2.0, 100)],
        );
        assert_eq!(tree_rss_peak(&[&a, &b]), Some(1000));
        assert_eq!(tree_rss_peak(&[]), None);
    }

    #[test]
    fn steps_matched_by_pid_or_file_key() {
        let worker = proc(20, 900, Role::RunWorker, 20, None, 0.0, 40.0);
        let dbt_step = with_samples(proc(30, 901, Role::Step, 20, Some(30), 1.0, 35.0), &[(2.0, 300)]);
        let mut dbt = with_samples(proc(40, 903, Role::Dbt, 20, Some(30), 5.0, 30.0), &[(2.2, 600)]);
        dbt.read_bytes = Some(10);
        // Step whose PID is unknown to Dagster, matched by its log key instead.
        let mut ingest = proc(31, 950, Role::Step, 20, Some(31), 1.0, 3.0);
        ingest.file_key = Some("pnageyhi".into());
        // Step known to neither.
        let unknown = proc(32, 951, Role::Step, 20, Some(32), 1.0, 2.0);
        let procs = vec![dbt, dbt_step, ingest, unknown, worker];

        let lines = step_lines(Some(RUN), Some(&info(Executor::Multiprocess)), &procs);
        assert_eq!(lines.len(), 4);
        let rows: Vec<Vec<String>> = lines.iter().map(cells).collect();
        assert_eq!(rows[0].len(), STEPS_HEADER.split('\t').count());
        let dbt_row = rows.iter().find(|r| r[2] == "sapo_dbt_assets").unwrap();
        assert_eq!(
            &dbt_row[..4],
            &[RUN, "pipeline_sapo_v2_realtime_job", "sapo_dbt_assets", "multiprocess"]
        );
        assert_eq!(dbt_row[6], "901");
        assert_eq!(dbt_row[7], "900"); // 300 + 600 in second 2
        assert_eq!(dbt_row[8], "2.00");
        assert_eq!((dbt_row[9].as_str(), dbt_row[10].as_str()), ("10", ""));
        assert!(rows.iter().any(|r| r[2] == "ingest" && r[6] == "950"));
        assert!(rows.iter().any(|r| r[2].is_empty() && r[6] == "951"));
        let w = rows.iter().find(|r| r[2] == RUN_WORKER_KEY).unwrap();
        assert_eq!(w[6], "900");
    }

    #[test]
    fn in_process_run_is_one_job_row() {
        let worker = proc(20, 900, Role::RunWorker, 20, None, 0.0, 12.0);
        let child = proc(25, 905, Role::StepChild, 20, None, 1.0, 2.0);
        let lines = step_lines(Some(RUN), Some(&info(Executor::InProcess)), &[child, worker]);
        assert_eq!(lines.len(), 1);
        let r = cells(&lines[0]);
        assert_eq!(&r[2..4], &[JOB_LEVEL_KEY, "in_process"]);
        assert_eq!(r[8], "2.00"); // worker + its child
    }

    #[test]
    fn without_graphql_rows_have_no_keys() {
        let worker = proc(20, 900, Role::RunWorker, 20, None, 0.0, 12.0);
        let step = proc(30, 901, Role::Step, 20, Some(30), 1.0, 2.0);
        let rows: Vec<Vec<String>> = step_lines(Some(RUN), None, &[step, worker]).iter().map(cells).collect();
        assert_eq!(rows.len(), 2);
        assert_eq!(&rows[0][..4], &[RUN, "", "", "multiprocess"]);
    }

    #[test]
    fn attributor_queues_runs_and_gives_up_cleanly() {
        let mut a = Attributor::new(Settings {
            graphql: None,
            dbt_target_dir: None,
        });
        let now = T0 + 100.0;
        a.on_exit(proc(30, 901, Role::Step, 20, Some(30), 1.0, 2.0), now);
        let mut service = proc(11, 203, Role::Service, 20, None, 0.0, 1.0);
        service.worker_pid = None;
        a.on_exit(service, now);
        assert_eq!(a.buffered_runs(), 1);
        assert!(a.poll(now).steps.is_empty());
        a.on_exit(proc(20, 900, Role::RunWorker, 20, None, 0.0, 3.0), now);
        // Not before the settle delay.
        assert!(a.poll(now + 1.0).steps.is_empty());
        let out = a.poll(now + SETTLE_SECONDS);
        assert_eq!(out.steps.len(), 2);
        assert_eq!(a.buffered_runs(), 0);
    }

    #[test]
    fn graphql_failure_is_retried_then_drained() {
        // A closed loopback port: every request fails quickly.
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        drop(listener);
        let mut a = Attributor::new(Settings {
            graphql: Some(Endpoint::parse_loopback(&addr.to_string()).unwrap()),
            dbt_target_dir: None,
        });
        let now = T0;
        a.on_exit(proc(20, 900, Role::RunWorker, 20, None, 0.0, 3.0), now);
        let out = a.poll(now + SETTLE_SECONDS);
        assert!(out.steps.is_empty());
        assert!(out.errors[0].contains("retrying"));
        assert_eq!(a.buffered_runs(), 1);
        // Not retried before the retry delay.
        assert!(a.poll(now + SETTLE_SECONDS + 1.0).errors.is_empty());
        let out = a.drain(now + SETTLE_SECONDS + 2.0);
        assert_eq!(out.steps.len(), 1);
        assert!(out.errors[0].contains("giving up"));
    }

    #[test]
    fn stale_runs_are_attributed() {
        let mut a = Attributor::new(Settings {
            graphql: None,
            dbt_target_dir: None,
        });
        a.on_exit(proc(30, 901, Role::Step, 20, Some(30), 1.0, 2.0), T0);
        assert!(a.poll(T0 + 60.0).steps.is_empty());
        assert_eq!(a.poll(T0 + STALE_RUN_SECONDS).steps.len(), 1);
    }

    #[test]
    fn dbt_build_exit_produces_model_rows() {
        let t = TempTree::new();
        t.file(
            "sapo_dbt_assets-0a1b2c3-bbbbbbb/run_results.json",
            r#"{"metadata":{"generated_at":"2026-10-17T00:00:31Z"},"results":[
                {"status":"success","timing":[{"name":"execute","started_at":"2026-10-17T00:00:10Z","completed_at":"2026-10-17T00:00:13Z"}],
                 "execution_time":3.2,"adapter_response":{"rows_affected":7},"unique_id":"model.p.m1","compiled_code":"select 1"},
                {"status":"success","timing":[{"name":"execute","started_at":"2026-10-17T00:00:14Z","completed_at":"2026-10-17T00:00:14.300Z"}],
                 "execution_time":0.3,"adapter_response":{},"unique_id":"model.p.m2"},
                {"status":"success","timing":[{"name":"execute","started_at":"2026-10-17T00:00:15Z","completed_at":"2026-10-17T00:00:15.050Z"}],
                 "execution_time":0.06,"adapter_response":{},"unique_id":"model.p.too_short"},
                {"status":"skipped","timing":[],"execution_time":0,"adapter_response":{},"unique_id":"model.p.skipped"}],
              "args":{"invocation_command":"dbt build --select x"}}"#,
        );
        let mut a = Attributor::new(Settings {
            graphql: None,
            dbt_target_dir: Some(t.path().to_path_buf()),
        });
        let mut dbt = proc(40, 903, Role::Dbt, 20, Some(30), 5.0, 30.0);
        dbt.name = "dbt build".into();
        dbt.samples = [
            (9.75, 100u64, 0u64),
            (11.0, 400, 50),
            (12.0, 350, 150),
            (14.1, 300, 160),
        ]
        .iter()
        .map(|&(ts, rss, cpu)| Sample {
            ts: T0 + ts,
            rss_kb: rss,
            cpu_ticks: cpu,
        })
        .collect();
        a.on_exit(dbt, T0 + 31.0);
        let out = a.poll(T0 + 32.0);
        assert_eq!(out.models.len(), 2, "{:?}", out.errors);
        let m1 = cells(&out.models[0]);
        assert_eq!(m1.len(), MODELS_HEADER.split('\t').count());
        assert_eq!(&m1[..3], &[RUN, "model.p.m1", "success"]);
        assert_eq!(&m1[5..], &["3.200", "400", "300", "1.50", "7"]);
        let m2 = cells(&out.models[1]);
        assert_eq!(&m2[6..9], &["", "", ""]);
        assert!(out
            .models
            .iter()
            .all(|l| !l.text.contains("--select") && !l.text.contains("select 1")));
    }

    #[test]
    fn missing_run_results_is_retried_then_reported() {
        let t = TempTree::new();
        let mut a = Attributor::new(Settings {
            graphql: None,
            dbt_target_dir: Some(t.path().to_path_buf()),
        });
        let mut dbt = proc(40, 903, Role::Dbt, 20, Some(30), 5.0, 30.0);
        dbt.name = "dbt build".into();
        a.on_exit(dbt, T0);
        let mut now = T0;
        let mut errors = Vec::new();
        for _ in 0..DBT_ATTEMPTS {
            now += DBT_RETRY_SECONDS;
            errors.extend(a.poll(now).errors);
        }
        assert_eq!(errors.len(), 1);
        assert!(errors[0].contains("no run_results.json"));
    }
}
