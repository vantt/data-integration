// Package domain contains pure CRM entities and business rules.
// No imports from sqlite, http, or any adapter package.
package domain

// AppUser represents a CRM staff account mapped to a Sapo staff record.
// Role is informational in v1 (auth deferred — LAN-trust model).
type AppUser struct {
	UserID    string // UUID (TEXT in SQLite)
	StaffID   *int64 // nullable — links to dim_staff.staff_id
	Email     string
	FullName  string
	Role      string // sales | care | manager | admin
	IsActive  bool
	CreatedAt string // UTC ISO-8601 with 'Z'
	UpdatedAt string // UTC ISO-8601 with 'Z'
}

// ValidRoles lists the accepted role values. Enforcement is deferred until auth is added.
var ValidRoles = []string{"sales", "care", "manager", "admin"}
