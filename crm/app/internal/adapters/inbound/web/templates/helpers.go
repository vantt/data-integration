// Package templates — pure-Go helpers called from templ files.
// Templ components can call normal Go functions defined in the same package.
package templates

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// queryEscapeHelper URL-encodes a string for safe use in query parameters.
func queryEscapeHelper(s string) string {
	return url.QueryEscape(s)
}

// itoa renders an int as a decimal string (for SVG width/height attributes).
func itoa(n int) string { return strconv.Itoa(n) }

// ict is loaded once; falls back to UTC+7 fixed offset.
var ict *time.Location

func init() {
	loc, err := time.LoadLocation("Asia/Ho_Chi_Minh")
	if err != nil {
		loc = time.FixedZone("ICT", 7*3600)
	}
	ict = loc
}

// formatVNDHelper formats an int64 VND amount with dot separators.
func formatVNDHelper(vnd int64) string {
	if vnd == 0 {
		return "—"
	}
	s := strconv.FormatInt(vnd, 10)
	n := len(s)
	var b strings.Builder
	for i, c := range s {
		if i > 0 && (n-i)%3 == 0 {
			b.WriteByte('.')
		}
		b.WriteRune(c)
	}
	return b.String() + "đ"
}

// formatICTHelper parses a UTC ISO-8601 string and returns "DD/MM/YYYY HH:MM ICT".
func formatICTHelper(utcISO string) string {
	if utcISO == "" {
		return "—"
	}
	layouts := []string{
		"2006-01-02T15:04:05.000Z",
		"2006-01-02T15:04:05Z",
		"2006-01-02T15:04:05",
		"2006-01-02",
	}
	var t time.Time
	var parsed bool
	for _, l := range layouts {
		if pt, err := time.Parse(l, utcISO); err == nil {
			t = pt
			parsed = true
			break
		}
	}
	if !parsed {
		return utcISO
	}
	t = t.In(ict)
	if strings.Contains(utcISO, "T") || strings.HasSuffix(utcISO, "Z") {
		return t.Format("02/01/2006 15:04 ICT")
	}
	return t.Format("02/01/2006")
}

// formatDateKeyHelper converts an ICT YYYYMMDD int to "DD/MM/YYYY".
func formatDateKeyHelper(dk int) string {
	if dk == 0 {
		return "—"
	}
	s := fmt.Sprintf("%08d", dk)
	return fmt.Sprintf("%s/%s/%s", s[6:8], s[4:6], s[0:4])
}

// actionTypeBadgeClassHelper returns the Precision chip tone modifier for an
// action type. Pair with the base class: class={ "chip " + ... }.
func actionTypeBadgeClassHelper(actionType string) string {
	switch strings.ToUpper(actionType) {
	case "CALL_NOW":
		return "chip--coral"
	case "WIN_BACK", "UPSELL", "CROSS_SELL":
		return "chip--amber"
	case "REORDER_NUDGE":
		return "chip--moss"
	default:
		return ""
	}
}

// valueGroupBadgeClassHelper returns the Precision badge tone modifier for a
// value group. Pair with the base class: class={ "bdg " + ... }.
func valueGroupBadgeClassHelper(vg string) string {
	switch strings.ToUpper(vg) {
	case "VIP", "GOLD":
		return "bdg--accent"
	case "NEW":
		return "bdg--good"
	default: // SILVER / BRONZE / unknown — neutral badge
		return ""
	}
}

// statusBadgeClassHelper returns the Precision badge tone modifier for a
// customer lifecycle status. Pair with the base class: class={ "bdg " + ... }.
func statusBadgeClassHelper(status string) string {
	switch status {
	case "active":
		return "bdg--good"
	case "at_risk":
		return "bdg--warn"
	case "churned":
		return "bdg--bad"
	default:
		return ""
	}
}

// taskStatusClassHelper returns the Precision badge tone modifier for a task
// status. Pair with the base class: class={ "bdg " + ... }.
func taskStatusClassHelper(status string) string {
	switch status {
	case "doing":
		return "bdg--warn"
	case "done":
		return "bdg--good"
	case "cancelled":
		return "bdg--bad"
	default: // open / unknown — neutral badge
		return ""
	}
}

// safeStr dereferences a *string, returning "" if nil.
func safeStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// truncStr truncates to max runes, appending "…" if needed.
func truncStr(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max]) + "…"
}
