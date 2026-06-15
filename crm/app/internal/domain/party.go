// Package domain contains pure CRM entities and business rules.
// No imports from sqlite, http, or any adapter package.
package domain

// Party is the golden record for a unique real-world customer/org.
// Multiple Sapo customer IDs, phones, emails, etc. converge to one Party.
type Party struct {
	PartyID      string  // UUID (TEXT in SQLite)
	PartyType    string  // person|org
	DisplayName  string
	PrimaryPhone string  // normalised E.164-ish (+84...)
	PrimaryEmail string
	Status       string  // active|inactive|blocked
	IsMerged     bool    // true if absorbed into another party
	MergedInto   *string // FK → party_id of surviving party
	CreatedAt    string  // UTC ISO-8601 with 'Z'
	UpdatedAt    string  // UTC ISO-8601 with 'Z'
}

// ValidPartyTypes lists accepted party_type values.
var ValidPartyTypes = []string{"person", "org"}

// ValidPartyStatuses lists accepted status values.
var ValidPartyStatuses = []string{"active", "inactive", "blocked"}

// PartyIdentity maps one identity value (phone, email, Sapo customer ID…) to a Party.
// UNIQUE(identity_type, identity_value) enforces one-owner-per-identity at DB level.
type PartyIdentity struct {
	IdentityID    string  // UUID
	PartyID       string  // FK → crm_party
	SourceSystem  string  // sapo|messenger|zalo|manual
	IdentityType  string  // sapo_customer|phone|email|psid|zalo_uid|customer_code
	IdentityValue string  // normalised value
	Confidence    float64 // 0.0–1.0
	IsPrimary     bool
	VerifiedAt           *string // nullable UTC ISO-8601
	SourceContactQuality string  // masked|real — immutable, set at creation
	ContactQuality       string  // masked|unverified|verified — mutable
	CreatedAt            string
}

// ValidContactQualities lists accepted contact_quality values.
var ValidContactQualities = []string{"masked", "unverified", "verified"}

// ValidIdentityTypes lists known identity_type values.
var ValidIdentityTypes = []string{
	"sapo_customer", "phone", "email", "psid", "zalo_uid", "customer_code",
}

// DedupCandidate is a suspect-match pair queued for manual review.
type DedupCandidate struct {
	CandidateID string  // UUID
	PartyA      string  // FK → crm_party
	PartyB      string  // FK → crm_party
	MatchRule   string  // exact_phone|exact_email|fts_name_phone
	MatchScore  float64 // 0.0–1.0
	Status      string  // pending|merged|rejected
	ReviewedBy  *string // nullable FK → crm_app_user
	ReviewedAt  *string // nullable UTC ISO-8601
	CreatedAt   string
}

// MergeLog records every merge operation and carries a JSON snapshot for undo.
type MergeLog struct {
	MergeID          string  // UUID
	SurvivingPartyID string  // FK → crm_party (winner)
	MergedPartyID    string  // soft ref — the absorbed party
	Reason           string
	MergedBy         *string // nullable FK → crm_app_user
	Snapshot         string  // JSON: pre-merge state (identities + party flags)
	MergedAt         string  // UTC ISO-8601 with 'Z'
}
