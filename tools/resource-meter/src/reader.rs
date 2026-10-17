//! Reading the daily TSV files back (`.tsv` or `.tsv.gz`).

use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};

use flate2::read::GzDecoder;

use crate::clock::day_stamp;

/// Column positions from a header line.
#[derive(Debug, Default)]
pub struct Header {
    cols: HashMap<String, usize>,
}

impl Header {
    pub fn col(&self, name: &str) -> Result<usize, String> {
        self.cols
            .get(name)
            .copied()
            .ok_or_else(|| format!("column {name} missing"))
    }

    pub fn width(&self) -> usize {
        self.cols.len()
    }
}

/// Calls `f` for every well-formed line, one at a time (a day of containers is about
/// 120,000 lines, so nothing is kept unless `f` keeps it). Returns the number of lines
/// skipped because their cell count did not match the header (a line cut short by a crash,
/// for example). A truncated gzip stream or invalid UTF-8 ends the scan with what was read.
pub fn scan_reader(
    reader: impl BufRead,
    mut f: impl FnMut(&Header, &[&str]) -> Result<(), String>,
) -> Result<usize, String> {
    let mut lines = reader.lines();
    let header = match lines.next() {
        Some(h) => h.map_err(|e| e.to_string())?,
        None => return Ok(0),
    };
    let header = Header {
        cols: header
            .split('\t')
            .enumerate()
            .map(|(i, c)| (c.to_string(), i))
            .collect(),
    };
    let mut skipped = 0;
    for line in lines {
        let Ok(line) = line else {
            skipped += 1;
            break;
        };
        let cells: Vec<&str> = line.split('\t').collect();
        if cells.len() == header.width() {
            f(&header, &cells)?;
        } else if !line.is_empty() {
            skipped += 1;
        }
    }
    Ok(skipped)
}

/// The file of `kind` for `day`: the `.tsv` while the day is open, `.tsv.gz` afterwards.
pub fn file_for(dir: &Path, kind: &str, day: i64) -> Option<PathBuf> {
    let base = dir.join(format!("{kind}-{}.tsv", day_stamp(day)));
    if base.exists() {
        return Some(base);
    }
    let gz = dir.join(format!("{kind}-{}.tsv.gz", day_stamp(day)));
    gz.exists().then_some(gz)
}

/// Streams one day of one kind; an absent file has no lines.
pub fn scan(
    dir: &Path,
    kind: &str,
    day: i64,
    f: impl FnMut(&Header, &[&str]) -> Result<(), String>,
) -> Result<usize, String> {
    let Some(path) = file_for(dir, kind, day) else {
        return Ok(0);
    };
    let file = File::open(&path).map_err(|e| format!("open {}: {e}", path.display()))?;
    let reader: Box<dyn Read> = if path.extension().is_some_and(|e| e == "gz") {
        Box::new(GzDecoder::new(file))
    } else {
        Box::new(file)
    };
    scan_reader(BufReader::with_capacity(64 * 1024, reader), f).map_err(|e| format!("read {}: {e}", path.display()))
}

/// A small file (steps, models) loaded into memory.
#[derive(Debug, Default)]
pub struct Table {
    header: Header,
    pub rows: Vec<Vec<String>>,
    pub skipped: usize,
}

impl Table {
    pub fn parse(reader: impl BufRead) -> Result<Self, String> {
        let mut rows = Vec::new();
        let mut cols = None;
        let skipped = scan_reader(reader, |h, cells| {
            if cols.is_none() {
                cols = Some(h.cols.clone());
            }
            rows.push(cells.iter().map(|c| c.to_string()).collect());
            Ok(())
        })?;
        Ok(Self {
            header: Header {
                cols: cols.unwrap_or_default(),
            },
            rows,
            skipped,
        })
    }

    pub fn col(&self, name: &str) -> Result<usize, String> {
        self.header.col(name)
    }
}

/// Loads one day of one kind; an absent file is an empty table.
pub fn load(dir: &Path, kind: &str, day: i64) -> Result<Table, String> {
    let mut rows = Vec::new();
    let mut cols = None;
    let skipped = scan(dir, kind, day, |h, cells| {
        if cols.is_none() {
            cols = Some(h.cols.clone());
        }
        rows.push(cells.iter().map(|c| c.to_string()).collect());
        Ok(())
    })?;
    Ok(Table {
        header: Header {
            cols: cols.unwrap_or_default(),
        },
        rows,
        skipped,
    })
}

pub fn num(cell: &str) -> Option<f64> {
    if cell.is_empty() {
        None
    } else {
        cell.parse().ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::TempTree;
    use flate2::write::GzEncoder;
    use flate2::Compression;
    use std::io::Write;

    #[test]
    fn parses_and_skips_partial_lines() {
        let t = Table::parse("a\tb\n1\t2\n3\n\n4\t\n".as_bytes()).unwrap();
        assert_eq!(
            t.rows,
            vec![vec!["1".to_string(), "2".into()], vec!["4".into(), "".into()]]
        );
        assert_eq!(t.skipped, 1);
        assert_eq!(t.col("b"), Ok(1));
        assert!(t.col("c").is_err());
        assert!(Table::parse("".as_bytes()).unwrap().rows.is_empty());
    }

    #[test]
    fn loads_plain_then_gzip() {
        let t = TempTree::new();
        let day = 20_743;
        assert!(load(t.path(), "steps", day).unwrap().rows.is_empty());
        let mut enc = GzEncoder::new(Vec::new(), Compression::default());
        enc.write_all(b"x\n1\n2\n").unwrap();
        t.file("steps-20261017.tsv.gz", enc.finish().unwrap());
        assert_eq!(load(t.path(), "steps", day).unwrap().rows.len(), 2);
        t.file("steps-20261017.tsv", "x\n9\n");
        assert_eq!(load(t.path(), "steps", day).unwrap().rows, vec![vec!["9".to_string()]]);
    }

    #[test]
    fn numbers() {
        assert_eq!(num(""), None);
        assert_eq!(num("1.5"), Some(1.5));
        assert_eq!(num("x"), None);
    }
}
