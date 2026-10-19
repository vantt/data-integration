//! `report`, `compare` and `status`: plain-text tables read straight from the TSV files.

use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::path::{Path, PathBuf};

use crate::cgroup;
use crate::procfs::{ProcFs, CLK_TCK};
use crate::clock::{day_stamp, local_day, parse_day_stamp};
use crate::reader::{load, num, scan, Table};

/// Changes smaller than these are never flagged by `compare`, whatever the percentage
/// (a 0.2 s model going to 0.3 s is +50% but means nothing).
const MIN_FLAG_SECONDS: f64 = 0.5;
const MIN_FLAG_RSS_KB: f64 = 8.0 * 1024.0;
/// The meter writes a `self` row every 60 s; older than this means it is not running.
const SELF_ROW_STALE_SECONDS: f64 = 150.0;
pub const UNIT_NAME: &str = "resource-meter.service";

/// `YYYY-MM-DD` to a day number.
pub fn parse_date(s: &str) -> Result<i64, String> {
    let ok = s.len() == 10 && s.as_bytes()[4] == b'-' && s.as_bytes()[7] == b'-';
    ok.then(|| parse_day_stamp(&s.replace('-', "")))
        .flatten()
        .ok_or_else(|| format!("{s}: expected a date YYYY-MM-DD"))
}

fn date_text(day: i64) -> String {
    let s = day_stamp(day);
    format!("{}-{}-{}", &s[0..4], &s[4..6], &s[6..8])
}

fn kb_text(kb: f64) -> String {
    if kb >= 1024.0 * 1024.0 {
        format!("{:.2} GB", kb / 1024.0 / 1024.0)
    } else {
        format!("{:.0} MB", kb / 1024.0)
    }
}

fn bytes_text(b: f64) -> String {
    kb_text(b / 1024.0)
}

fn opt<T>(v: Option<T>, f: impl Fn(T) -> String) -> String {
    v.map(f).unwrap_or_else(|| "-".into())
}

/// Left-aligned first `left` columns, right-aligned numbers after.
fn render(headers: &[&str], rows: &[Vec<String>], left: usize) -> String {
    let mut widths: Vec<usize> = headers.iter().map(|h| h.chars().count()).collect();
    for r in rows {
        for (i, c) in r.iter().enumerate() {
            widths[i] = widths[i].max(c.chars().count());
        }
    }
    let line = |cells: Vec<&str>| {
        let parts: Vec<String> = cells
            .iter()
            .enumerate()
            .map(|(i, c)| {
                if i < left {
                    format!("{c:<w$}", w = widths[i])
                } else {
                    format!("{c:>w$}", w = widths[i])
                }
            })
            .collect();
        parts.join("  ").trim_end().to_string() + "\n"
    };
    let mut out = line(headers.to_vec());
    for r in rows {
        out += &line(r.iter().map(String::as_str).collect());
    }
    out
}

fn median(mut v: Vec<f64>) -> Option<f64> {
    if v.is_empty() {
        return None;
    }
    v.sort_by(f64::total_cmp);
    let n = v.len();
    Some(if n % 2 == 1 {
        v[n / 2]
    } else {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    })
}

fn max_of(v: &[f64]) -> Option<f64> {
    v.iter().copied().reduce(f64::max)
}

#[derive(Debug, Clone)]
pub struct ReportOptions {
    pub dir: PathBuf,
    pub day: i64,
    pub container: Option<String>,
    pub job: Option<String>,
    pub top: usize,
}

/// One row per step execution, with the job resolved.
struct StepRec {
    job: String,
    key: String,
    run_id: String,
    duration: f64,
    rss_kb: Option<f64>,
    cpu_s: Option<f64>,
    write_bytes: Option<f64>,
}

fn step_records(t: &Table) -> Result<Vec<StepRec>, String> {
    let (run, job, key) = (t.col("run_id")?, t.col("job")?, t.col("step_key")?);
    let (s, e, rss, cpu, w) = (
        t.col("ts_start")?,
        t.col("ts_end")?,
        t.col("rss_peak_tree_kb")?,
        t.col("cpu_s")?,
        t.col("write_bytes")?,
    );
    Ok(t.rows
        .iter()
        .map(|r| StepRec {
            job: if r[job].is_empty() {
                "(unknown job)".into()
            } else {
                r[job].clone()
            },
            key: if r[key].is_empty() {
                "(unknown step)".into()
            } else {
                r[key].clone()
            },
            run_id: r[run].clone(),
            duration: num(&r[e]).unwrap_or(0.0) - num(&r[s]).unwrap_or(0.0),
            rss_kb: num(&r[rss]),
            cpu_s: num(&r[cpu]),
            write_bytes: num(&r[w]),
        })
        .collect())
}

struct ModelRec {
    unique_id: String,
    run_id: String,
    exec_s: f64,
    rss_kb: Option<f64>,
    cpu_s: Option<f64>,
}

fn model_records(t: &Table) -> Result<Vec<ModelRec>, String> {
    let (run, id, s, e, rss, cpu) = (
        t.col("run_id")?,
        t.col("unique_id")?,
        t.col("ts_start")?,
        t.col("ts_end")?,
        t.col("rss_peak_kb")?,
        t.col("cpu_s")?,
    );
    Ok(t.rows
        .iter()
        .map(|r| ModelRec {
            unique_id: r[id].clone(),
            run_id: r[run].clone(),
            exec_s: num(&r[e]).unwrap_or(0.0) - num(&r[s]).unwrap_or(0.0),
            rss_kb: num(&r[rss]),
            cpu_s: num(&r[cpu]),
        })
        .collect())
}

fn job_of_runs(steps: &[StepRec]) -> HashMap<String, String> {
    steps
        .iter()
        .filter(|s| !s.run_id.is_empty())
        .map(|s| (s.run_id.clone(), s.job.clone()))
        .collect()
}

/// A cumulative counter summed as increases (a decrease is a reset and is skipped).
#[derive(Default)]
struct Counter {
    last: Option<f64>,
    total: f64,
}

impl Counter {
    fn add(&mut self, v: Option<f64>) {
        if let Some(v) = v {
            if let Some(last) = self.last {
                self.total += (v - last).max(0.0);
            }
            self.last = Some(v);
        }
    }
}

const COUNTERS: [&str; 6] = [
    "ev_max",
    "ev_oom_kill",
    "cpu_usage_usec",
    "cpu_throttled_usec",
    "io_rbytes",
    "io_wbytes",
];

#[derive(Default)]
struct ContainerAgg {
    anon: Vec<f64>,
    current_max: Option<f64>,
    file_max: Option<f64>,
    psi_max: Option<f64>,
    /// Counters per container id: a recreated container restarts them.
    counters: HashMap<String, [Counter; 6]>,
}

impl ContainerAgg {
    fn total(&self, i: usize) -> f64 {
        self.counters.values().map(|c| c[i].total).sum()
    }
}

fn fmax(a: Option<f64>, b: Option<f64>) -> Option<f64> {
    match (a, b) {
        (Some(x), Some(y)) => Some(x.max(y)),
        (x, y) => x.or(y),
    }
}

/// RSS now, peak RSS and average CPU of the meter itself from its `self` rows.
struct SelfStats {
    first_ts: f64,
    last_ts: f64,
    rss_bytes: Option<f64>,
    hwm_bytes: Option<f64>,
    cpu: Counter,
}

impl SelfStats {
    fn cpu_pct(&self) -> Option<f64> {
        let span = self.last_ts - self.first_ts;
        (span > 0.0).then(|| self.cpu.total / 1e6 / span * 100.0)
    }
}

/// One day of `containers-*.tsv`, aggregated while streaming.
#[derive(Default)]
struct ContainerDay {
    containers: BTreeMap<String, ContainerAgg>,
    meter: Option<SelfStats>,
    rows: usize,
    skipped: usize,
}

fn read_container_day(dir: &Path, day: i64, filter: Option<&str>) -> Result<ContainerDay, String> {
    let mut d = ContainerDay::default();
    let mut cols: Option<[usize; 9]> = None;
    let mut counter_cols = [0usize; 6];
    d.skipped = scan(dir, "containers", day, |h, r| {
        let c = match cols {
            Some(c) => c,
            None => {
                let c = [
                    h.col("ts")?,
                    h.col("container")?,
                    h.col("cid")?,
                    h.col("anon")?,
                    h.col("mem_current")?,
                    h.col("file")?,
                    h.col("psi_mem_some10")?,
                    h.col("mem_max")?,
                    h.col("cpu_usage_usec")?,
                ];
                for (i, name) in COUNTERS.iter().enumerate() {
                    counter_cols[i] = h.col(name)?;
                }
                cols = Some(c);
                c
            }
        };
        let [ts, name, cid, anon, cur, file, psi, max, cpu] = c;
        d.rows += 1;
        if r[name] == "self" {
            let t = num(r[ts]).unwrap_or(0.0);
            let m = d.meter.get_or_insert(SelfStats {
                first_ts: t,
                last_ts: t,
                rss_bytes: None,
                hwm_bytes: None,
                cpu: Counter::default(),
            });
            m.last_ts = t;
            m.rss_bytes = num(r[cur]);
            m.hwm_bytes = fmax(m.hwm_bytes, num(r[max]));
            m.cpu.add(num(r[cpu]));
            return Ok(());
        }
        if filter.is_some_and(|f| r[name] != f) {
            return Ok(());
        }
        let agg = d.containers.entry(r[name].to_string()).or_default();
        if let Some(v) = num(r[anon]) {
            agg.anon.push(v);
        }
        agg.current_max = fmax(agg.current_max, num(r[cur]));
        agg.file_max = fmax(agg.file_max, num(r[file]));
        agg.psi_max = fmax(agg.psi_max, num(r[psi]));
        let counters = agg.counters.entry(r[cid].to_string()).or_default();
        for (i, col) in counter_cols.iter().enumerate() {
            counters[i].add(num(r[*col]));
        }
        Ok(())
    })?;
    Ok(d)
}

fn containers_section(d: &ContainerDay, top: usize) -> String {
    let mut rows: Vec<(f64, Vec<String>)> = d
        .containers
        .iter()
        .map(|(name, a)| {
            let peak = max_of(&a.anon).unwrap_or(0.0);
            (
                peak,
                vec![
                    name.clone(),
                    bytes_text(peak),
                    opt(median(a.anon.clone()), bytes_text),
                    opt(a.current_max, bytes_text),
                    opt(a.file_max, bytes_text),
                    format!("{:.0}", a.total(0)),
                    format!("{:.0}", a.total(1)),
                    format!("{:.0}", a.total(2) / 1e6),
                    format!("{:.0}", a.total(3) / 1e6),
                    bytes_text(a.total(4)),
                    bytes_text(a.total(5)),
                    opt(a.psi_max, |v| format!("{v:.1}")),
                ],
            )
        })
        .collect();
    rows.sort_by(|a, b| b.0.total_cmp(&a.0));
    let shown: Vec<Vec<String>> = rows.into_iter().take(top).map(|r| r.1).collect();
    if shown.is_empty() {
        return "(no container rows)\n".into();
    }
    render(
        &[
            "CONTAINER",
            "RAM PEAK",
            "RAM P50",
            "+CACHE PEAK",
            "CACHE PEAK",
            "HIT LIMIT",
            "OOM KILL",
            "CPU-S",
            "THROTTLED-S",
            "DISK READ",
            "DISK WRITE",
            "PSI MEM MAX",
        ],
        &shown,
        1,
    )
}

fn steps_section(steps: &[StepRec], job: Option<&str>, top: usize) -> String {
    let mut groups: BTreeMap<(&str, &str), Vec<&StepRec>> = BTreeMap::new();
    for s in steps.iter().filter(|s| job.is_none_or(|j| s.job == j)) {
        groups.entry((&s.job, &s.key)).or_default().push(s);
    }
    let mut rows: Vec<(f64, Vec<String>)> = groups
        .into_iter()
        .map(|((job, key), v)| {
            let durs: Vec<f64> = v.iter().map(|s| s.duration).collect();
            let rss: Vec<f64> = v.iter().filter_map(|s| s.rss_kb).collect();
            let peak = max_of(&rss).unwrap_or(0.0);
            let cpu: f64 = v.iter().filter_map(|s| s.cpu_s).sum();
            let write: Option<f64> = v.iter().filter_map(|s| s.write_bytes).reduce(|a, b| a + b);
            (
                peak,
                vec![
                    job.to_string(),
                    key.to_string(),
                    v.len().to_string(),
                    opt(median(durs.clone()), |d| format!("{d:.1}")),
                    opt(max_of(&durs), |d| format!("{d:.1}")),
                    kb_text(peak),
                    format!("{cpu:.0}"),
                    opt(write, bytes_text),
                ],
            )
        })
        .collect();
    rows.sort_by(|a, b| b.0.total_cmp(&a.0));
    let shown: Vec<Vec<String>> = rows.into_iter().take(top).map(|r| r.1).collect();
    if shown.is_empty() {
        return "(no step rows)\n".into();
    }
    render(
        &[
            "JOB",
            "STEP",
            "RUNS",
            "DUR P50 S",
            "DUR MAX S",
            "RSS PEAK",
            "CPU-S",
            "DISK WRITE",
        ],
        &shown,
        2,
    )
}

fn models_section(models: &[ModelRec], jobs: &HashMap<String, String>, job: Option<&str>, top: usize) -> String {
    let mut groups: BTreeMap<&str, Vec<&ModelRec>> = BTreeMap::new();
    for m in models
        .iter()
        .filter(|m| job.is_none_or(|j| jobs.get(&m.run_id).is_some_and(|x| x == j)))
    {
        groups.entry(&m.unique_id).or_default().push(m);
    }
    let mut rows: Vec<(f64, Vec<String>)> = groups
        .into_iter()
        .map(|(id, v)| {
            let execs: Vec<f64> = v.iter().map(|m| m.exec_s).collect();
            let total: f64 = execs.iter().sum();
            let rss: Vec<f64> = v.iter().filter_map(|m| m.rss_kb).collect();
            let cpu: Vec<f64> = v.iter().filter_map(|m| m.cpu_s).collect();
            (
                total,
                vec![
                    id.to_string(),
                    v.len().to_string(),
                    format!("{total:.1}"),
                    opt(median(execs.clone()), |d| format!("{d:.2}")),
                    opt(max_of(&execs), |d| format!("{d:.2}")),
                    opt(max_of(&rss), kb_text),
                    if cpu.is_empty() {
                        "-".into()
                    } else {
                        format!("{:.1}", cpu.iter().sum::<f64>())
                    },
                ],
            )
        })
        .collect();
    rows.sort_by(|a, b| b.0.total_cmp(&a.0));
    let shown: Vec<Vec<String>> = rows.into_iter().take(top).map(|r| r.1).collect();
    if shown.is_empty() {
        return "(no model rows)\n".into();
    }
    render(
        &["MODEL", "RUNS", "TOTAL S", "P50 S", "MAX S", "RSS PEAK", "CPU-S"],
        &shown,
        1,
    )
}

pub fn report(o: &ReportOptions) -> Result<String, String> {
    let containers = read_container_day(&o.dir, o.day, o.container.as_deref())?;
    let steps_t = load(&o.dir, "steps", o.day)?;
    let models_t = load(&o.dir, "models", o.day)?;
    let steps = if steps_t.rows.is_empty() {
        Vec::new()
    } else {
        step_records(&steps_t)?
    };
    let models = if models_t.rows.is_empty() {
        Vec::new()
    } else {
        model_records(&models_t)?
    };
    let jobs = job_of_runs(&steps);

    let mut out = format!("resource-meter report {} ({})\n", date_text(o.day), o.dir.display());
    out += "\nContainers (RAM = anon, the processes' own memory; +CACHE = memory.current incl. page cache;\n HIT LIMIT = times memory.max was reached; counters are increases over the day)\n";
    out += &containers_section(&containers, o.top);
    out += "\nHeaviest Dagster steps (by peak RSS of the step's process tree)\n";
    out += &steps_section(&steps, o.job.as_deref(), o.top);
    out += "\nHeaviest dbt models (by total execute time; RSS only for models >= 1 s)\n";
    out += &models_section(&models, &jobs, o.job.as_deref(), o.top);
    if let Some(s) = &containers.meter {
        out += &format!(
            "\nresource-meter itself: RSS {}, peak {}, CPU {} of one core (average over the day)\n",
            opt(s.rss_bytes, bytes_text),
            opt(s.hwm_bytes, bytes_text),
            opt(s.cpu_pct(), |p| format!("{p:.3}%"))
        );
    }
    let skipped = containers.skipped + steps_t.skipped + models_t.skipped;
    if skipped > 0 {
        out += &format!("\n{skipped} malformed line(s) skipped\n");
    }
    Ok(out)
}

#[derive(Debug, Clone)]
pub struct CompareOptions {
    pub dir: PathBuf,
    pub base: i64,
    pub day: i64,
    pub job: Option<String>,
    pub top: usize,
    pub threshold_pct: f64,
}

/// Medians of one step or model on one day.
#[derive(Debug, Clone, Copy, Default)]
struct Profile {
    runs: usize,
    seconds: Option<f64>,
    rss_kb: Option<f64>,
    cpu_s: Option<f64>,
}

fn profile(seconds: Vec<f64>, rss: Vec<f64>, cpu: Vec<f64>) -> Profile {
    Profile {
        runs: seconds.len(),
        seconds: median(seconds),
        rss_kb: median(rss),
        cpu_s: median(cpu),
    }
}

fn step_profiles(steps: &[StepRec], job: Option<&str>) -> BTreeMap<String, Profile> {
    let mut groups: BTreeMap<String, Vec<&StepRec>> = BTreeMap::new();
    for s in steps.iter().filter(|s| job.is_none_or(|j| s.job == j)) {
        groups
            .entry(format!("step  {} / {}", s.job, s.key))
            .or_default()
            .push(s);
    }
    groups
        .into_iter()
        .map(|(k, v)| {
            let p = profile(
                v.iter().map(|s| s.duration).collect(),
                v.iter().filter_map(|s| s.rss_kb).collect(),
                v.iter().filter_map(|s| s.cpu_s).collect(),
            );
            (k, p)
        })
        .collect()
}

fn model_profiles(models: &[ModelRec], jobs: &HashMap<String, String>, job: Option<&str>) -> BTreeMap<String, Profile> {
    let mut groups: BTreeMap<String, Vec<&ModelRec>> = BTreeMap::new();
    for m in models
        .iter()
        .filter(|m| job.is_none_or(|j| jobs.get(&m.run_id).is_some_and(|x| x == j)))
    {
        groups.entry(format!("model {}", m.unique_id)).or_default().push(m);
    }
    groups
        .into_iter()
        .map(|(k, v)| {
            let p = profile(
                v.iter().map(|m| m.exec_s).collect(),
                v.iter().filter_map(|m| m.rss_kb).collect(),
                v.iter().filter_map(|m| m.cpu_s).collect(),
            );
            (k, p)
        })
        .collect()
}

/// Percentage change when it counts: above the threshold and above the absolute floor.
fn flagged(base: Option<f64>, new: Option<f64>, floor: f64, threshold_pct: f64) -> Option<f64> {
    let (b, n) = (base?, new?);
    if b <= 0.0 || n - b < floor {
        return None;
    }
    let pct = (n - b) / b * 100.0;
    (pct > threshold_pct).then_some(pct)
}

fn change_text(base: Option<f64>, new: Option<f64>, f: impl Fn(f64) -> String) -> String {
    match (base, new) {
        (Some(b), Some(n)) if b > 0.0 => format!("{} -> {} ({:+.0}%)", f(b), f(n), (n - b) / b * 100.0),
        (b, n) => format!("{} -> {}", opt(b, &f), opt(n, &f)),
    }
}

pub fn compare(o: &CompareOptions) -> Result<String, String> {
    // Steps and models of one day, keyed "step  <job> / <key>" and "model <unique_id>".
    let load_day = |day| -> Result<BTreeMap<String, Profile>, String> {
        let st = load(&o.dir, "steps", day)?;
        let mt = load(&o.dir, "models", day)?;
        let steps = if st.rows.is_empty() {
            Vec::new()
        } else {
            step_records(&st)?
        };
        let models = if mt.rows.is_empty() {
            Vec::new()
        } else {
            model_records(&mt)?
        };
        let jobs = job_of_runs(&steps);
        let mut all = step_profiles(&steps, o.job.as_deref());
        all.extend(model_profiles(&models, &jobs, o.job.as_deref()));
        Ok(all)
    };
    let base = load_day(o.base)?;
    let new = load_day(o.day)?;

    let mut rows: Vec<(f64, Vec<String>)> = Vec::new();
    let mut unchanged = 0;
    for (key, n) in &new {
        let Some(b) = base.get(key) else { continue };
        let flags = [
            ("time", flagged(b.seconds, n.seconds, MIN_FLAG_SECONDS, o.threshold_pct)),
            ("rss", flagged(b.rss_kb, n.rss_kb, MIN_FLAG_RSS_KB, o.threshold_pct)),
            ("cpu", flagged(b.cpu_s, n.cpu_s, MIN_FLAG_SECONDS, o.threshold_pct)),
        ];
        let worst = flags.iter().filter_map(|f| f.1).reduce(f64::max);
        let Some(worst) = worst else {
            unchanged += 1;
            continue;
        };
        let names: Vec<&str> = flags.iter().filter(|f| f.1.is_some()).map(|f| f.0).collect();
        rows.push((
            worst,
            vec![
                key.clone(),
                format!("{}/{}", b.runs, n.runs),
                change_text(b.seconds, n.seconds, |v| format!("{v:.2}s")),
                change_text(b.rss_kb, n.rss_kb, kb_text),
                change_text(b.cpu_s, n.cpu_s, |v| format!("{v:.2}")),
                names.join(","),
            ],
        ));
    }
    rows.sort_by(|a, b| b.0.total_cmp(&a.0));
    let total_flagged = rows.len();
    let shown: Vec<Vec<String>> = rows.into_iter().take(o.top).map(|r| r.1).collect();

    let mut out = format!(
        "resource-meter compare {} -> {} (medians per run; flagged when > {:.0}% and at least {MIN_FLAG_SECONDS} s or {} MB more)\n\n",
        date_text(o.base),
        date_text(o.day),
        o.threshold_pct,
        MIN_FLAG_RSS_KB / 1024.0
    );
    if shown.is_empty() {
        out += "(nothing heavier)\n";
    } else {
        out += &render(
            &["STEP / MODEL", "RUNS", "TIME P50", "RSS P50", "CPU-S P50", "HEAVIER"],
            &shown,
            2,
        );
        if total_flagged > shown.len() {
            out += &format!("... {} more\n", total_flagged - shown.len());
        }
    }
    let appeared: Vec<&String> = new.keys().filter(|k| !base.contains_key(*k)).collect();
    let gone = base.keys().filter(|k| !new.contains_key(*k)).count();
    out += &format!(
        "\n{total_flagged} heavier, {unchanged} not heavier, {} only on {}, {gone} only on {}\n",
        appeared.len(),
        date_text(o.day),
        date_text(o.base)
    );
    for k in appeared.iter().take(o.top) {
        out += &format!("  new: {k}\n");
    }
    Ok(out)
}

#[derive(Debug, Clone)]
pub struct StatusOptions {
    pub dir: PathBuf,
    pub cgroup_root: PathBuf,
    pub proc_root: PathBuf,
    pub now: f64,
    pub utc_offset_hours: i32,
}

fn meter_pids(proc_root: &Path) -> Vec<u32> {
    let me = std::process::id();
    let Ok(entries) = fs::read_dir(proc_root) else {
        return Vec::new();
    };
    let mut pids: Vec<u32> = entries
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().to_str()?.parse::<u32>().ok())
        .filter(|&pid| pid != me)
        .filter(|pid| {
            fs::read_to_string(proc_root.join(pid.to_string()).join("comm")).is_ok_and(|c| c.trim() == "resource-meter")
        })
        .collect();
    pids.sort_unstable();
    pids
}

/// Seconds since the oldest running meter process started (the unit's main process).
fn meter_running_seconds(proc_root: &Path, pids: &[u32], now: f64) -> Option<f64> {
    let procfs = ProcFs::new(proc_root);
    let btime = procfs.btime()? as f64;
    let start = pids
        .iter()
        .filter_map(|&pid| procfs.stat(pid))
        .map(|s| btime + s.start_ticks as f64 / CLK_TCK as f64)
        .reduce(f64::min)?;
    Some(now - start)
}

/// Returns the text and whether the meter is running (a recent `self` row).
pub fn status(o: &StatusOptions) -> Result<(String, bool), String> {
    let today = local_day(o.now, o.utc_offset_hours);
    let mut out = format!("resource-meter status ({})\n", o.dir.display());

    let containers = read_container_day(&o.dir, today, None)?;
    let stats = containers.meter.as_ref();
    let running = stats.is_some_and(|s| o.now - s.last_ts <= SELF_ROW_STALE_SECONDS);
    match stats {
        Some(s) => {
            out += &format!(
                "  {}: last self row {:.0} s ago\n  own use today: RSS {}, peak {}, CPU {} of one core\n",
                if running { "running" } else { "NOT RUNNING" },
                o.now - s.last_ts,
                opt(s.rss_bytes, bytes_text),
                opt(s.hwm_bytes, bytes_text),
                opt(s.cpu_pct(), |p| format!("{p:.3}%"))
            );
        }
        None => out += "  NOT RUNNING: no self row today\n",
    }
    let pids = meter_pids(&o.proc_root);
    out += &format!(
        "  resource-meter processes: {}\n",
        if pids.is_empty() {
            "none".into()
        } else {
            pids.iter().map(u32::to_string).collect::<Vec<_>>().join(", ")
        }
    );

    let unit = o.cgroup_root.join("system.slice").join(UNIT_NAME);
    if unit.is_dir() {
        let read = |f: &str| fs::read_to_string(unit.join(f)).ok();
        let events = read("memory.events")
            .map(|t| cgroup::parse_memory_events(&t))
            .unwrap_or_default();
        let peak = read("memory.peak").and_then(|t| cgroup::parse_single(&t));
        let cpu_text = read("cpu.stat").unwrap_or_default();
        let field = |k: &str| {
            cpu_text
                .lines()
                .find_map(|l| l.strip_prefix(k).and_then(|v| v.trim().parse::<f64>().ok()))
        };
        // Share of wall time the unit was throttled since the meter started: the acceptance
        // criterion. nr_throttled / nr_periods overstates it, because only periods in which the
        // meter had work are counted, and one scan longer than the per-period quota is throttled.
        let running_s = meter_running_seconds(&o.proc_root, &pids, o.now);
        let throttled = match (field("throttled_usec "), running_s) {
            (Some(t), Some(r)) if r > 0.0 => format!(
                "{:.2}% of time ({:.0} s of {:.0} s since start)",
                t / 1e6 / r * 100.0,
                t / 1e6,
                r
            ),
            _ => "-".into(),
        };
        out += &format!(
            "  unit {UNIT_NAME}: memory peak {}, MemoryMax reached {} time(s), OOM kills {}, CPU throttled {}\n",
            opt(peak.map(|v| v as f64), bytes_text),
            opt(events.max, |v| v.to_string()),
            opt(events.oom_kill, |v| v.to_string()),
            throttled
        );
    } else {
        out += &format!("  unit {UNIT_NAME}: not found (not installed, or not running)\n");
    }

    let mut days: Vec<i64> = Vec::new();
    let mut size = 0u64;
    let mut files = 0;
    if let Ok(entries) = fs::read_dir(&o.dir) {
        for e in entries.filter_map(Result::ok) {
            let name = e.file_name().to_string_lossy().into_owned();
            let stamp = name.split('-').nth(1).and_then(|r| r.get(..8));
            if let Some(day) = stamp.and_then(parse_day_stamp) {
                files += 1;
                size += e.metadata().map(|m| m.len()).unwrap_or(0);
                days.push(day);
            }
        }
    }
    days.sort_unstable();
    out += &format!(
        "  data: {files} file(s), {}, days {} .. {}\n",
        bytes_text(size as f64),
        opt(days.first().copied(), date_text),
        opt(days.last().copied(), date_text)
    );
    let rows_of = |kind| {
        let mut n = 0usize;
        let _ = scan(&o.dir, kind, today, |_, _| {
            n += 1;
            Ok(())
        });
        n
    };
    out += &format!(
        "  today: {} container rows, {} process rows, {} step rows, {} model rows\n",
        containers.rows,
        rows_of("processes"),
        rows_of("steps"),
        rows_of("models")
    );
    Ok((out, running))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::attribution::{MODELS_HEADER, STEPS_HEADER};
    use crate::collector::CONTAINERS_HEADER;
    use crate::test_support::TempTree;

    const BASE: i64 = 20_742; // 2026-10-16
    const DAY: i64 = 20_743; // 2026-10-17
    const T: f64 = 1_792_195_200.0; // 2026-10-17T00:00:00Z

    fn container_row(ts: f64, name: &str, cid: &str, anon: u64, cur: u64, evmax: u64, cpu: u64) -> String {
        format!("{ts}\t{name}\t{cid}\t{cur}\t{anon}\t100\t10\t0\t8589934592\t{evmax}\t0\t0\t{cpu}\t0\t0\t0\t0\t0.10\t0.00\t0.00\t0.00\n")
    }

    fn step_row(run: &str, job: &str, key: &str, start: f64, end: f64, rss: u64, cpu: f64) -> String {
        format!("{run}\t{job}\t{key}\tmultiprocess\t{start}\t{end}\t901\t{rss}\t{cpu}\t\t\n")
    }

    fn model_row(run: &str, id: &str, start: f64, end: f64, rss: &str, cpu: &str) -> String {
        format!(
            "{run}\t{id}\tsuccess\t{start}\t{end}\t{}\t{rss}\t\t{cpu}\t\n",
            end - start
        )
    }

    fn fixture(t: &TempTree) {
        let mut c = format!("{CONTAINERS_HEADER}\n");
        c += &container_row(T, "data_platform", "aaa", 1 << 30, 8 << 30, 10, 1_000_000);
        c += &container_row(T + 15.0, "data_platform", "aaa", 3 << 30, 8 << 30, 15, 61_000_000);
        // Recreated container: new cid, counters restart.
        c += &container_row(T + 30.0, "data_platform", "bbb", 2 << 30, 4 << 30, 0, 500_000);
        c += &container_row(T + 45.0, "data_platform", "bbb", 2 << 30, 4 << 30, 2, 2_500_000);
        c += &container_row(T, "metabase", "ccc", 1 << 29, 1 << 30, 0, 0);
        c += "1792195260\tself\t\t2000000\t\t\t\t\t3000000\t\t\t\t100000\t\t\t0\t0\t\t\t\t\n";
        c += "1792195320\tself\t\t2100000\t\t\t\t\t3100000\t\t\t\t160000\t\t\t0\t0\t\t\t\t\n";
        c += "broken line\n";
        t.file("containers-20261017.tsv", c);

        let mut s = format!("{STEPS_HEADER}\n");
        s += &step_row("r1", "nightly", "sapo_dbt_assets", T, T + 36.0, 1_800_000, 39.0);
        s += &step_row("r1", "nightly", "ingest", T, T + 10.0, 300_000, 3.0);
        s += &step_row("r2", "realtime", "sapo_dbt_assets", T, T + 30.0, 1_700_000, 30.0);
        t.file("steps-20261017.tsv", s);
        let mut s = format!("{STEPS_HEADER}\n");
        s += &step_row("r0", "nightly", "sapo_dbt_assets", T, T + 30.0, 1_500_000, 30.0);
        s += &step_row("r0", "nightly", "ingest", T, T + 10.0, 300_000, 3.0);
        s += &step_row("r0", "nightly", "dropped_step", T, T + 1.0, 1, 1.0);
        t.file("steps-20261016.tsv", s);

        let mut m = format!("{MODELS_HEADER}\n");
        m += &model_row("r1", "model.p.big", T, T + 5.0, "900000", "4.5");
        m += &model_row("r1", "model.p.small", T, T + 0.3, "", "");
        m += &model_row("r2", "model.p.big", T, T + 4.0, "800000", "3.5");
        t.file("models-20261017.tsv", m);
        let mut m = format!("{MODELS_HEADER}\n");
        m += &model_row("r0", "model.p.big", T, T + 4.0, "850000", "3.0");
        m += &model_row("r0", "model.p.small", T, T + 0.2, "", "");
        t.file("models-20261016.tsv", m);
    }

    #[test]
    fn dates() {
        assert_eq!(parse_date("2026-10-17"), Ok(DAY));
        assert!(parse_date("20261017").is_err());
        assert!(parse_date("2026-02-30").is_err());
        assert_eq!(date_text(DAY), "2026-10-17");
    }

    #[test]
    fn helpers() {
        assert_eq!(median(vec![3.0, 1.0, 2.0]), Some(2.0));
        assert_eq!(median(vec![4.0, 1.0]), Some(2.5));
        assert_eq!(median(vec![]), None);
        let mut c = Counter::default();
        for v in [Some(10.0), Some(15.0), None, Some(2.0), Some(4.0)] {
            c.add(v);
        }
        assert_eq!(c.total, 7.0);
        assert_eq!(kb_text(1536.0), "2 MB");
        assert_eq!(kb_text(3.0 * 1024.0 * 1024.0), "3.00 GB");
        assert_eq!(flagged(Some(10.0), Some(12.0), 0.5, 10.0), Some(20.0));
        assert_eq!(flagged(Some(0.2), Some(0.3), 0.5, 10.0), None);
        assert_eq!(flagged(Some(10.0), Some(10.5), 0.5, 10.0), None);
        assert_eq!(flagged(None, Some(1.0), 0.5, 10.0), None);
    }

    #[test]
    fn report_tables() {
        let t = TempTree::new();
        fixture(&t);
        let o = ReportOptions {
            dir: t.path().into(),
            day: DAY,
            container: None,
            job: None,
            top: 10,
        };
        let out = report(&o).unwrap();
        // data_platform first (anon peak 3 GB), with counters summed across cids.
        let dp = out.lines().find(|l| l.starts_with("data_platform")).unwrap();
        let cells: Vec<&str> = dp.split("  ").filter(|c| !c.trim().is_empty()).map(str::trim).collect();
        assert_eq!(cells[0], "data_platform");
        assert_eq!(cells[1], "3.00 GB");
        assert_eq!(cells[5], "7"); // 5 + 2 limit hits
        assert_eq!(cells[7], "62"); // 60 + 2 CPU seconds
        assert!(out.find("data_platform").unwrap() < out.find("metabase").unwrap());
        // Steps: the dbt step of the nightly has the highest peak.
        let first_step = out.lines().skip_while(|l| !l.starts_with("JOB")).nth(1).unwrap();
        assert!(first_step.starts_with("nightly") && first_step.contains("sapo_dbt_assets"));
        // Models: big ran twice, 9 s in total.
        let big = out.lines().find(|l| l.starts_with("model.p.big")).unwrap();
        assert!(big.contains("9.0"));
        assert!(out.contains("CPU 0.100% of one core"));
        assert!(out.contains("1 malformed line(s) skipped"));

        let only_realtime = report(&ReportOptions {
            job: Some("realtime".into()),
            ..o.clone()
        })
        .unwrap();
        assert!(!only_realtime.lines().any(|l| l.starts_with("nightly")));
        let big = only_realtime.lines().find(|l| l.starts_with("model.p.big")).unwrap();
        assert!(big.contains("4.0"));
        let one = report(&ReportOptions {
            container: Some("metabase".into()),
            ..o.clone()
        })
        .unwrap();
        assert!(!one.lines().any(|l| l.starts_with("data_platform")));

        let empty = report(&ReportOptions { day: DAY + 5, ..o }).unwrap();
        assert!(empty.contains("(no container rows)") && empty.contains("(no step rows)"));
    }

    #[test]
    fn compare_flags_heavier_steps_and_models() {
        let t = TempTree::new();
        fixture(&t);
        let o = CompareOptions {
            dir: t.path().into(),
            base: BASE,
            day: DAY,
            job: None,
            top: 10,
            threshold_pct: 10.0,
        };
        let out = compare(&o).unwrap();
        // nightly dbt step: 30 s -> 36 s (+20%), RSS +20%, CPU +30%.
        let dbt = out.lines().find(|l| l.contains("nightly / sapo_dbt_assets")).unwrap();
        assert!(dbt.contains("time,rss,cpu"), "{dbt}");
        assert!(dbt.contains("(+20%)"));
        // model big: median 4.5 s vs 4 s (+12.5%, but only 0.5 s: at the floor, flagged);
        // CPU median 4.0 vs 3.0 (+33%).
        let big = out.lines().find(|l| l.contains("model model.p.big")).unwrap();
        assert!(big.contains("cpu"));
        // Unchanged step, tiny model and the step that disappeared are not flagged.
        assert!(!out.lines().any(|l| l.contains("nightly / ingest") && l.contains("->")));
        assert!(!out.contains("model.p.small ->"));
        assert!(out.contains("1 only on 2026-10-17") && out.contains("1 only on 2026-10-16"));
        assert!(out.contains("new: step  realtime / sapo_dbt_assets"));

        let strict = compare(&CompareOptions {
            threshold_pct: 50.0,
            ..o
        })
        .unwrap();
        assert!(strict.contains("(nothing heavier)"));
    }

    #[test]
    fn status_running_and_not() {
        let t = TempTree::new();
        fixture(&t);
        t.file(
            &format!("cg/system.slice/{UNIT_NAME}/memory.events"),
            "max 0\noom 0\noom_kill 0\n",
        );
        t.file(&format!("cg/system.slice/{UNIT_NAME}/memory.peak"), "4194304\n");
        t.file(
            &format!("cg/system.slice/{UNIT_NAME}/cpu.stat"),
            "usage_usec 1\nnr_periods 200\nnr_throttled 1\nthrottled_usec 900000\n",
        );
        t.file("proc/4242/comm", "resource-meter\n");
        // Started 100 s before T + 180: btime T, start ticks 80 s.
        t.file("proc/stat", &format!("cpu 1 2 3\nbtime {}\n", T as u64));
        t.file(
            "proc/4242/stat",
            "4242 (resource-meter) S 1 4242 4242 0 -1 0 0 0 0 0 1 1 0 0 39 19 1 0 8000 0 0",
        );
        t.file("proc/4243/comm", "bash\n");
        let o = StatusOptions {
            dir: t.path().into(),
            cgroup_root: t.path().join("cg"),
            proc_root: t.path().join("proc"),
            now: T + 180.0,
            utc_offset_hours: 0,
        };
        let (text, running) = status(&o).unwrap();
        assert!(running, "{text}");
        assert!(text.contains("resource-meter processes: 4242"));
        assert!(text.contains("MemoryMax reached 0 time(s)") && text.contains("0.90% of time (1 s of 100 s since start)"));
        assert!(text.contains("today: 7 container rows, 0 process rows, 3 step rows, 3 model rows"));
        assert!(text.contains("days 2026-10-16 .. 2026-10-17"));

        let (text, running) = status(&StatusOptions {
            now: T + 3600.0,
            cgroup_root: t.path().join("none"),
            ..o
        })
        .unwrap();
        assert!(!running);
        assert!(text.contains("NOT RUNNING") && text.contains("not found"));
    }
}
