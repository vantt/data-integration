// Package domain — Segment and SegmentMember entities + rule definitions.
// Pure domain: no adapter or infrastructure imports.
package domain

import "errors"

// Segment groups parties by shared criteria (static or dynamic/rule-based).
type Segment struct {
	SegmentID   string  `json:"segment_id"`
	Name        string  `json:"name"`
	Description string  `json:"description"`
	IsDynamic   bool    `json:"is_dynamic"`
	Definition  string  `json:"definition"` // JSON rule blob, empty for static segments
	OwnerUserID *string `json:"owner_user_id,omitempty"`
	CreatedAt   string  `json:"created_at"`
	UpdatedAt   string  `json:"updated_at"`
}

// SegmentMember records a party's membership in a segment.
type SegmentMember struct {
	SegmentID string `json:"segment_id"`
	PartyID   string `json:"party_id"`
	Source    string `json:"source"`  // "rule" | "manual"
	AddedAt   string `json:"added_at"`
}

// SegmentRule is the parsed, validated form of a segment's definition JSON.
// Only fields present in the WHITELIST are populated; unknown keys are rejected.
type SegmentRule struct {
	ValueGroup           []string `json:"value_group,omitempty"`             // e.g. ["VIP","GOLD"]
	CustomerStatus       string   `json:"customer_status,omitempty"`         // e.g. "at_risk"
	DaysSinceLastOrderGte int     `json:"days_since_last_order_gte,omitempty"` // e.g. 60
	ChannelPreference    string   `json:"channel_preference,omitempty"`      // e.g. "messenger"
}

// AllowedRuleKeys is the whitelist of keys permitted in a segment definition JSON.
// Any key not in this set causes RefreshDynamicSegment to return a ValidationError.
var AllowedRuleKeys = map[string]struct{}{
	"value_group":              {},
	"customer_status":          {},
	"days_since_last_order_gte": {},
	"channel_preference":       {},
}

// ValidMemberSources enumerates allowed segment_member.source values.
var ValidMemberSources = map[string]struct{}{
	"rule":   {},
	"manual": {},
}

// ErrUnknownRuleKey is returned when a segment definition contains an unknown field.
var ErrUnknownRuleKey = errors.New("unknown segment rule key")
