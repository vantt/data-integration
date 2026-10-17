//! dbt models: find the `run_results.json` of a `dbt build` invocation and cut the dbt
//! process's sample series into per-model windows.
//!
//! dagster-dbt gives each invocation its own directory
//! `<target dir>/<op name>-<run_id[:7]>-<7 random hex>/`. The file is parsed with
//! `RawValue`, so large fields (`compiled_code`, `args` with the full command line) are
//! skipped without being decoded or copied.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::value::RawValue;
use serde_json::Value;

use crate::procfs::CLK_TCK;
use crate::tracker::Sample;

/// Files larger than this are not read (a full build is about 2 MB).
pub const MAX_RUN_RESULTS_BYTES: u64 = 24 * 1024 * 1024;
/// Models shorter than this get a duration but no memory or CPU figures.
pub const MIN_MODEL_SECONDS: f64 = 1.0;
/// Nodes whose `execute` window is shorter than this (or missing, e.g. skipped nodes) are
/// not written at all, to keep the models file small.
pub const MIN_WRITTEN_SECONDS: f64 = 0.1;
/// Result kinds written to the models file.
const NODE_PREFIXES: [&str; 3] = ["model.", "seed.", "snapshot."];

/// Seconds since the epoch for an ISO-8601 UTC time such as `2026-10-17T13:24:05.123456Z`
/// (a missing zone is read as UTC, as dbt writes UTC).
pub fn parse_utc(s: &str) -> Option<f64> {
    let s = s.trim();
    let s = s.strip_suffix('Z').or_else(|| s.strip_suffix("+00:00")).unwrap_or(s);
    let (date, time) = s.split_once('T').or_else(|| s.split_once(' '))?;
    let day = crate::clock::parse_day_stamp(&date.replace('-', ""))?;
    if date.len() != 10 {
        return None;
    }
    let (hms, frac) = match time.split_once('.') {
        Some((a, b)) => (a, Some(b)),
        None => (time, None),
    };
    let mut parts = hms.split(':');
    let h: u32 = parts.next()?.parse().ok()?;
    let m: u32 = parts.next()?.parse().ok()?;
    let sec: u32 = parts.next()?.parse().ok()?;
    if parts.next().is_some() || h > 23 || m > 59 || sec > 60 {
        return None;
    }
    let frac = match frac {
        Some(f) if !f.is_empty() && f.bytes().all(|b| b.is_ascii_digit()) => format!("0.{f}").parse::<f64>().ok()?,
        Some(_) => return None,
        None => 0.0,
    };
    Some(day as f64 * 86_400.0 + f64::from(h * 3600 + m * 60 + sec) + frac)
}

#[derive(Debug, Clone, PartialEq)]
pub struct NodeResult {
    pub unique_id: String,
    pub status: String,
    pub execution_time: Option<f64>,
    /// `execute` timing window, epoch seconds.
    pub execute: Option<(f64, f64)>,
    pub rows_affected: Option<u64>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RunResults {
    pub generated_at: Option<f64>,
    pub nodes: Vec<NodeResult>,
}

/// Decodes one small field (never `compiled_code` or `args`).
fn small(raw: Option<&&RawValue>) -> Value {
    raw.and_then(|r| serde_json::from_str(r.get()).ok())
        .unwrap_or(Value::Null)
}

/// Parses the fields needed from `run_results.json`, keeping only model-like nodes.
pub fn parse_run_results(bytes: &[u8]) -> Result<RunResults, String> {
    let top: HashMap<String, &RawValue> =
        serde_json::from_slice(bytes).map_err(|e| format!("run_results.json: {e}"))?;
    let generated_at = top
        .get("metadata")
        .and_then(|m| serde_json::from_str::<HashMap<String, &RawValue>>(m.get()).ok())
        .and_then(|m| small(m.get("generated_at")).as_str().and_then(parse_utc));
    let results: Vec<&RawValue> = match top.get("results") {
        Some(r) => serde_json::from_str(r.get()).map_err(|e| format!("run_results.json results: {e}"))?,
        None => return Err("run_results.json has no results".into()),
    };
    let mut nodes = Vec::new();
    for r in results {
        let Ok(fields) = serde_json::from_str::<HashMap<String, &RawValue>>(r.get()) else {
            continue;
        };
        let Some(unique_id) = small(fields.get("unique_id")).as_str().map(String::from) else {
            continue;
        };
        if !NODE_PREFIXES.iter().any(|p| unique_id.starts_with(p)) {
            continue;
        }
        let timing = small(fields.get("timing"));
        let execute = timing
            .as_array()
            .into_iter()
            .flatten()
            .find(|t| t["name"] == "execute")
            .and_then(|t| {
                let s = parse_utc(t["started_at"].as_str()?)?;
                let e = parse_utc(t["completed_at"].as_str()?)?;
                (e >= s).then_some((s, e))
            });
        let adapter = small(fields.get("adapter_response"));
        nodes.push(NodeResult {
            unique_id,
            status: small(fields.get("status")).as_str().unwrap_or("").to_string(),
            execution_time: small(fields.get("execution_time")).as_f64(),
            execute,
            rows_affected: adapter["rows_affected"].as_u64(),
        });
    }
    Ok(RunResults { generated_at, nodes })
}

/// Directories of invocations that belong to `run_id` (`<op>-<run_id[:7]>-<id>`).
pub fn candidate_dirs(target_dir: &Path, run_id: &str) -> Vec<PathBuf> {
    let Some(run7) = run_id.get(..7) else { return Vec::new() };
    let Ok(entries) = fs::read_dir(target_dir) else {
        return Vec::new();
    };
    entries
        .filter_map(Result::ok)
        .filter(|e| {
            let name = e.file_name();
            let name = name.to_string_lossy();
            let mut parts = name.rsplitn(3, '-');
            let (_id, run, op) = (parts.next(), parts.next(), parts.next());
            op.is_some_and(|o| !o.is_empty()) && run == Some(run7)
        })
        .map(|e| e.path())
        .collect()
}

/// Finds and parses the `run_results.json` written by the dbt process that ran from
/// `started` to `ended` in run `run_id`: among the run's invocation directories, the one
/// whose `generated_at` is inside the process lifetime (with slack), closest to its end.
pub fn find_run_results(target_dir: &Path, run_id: &str, started: f64, ended: f64) -> Result<RunResults, String> {
    let mut best: Option<(f64, RunResults)> = None;
    let mut seen = 0;
    for dir in candidate_dirs(target_dir, run_id) {
        let path = dir.join("run_results.json");
        let Ok(meta) = fs::metadata(&path) else { continue };
        seen += 1;
        if meta.len() > MAX_RUN_RESULTS_BYTES {
            return Err(format!(
                "{} is larger than {MAX_RUN_RESULTS_BYTES} bytes",
                path.display()
            ));
        }
        let bytes = fs::read(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
        let parsed = parse_run_results(&bytes)?;
        let Some(gen) = parsed.generated_at else { continue };
        if gen < started - 5.0 || gen > ended + 120.0 {
            continue;
        }
        let distance = (gen - ended).abs();
        if best.as_ref().is_none_or(|(d, _)| distance < *d) {
            best = Some((distance, parsed));
        }
    }
    best.map(|(_, r)| r).ok_or_else(|| {
        format!(
            "no run_results.json for run {run_id} in {} ({seen} candidates)",
            target_dir.display()
        )
    })
}

#[derive(Debug, Clone, PartialEq)]
pub struct ModelUsage {
    pub rss_peak_kb: u64,
    pub rss_delta_kb: i64,
    pub cpu_s: f64,
}

/// Memory and CPU of the dbt process during one model's `execute` window. `None` when
/// the window is shorter than [`MIN_MODEL_SECONDS`] or has no sample.
pub fn model_usage(samples: &[Sample], start: f64, end: f64) -> Option<ModelUsage> {
    if end - start < MIN_MODEL_SECONDS {
        return None;
    }
    let inside: Vec<&Sample> = samples.iter().filter(|s| s.ts >= start && s.ts <= end).collect();
    let first = *inside.first()?;
    let last = *inside.last()?;
    let baseline = samples.iter().rev().find(|s| s.ts <= start).unwrap_or(first);
    let peak = inside.iter().map(|s| s.rss_kb).max().unwrap_or(0);
    Some(ModelUsage {
        rss_peak_kb: peak,
        rss_delta_kb: peak as i64 - baseline.rss_kb as i64,
        cpu_s: last.cpu_ticks.saturating_sub(baseline.cpu_ticks) as f64 / CLK_TCK as f64,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::TempTree;

    const RUN: &str = "0a1b2c3d-0000-4111-8222-123456789abc";
    // 2026-10-17T00:00:00Z
    const DAY0: f64 = 1_792_195_200.0;

    fn run_results(generated: &str) -> String {
        format!(
            r#"{{"metadata":{{"dbt_schema_version":"x","dbt_version":"1.11.12","generated_at":"{generated}","invocation_id":"i","env":{{}}}},
            "results":[
              {{"status":"success","timing":[{{"name":"compile","started_at":"2026-10-17T00:00:01.000000Z","completed_at":"2026-10-17T00:00:01.500000Z"}},
                {{"name":"execute","started_at":"2026-10-17T00:00:02.000000Z","completed_at":"2026-10-17T00:00:05.000000Z"}}],
               "thread_id":"Thread-1 (worker)","execution_time":3.6,"adapter_response":{{"_message":"OK","rows_affected":42}},
               "message":"OK","failures":null,"unique_id":"model.proj.fact_orders","compiled":true,
               "compiled_code":"select \"secret\" from big_table","relation_name":"x","batch_results":null}},
              {{"status":"pass","timing":[],"execution_time":0.1,"adapter_response":{{}},"unique_id":"test.proj.not_null_x"}},
              {{"status":"skipped","timing":[],"execution_time":0,"adapter_response":{{}},"unique_id":"model.proj.skipped_one"}},
              {{"status":"success","timing":[{{"name":"execute","started_at":"2026-10-17T00:00:06Z","completed_at":"2026-10-17T00:00:06.4Z"}}],"execution_time":0.4,"adapter_response":{{"_message":"OK"}},"unique_id":"seed.proj.channels"}}
            ],
            "elapsed_time":6.0,"args":{{"invocation_command":"dbt build --select a b c","which":"build"}}}}"#
        )
    }

    #[test]
    fn utc_parsing() {
        assert_eq!(parse_utc("2026-10-17T00:00:00Z"), Some(DAY0));
        assert_eq!(parse_utc("2026-10-17T00:00:02.250000Z"), Some(DAY0 + 2.25));
        assert_eq!(parse_utc("2026-10-17 01:00:00+00:00"), Some(DAY0 + 3600.0));
        assert_eq!(parse_utc("2026-10-17T00:00:00"), Some(DAY0));
        for bad in [
            "2026-10-17",
            "2026-13-01T00:00:00Z",
            "2026-10-17T25:00:00Z",
            "2026-10-17T00:00:00.xZ",
            "x",
        ] {
            assert_eq!(parse_utc(bad), None, "{bad}");
        }
    }

    #[test]
    fn parses_models_only_and_skips_large_fields() {
        let r = parse_run_results(run_results("2026-10-17T00:00:07.000000Z").as_bytes()).unwrap();
        assert_eq!(r.generated_at, Some(DAY0 + 7.0));
        let ids: Vec<&str> = r.nodes.iter().map(|n| n.unique_id.as_str()).collect();
        assert_eq!(
            ids,
            vec!["model.proj.fact_orders", "model.proj.skipped_one", "seed.proj.channels"]
        );
        let m = &r.nodes[0];
        assert_eq!(m.status, "success");
        assert_eq!(m.execute, Some((DAY0 + 2.0, DAY0 + 5.0)));
        assert_eq!(m.execution_time, Some(3.6));
        assert_eq!(m.rows_affected, Some(42));
        assert_eq!(r.nodes[1].execute, None);
        assert_eq!(r.nodes[2].rows_affected, None);
        assert!(parse_run_results(b"{\"metadata\":{}}").is_err());
        assert!(parse_run_results(b"not json").is_err());
    }

    #[test]
    fn finds_the_invocation_of_the_process() {
        let t = TempTree::new();
        // Same run, an older build (generated long before the process started).
        t.file(
            "sapo_dbt_assets-0a1b2c3-aaaaaaa/run_results.json",
            run_results("2026-10-16T23:00:00Z"),
        );
        t.file(
            "sapo_dbt_assets-0a1b2c3-bbbbbbb/run_results.json",
            run_results("2026-10-17T00:00:07Z"),
        );
        // Other run, and a context-less invocation directory.
        t.file(
            "sapo_dbt_assets-ffffff0-ccccccc/run_results.json",
            run_results("2026-10-17T00:00:07Z"),
        );
        t.file("1234567/run_results.json", run_results("2026-10-17T00:00:07Z"));
        t.file("manifest.json", "{}");
        assert_eq!(candidate_dirs(t.path(), RUN).len(), 2);
        let r = find_run_results(t.path(), RUN, DAY0, DAY0 + 6.5).unwrap();
        assert_eq!(r.generated_at, Some(DAY0 + 7.0));
        assert!(find_run_results(t.path(), "ffffff0-x", DAY0 + 1000.0, DAY0 + 1010.0).is_err());
        assert!(find_run_results(&t.path().join("missing"), RUN, DAY0, DAY0 + 6.5).is_err());
    }

    #[test]
    fn model_windows() {
        let s = |ts: f64, rss: u64, cpu: u64| Sample {
            ts: DAY0 + ts,
            rss_kb: rss,
            cpu_ticks: cpu,
        };
        let samples = vec![
            s(1.75, 100, 10),
            s(2.0, 150, 20),
            s(3.0, 400, 80),
            s(4.0, 300, 120),
            s(5.5, 120, 130),
        ];
        let u = model_usage(&samples, DAY0 + 2.0, DAY0 + 5.0).unwrap();
        assert_eq!(
            u,
            ModelUsage {
                rss_peak_kb: 400,
                rss_delta_kb: 250,
                cpu_s: 1.0
            }
        );
        // Shorter than one second: duration only.
        assert_eq!(model_usage(&samples, DAY0 + 2.0, DAY0 + 2.9), None);
        // No sample inside the window.
        assert_eq!(model_usage(&samples, DAY0 + 10.0, DAY0 + 12.0), None);
        // No sample before the window: the first one inside is the baseline.
        let u = model_usage(&samples[1..], DAY0 + 1.9, DAY0 + 4.0).unwrap();
        assert_eq!(u.rss_delta_kb, 250);
        // Memory freed during the model gives a negative delta.
        let falling = vec![s(0.0, 900, 0), s(1.0, 500, 5), s(2.0, 400, 9)];
        assert_eq!(
            model_usage(&falling, DAY0 + 0.5, DAY0 + 2.0).unwrap().rss_delta_kb,
            -400
        );
    }
}
