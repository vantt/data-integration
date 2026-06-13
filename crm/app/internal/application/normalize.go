// Package application contains CRM application services.
// Depends only on domain and ports — no adapter imports.
package application

import (
	"strings"
	"unicode"
)

// NormalizePhone converts a Vietnamese phone number to a canonical +84 format.
//
// Rules (VN-specific):
//   - Strip spaces, dashes, dots, parentheses.
//   - "0xxxxxxxxx"  → "+84xxxxxxxxx"
//   - "+84xxxxxxxxx" kept as-is (after stripping non-digit prefix chars).
//   - "84xxxxxxxxx"  → "+84xxxxxxxxx"
//   - Non-VN or unrecognised formats are returned lowercased-and-stripped only.
//
// Returns empty string if input is empty after stripping.
func NormalizePhone(raw string) string {
	// Strip all non-digit, non-plus characters.
	var b strings.Builder
	for _, r := range raw {
		if unicode.IsDigit(r) || r == '+' {
			b.WriteRune(r)
		}
	}
	s := b.String()
	if s == "" {
		return ""
	}

	// After stripping, if no digit remains (e.g. bare "+", punctuation-only) → invalid.
	hasDigit := false
	for _, r := range s {
		if unicode.IsDigit(r) {
			hasDigit = true
			break
		}
	}
	if !hasDigit {
		return ""
	}

	// "+84..." → keep
	if strings.HasPrefix(s, "+84") {
		return s
	}
	// "84..." (at least 11 digits total) → prepend "+"
	if strings.HasPrefix(s, "84") && len(s) >= 11 {
		return "+" + s
	}
	// "0..." → replace leading 0 with "+84"
	if strings.HasPrefix(s, "0") {
		return "+84" + s[1:]
	}
	return s
}

// NormalizeEmail returns a lower-cased, trimmed email address.
// Returns empty string if input is empty.
func NormalizeEmail(raw string) string {
	return strings.ToLower(strings.TrimSpace(raw))
}

// NormalizeName lower-cases a display name for FTS indexing.
// Unicode diacritics removal is handled by FTS5 tokenize='unicode61 remove_diacritics 2'.
func NormalizeName(raw string) string {
	return strings.ToLower(strings.TrimSpace(raw))
}
