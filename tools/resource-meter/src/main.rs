use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Duration;

use resource_meter::clock::{local_day, now_epoch};
use resource_meter::collector::{self, Config};
use resource_meter::http::Endpoint;
use resource_meter::report;

const DEFAULT_GRAPHQL: &str = "127.0.0.1:3000";
/// Host path of the production checkout's dbt target directory (bind-mounted into data_platform).
const DEFAULT_DBT_TARGET_DIR: &str = "/home/vantt/app/fg-dataware-house/transformation/target";

const DEFAULT_DIR: &str = "/var/lib/resource-meter";

const USAGE: &str = "\
usage:
  resource-meter run [options]
  resource-meter report [--date YYYY-MM-DD] [--container NAME] [--job NAME] [--top N] [--dir DIR]
  resource-meter compare --base YYYY-MM-DD [--date YYYY-MM-DD] [--job NAME] [--top N]
                         [--threshold-pct P] [--dir DIR]
  resource-meter status [--dir DIR]

run: samples cgroup v2 and /proc (read-only) and appends daily TSV files.
report: per-container, heaviest Dagster steps and dbt models of one day (default today).
compare: steps and models heavier on --date (default today) than on --base, by more than
  --threshold-pct (default 10) in time, peak RSS or CPU seconds (medians per run).
status: whether the meter runs, its own cost, and its data directory.
Common: --dir (default /var/lib/resource-meter), --utc-offset-hours (default 7), --top (default 15).

run options:
  --out-dir DIR           output directory (default /var/lib/resource-meter)
  --track NAMES           comma-separated container names (or 12+ char id prefixes)
                          whose processes are tracked (default data_platform)
  --duration SECS         stop after SECS seconds (default: run until killed)
  --retention-days N      delete files older than N days (default 90)
  --utc-offset-hours H    offset of the local day used to split files (default 7)
  --rss-threshold-mb N    also record non-Dagster processes whose RSS reached N MiB (default 256)
  --dagster-graphql ADDR  read-only Dagster GraphQL: loopback IP:PORT[/path], or \"off\"
                          (default 127.0.0.1:3000)
  --dbt-target-dir DIR    host path of the dbt target directory, or \"off\"
                          (default /home/vantt/app/fg-dataware-house/transformation/target)
  --cgroup-root DIR       (default /sys/fs/cgroup)
  --proc-root DIR         (default /proc)
  --docker-root DIR       read only for container names (default /var/lib/docker)
";

fn parse_run(args: &[String]) -> Result<Config, String> {
    let mut cfg = Config {
        out_dir: PathBuf::from(DEFAULT_DIR),
        cgroup_root: PathBuf::from("/sys/fs/cgroup"),
        proc_root: PathBuf::from("/proc"),
        docker_root: PathBuf::from("/var/lib/docker"),
        track: vec!["data_platform".to_string()],
        duration: None,
        retention_days: 90,
        utc_offset_hours: 7,
        rss_threshold_kb: 256 * 1024,
        graphql: Some(Endpoint::parse_loopback(DEFAULT_GRAPHQL)?),
        dbt_target_dir: Some(PathBuf::from(DEFAULT_DBT_TARGET_DIR)),
    };
    let mut it = args.iter();
    while let Some(flag) = it.next() {
        let mut value = || it.next().cloned().ok_or_else(|| format!("{flag} needs a value"));
        match flag.as_str() {
            "--out-dir" => cfg.out_dir = PathBuf::from(value()?),
            "--cgroup-root" => cfg.cgroup_root = PathBuf::from(value()?),
            "--proc-root" => cfg.proc_root = PathBuf::from(value()?),
            "--docker-root" => cfg.docker_root = PathBuf::from(value()?),
            "--track" => {
                let v = value()?;
                cfg.track = v
                    .split(',')
                    .map(str::trim)
                    .filter(|s| !s.is_empty())
                    .map(String::from)
                    .collect();
            }
            "--duration" => {
                let secs: u64 = value()?
                    .parse()
                    .map_err(|_| "--duration must be whole seconds".to_string())?;
                if secs == 0 {
                    return Err("--duration must be > 0".into());
                }
                cfg.duration = Some(Duration::from_secs(secs));
            }
            "--retention-days" => {
                cfg.retention_days = value()?
                    .parse()
                    .map_err(|_| "--retention-days must be a number".to_string())?;
                if cfg.retention_days == 0 {
                    return Err("--retention-days must be > 0".into());
                }
            }
            "--utc-offset-hours" => {
                cfg.utc_offset_hours = value()?
                    .parse()
                    .map_err(|_| "--utc-offset-hours must be an integer".to_string())?;
                if !(-12..=14).contains(&cfg.utc_offset_hours) {
                    return Err("--utc-offset-hours must be between -12 and 14".into());
                }
            }
            "--rss-threshold-mb" => {
                let mb: u64 = value()?
                    .parse()
                    .map_err(|_| "--rss-threshold-mb must be a number".to_string())?;
                cfg.rss_threshold_kb = mb.saturating_mul(1024);
            }
            "--dagster-graphql" => {
                let v = value()?;
                cfg.graphql = if v == "off" {
                    None
                } else {
                    Some(Endpoint::parse_loopback(&v)?)
                };
            }
            "--dbt-target-dir" => {
                let v = value()?;
                cfg.dbt_target_dir = if v == "off" { None } else { Some(PathBuf::from(v)) };
            }
            other => return Err(format!("unknown option {other}")),
        }
    }
    Ok(cfg)
}

/// Options shared by `report`, `compare` and `status`.
struct ViewArgs {
    dir: PathBuf,
    date: Option<i64>,
    base: Option<i64>,
    container: Option<String>,
    job: Option<String>,
    top: usize,
    threshold_pct: f64,
    utc_offset_hours: i32,
}

fn parse_view(args: &[String], allowed: &[&str]) -> Result<ViewArgs, String> {
    let mut v = ViewArgs {
        dir: PathBuf::from(DEFAULT_DIR),
        date: None,
        base: None,
        container: None,
        job: None,
        top: 15,
        threshold_pct: 10.0,
        utc_offset_hours: 7,
    };
    let mut it = args.iter();
    while let Some(flag) = it.next() {
        if !allowed.contains(&flag.as_str()) && !matches!(flag.as_str(), "--dir" | "--utc-offset-hours") {
            return Err(format!("unknown option {flag}"));
        }
        let value = it.next().cloned().ok_or_else(|| format!("{flag} needs a value"))?;
        match flag.as_str() {
            "--dir" => v.dir = PathBuf::from(value),
            "--date" => v.date = Some(report::parse_date(&value)?),
            "--base" => v.base = Some(report::parse_date(&value)?),
            "--container" => v.container = Some(value),
            "--job" => v.job = Some(value),
            "--top" => {
                v.top = value.parse().map_err(|_| "--top must be a number".to_string())?;
                if v.top == 0 {
                    return Err("--top must be > 0".into());
                }
            }
            "--threshold-pct" => {
                v.threshold_pct = value
                    .parse()
                    .map_err(|_| "--threshold-pct must be a number".to_string())?;
                if !(v.threshold_pct >= 0.0 && v.threshold_pct.is_finite()) {
                    return Err("--threshold-pct must be >= 0".into());
                }
            }
            "--utc-offset-hours" => {
                v.utc_offset_hours = value
                    .parse()
                    .map_err(|_| "--utc-offset-hours must be an integer".to_string())?;
                if !(-12..=14).contains(&v.utc_offset_hours) {
                    return Err("--utc-offset-hours must be between -12 and 14".into());
                }
            }
            _ => unreachable!("flag checked against the allowed list"),
        }
    }
    Ok(v)
}

fn today(offset: i32) -> i64 {
    local_day(now_epoch(), offset)
}

fn print_result(result: Result<String, String>) -> ExitCode {
    match result {
        Ok(text) => {
            print!("{text}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("resource-meter: {e}");
            ExitCode::FAILURE
        }
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let rest = args.get(1..).unwrap_or(&[]);
    match args.first().map(String::as_str) {
        Some("run") => match parse_run(rest).and_then(collector::run) {
            Ok(()) => ExitCode::SUCCESS,
            Err(e) => {
                eprintln!("resource-meter: {e}");
                ExitCode::FAILURE
            }
        },
        Some("report") => print_result(
            parse_view(rest, &["--date", "--container", "--job", "--top"]).and_then(|v| {
                report::report(&report::ReportOptions {
                    day: v.date.unwrap_or_else(|| today(v.utc_offset_hours)),
                    dir: v.dir,
                    container: v.container,
                    job: v.job,
                    top: v.top,
                })
            }),
        ),
        Some("compare") => print_result(
            parse_view(rest, &["--base", "--date", "--job", "--top", "--threshold-pct"]).and_then(|v| {
                let base = v.base.ok_or("compare needs --base YYYY-MM-DD")?;
                report::compare(&report::CompareOptions {
                    day: v.date.unwrap_or_else(|| today(v.utc_offset_hours)),
                    base,
                    dir: v.dir,
                    job: v.job,
                    top: v.top,
                    threshold_pct: v.threshold_pct,
                })
            }),
        ),
        Some("status") => {
            let result = parse_view(rest, &[]).and_then(|v| {
                report::status(&report::StatusOptions {
                    dir: v.dir,
                    cgroup_root: PathBuf::from("/sys/fs/cgroup"),
                    proc_root: PathBuf::from("/proc"),
                    now: now_epoch(),
                    utc_offset_hours: v.utc_offset_hours,
                })
            });
            match result {
                Ok((text, running)) => {
                    print!("{text}");
                    if running {
                        ExitCode::SUCCESS
                    } else {
                        ExitCode::from(3)
                    }
                }
                Err(e) => {
                    eprintln!("resource-meter: {e}");
                    ExitCode::FAILURE
                }
            }
        }
        Some("-h" | "--help" | "help") => {
            print!("{USAGE}");
            ExitCode::SUCCESS
        }
        _ => {
            eprint!("{USAGE}");
            ExitCode::from(2)
        }
    }
}
