//! Fixture directories for tests (no external crates).

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// A temporary directory removed on drop.
pub struct TempTree {
    root: PathBuf,
}

impl TempTree {
    pub fn new() -> Self {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let root = std::env::temp_dir().join(format!("resource-meter-test-{}-{n}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).expect("create temp dir");
        Self { root }
    }

    pub fn path(&self) -> &Path {
        &self.root
    }

    /// Writes `content` at `rel`, creating parent directories.
    pub fn file(&self, rel: &str, content: impl AsRef<[u8]>) {
        let path = self.root.join(rel);
        fs::create_dir_all(path.parent().expect("parent")).expect("create parent");
        fs::write(path, content).expect("write fixture");
    }

    pub fn remove(&self, rel: &str) {
        let _ = fs::remove_dir_all(self.root.join(rel));
    }
}

impl Drop for TempTree {
    fn drop(&mut self) {
        if !self.root.as_os_str().is_empty() {
            let _ = fs::remove_dir_all(&self.root);
        }
    }
}

/// Writes a fake `/proc/<pid>` with `status`, `stat`, `cmdline` and optionally `io`.
#[allow(clippy::too_many_arguments)]
pub fn fake_proc(
    t: &TempTree,
    pid: u32,
    ppid: u32,
    ns_pid: u32,
    comm: &str,
    argv: &[&str],
    start_ticks: u64,
    rss_kb: u64,
    cpu_ticks: u64,
    io: Option<(u64, u64)>,
) {
    t.file(
        &format!("{pid}/status"),
        format!(
            "Name:\t{comm}\nPPid:\t{ppid}\nNSpid:\t{pid}\t{ns_pid}\nVmHWM:\t{} kB\nVmRSS:\t{rss_kb} kB\n",
            rss_kb + 100
        ),
    );
    t.file(
        &format!("{pid}/stat"),
        format!("{pid} ({comm}) S {ppid} 1 1 0 -1 0 0 0 0 0 {cpu_ticks} 0 0 0 20 0 1 0 {start_ticks} 0 0"),
    );
    let mut cmd = argv.join("\0");
    cmd.push('\0');
    t.file(&format!("{pid}/cmdline"), cmd);
    if let Some((r, w)) = io {
        t.file(
            &format!("{pid}/io"),
            format!("rchar: 1\nwchar: 1\nread_bytes: {r}\nwrite_bytes: {w}\n"),
        );
    }
}

impl TempTree {
    /// A view of a subdirectory, sharing the parent's lifetime (not removed on its own).
    pub fn sub(parent: &TempTree, rel: &str) -> SubTree {
        let root = parent.root.join(rel);
        fs::create_dir_all(&root).expect("create sub dir");
        SubTree(TempTree { root })
    }
}

/// Subdirectory of a [`TempTree`]; dropping it does not delete anything.
pub struct SubTree(TempTree);

impl std::ops::Deref for SubTree {
    type Target = TempTree;
    fn deref(&self) -> &TempTree {
        &self.0
    }
}

impl Drop for SubTree {
    fn drop(&mut self) {
        // Leave the files to the parent tree; replace the root so the inner drop is a no-op.
        self.0.root = PathBuf::new();
    }
}
