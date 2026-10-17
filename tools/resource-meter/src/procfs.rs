//! Reading `/proc/<pid>/*` and classifying a process from its argument vector.
//!
//! Full command lines are never returned to callers: `classify` reduces them to a short
//! name plus, for Dagster's compute-log `tail` helper, the run id and log file key.

use std::fs;
use std::path::{Path, PathBuf};

/// Clock ticks per second used by `/proc/<pid>/stat` (USER_HZ, fixed at 100 on Linux).
pub const CLK_TCK: u64 = 100;

const MAX_NAME_LEN: usize = 40;

#[derive(Debug, Clone, PartialEq)]
pub struct Status {
    pub name: String,
    pub ppid: u32,
    /// PID inside the innermost PID namespace (the container), last field of `NSpid:`.
    pub ns_pid: Option<u32>,
    pub rss_kb: Option<u64>,
    pub hwm_kb: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Stat {
    pub ppid: u32,
    pub utime: u64,
    pub stime: u64,
    /// Start time in clock ticks after boot; identifies a PID across reuse.
    pub start_ticks: u64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Io {
    pub read_bytes: u64,
    pub write_bytes: u64,
}

fn kb_field(value: &str) -> Option<u64> {
    value.split_ascii_whitespace().next()?.parse().ok()
}

pub fn parse_status(text: &str) -> Option<Status> {
    let mut name = None;
    let mut ppid = None;
    let mut ns_pid = None;
    let mut rss_kb = None;
    let mut hwm_kb = None;
    for line in text.lines() {
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        match key {
            "Name" => name = Some(value.trim().to_string()),
            "PPid" => ppid = value.trim().parse().ok(),
            "NSpid" => ns_pid = value.split_ascii_whitespace().last().and_then(|v| v.parse().ok()),
            "VmRSS" => rss_kb = kb_field(value),
            "VmHWM" => hwm_kb = kb_field(value),
            _ => {}
        }
    }
    Some(Status {
        name: name?,
        ppid: ppid?,
        ns_pid,
        rss_kb,
        hwm_kb,
    })
}

/// Parses `/proc/<pid>/stat`; the command name may contain spaces and parentheses,
/// so fields are counted from the last `)`.
pub fn parse_stat(text: &str) -> Option<Stat> {
    let rest = &text[text.rfind(')')? + 1..];
    let f: Vec<&str> = rest.split_ascii_whitespace().collect();
    // f[0] is field 3 (state); field N is f[N - 3].
    Some(Stat {
        ppid: f.get(1)?.parse().ok()?,
        utime: f.get(11)?.parse().ok()?,
        stime: f.get(12)?.parse().ok()?,
        start_ticks: f.get(19)?.parse().ok()?,
    })
}

pub fn parse_io(text: &str) -> Option<Io> {
    let mut read_bytes = None;
    let mut write_bytes = None;
    for line in text.lines() {
        if let Some(v) = line.strip_prefix("read_bytes:") {
            read_bytes = v.trim().parse().ok();
        } else if let Some(v) = line.strip_prefix("write_bytes:") {
            write_bytes = v.trim().parse().ok();
        }
    }
    Some(Io {
        read_bytes: read_bytes?,
        write_bytes: write_bytes?,
    })
}

/// Boot time (`btime`) from `/proc/stat`, seconds since the epoch.
pub fn parse_btime(text: &str) -> Option<u64> {
    text.lines().find_map(|l| l.strip_prefix("btime ")?.trim().parse().ok())
}

pub fn split_cmdline(raw: &[u8]) -> Vec<String> {
    raw.split(|&b| b == 0)
        .filter(|a| !a.is_empty())
        .map(|a| String::from_utf8_lossy(a).into_owned())
        .collect()
}

/// What a process is, as far as its arguments tell.
#[derive(Debug, Clone, PartialEq)]
pub enum Kind {
    /// `dagster api grpc`: the code server that spawns run workers.
    DagsterGrpc,
    /// A `multiprocessing` spawn child (run worker or step, decided by its parent).
    MpFork,
    /// A dbt CLI invocation.
    Dbt,
    /// Dagster's compute-log `tail -F .../storage/<run_id>/compute_logs/<key>.out|err`.
    ComputeLogTail {
        run_id: String,
        file_key: String,
    },
    /// Other Dagster plumbing that only mirrors a step (log tailing, orphan watcher).
    Helper,
    Other,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Classified {
    pub kind: Kind,
    /// Short, path-free name; never the command line.
    pub name: String,
}

fn basename(path: &str) -> &str {
    path.rsplit('/').next().unwrap_or(path)
}

fn clean_name(raw: &str) -> String {
    raw.chars().filter(|c| !c.is_control()).take(MAX_NAME_LEN).collect()
}

/// Run id and file key from a compute-log path `.../storage/<uuid>/compute_logs/<key>.out|err`.
pub fn parse_compute_log_path(path: &str) -> Option<(String, String)> {
    let (_, after) = path.rsplit_once("/storage/")?;
    let (run_id, rest) = after.split_once("/compute_logs/")?;
    let key = rest.strip_suffix(".out").or_else(|| rest.strip_suffix(".err"))?;
    let uuid_ok = run_id.len() == 36
        && run_id.char_indices().all(|(i, c)| match i {
            8 | 13 | 18 | 23 => c == '-',
            _ => c.is_ascii_hexdigit() && !c.is_ascii_uppercase(),
        });
    let key_ok = !key.is_empty() && key.len() <= 32 && key.bytes().all(|b| b.is_ascii_lowercase());
    (uuid_ok && key_ok).then(|| (run_id.to_string(), key.to_string()))
}

fn dbt_name(sub: Option<&String>) -> String {
    match sub.map(|s| s.trim_start_matches('-')) {
        Some(s) if !s.is_empty() && s.len() <= 20 && s.bytes().all(|b| b.is_ascii_alphabetic() || b == b'-') => {
            format!("dbt {s}")
        }
        _ => "dbt".to_string(),
    }
}

/// Classifies a process from its argument vector; `comm` is used when there are no
/// arguments (kernel threads, zombies, a process between fork and exec).
pub fn classify(argv: &[String], comm: &str) -> Classified {
    let Some(first) = argv.first() else {
        return Classified {
            kind: Kind::Other,
            name: clean_name(comm),
        };
    };
    let program = basename(first);

    if argv.iter().any(|a| a == "--multiprocessing-fork") {
        return Classified {
            kind: Kind::MpFork,
            name: "mp-spawn".into(),
        };
    }
    if program == "tail" {
        let kind = argv
            .last()
            .and_then(|p| parse_compute_log_path(p))
            .map(|(run_id, file_key)| Kind::ComputeLogTail { run_id, file_key })
            .unwrap_or(Kind::Other);
        return Classified {
            kind,
            name: "tail".into(),
        };
    }
    if program == "dbt" {
        return Classified {
            kind: Kind::Dbt,
            name: dbt_name(argv.get(1)),
        };
    }
    if argv.windows(2).any(|w| w[0] == "api" && w[1] == "grpc") && argv.iter().any(|a| basename(a) == "dagster") {
        return Classified {
            kind: Kind::DagsterGrpc,
            name: "dagster api grpc".into(),
        };
    }

    if program.starts_with("python") {
        let mut i = 1;
        while i < argv.len() {
            let a = &argv[i];
            match a.as_str() {
                "-m" => {
                    let module = argv.get(i + 1).map(String::as_str).unwrap_or("python -m");
                    return Classified {
                        kind: Kind::Other,
                        name: clean_name(module),
                    };
                }
                "-c" => {
                    let code = argv.get(i + 1).map(String::as_str).unwrap_or("");
                    let name = if code.contains("resource_tracker") {
                        "mp-resource-tracker"
                    } else {
                        "python -c"
                    };
                    return Classified {
                        kind: Kind::Other,
                        name: name.into(),
                    };
                }
                _ if a.starts_with('-') => i += 1,
                _ => {
                    let script = basename(a);
                    if script == "dbt" {
                        return Classified {
                            kind: Kind::Dbt,
                            name: dbt_name(argv.get(i + 1)),
                        };
                    }
                    let kind = if script == "watch_orphans.py" {
                        Kind::Helper
                    } else {
                        Kind::Other
                    };
                    return Classified {
                        kind,
                        name: clean_name(script),
                    };
                }
            }
        }
        return Classified {
            kind: Kind::Other,
            name: clean_name(program),
        };
    }

    Classified {
        kind: Kind::Other,
        name: clean_name(program),
    }
}

/// Reader rooted at a `/proc` directory (a fixture tree in tests).
#[derive(Debug, Clone)]
pub struct ProcFs {
    root: PathBuf,
}

impl ProcFs {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    fn read(&self, pid: u32, file: &str) -> Option<String> {
        fs::read_to_string(self.root.join(pid.to_string()).join(file)).ok()
    }

    pub fn status(&self, pid: u32) -> Option<Status> {
        parse_status(&self.read(pid, "status")?)
    }

    pub fn stat(&self, pid: u32) -> Option<Stat> {
        parse_stat(&self.read(pid, "stat")?)
    }

    /// `None` when unreadable, which is normal for other users' processes without root.
    pub fn io(&self, pid: u32) -> Option<Io> {
        parse_io(&self.read(pid, "io")?)
    }

    pub fn argv(&self, pid: u32) -> Vec<String> {
        fs::read(self.root.join(pid.to_string()).join("cmdline"))
            .map(|raw| split_cmdline(&raw))
            .unwrap_or_default()
    }

    pub fn btime(&self) -> Option<u64> {
        parse_btime(&fs::read_to_string(self.root.join("stat")).ok()?)
    }

    pub fn self_status(&self) -> Option<Status> {
        parse_status(&fs::read_to_string(self.root.join("self/status")).ok()?)
    }

    pub fn self_stat(&self) -> Option<Stat> {
        parse_stat(&fs::read_to_string(self.root.join("self/stat")).ok()?)
    }

    pub fn self_io(&self) -> Option<Io> {
        parse_io(&fs::read_to_string(self.root.join("self/io")).ok()?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn argv(parts: &[&str]) -> Vec<String> {
        parts.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn status_fields() {
        let s = parse_status(
            "Name:\tpython3.10\nUmask:\t0022\nState:\tS (sleeping)\nPPid:\t42\nNSpid:\t2068600\t202\nVmHWM:\t  204800 kB\nVmRSS:\t  102400 kB\n",
        )
        .unwrap();
        assert_eq!(
            s,
            Status {
                name: "python3.10".into(),
                ppid: 42,
                ns_pid: Some(202),
                rss_kb: Some(102_400),
                hwm_kb: Some(204_800)
            }
        );
    }

    #[test]
    fn status_kernel_thread_has_no_memory() {
        let s = parse_status("Name:\tkworker/0:1\nPPid:\t2\nNSpid:\t17\n").unwrap();
        assert_eq!(s.rss_kb, None);
        assert_eq!(s.ns_pid, Some(17));
        assert!(parse_status("garbage").is_none());
    }

    #[test]
    fn stat_with_spaces_and_parens_in_comm() {
        let line = "1234 (weird ) name) S 77 1234 1234 0 -1 4194304 100 0 0 0 250 50 0 0 20 0 1 0 98765 1000 200 18446744073709551615";
        let s = parse_stat(line).unwrap();
        assert_eq!(
            s,
            Stat {
                ppid: 77,
                utime: 250,
                stime: 50,
                start_ticks: 98_765
            }
        );
        assert!(parse_stat("1 (x) S 1").is_none());
    }

    #[test]
    fn io_and_btime() {
        let io =
            parse_io("rchar: 5\nwchar: 6\nread_bytes: 4096\nwrite_bytes: 8192\ncancelled_write_bytes: 0\n").unwrap();
        assert_eq!(
            io,
            Io {
                read_bytes: 4096,
                write_bytes: 8192
            }
        );
        assert!(parse_io("rchar: 5\n").is_none());
        assert_eq!(
            parse_btime("cpu  1 2 3\nbtime 1791900000\nprocesses 9\n"),
            Some(1_791_900_000)
        );
    }

    #[test]
    fn cmdline_drops_trailing_nul() {
        assert_eq!(split_cmdline(b"tail\0-F\0/x\0"), argv(&["tail", "-F", "/x"]));
        assert!(split_cmdline(b"").is_empty());
    }

    #[test]
    fn compute_log_path() {
        let p = "/app/var/dagster_home/storage/0a1b2c3d-0000-4111-8222-123456789abc/compute_logs/nkhtzjiq.out";
        assert_eq!(
            parse_compute_log_path(p),
            Some(("0a1b2c3d-0000-4111-8222-123456789abc".into(), "nkhtzjiq".into()))
        );
        let err = p.replace(".out", ".err");
        assert!(parse_compute_log_path(&err).is_some());
        assert!(parse_compute_log_path("/storage/not-a-uuid/compute_logs/abc.out").is_none());
        assert!(parse_compute_log_path(&p.replace(".out", ".txt")).is_none());
        assert!(parse_compute_log_path(&p.replace("nkhtzjiq", "BAD1")).is_none());
    }

    #[test]
    fn classify_dagster_tree() {
        let fork = argv(&[
            "/usr/local/bin/python3.10",
            "-c",
            "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=5, pipe_handle=7)",
            "--multiprocessing-fork",
        ]);
        assert_eq!(classify(&fork, "python3.10").kind, Kind::MpFork);

        let grpc = argv(&[
            "/usr/local/bin/python3.10",
            "-m",
            "dagster",
            "api",
            "grpc",
            "--lazy-load-user-code",
        ]);
        assert_eq!(classify(&grpc, "python3.10").kind, Kind::DagsterGrpc);

        let web = argv(&["/usr/local/bin/python3.10", "-m", "dagster_webserver", "--port", "3001"]);
        assert_eq!(
            classify(&web, "python3.10"),
            Classified {
                kind: Kind::Other,
                name: "dagster_webserver".into()
            }
        );

        let tail = argv(&[
            "tail",
            "-F",
            "-c",
            "+0",
            "/app/var/dagster_home/storage/0a1b2c3d-0000-4111-8222-123456789abc/compute_logs/abcdefgh.err",
        ]);
        assert_eq!(
            classify(&tail, "tail").kind,
            Kind::ComputeLogTail {
                run_id: "0a1b2c3d-0000-4111-8222-123456789abc".into(),
                file_key: "abcdefgh".into()
            }
        );

        let orphans = argv(&[
            "/usr/local/bin/python3.10",
            "/usr/local/lib/python3.10/site-packages/dagster/_core/execution/scripts/watch_orphans.py",
            "1",
            "2",
        ]);
        assert_eq!(classify(&orphans, "python3.10").kind, Kind::Helper);
    }

    #[test]
    fn classify_dbt_never_keeps_selection() {
        let long_select = "model_a model_b ".repeat(500);
        let build = argv(&[
            "/usr/local/bin/python3.10",
            "/usr/local/bin/dbt",
            "build",
            "--select",
            &long_select,
        ]);
        assert_eq!(
            classify(&build, "dbt"),
            Classified {
                kind: Kind::Dbt,
                name: "dbt build".into()
            }
        );
        let version = argv(&["/usr/local/bin/python3.10", "/usr/local/bin/dbt", "--version"]);
        assert_eq!(classify(&version, "dbt").name, "dbt version");
        let direct = argv(&["/usr/local/bin/dbt", "parse", "--project-dir", "/app/transformation"]);
        assert_eq!(classify(&direct, "dbt").name, "dbt parse");
    }

    #[test]
    fn classify_names_are_short_and_path_free() {
        let script = argv(&[
            "/usr/local/bin/python3.10",
            "/app/scripts/provisioning/refresh_rolling.py",
        ]);
        assert_eq!(classify(&script, "python3.10").name, "refresh_rolling.py");
        let sh = argv(&["sh", "-c", "secret-looking command line with --password=x"]);
        assert_eq!(classify(&sh, "sh").name, "sh");
        let tracker = argv(&[
            "/usr/local/bin/python3.10",
            "-c",
            "from multiprocessing.resource_tracker import main;main(3)",
        ]);
        assert_eq!(classify(&tracker, "python3.10").name, "mp-resource-tracker");
        assert_eq!(classify(&[], "kthreadd").name, "kthreadd");
        let long = "x".repeat(200);
        assert!(classify(&[long], "x").name.len() <= MAX_NAME_LEN);
    }
}
