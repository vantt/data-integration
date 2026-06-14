// Package domain — Activity entity.
// An Activity is any recorded interaction between staff and a party.
// No adapter imports allowed here.
package domain

// Activity records one touchpoint between a staff member and a party.
type Activity struct {
	ActivityID       string  // UUID
	PartyID          string  // FK → crm_party
	ActivityType     string  // call|note|visit|email|chat|other
	Direction        string  // in|out (empty = not applicable)
	Channel          string  // phone|messenger|zalo|store|...
	Subject          string
	Body             string
	Outcome          string
	RelatedOrderCode string  // soft ref; order lives in warehouse
	StaffUserID      *string // FK → crm_app_user (nullable)
	OccurredAt       string  // UTC ISO-8601
	CreatedAt        string  // UTC ISO-8601
}

// ValidActivityTypes lists allowed activity_type values.
var ValidActivityTypes = []string{"call", "note", "visit", "email", "chat", "other"}

// IsValidActivityType returns true when t is an accepted activity type.
func IsValidActivityType(t string) bool {
	for _, v := range ValidActivityTypes {
		if v == t {
			return true
		}
	}
	return false
}
