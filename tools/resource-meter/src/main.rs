use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Duration;

use resource_meter::collector::{self, Config};

const USAGE: &str = "\
usage: resource-meter run [options]

Samples cgroup v2 and /proc (read-only) and appends daily TSV files.

options:
  --out-dir DIR           output directory (default /var/lib/resource-meter)
  --track NAMES           comma-separated container names (or 12+ char id prefixes)
                          whose processes are tracked (default data_platform)
  --duration SECS         stop after SECS seconds (default: run until killed)
  --retention-days N      delete files older than N days (default 90)
  --utc-offset-hours H    offset of the local day used to split files (default 7)
  --rss-threshold-mb N    also record non-Dagster processes whose RSS reached N MiB (default 256)
  --cgroup-root DIR       (default /sys/fs/cgroup)
  --proc-root DIR         (default /proc)
  --docker-root DIR       read only for container names (default /var/lib/docker)
";

fn parse_run(args: &[String]) -> Result<Config, String> {
    let mut cfg = Config {
        out_dir: PathBuf::from("/var/lib/resource-meter"),
        cgroup_root: PathBuf::from("/sys/fs/cgroup"),
        proc_root: PathBuf::from("/proc"),
        docker_root: PathBuf::from("/var/lib/docker"),
        track: vec!["data_platform".to_string()],
        duration: None,
        retention_days: 90,
        utc_offset_hours: 7,
        rss_threshold_kb: 256 * 1024,
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
            other => return Err(format!("unknown option {other}")),
        }
    }
    Ok(cfg)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("run") => match parse_run(&args[1..]).and_then(collector::run) {
            Ok(()) => ExitCode::SUCCESS,
            Err(e) => {
                eprintln!("resource-meter: {e}");
                ExitCode::FAILURE
            }
        },
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
