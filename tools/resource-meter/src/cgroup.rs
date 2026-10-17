//! Parsers for cgroup v2 interface files. Every parser is total: unknown or malformed
//! lines are skipped, and missing keys stay `None`.

/// Selected keys of `memory.stat` (bytes).
#[derive(Debug, Default, Clone, PartialEq)]
pub struct MemoryStat {
    pub anon: Option<u64>,
    pub file: Option<u64>,
    pub kernel: Option<u64>,
    pub shmem: Option<u64>,
}

/// Selected counters of `memory.events`.
#[derive(Debug, Default, Clone, PartialEq)]
pub struct MemoryEvents {
    pub max: Option<u64>,
    pub oom: Option<u64>,
    pub oom_kill: Option<u64>,
}

/// Selected counters of `cpu.stat`.
#[derive(Debug, Default, Clone, PartialEq)]
pub struct CpuStat {
    pub usage_usec: Option<u64>,
    pub throttled_usec: Option<u64>,
    pub nr_throttled: Option<u64>,
}

/// `io.stat` summed over every device.
#[derive(Debug, Default, Clone, PartialEq)]
pub struct IoStat {
    pub rbytes: u64,
    pub wbytes: u64,
}

/// `avg10` of the `some` and `full` lines of a `*.pressure` file (percent).
#[derive(Debug, Default, Clone, PartialEq)]
pub struct Pressure {
    pub some_avg10: Option<f64>,
    pub full_avg10: Option<f64>,
}

fn key_values(text: &str) -> impl Iterator<Item = (&str, u64)> {
    text.lines().filter_map(|line| {
        let mut it = line.split_ascii_whitespace();
        let key = it.next()?;
        let value = it.next()?.parse().ok()?;
        Some((key, value))
    })
}

pub fn parse_memory_stat(text: &str) -> MemoryStat {
    let mut out = MemoryStat::default();
    for (key, value) in key_values(text) {
        match key {
            "anon" => out.anon = Some(value),
            "file" => out.file = Some(value),
            "kernel" => out.kernel = Some(value),
            "shmem" => out.shmem = Some(value),
            _ => {}
        }
    }
    out
}

pub fn parse_memory_events(text: &str) -> MemoryEvents {
    let mut out = MemoryEvents::default();
    for (key, value) in key_values(text) {
        match key {
            "max" => out.max = Some(value),
            "oom" => out.oom = Some(value),
            "oom_kill" => out.oom_kill = Some(value),
            _ => {}
        }
    }
    out
}

pub fn parse_cpu_stat(text: &str) -> CpuStat {
    let mut out = CpuStat::default();
    for (key, value) in key_values(text) {
        match key {
            "usage_usec" => out.usage_usec = Some(value),
            "throttled_usec" => out.throttled_usec = Some(value),
            "nr_throttled" => out.nr_throttled = Some(value),
            _ => {}
        }
    }
    out
}

/// Sums `rbytes=`/`wbytes=` over every device line (`MAJ:MIN rbytes=.. wbytes=.. ...`).
pub fn parse_io_stat(text: &str) -> IoStat {
    let mut out = IoStat::default();
    for field in text.split_ascii_whitespace() {
        if let Some(v) = field.strip_prefix("rbytes=") {
            out.rbytes = out.rbytes.saturating_add(v.parse().unwrap_or(0));
        } else if let Some(v) = field.strip_prefix("wbytes=") {
            out.wbytes = out.wbytes.saturating_add(v.parse().unwrap_or(0));
        }
    }
    out
}

pub fn parse_pressure(text: &str) -> Pressure {
    let mut out = Pressure::default();
    for line in text.lines() {
        let mut it = line.split_ascii_whitespace();
        let kind = it.next();
        let avg10 = it
            .find_map(|f| f.strip_prefix("avg10="))
            .and_then(|v| v.parse::<f64>().ok());
        match kind {
            Some("some") => out.some_avg10 = avg10,
            Some("full") => out.full_avg10 = avg10,
            _ => {}
        }
    }
    out
}

/// A single-number file such as `memory.current`; `max` (no limit) is `None`.
pub fn parse_single(text: &str) -> Option<u64> {
    text.trim().parse().ok()
}

/// PIDs listed in `cgroup.procs`.
pub fn parse_procs(text: &str) -> Vec<u32> {
    text.lines().filter_map(|l| l.trim().parse().ok()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_stat_selected_keys() {
        let s = parse_memory_stat("anon 100\nfile 200\nkernel_stack 7\nkernel 30\nshmem 4\nfile_mapped 9\n");
        assert_eq!(
            s,
            MemoryStat {
                anon: Some(100),
                file: Some(200),
                kernel: Some(30),
                shmem: Some(4)
            }
        );
    }

    #[test]
    fn memory_events_and_garbage() {
        let e = parse_memory_events("low 0\nhigh 0\nmax 61\noom 0\noom_kill 2\nbroken\noom_group_kill x\n");
        assert_eq!(
            e,
            MemoryEvents {
                max: Some(61),
                oom: Some(0),
                oom_kill: Some(2)
            }
        );
    }

    #[test]
    fn cpu_stat_counters() {
        let c = parse_cpu_stat("usage_usec 500\nuser_usec 400\nnr_periods 9\nnr_throttled 3\nthrottled_usec 77\n");
        assert_eq!(
            c,
            CpuStat {
                usage_usec: Some(500),
                throttled_usec: Some(77),
                nr_throttled: Some(3)
            }
        );
    }

    #[test]
    fn io_stat_sums_devices() {
        let io = parse_io_stat(
            "259:0 rbytes=10 wbytes=20 rios=1 wios=2 dbytes=0 dios=0\n8:0 rbytes=5 wbytes=1 rios=1 wios=1\n",
        );
        assert_eq!(io, IoStat { rbytes: 15, wbytes: 21 });
        assert_eq!(parse_io_stat(""), IoStat::default());
    }

    #[test]
    fn pressure_some_and_full() {
        let p = parse_pressure(
            "some avg10=1.25 avg60=0.87 avg300=1.20 total=27\nfull avg10=0.50 avg60=0.85 avg300=1.16 total=26\n",
        );
        assert_eq!(
            p,
            Pressure {
                some_avg10: Some(1.25),
                full_avg10: Some(0.5)
            }
        );
        let cpu_only_some = parse_pressure("some avg10=0.01 avg60=0 avg300=0 total=1\n");
        assert_eq!(cpu_only_some.full_avg10, None);
    }

    #[test]
    fn single_and_procs() {
        assert_eq!(parse_single("8589934592\n"), Some(8_589_934_592));
        assert_eq!(parse_single("max\n"), None);
        assert_eq!(parse_procs("1\n22\n\nx\n333\n"), vec![1, 22, 333]);
    }
}
