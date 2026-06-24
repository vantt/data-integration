# Phase 4 — format_helpers.py Migration

**Status:** Todo  
**Effort:** ~1h  
**Depends on:** Phase 1 (i18n.py), Phase 2 (locale files)

## Overview

Ba nơi trong `format_helpers.py` có hardcoded Vietnamese strings:
1. `_RELATIVE_THRESHOLDS` — time unit strings
2. `format_relative` — "vừa xong", "{n} {unit} trước"
3. `_VERDICT_WORD` — "Có lãi", "Lỗ", "Hòa vốn"

`_geo_region` trong `screen_customer_360.py` (Phase 6 handles).

## Changes

### 1. `format_relative` — locale-aware relative time

```python
# Before
_RELATIVE_THRESHOLDS = [
    (60, "giây", 1),
    (3600, "phút", 60),
    ...
]

def format_relative(iso_str: str | None) -> str:
    ...
    if delta < 5:
        return "vừa xong"
    for limit, unit, divisor in _RELATIVE_THRESHOLDS:
        if limit is None or delta < limit:
            n = delta // divisor
            return f"{n} {unit} trước"
```

```python
# After — _RELATIVE_THRESHOLDS stores i18n keys instead of unit words
_RELATIVE_THRESHOLDS = [
    (60,          "time.n_seconds_ago", 1),
    (3600,        "time.n_minutes_ago", 60),
    (86400,       "time.n_hours_ago",   3600),
    (86400 * 30,  "time.n_days_ago",    86400),
    (86400 * 365, "time.n_months_ago",  86400 * 30),
    (None,        "time.n_years_ago",   86400 * 365),
]

def format_relative(iso_str: str | None) -> str:
    """Return a localized relative time string (e.g. '2 giờ trước' / '2 hours ago')."""
    from adapters.inbound.web.i18n import t
    if not iso_str:
        return "—"
    dt = _parse_iso(iso_str)
    if dt is None:
        return iso_str
    delta = int((datetime.now(_UTC) - dt).total_seconds())
    if delta < 5:
        return t("time.just_now")
    for limit, key, divisor in _RELATIVE_THRESHOLDS:
        if limit is None or delta < limit:
            n = delta // divisor
            return t(key).format(n=n)
    return "—"
```

**Locale entries needed:**
```json
"time": {
  "just_now":       { "vi": "vừa xong",        "en": "just now"       },
  "n_seconds_ago":  { "vi": "{n} giây trước",   "en": "{n}s ago"       },
  "n_minutes_ago":  { "vi": "{n} phút trước",   "en": "{n}m ago"       },
  "n_hours_ago":    { "vi": "{n} giờ trước",    "en": "{n}h ago"       },
  "n_days_ago":     { "vi": "{n} ngày trước",   "en": "{n}d ago"       },
  "n_months_ago":   { "vi": "{n} tháng trước",  "en": "{n} months ago" },
  "n_years_ago":    { "vi": "{n} năm trước",    "en": "{n} years ago"  }
}
```

Note: EN uses compact notation for seconds/minutes/hours/days (`{n}s`, `{n}m`, `{n}h`, `{n}d`) — common in CRM UIs and avoids plural complexity.

### 2. `verdict_word` — locale-aware verdict labels

```python
# Before
_VERDICT_WORD: dict[str, str] = {
    "positive": "Có lãi",
    "negative": "Lỗ",
    "neutral":  "Hòa vốn",
}

def verdict_word(tone: str) -> str:
    return _VERDICT_WORD.get(tone or "", "—")
```

```python
# After
_VERDICT_KEYS: dict[str, str] = {
    "positive": "order.verdict.positive",
    "negative": "order.verdict.negative",
    "neutral":  "order.verdict.neutral",
}

def verdict_word(tone: str) -> str:
    from adapters.inbound.web.i18n import t
    key = _VERDICT_KEYS.get(tone or "")
    return t(key) if key else "—"
```

### 3. No changes needed for

- `format_vnd` / `fmt_vnd_signed` — "đ" currency symbol is language-neutral for this system (Vietnamese CRM, VND stays as đ in both languages)
- `recency_days_label` — returns "N d" (days abbreviation, universally understood)
- `days_since` — returns "626 d (1.7 y)" (compact, universally understood)
- `format_date_ict` / `format_datetime_ict` — DD/MM/YYYY format is fine for both languages in this context

## Verification

```python
# set_lang("vi") → format_relative("2024-01-01T00:00:00Z") → "N ngày trước"
# set_lang("en") → format_relative("2024-01-01T00:00:00Z") → "Nd ago"
# set_lang("vi") → verdict_word("positive") → "Có lãi"
# set_lang("en") → verdict_word("positive") → "Profitable"
```

## Notes

- Local imports inside functions avoid module-level circular dependency
- `_RELATIVE_THRESHOLDS` variable is renamed implicitly — existing callers (none outside this module) unaffected
- `_VERDICT_WORD` dict removed; `_VERDICT_KEYS` is private, same pattern
