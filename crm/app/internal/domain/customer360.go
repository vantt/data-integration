// Package domain — Customer 360 entities: CustomerProfile, CustomFieldDef, Tag, Note.
// Pure structs + business rules; NO adapter imports.
package domain

// CustomerProfile holds enrichment data owned by the CRM for one party.
// Maps 1-1 with crm_customer_profile (party_id = PK = FK → crm_party).
type CustomerProfile struct {
	PartyID           string  // FK → crm_party (also PK — 1:1)
	OwnerUserID       *string // FK → crm_app_user (assigned sales rep)
	LifecycleStage    string  // lead|new|active|at_risk|churned
	AcquisitionSource string  // human-confirmed acquisition source
	Birthday          string  // YYYY-MM-DD or empty
	Address           string  // JSON {province,district,ward,street}
	Preferences       string  // JSON: manually recorded preferences
	Custom            string  // JSON map — values keyed by CustomFieldDef.FieldKey
	ConsentContact    bool    // false = opted out (blocks Phase 06 campaigns)
	CreatedAt         string  // UTC ISO-8601 with 'Z'
	UpdatedAt         string  // UTC ISO-8601 with 'Z'
}

// CustomFieldDef describes one dynamic field that can be stored in
// CustomerProfile.Custom (a JSON blob).  The registry drives UI rendering
// and server-side validation without schema migrations.
type CustomFieldDef struct {
	FieldID    string   // UUID
	EntityType string   // "party" | "order" (extensible)
	FieldKey   string   // key inside the JSON custom blob
	Label      string   // human-readable label
	DataType   string   // text|number|date|bool|select|multiselect
	Options    []string // allowed values for select/multiselect; nil for other types
	IsRequired bool
	IsActive   bool
	SortOrder  int
}

// ValidCustomDataTypes lists all accepted data_type values for CustomFieldDef.
var ValidCustomDataTypes = []string{"text", "number", "date", "bool", "select", "multiselect"}

// IsValidDataType reports whether dataType is one of the accepted values.
func IsValidDataType(dataType string) bool {
	for _, v := range ValidCustomDataTypes {
		if v == dataType {
			return true
		}
	}
	return false
}

// Tag is a label that can be attached to many parties.
type Tag struct {
	TagID    string // UUID
	Name     string
	Category string // e.g. segment|profile|action
	Color    string // hex color string, optional
}

// PartyTag is the join record between a party and a tag.
type PartyTag struct {
	PartyID  string
	TagID    string
	TaggedBy *string // FK → crm_app_user (nullable)
	TaggedAt string  // UTC ISO-8601 with 'Z'
}

// Note is a free-form text note attached to a party by a CRM user.
type Note struct {
	NoteID       string  // UUID
	PartyID      string  // FK → crm_party
	Body         string
	AuthorUserID *string // FK → crm_app_user (nullable)
	CreatedAt    string  // UTC ISO-8601 with 'Z'
}

// Party360 is the aggregated read model returned by crm_party_360 view.
// Combines party + profile fields + tags for the detail screen.
type Party360 struct {
	// Core party fields
	PartyID      string
	PartyType    string
	DisplayName  string
	PrimaryPhone string
	PrimaryEmail string
	Status       string
	IsMerged     bool
	PartyCreatedAt string
	PartyUpdatedAt string
	// Profile fields (zero-values when no profile exists)
	OwnerUserID       *string
	LifecycleStage    string
	AcquisitionSource string
	Birthday          string
	Address           string
	Preferences       string
	Custom            string // raw JSON
	ConsentContact    *bool  // nil when no profile row
	ProfileUpdatedAt  string
	// Tags as raw JSON array string from the view
	TagsJSON string
}
