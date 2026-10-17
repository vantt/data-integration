//! Daily TSV files (`<kind>-YYYYMMDD.tsv`): append-only writing, then gzip of closed
//! days and deletion past the retention period.

use std::fmt::Write as _;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufWriter, Write};
use std::path::{Path, PathBuf};

use flate2::write::GzEncoder;
use flate2::Compression;

use crate::clock::{day_stamp, parse_day_stamp};

/// Builds one TSV line. Empty cells for missing values; tabs and newlines in text are
/// replaced so a value can never break the layout.
#[derive(Default)]
pub struct Row {
    line: String,
    cells: usize,
}

impl Row {
    pub fn new() -> Self {
        Self {
            line: String::with_capacity(256),
            cells: 0,
        }
    }

    fn sep(&mut self) {
        if self.cells > 0 {
            self.line.push('\t');
        }
        self.cells += 1;
    }

    pub fn text(mut self, v: &str) -> Self {
        self.sep();
        self.line
            .extend(v.chars().map(|c| if c.is_control() { ' ' } else { c }));
        self
    }

    pub fn opt_text(self, v: Option<&str>) -> Self {
        self.text(v.unwrap_or(""))
    }

    pub fn int(mut self, v: impl Into<Option<u64>>) -> Self {
        self.sep();
        if let Some(v) = v.into() {
            let _ = write!(self.line, "{v}");
        }
        self
    }

    pub fn signed(mut self, v: impl Into<Option<i64>>) -> Self {
        self.sep();
        if let Some(v) = v.into() {
            let _ = write!(self.line, "{v}");
        }
        self
    }

    /// Decimal with fixed precision; empty when `None` or not finite.
    pub fn dec(mut self, v: impl Into<Option<f64>>, places: usize) -> Self {
        self.sep();
        if let Some(v) = v.into().filter(|v| v.is_finite()) {
            let _ = write!(self.line, "{v:.places$}");
        }
        self
    }

    pub fn finish(mut self) -> String {
        self.line.push('\n');
        self.line
    }
}

/// Appends rows to the file of the row's day, writing the header when a file is new.
pub struct DailyWriter {
    dir: PathBuf,
    kind: &'static str,
    header: &'static str,
    day: Option<i64>,
    out: Option<BufWriter<File>>,
}

impl DailyWriter {
    pub fn new(dir: &Path, kind: &'static str, header: &'static str) -> Self {
        Self {
            dir: dir.to_path_buf(),
            kind,
            header,
            day: None,
            out: None,
        }
    }

    pub fn path_for(&self, day: i64) -> PathBuf {
        self.dir.join(format!("{}-{}.tsv", self.kind, day_stamp(day)))
    }

    pub fn write_row(&mut self, day: i64, line: &str) -> io::Result<()> {
        if self.day != Some(day) || self.out.is_none() {
            self.close()?;
            let path = self.path_for(day);
            let file = OpenOptions::new().create(true).append(true).open(&path)?;
            let mut out = BufWriter::new(file);
            if fs::metadata(&path)?.len() == 0 {
                out.write_all(self.header.as_bytes())?;
                out.write_all(b"\n")?;
            }
            self.out = Some(out);
            self.day = Some(day);
        }
        match self.out.as_mut() {
            Some(out) => out.write_all(line.as_bytes()),
            None => Err(io::Error::other("writer not open")),
        }
    }

    pub fn flush(&mut self) -> io::Result<()> {
        match self.out.as_mut() {
            Some(out) => out.flush(),
            None => Ok(()),
        }
    }

    pub fn close(&mut self) -> io::Result<()> {
        let result = self.flush();
        self.out = None;
        self.day = None;
        result
    }
}

#[derive(Debug, Default, PartialEq)]
pub struct Housekeeping {
    pub compressed: usize,
    pub deleted: usize,
    pub errors: Vec<String>,
}

/// `(kind, day, is_gz)` for names like `containers-20261017.tsv[.gz]`.
fn parse_file_name(name: &str) -> Option<(&str, i64, bool)> {
    let (stem, gz) = match name.strip_suffix(".tsv.gz") {
        Some(s) => (s, true),
        None => (name.strip_suffix(".tsv")?, false),
    };
    let (kind, stamp) = stem.rsplit_once('-')?;
    if kind.is_empty() || !kind.bytes().all(|b| b.is_ascii_lowercase()) {
        return None;
    }
    Some((kind, parse_day_stamp(stamp)?, gz))
}

/// Compresses every `.tsv` of a day before `today` and deletes files older than
/// `retention_days`. Other files in the directory are never touched. Writers must be
/// closed for past days before calling this.
pub fn housekeeping(dir: &Path, today: i64, retention_days: u32) -> Housekeeping {
    let mut report = Housekeeping::default();
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(e) => {
            report.errors.push(format!("list {}: {e}", dir.display()));
            return report;
        }
    };
    let oldest_kept = today - i64::from(retention_days);
    for entry in entries.filter_map(Result::ok) {
        let Ok(name) = entry.file_name().into_string() else {
            continue;
        };
        let Some((_, day, is_gz)) = parse_file_name(&name) else {
            continue;
        };
        let path = entry.path();
        if day < oldest_kept {
            match fs::remove_file(&path) {
                Ok(()) => report.deleted += 1,
                Err(e) => report.errors.push(format!("delete {name}: {e}")),
            }
        } else if !is_gz && day < today {
            match gzip_and_remove(&path) {
                Ok(()) => report.compressed += 1,
                Err(e) => report.errors.push(format!("compress {name}: {e}")),
            }
        }
    }
    report
}

/// Writes `<file>.gz` through a temporary name, then removes the original. An existing
/// `.gz` (left by an interrupted earlier run) is replaced.
fn gzip_and_remove(src: &Path) -> io::Result<()> {
    let mut gz_name = src.as_os_str().to_owned();
    gz_name.push(".gz");
    let dst = PathBuf::from(gz_name);
    let mut tmp_name = dst.as_os_str().to_owned();
    tmp_name.push(".tmp");
    let tmp = PathBuf::from(tmp_name);

    let result = (|| {
        let mut input = File::open(src)?;
        let mut enc = GzEncoder::new(BufWriter::new(File::create(&tmp)?), Compression::default());
        io::copy(&mut input, &mut enc)?;
        let file = enc.finish()?.into_inner().map_err(|e| e.into_error())?;
        file.sync_all()?;
        fs::rename(&tmp, &dst)?;
        fs::remove_file(src)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::TempTree;
    use flate2::read::GzDecoder;
    use std::io::Read;

    const DAY: i64 = 20_743; // 2026-10-17

    #[test]
    fn row_formatting() {
        let line = Row::new()
            .int(5u64)
            .text("a\tb\nc")
            .opt_text(None)
            .dec(1.23456, 3)
            .int(None)
            .dec(f64::NAN, 2)
            .finish();
        assert_eq!(line, "5\ta b c\t\t1.235\t\t\n");
        assert_eq!(Row::new().text("").int(7u64).finish(), "\t7\n");
        assert_eq!(Row::new().signed(-3i64).signed(None).finish(), "-3\t\n");
    }

    #[test]
    fn writes_header_once_and_appends() {
        let t = TempTree::new();
        let mut w = DailyWriter::new(t.path(), "containers", "ts\tcontainer");
        w.write_row(DAY, "1\ta\n").unwrap();
        w.close().unwrap();
        let mut w = DailyWriter::new(t.path(), "containers", "ts\tcontainer");
        w.write_row(DAY, "2\tb\n").unwrap();
        w.write_row(DAY + 1, "3\tc\n").unwrap();
        w.flush().unwrap();
        let today = fs::read_to_string(t.path().join("containers-20261017.tsv")).unwrap();
        assert_eq!(today, "ts\tcontainer\n1\ta\n2\tb\n");
        let next = fs::read_to_string(t.path().join("containers-20261018.tsv")).unwrap();
        assert_eq!(next, "ts\tcontainer\n3\tc\n");
    }

    #[test]
    fn housekeeping_compresses_and_expires() {
        let t = TempTree::new();
        t.file("containers-20261017.tsv", "today\n");
        t.file("containers-20261016.tsv", "yesterday\n");
        t.file("processes-20260720.tsv.gz", "old");
        t.file("processes-20260718.tsv.gz", "expired");
        t.file("processes-20260717.tsv", "expired too");
        t.file("containers-20261015.tsv.gz.tmp", "leftover");
        t.file("notes.txt", "keep");
        let r = housekeeping(t.path(), DAY, 90);
        assert_eq!(
            r,
            Housekeeping {
                compressed: 1,
                deleted: 2,
                errors: vec![]
            }
        );

        let mut text = String::new();
        GzDecoder::new(File::open(t.path().join("containers-20261016.tsv.gz")).unwrap())
            .read_to_string(&mut text)
            .unwrap();
        assert_eq!(text, "yesterday\n");
        assert!(!t.path().join("containers-20261016.tsv").exists());
        assert!(t.path().join("containers-20261017.tsv").exists());
        assert!(t.path().join("processes-20260720.tsv.gz").exists());
        assert!(!t.path().join("processes-20260718.tsv.gz").exists());
        assert!(!t.path().join("processes-20260717.tsv").exists());
        assert!(t.path().join("notes.txt").exists());
    }

    #[test]
    fn housekeeping_replaces_partial_gz() {
        let t = TempTree::new();
        t.file("steps-20261016.tsv", "full content\n");
        t.file("steps-20261016.tsv.gz", "truncated");
        let r = housekeeping(t.path(), DAY, 90);
        assert_eq!(r.compressed, 1);
        let mut text = String::new();
        GzDecoder::new(File::open(t.path().join("steps-20261016.tsv.gz")).unwrap())
            .read_to_string(&mut text)
            .unwrap();
        assert_eq!(text, "full content\n");
    }

    #[test]
    fn file_name_parsing() {
        assert_eq!(
            parse_file_name("containers-20261017.tsv"),
            Some(("containers", DAY, false))
        );
        assert_eq!(parse_file_name("models-20261017.tsv.gz"), Some(("models", DAY, true)));
        assert_eq!(parse_file_name("models-2026101.tsv"), None);
        assert_eq!(parse_file_name("Models-20261017.tsv"), None);
        assert_eq!(parse_file_name("models-20261017.csv"), None);
    }
}
