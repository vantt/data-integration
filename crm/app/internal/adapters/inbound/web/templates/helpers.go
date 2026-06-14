// Package templates — pure-Go helpers called from templ files.
// Templ components can call normal Go functions defined in the same package.
package templates

import (
	"fmt"
	"strconv"
	"strings"
	"time"
)

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

// actionTypeBadgeClassHelper returns a CSS badge class for the action type.
func actionTypeBadgeClassHelper(actionType string) string {
	switch strings.ToUpper(actionType) {
	case "CALL_NOW":
		return "badge-action-call"
	case "WIN_BACK":
		return "badge-action-win"
	case "REORDER_NUDGE":
		return "badge-action-reorder"
	case "UPSELL", "CROSS_SELL":
		return "badge-action-upsell"
	default:
		return "badge-action-default"
	}
}

// valueGroupBadgeClassHelper returns a CSS badge class for a value group.
func valueGroupBadgeClassHelper(vg string) string {
	switch strings.ToUpper(vg) {
	case "VIP":
		return "badge-vip"
	case "GOLD":
		return "badge-gold"
	case "SILVER":
		return "badge-silver"
	case "BRONZE":
		return "badge-bronze"
	default:
		return "badge-new"
	}
}

// statusBadgeClassHelper returns a CSS badge class for customer status.
func statusBadgeClassHelper(status string) string {
	switch status {
	case "active":
		return "badge-active"
	case "at_risk":
		return "badge-at-risk"
	case "churned":
		return "badge-churned"
	default:
		return "badge-silver"
	}
}

// taskStatusClassHelper returns a CSS class for a task status string.
func taskStatusClassHelper(status string) string {
	switch status {
	case "open":
		return "status-open"
	case "doing":
		return "status-doing"
	case "done":
		return "status-done"
	case "cancelled":
		return "status-cancelled"
	default:
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
