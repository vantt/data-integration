//! Container-level readings from cgroup v2 scopes created by Docker's systemd driver
//! (`<cgroup root>/system.slice/docker-<64 hex id>.scope`).

use std::fs;
use std::path::{Path, PathBuf};

use crate::cgroup::{self, CpuStat, IoStat, MemoryEvents, MemoryStat, Pressure};

#[derive(Debug, Clone, PartialEq)]
pub struct Scope {
    pub id: String,
    pub dir: PathBuf,
}

impl Scope {
    pub fn short_id(&self) -> &str {
        &self.id[..12]
    }

    pub fn procs_file(&self) -> PathBuf {
        self.dir.join("cgroup.procs")
    }
}

fn is_container_id(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

/// Lists the Docker container scopes, sorted by id. An unreadable directory yields none.
pub fn list_scopes(cgroup_root: &Path) -> Vec<Scope> {
    let dir = cgroup_root.join("system.slice");
    let Ok(entries) = fs::read_dir(&dir) else {
        return Vec::new();
    };
    let mut out: Vec<Scope> = entries
        .filter_map(Result::ok)
        .filter_map(|e| {
            let name = e.file_name().into_string().ok()?;
            let id = name.strip_prefix("docker-")?.strip_suffix(".scope")?;
            is_container_id(id).then(|| Scope {
                id: id.to_string(),
                dir: e.path(),
            })
        })
        .collect();
    out.sort_by(|a, b| a.id.cmp(&b.id));
    out
}

/// Container name from Docker's own state file (`<docker root>/containers/<id>/config.v2.json`,
/// top-level `"Name": "/<name>"`). Needs root; `None` when unreadable. Only the name is kept.
pub fn container_name(docker_root: &Path, id: &str) -> Option<String> {
    let raw = fs::read(docker_root.join("containers").join(id).join("config.v2.json")).ok()?;
    let value: serde_json::Value = serde_json::from_slice(&raw).ok()?;
    let name = value.get("Name")?.as_str()?.trim_start_matches('/');
    let valid = !name.is_empty()
        && name.len() <= 128
        && name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'.' | b'-'));
    valid.then(|| name.to_string())
}

#[derive(Debug, Default, Clone, PartialEq)]
pub struct ContainerSample {
    pub mem_current: Option<u64>,
    pub mem_max: Option<u64>,
    pub mem: MemoryStat,
    pub events: MemoryEvents,
    pub cpu: CpuStat,
    pub io: Option<IoStat>,
    pub psi_mem: Pressure,
    pub psi_cpu: Pressure,
    pub psi_io: Pressure,
}

/// Reads one scope. Each file is optional: a missing file leaves its fields empty.
/// Returns `None` when the scope itself is gone (container stopped between scan and read).
pub fn read_sample(dir: &Path) -> Option<ContainerSample> {
    let read = |f: &str| fs::read_to_string(dir.join(f)).ok();
    let mem_current = cgroup::parse_single(&read("memory.current")?);
    Some(ContainerSample {
        mem_current,
        mem_max: read("memory.max").and_then(|t| cgroup::parse_single(&t)),
        mem: read("memory.stat")
            .map(|t| cgroup::parse_memory_stat(&t))
            .unwrap_or_default(),
        events: read("memory.events")
            .map(|t| cgroup::parse_memory_events(&t))
            .unwrap_or_default(),
        cpu: read("cpu.stat").map(|t| cgroup::parse_cpu_stat(&t)).unwrap_or_default(),
        io: read("io.stat").map(|t| cgroup::parse_io_stat(&t)),
        psi_mem: read("memory.pressure")
            .map(|t| cgroup::parse_pressure(&t))
            .unwrap_or_default(),
        psi_cpu: read("cpu.pressure")
            .map(|t| cgroup::parse_pressure(&t))
            .unwrap_or_default(),
        psi_io: read("io.pressure")
            .map(|t| cgroup::parse_pressure(&t))
            .unwrap_or_default(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::TempTree;

    const ID: &str = "c7ba6271e6e554ed72810197daa437be348f05af93a2c54385316e497a15c8de";

    #[test]
    fn lists_only_docker_scopes() {
        let t = TempTree::new();
        t.file(&format!("system.slice/docker-{ID}.scope/memory.current"), "1\n");
        t.file("system.slice/docker-short.scope/memory.current", "1\n");
        t.file("system.slice/ssh.service/memory.current", "1\n");
        let scopes = list_scopes(t.path());
        assert_eq!(scopes.len(), 1);
        assert_eq!(scopes[0].id, ID);
        assert_eq!(scopes[0].short_id(), "c7ba6271e6e5");
        assert!(list_scopes(&t.path().join("missing")).is_empty());
    }

    #[test]
    fn reads_full_sample() {
        let t = TempTree::new();
        let d = format!("system.slice/docker-{ID}.scope");
        t.file(&format!("{d}/memory.current"), "1000\n");
        t.file(&format!("{d}/memory.max"), "8589934592\n");
        t.file(&format!("{d}/memory.stat"), "anon 600\nfile 300\nkernel 90\nshmem 10\n");
        t.file(&format!("{d}/memory.events"), "low 0\nmax 5\noom 0\noom_kill 0\n");
        t.file(
            &format!("{d}/cpu.stat"),
            "usage_usec 77\nnr_throttled 2\nthrottled_usec 9\n",
        );
        t.file(&format!("{d}/io.stat"), "259:0 rbytes=4 wbytes=8 rios=1 wios=1\n");
        t.file(
            &format!("{d}/memory.pressure"),
            "some avg10=0.10 avg60=0 avg300=0 total=1\nfull avg10=0.05 avg60=0 avg300=0 total=1\n",
        );
        t.file(
            &format!("{d}/cpu.pressure"),
            "some avg10=1.50 avg60=0 avg300=0 total=1\n",
        );
        t.file(
            &format!("{d}/io.pressure"),
            "some avg10=0.00 avg60=0 avg300=0 total=1\n",
        );
        let s = read_sample(&t.path().join(&d)).unwrap();
        assert_eq!(s.mem_current, Some(1000));
        assert_eq!(s.mem_max, Some(8_589_934_592));
        assert_eq!(s.mem.anon, Some(600));
        assert_eq!(s.events.max, Some(5));
        assert_eq!(s.cpu.throttled_usec, Some(9));
        assert_eq!(s.io, Some(IoStat { rbytes: 4, wbytes: 8 }));
        assert_eq!(s.psi_mem.full_avg10, Some(0.05));
        assert_eq!(s.psi_cpu.some_avg10, Some(1.5));
    }

    #[test]
    fn missing_files_leave_fields_empty() {
        let t = TempTree::new();
        t.file("scope/memory.current", "5\n");
        t.file("scope/memory.max", "max\n");
        let s = read_sample(&t.path().join("scope")).unwrap();
        assert_eq!(s.mem_current, Some(5));
        assert_eq!(s.mem_max, None);
        assert_eq!(s.io, None);
        assert!(read_sample(&t.path().join("gone")).is_none());
    }

    #[test]
    fn container_name_from_docker_state() {
        let t = TempTree::new();
        t.file(
            &format!("containers/{ID}/config.v2.json"),
            r#"{"Config":{"Env":["SECRET=x"]},"HostConfig":{"RestartPolicy":{"Name":"always"}},"Name":"/data_platform"}"#,
        );
        assert_eq!(container_name(t.path(), ID).as_deref(), Some("data_platform"));
        assert_eq!(container_name(t.path(), "0000"), None);
        t.file("containers/bad/config.v2.json", r#"{"Name":"/x\ty"}"#);
        assert_eq!(container_name(t.path(), "bad"), None);
    }
}
