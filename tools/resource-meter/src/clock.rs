//! Wall-clock helpers. Files are split by local calendar day using a fixed UTC offset
//! (Viet Nam has no daylight saving time), so no time-zone database is needed.

use std::time::{SystemTime, UNIX_EPOCH};

/// Seconds since the Unix epoch, with sub-second precision.
pub fn now_epoch() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// Day number (days since 1970-01-01) of the local calendar day containing `epoch`.
pub fn local_day(epoch: f64, utc_offset_hours: i32) -> i64 {
    (epoch.floor() as i64 + i64::from(utc_offset_hours) * 3600).div_euclid(86_400)
}

/// `YYYYMMDD` for a day number.
pub fn day_stamp(day: i64) -> String {
    let (y, m, d) = civil_from_days(day);
    format!("{y:04}{m:02}{d:02}")
}

/// Day number for a `YYYYMMDD` stamp; `None` when it is not a valid date.
pub fn parse_day_stamp(stamp: &str) -> Option<i64> {
    if stamp.len() != 8 || !stamp.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let y: i64 = stamp[0..4].parse().ok()?;
    let m: u32 = stamp[4..6].parse().ok()?;
    let d: u32 = stamp[6..8].parse().ok()?;
    if !(1..=12).contains(&m) || d == 0 || d > days_in_month(y, m) {
        return None;
    }
    Some(days_from_civil(y, m, d))
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

fn days_in_month(y: i64, m: u32) -> u32 {
    match m {
        2 if is_leap(y) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

// Proleptic Gregorian conversions (H. Hinnant, "chrono-Compatible Low-Level Date Algorithms").
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let y = yoe + era * 400 + i64::from(m <= 2);
    (y, m, d)
}

fn days_from_civil(y: i64, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = i64::from(if m > 2 { m - 3 } else { m + 9 });
    let doy = (153 * mp + 2) / 5 + i64::from(d) - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn epoch_day_round_trip() {
        assert_eq!(day_stamp(0), "19700101");
        assert_eq!(parse_day_stamp("19700101"), Some(0));
        for day in [-1000, 0, 11_016, 20_743, 20_744, 30_000] {
            assert_eq!(parse_day_stamp(&day_stamp(day)), Some(day));
        }
    }

    #[test]
    fn local_day_uses_offset() {
        // 2026-10-16T17:30:00Z is 2026-10-17 00:30 in UTC+7.
        let epoch = 1_792_171_800.0;
        assert_eq!(day_stamp(local_day(epoch, 0)), "20261016");
        assert_eq!(day_stamp(local_day(epoch, 7)), "20261017");
    }

    #[test]
    fn rejects_invalid_stamps() {
        for bad in ["2026101", "2026-10-1", "20261301", "20260230", "20250229", "abcdefgh"] {
            assert_eq!(parse_day_stamp(bad), None, "{bad}");
        }
        assert!(parse_day_stamp("20240229").is_some());
    }
}
