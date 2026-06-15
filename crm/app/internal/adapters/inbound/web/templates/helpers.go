// Package templates — pure-Go helpers called from templ files.
// Templ components can call normal Go functions defined in the same package.
package templates

import (
	"fmt"
	"math"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/vantt/data-integration/crm/app/internal/domain"
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

// customerLabelHelper returns the customer's display name if known, else the raw key.
func customerLabelHelper(name, key string) string {
	if name != "" {
		return name
	}
	return key
}

// truncStr truncates to max runes, appending "…" if needed.
func truncStr(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max]) + "…"
}

// ── Order detail helpers ───────────────────────────────────────────────────────

// formatPctHelper formats a *float64 (0.0–1.0 scale) as "12.5%" or "".
// Returns "" (not "—") so callers can omit the element entirely on nil.
func formatPctHelper(pct *float64) string {
	if pct == nil {
		return ""
	}
	v := *pct * 100
	if v < 0 {
		return fmt.Sprintf("−%.1f%%", -v)
	}
	return fmt.Sprintf("%.1f%%", v)
}

// formatPctAmtHelper computes amt/base as a percentage string (e.g. "12.5%").
// Returns "" when base is zero to avoid division-by-zero.
func formatPctAmtHelper(amt, base int64) string {
	if base == 0 {
		return ""
	}
	v := math.Abs(float64(amt)/float64(base)) * 100
	return fmt.Sprintf("%.1f%%", v)
}

// verdictToneHelper returns "moss" (profit), "coral" (loss), or "mute" (indeterminate).
func verdictToneHelper(cogsSource string, profit int64) string {
	if cogsSource == "" || cogsSource == "none" {
		return "mute"
	}
	if profit <= 0 {
		return "coral"
	}
	return "moss"
}

// verdictWordHelper returns the Vietnamese verdict word for a tone.
func verdictWordHelper(tone string) string {
	switch tone {
	case "coral":
		return "Lỗ"
	case "moss":
		return "Lãi"
	default:
		return "Chưa xác định"
	}
}

// shipToneHelper maps a fulfillment/shipment status to a Precision tone name.
func shipToneHelper(status string) string {
	switch strings.ToUpper(status) {
	case "DELIVERED":
		return "good"
	case "SHIPPING", "PENDING", "PACKED":
		return "warn"
	case "CANCELLED", "FAILED":
		return "bad"
	default:
		return "neutral"
	}
}

// paymentToneHelper maps a payment status to a Precision tone name.
func paymentToneHelper(status string) string {
	switch strings.ToUpper(status) {
	case "PAID", "COMPLETED", "SUCCESS":
		return "good"
	case "PENDING", "PROCESSING":
		return "warn"
	case "FAILED", "VOIDED", "CANCELLED":
		return "bad"
	default:
		return "neutral"
	}
}

// bdgToneHelper converts a tone name to the Precision badge CSS modifier class.
func bdgToneHelper(tone string) string {
	switch tone {
	case "good":
		return "bdg--good"
	case "warn":
		return "bdg--warn"
	case "bad":
		return "bdg--bad"
	case "accent":
		return "bdg--accent"
	case "moss":
		return "bdg--good"
	case "coral":
		return "bdg--bad"
	default:
		return ""
	}
}

// cogsLabelHelper returns the human-readable COGS source label.
func cogsLabelHelper(source string) string {
	switch source {
	case "sapo_mac":
		return "Sapo-MAC"
	case "both":
		return "Sapo-MAC · MISA"
	case "misa":
		return "MISA"
	default:
		return ""
	}
}

// signPrefixHelper returns "+" for positive amounts, "−" for negative, "" for zero.
func signPrefixHelper(amt int64) string {
	if amt > 0 {
		return "+"
	}
	if amt < 0 {
		return "−"
	}
	return ""
}

// absVNDHelper returns the absolute VND amount as formatted string.
func absVNDHelper(amt int64) string {
	return formatVNDHelper(amt) // formatVNDHelper already shows "—" for zero; abs handled by caller
}

// formatVNDAbsHelper formats the absolute value of amt (always positive display).
func formatVNDAbsHelper(amt int64) string {
	if amt < 0 {
		amt = -amt
	}
	return formatVNDHelper(amt)
}

// titleCaseReplace replaces underscores with spaces and title-cases the string.
func titleCaseReplace(s string) string {
	s = strings.ReplaceAll(s, "_", " ")
	return strings.Title(strings.ToLower(s)) //nolint:staticcheck
}

// joinNonEmpty joins non-empty strings with sep.
func joinNonEmpty(parts []string, sep string) string {
	var out []string
	for _, p := range parts {
		if p != "" {
			out = append(out, p)
		}
	}
	return strings.Join(out, sep)
}

// ── Helpers extracted from templ components ({{ }} must be single-statement) ──

func absInt64(v int64) int64 {
	if v < 0 {
		return -v
	}
	return v
}

func absFloat64(v float64) float64 {
	return math.Abs(v)
}

func sortShipments(shps []domain.Shipment) []domain.Shipment {
	result := make([]domain.Shipment, len(shps))
	copy(result, shps)
	sort.Slice(result, func(i, j int) bool {
		a, b := result[i].ShippedAt, result[j].ShippedAt
		if a == "" && b == "" {
			return false
		}
		if a == "" {
			return false
		}
		if b == "" {
			return true
		}
		return a > b
	})
	return result
}

func sortReturns(rets []domain.ReturnEvent) []domain.ReturnEvent {
	result := make([]domain.ReturnEvent, len(rets))
	copy(result, rets)
	sort.Slice(result, func(i, j int) bool {
		return result[i].ReturnDate > result[j].ReturnDate
	})
	return result
}

// orderedCostCategories returns distinct cost categories in display order:
// priority order (DISCOUNT, PLATFORM_FEE, OVERHEAD) first, then others.
// COGS and PROMO_GOODS are excluded (rendered separately).
func orderedCostCategories(rows []domain.CostRow) []string {
	catOrder := []string{"DISCOUNT", "PLATFORM_FEE", "OVERHEAD"}
	inOrder := map[string]bool{}
	for _, c := range catOrder {
		inOrder[c] = true
	}
	seen := map[string]bool{}
	var result []string
	for _, cat := range catOrder {
		for _, row := range rows {
			if row.CostCategory == cat && !seen[cat] {
				seen[cat] = true
				result = append(result, cat)
				break
			}
		}
	}
	for _, row := range rows {
		cat := row.CostCategory
		if cat == "COGS" || cat == "PROMO_GOODS" || inOrder[cat] || seen[cat] {
			continue
		}
		seen[cat] = true
		result = append(result, cat)
	}
	return result
}

func costCategoryTone(cat string) string {
	switch cat {
	case "COGS":
		return "good"
	case "PLATFORM_FEE":
		return "warn"
	case "DISCOUNT", "PROMO_GOODS", "OVERHEAD":
		return "accent"
	default:
		return "neutral"
	}
}
