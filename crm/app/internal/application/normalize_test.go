package application

import "testing"

func TestNormalizePhone(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		// Standard VN mobile
		{"0912345678", "+84912345678"},
		{"0 912 345 678", "+84912345678"},
		{"0912.345.678", "+84912345678"},
		{"0912-345-678", "+84912345678"},
		// Already E.164
		{"+84912345678", "+84912345678"},
		{"+84 912 345 678", "+84912345678"},
		// 84 prefix without +
		{"84912345678", "+84912345678"},
		// Empty
		{"", ""},
		// Non-VN number (no known prefix) — returned stripped
		{"+1 800 555 1234", "+18005551234"},
		// Spaces only
		{"   ", ""},
		// Fix #8 edge cases: no digits after stripping → empty
		{"+", ""},
		{"+-.", ""},
		// Single zero digit — has a digit so passes the no-digit guard;
		// matches "0..." prefix rule → "+84" + "" = "+84" (too short to be valid VN,
		// but NormalizePhone does not length-validate non-E.164 outputs).
		{"0", "+84"},
		// Non-numeric junk (no digits) → empty
		{"abcdef", ""},
		{"!@#$%", ""},
	}
	for _, c := range cases {
		got := NormalizePhone(c.in)
		if got != c.want {
			t.Errorf("NormalizePhone(%q) = %q; want %q", c.in, got, c.want)
		}
	}
}

func TestNormalizeEmail(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"User@Example.COM", "user@example.com"},
		{"  trim@me.vn  ", "trim@me.vn"},
		{"", ""},
		{"UPPER@DOMAIN.VN", "upper@domain.vn"},
	}
	for _, c := range cases {
		got := NormalizeEmail(c.in)
		if got != c.want {
			t.Errorf("NormalizeEmail(%q) = %q; want %q", c.in, got, c.want)
		}
	}
}
