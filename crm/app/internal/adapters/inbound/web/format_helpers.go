// Package web — formatting helpers for the web handler layer.
// Only FormatICT is used here; duplicated helpers (VND, badge classes, etc.)
// live exclusively in templates/helpers.go which is the canonical location.
package web

import (
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

// FormatICT parses a UTC ISO-8601 string and returns "DD/MM/YYYY HH:MM ICT".
// Returns the raw string unchanged if parsing fails.
// Used by screen_worklist.go to display cache freshness timestamps.
func FormatICT(utcISO string) string {
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
	if strings.HasSuffix(utcISO, "Z") || strings.Contains(utcISO, "T") {
		return t.Format("02/01/2006 15:04 ICT")
	}
	return t.Format("02/01/2006")
}
