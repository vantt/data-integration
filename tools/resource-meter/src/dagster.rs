//! Read-only Dagster GraphQL queries: job name, executor and the per-process
//! `LogsCapturedEvent`s (container PID, compute-log key, step keys) of one run.

use serde_json::{json, Value};

use crate::http::Endpoint;

const RUN_QUERY: &str = "query($runId: ID!) { runOrError(runId: $runId) { __typename ... on Run { jobName status } ... on PythonError { message } } }";
const LOGS_QUERY: &str = "query($runId: ID!, $cursor: String) { logsForRun(runId: $runId, afterCursor: $cursor, limit: 1000) { __typename ... on EventConnection { cursor hasMore events { __typename ... on LogsCapturedEvent { fileKey stepKeys pid } ... on EngineEvent { message } } } ... on PythonError { message } ... on RunNotFoundError { message } } }";
/// Upper bound on pages per run (1000 events each); the nightly has about 3,300 events.
const MAX_PAGES: usize = 200;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Executor {
    Multiprocess,
    InProcess,
}

impl Executor {
    pub fn as_str(self) -> &'static str {
        match self {
            Executor::Multiprocess => "multiprocess",
            Executor::InProcess => "in_process",
        }
    }
}

/// One process whose output Dagster captured: a step process, or the run worker
/// under the in-process executor (then `step_keys` lists every step).
#[derive(Debug, Clone, PartialEq)]
pub struct Capture {
    pub file_key: String,
    pub step_keys: Vec<String>,
    /// PID inside the container.
    pub pid: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct RunInfo {
    pub job: Option<String>,
    pub status: Option<String>,
    pub executor: Option<Executor>,
    /// Run worker PID inside the container ("Started process for run (pid: N)").
    pub worker_pid: Option<u32>,
    pub captures: Vec<Capture>,
}

#[derive(Debug, PartialEq)]
pub enum FetchError {
    /// Dagster does not know the run (purged, or from another Dagster instance).
    NotFound,
    /// Network or server error: worth retrying later.
    Retry(String),
}

fn graphql(endpoint: &Endpoint, query: &str, variables: Value) -> Result<Value, FetchError> {
    let body = json!({ "query": query, "variables": variables }).to_string();
    let raw = endpoint.post_json(body.as_bytes()).map_err(FetchError::Retry)?;
    let v: Value = serde_json::from_slice(&raw).map_err(|e| FetchError::Retry(format!("bad JSON: {e}")))?;
    if let Some(errors) = v.get("errors") {
        return Err(FetchError::Retry(format!(
            "GraphQL errors: {}",
            truncate(&errors.to_string(), 200)
        )));
    }
    v.get("data")
        .cloned()
        .ok_or_else(|| FetchError::Retry("no data in GraphQL response".into()))
}

fn truncate(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// Fetches everything needed to attribute a finished run.
pub fn fetch_run(endpoint: &Endpoint, run_id: &str) -> Result<RunInfo, FetchError> {
    let data = graphql(endpoint, RUN_QUERY, json!({ "runId": run_id }))?;
    let mut info = RunInfo::default();
    let run = &data["runOrError"];
    match run["__typename"].as_str() {
        Some("Run") => {
            info.job = run["jobName"].as_str().map(String::from);
            info.status = run["status"].as_str().map(String::from);
        }
        Some("RunNotFoundError") => return Err(FetchError::NotFound),
        other => return Err(FetchError::Retry(format!("runOrError returned {other:?}"))),
    }

    let mut cursor: Option<String> = None;
    for _ in 0..MAX_PAGES {
        let data = graphql(endpoint, LOGS_QUERY, json!({ "runId": run_id, "cursor": cursor }))?;
        let page = &data["logsForRun"];
        match page["__typename"].as_str() {
            Some("EventConnection") => {}
            Some("RunNotFoundError") => return Err(FetchError::NotFound),
            other => return Err(FetchError::Retry(format!("logsForRun returned {other:?}"))),
        }
        apply_events(&mut info, page["events"].as_array().map(Vec::as_slice).unwrap_or(&[]));
        let more = page["hasMore"].as_bool().unwrap_or(false);
        let next = page["cursor"].as_str().map(String::from);
        if !more || next.is_none() || next == cursor {
            return Ok(info);
        }
        cursor = next;
    }
    Err(FetchError::Retry(format!("more than {MAX_PAGES} event pages")))
}

const RUNS_QUERY: &str = "query($after: Float) { runsOrError(filter: { updatedAfter: $after }, limit: 100) { __typename ... on Runs { results { runId startTime } } ... on PythonError { message } } }";
/// Candidate runs checked when looking a run up by its worker PID.
const MAX_CANDIDATES: usize = 5;
/// Slack between the worker process start and Dagster's run `startTime`.
const START_SLACK_SECONDS: f64 = 30.0;

/// Finds the run executed by a run worker when no compute-log `tail` revealed its id
/// (for example a run whose steps were all shorter than one sampling pass). Candidates
/// are runs updated since the worker started whose `startTime` falls in its lifetime;
/// a candidate is accepted only when its "Started process for run (pid: N)" names the
/// worker's container PID.
pub fn find_run_by_worker(
    endpoint: &Endpoint,
    worker_ns_pid: u32,
    started: f64,
    ended: f64,
) -> Result<Option<(String, RunInfo)>, FetchError> {
    let data = graphql(endpoint, RUNS_QUERY, json!({ "after": started - 60.0 }))?;
    let runs = &data["runsOrError"];
    if runs["__typename"].as_str() != Some("Runs") {
        return Err(FetchError::Retry(format!(
            "runsOrError returned {:?}",
            runs["__typename"].as_str()
        )));
    }
    let mut candidates: Vec<(f64, String)> = runs["results"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
        .iter()
        .filter_map(|r| Some((r["startTime"].as_f64()?, r["runId"].as_str()?.to_string())))
        .filter(|(t, _)| *t >= started - START_SLACK_SECONDS && *t <= ended + START_SLACK_SECONDS)
        .collect();
    candidates.sort_by(|a, b| (a.0 - started).abs().total_cmp(&(b.0 - started).abs()));
    for (_, run_id) in candidates.into_iter().take(MAX_CANDIDATES) {
        match fetch_run(endpoint, &run_id) {
            Ok(info) if info.worker_pid == Some(worker_ns_pid) => return Ok(Some((run_id, info))),
            Ok(_) | Err(FetchError::NotFound) => continue,
            Err(e) => return Err(e),
        }
    }
    Ok(None)
}

/// `pid: N` inside an engine message.
fn pid_in(message: &str) -> Option<u32> {
    let rest = &message[message.find("pid: ")? + 5..];
    let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
    digits.parse().ok()
}

pub fn apply_events(info: &mut RunInfo, events: &[Value]) {
    for e in events {
        match e["__typename"].as_str() {
            Some("LogsCapturedEvent") => {
                let Some(file_key) = e["fileKey"].as_str() else {
                    continue;
                };
                let step_keys = e["stepKeys"]
                    .as_array()
                    .map(|a| a.iter().filter_map(|k| k.as_str().map(String::from)).collect())
                    .unwrap_or_default();
                let pid = e["pid"].as_u64().and_then(|p| u32::try_from(p).ok());
                info.captures.push(Capture {
                    file_key: file_key.to_string(),
                    step_keys,
                    pid,
                });
            }
            Some("EngineEvent") => {
                let msg = e["message"].as_str().unwrap_or("");
                if msg.starts_with("Started process for run") {
                    info.worker_pid = pid_in(msg).or(info.worker_pid);
                } else if msg.starts_with("Executing steps in process") {
                    info.executor = Some(Executor::InProcess);
                } else if msg.starts_with("Executing steps using multiprocess executor") {
                    info.executor = Some(Executor::Multiprocess);
                }
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::thread;

    #[test]
    fn events_to_run_info() {
        let events: Vec<Value> = serde_json::from_str(
            r#"[
              {"__typename":"EngineEvent","message":"Started process for run (pid: 944359)."},
              {"__typename":"EngineEvent","message":"Executing steps using multiprocess executor: parent process (pid: 944359)"},
              {"__typename":"LogsCapturedEvent","fileKey":"qbiabrcl","stepKeys":["sapo_dbt_assets"],"pid":944468},
              {"__typename":"LogsCapturedEvent","fileKey":"pnageyhi","stepKeys":["a","b"],"pid":null},
              {"__typename":"ExecutionStepStartEvent"},
              {"__typename":"LogsCapturedEvent","stepKeys":["missing_key"]}
            ]"#,
        )
        .unwrap();
        let mut info = RunInfo::default();
        apply_events(&mut info, &events);
        assert_eq!(info.worker_pid, Some(944_359));
        assert_eq!(info.executor, Some(Executor::Multiprocess));
        assert_eq!(info.captures.len(), 2);
        assert_eq!(
            info.captures[0],
            Capture {
                file_key: "qbiabrcl".into(),
                step_keys: vec!["sapo_dbt_assets".into()],
                pid: Some(944_468)
            }
        );
        assert_eq!(info.captures[1].pid, None);

        let mut in_proc = RunInfo::default();
        apply_events(
            &mut in_proc,
            &[json!({"__typename":"EngineEvent","message":"Executing steps in process (pid: 874814)"})],
        );
        assert_eq!(in_proc.executor, Some(Executor::InProcess));
        assert_eq!(pid_in("x (pid: 12)."), Some(12));
        assert_eq!(pid_in("no pid"), None);
    }

    /// Serves the given bodies, one per connection, and returns the requests.
    fn serve(bodies: Vec<String>) -> (Endpoint, thread::JoinHandle<Vec<String>>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = thread::spawn(move || {
            let mut requests = Vec::new();
            for body in bodies {
                let (mut s, _) = listener.accept().unwrap();
                let mut got = Vec::new();
                let mut buf = [0u8; 8192];
                loop {
                    let n = s.read(&mut buf).unwrap();
                    got.extend_from_slice(&buf[..n]);
                    let text = String::from_utf8_lossy(&got);
                    if let Some(i) = text.find("\r\n\r\n") {
                        let len: usize = text
                            .lines()
                            .find_map(|l| l.strip_prefix("Content-Length: "))
                            .and_then(|v| v.trim().parse().ok())
                            .unwrap_or(0);
                        if got.len() >= i + 4 + len {
                            break;
                        }
                    }
                    if n == 0 {
                        break;
                    }
                }
                requests.push(String::from_utf8_lossy(&got).into_owned());
                let resp = format!("HTTP/1.1 200 OK\r\nContent-Length: {}\r\n\r\n{body}", body.len());
                s.write_all(resp.as_bytes()).unwrap();
            }
            requests
        });
        (Endpoint::parse_loopback(&addr.to_string()).unwrap(), handle)
    }

    #[test]
    fn fetches_run_with_pagination() {
        let (ep, server) = serve(vec![
            r#"{"data":{"runOrError":{"__typename":"Run","jobName":"pipeline_batch_nightly_job","status":"SUCCESS"}}}"#.into(),
            r#"{"data":{"logsForRun":{"__typename":"EventConnection","cursor":"c1","hasMore":true,"events":[{"__typename":"EngineEvent","message":"Started process for run (pid: 7)."}]}}}"#.into(),
            r#"{"data":{"logsForRun":{"__typename":"EventConnection","cursor":"c2","hasMore":false,"events":[{"__typename":"LogsCapturedEvent","fileKey":"abcdefgh","stepKeys":["s"],"pid":9}]}}}"#.into(),
        ]);
        let info = fetch_run(&ep, "0a1b2c3d-0000-4111-8222-123456789abc").unwrap();
        assert_eq!(info.job.as_deref(), Some("pipeline_batch_nightly_job"));
        assert_eq!(info.worker_pid, Some(7));
        assert_eq!(info.captures.len(), 1);
        let requests = server.join().unwrap();
        assert!(requests[2].contains(r#""cursor":"c1""#));
        // Only queries are sent: no mutation keyword anywhere.
        assert!(requests.iter().all(|r| !r.contains("mutation")));
    }

    #[test]
    fn finds_run_by_worker_pid() {
        let run = |job: &str| {
            format!(r#"{{"data":{{"runOrError":{{"__typename":"Run","jobName":"{job}","status":"SUCCESS"}}}}}}"#)
        };
        let logs = |pid: u32| {
            format!(
                r#"{{"data":{{"logsForRun":{{"__typename":"EventConnection","cursor":"c","hasMore":false,"events":[{{"__typename":"EngineEvent","message":"Started process for run (pid: {pid})."}}]}}}}}}"#
            )
        };
        let (ep, server) = serve(vec![
            r#"{"data":{"runsOrError":{"__typename":"Runs","results":[
                {"runId":"far","startTime":500.0},{"runId":"b","startTime":102.0},{"runId":"a","startTime":101.0},{"runId":"queued","startTime":null}]}}}"#
                .into(),
            run("job_a"),
            logs(5),
            run("job_b"),
            logs(7),
        ]);
        let (id, info) = find_run_by_worker(&ep, 7, 100.0, 150.0).unwrap().unwrap();
        assert_eq!((id.as_str(), info.job.as_deref()), ("b", Some("job_b")));
        let requests = server.join().unwrap();
        assert!(requests[0].contains("updatedAfter"));
        assert!(requests[1].contains(r#""runId":"a""#));

        let (ep, server) = serve(vec![
            r#"{"data":{"runsOrError":{"__typename":"Runs","results":[]}}}"#.into()
        ]);
        assert_eq!(find_run_by_worker(&ep, 7, 100.0, 150.0), Ok(None));
        server.join().unwrap();
    }

    #[test]
    fn not_found_and_errors() {
        let (ep, server) = serve(vec![
            r#"{"data":{"runOrError":{"__typename":"RunNotFoundError"}}}"#.into()
        ]);
        assert_eq!(fetch_run(&ep, "x"), Err(FetchError::NotFound));
        server.join().unwrap();

        let (ep, server) = serve(vec![r#"{"errors":[{"message":"boom"}]}"#.into()]);
        assert!(matches!(fetch_run(&ep, "x"), Err(FetchError::Retry(m)) if m.contains("boom")));
        server.join().unwrap();
    }
}
