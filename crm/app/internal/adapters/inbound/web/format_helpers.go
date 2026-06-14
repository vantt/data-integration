// Package web — formatting helpers for templates.
// VND money, ICT timestamps, action-type badges — no business logic here.
package web

import (
	"fmt"
	"strconv"
	"strings"
	"time"
)

// ict is the Asia/Ho_Chi_Minh timezone loaded once at startup.
// Falls back to UTC+7 fixed offset if the timezone database is unavailable.
var ict *time.Location

func init() {
	loc, err := time.LoadLocation("Asia/Ho_Chi_Minh")
	if err != nil {
		loc = time.FixedZone("ICT", 7*3600)
	}
	ict = loc
}

// FormatVND formats an integer VND amount as "1.200.000đ" (dot thousands separator).
func FormatVND(vnd int64) string {
	if vnd == 0 {
		return "—"
	}
	s := strconv.FormatInt(vnd, 10)
	// Insert dot separators every 3 digits from the right.
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

// FormatICT parses a UTC ISO-8601 string and returns "DD/MM/YYYY HH:MM ICT".
// Returns the raw string unchanged if parsing fails.
func FormatICT(utcISO string) string {
	if utcISO == "" {
		return "—"
	}
	// Try common layouts used in the domain layer.
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
	if strings.HasSuffix(utcISO, "Z") || strings.Contains(utcISO, "T") {
		return t.Format("02/01/2006 15:04 ICT")
	}
	return t.Format("02/01/2006")
}

// FormatDateKey converts an ICT YYYYMMDD integer to "DD/MM/YYYY".
func FormatDateKey(dk int) string {
	if dk == 0 {
		return "—"
	}
	s := strconv.Itoa(dk)
	if len(s) != 8 {
		return s
	}
	return fmt.Sprintf("%s/%s/%s", s[6:8], s[4:6], s[0:4])
}

// ActionTypeBadgeClass returns the CSS class for an action_type badge.
func ActionTypeBadgeClass(actionType string) string {
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

// ValueGroupBadgeClass returns the CSS class for a value_group badge.
func ValueGroupBadgeClass(vg string) string {
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

// StatusBadgeClass returns a CSS class for customer_status.
func StatusBadgeClass(status string) string {
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

// TaskStatusClass returns a CSS class for a task status.
func TaskStatusClass(status string) string {
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

// SafeStr dereferences a *string, returning "" if nil.
func SafeStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// TruncateStr truncates s to max runes, appending "…" if truncated.
func TruncateStr(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max]) + "…"
}
