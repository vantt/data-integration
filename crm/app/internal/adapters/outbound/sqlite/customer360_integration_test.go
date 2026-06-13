// Package sqlite — integration tests for Customer 360 (Phase 03).
// Uses a real temp SQLite file with all migrations applied; no mocks.
package sqlite

import (
	"context"
	"strings"
	"testing"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── helpers ─────────────────────────────────────────────────────────────────

// seedUserAndParty creates a deterministic app_user + party and returns both IDs.
func seedUserAndParty(t *testing.T, db *DB) (userID, partyID string) {
	t.Helper()
	ctx := context.Background()

	userID = uuid.New().String()
	_, err := db.SQLDB().ExecContext(ctx,
		`INSERT INTO crm_app_user (user_id, email, full_name, role) VALUES (?, ?, ?, ?)`,
		userID, "test@crm.local", "Test User", "sales",
	)
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}

	party := makeParty("Nguyen Thi C", "+84900000099", "c@test.vn")
	partyRepo := NewPartyRepo(db)
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}
	return userID, party.PartyID
}

// buildProfileSvc wires all repos into a ProfileService for testing.
func buildProfileSvc(db *DB) *application.ProfileService {
	return application.NewProfileService(
		NewProfileRepo(db),
		NewCustomFieldRepo(db),
		NewTagRepo(db),
		NewNoteRepo(db),
	)
}

// ─── Profile upsert / get ────────────────────────────────────────────────────

func TestProfileUpsertAndGet(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	userID, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// No profile yet → GetProfile returns nil.
	got, err := svc.GetProfile(ctx, partyID)
	if err != nil {
		t.Fatalf("get profile before upsert: %v", err)
	}
	if got != nil {
		t.Fatalf("expected nil profile before upsert, got %+v", got)
	}

	// Upsert profile.
	p := &domain.CustomerProfile{
		PartyID:           partyID,
		OwnerUserID:       &userID,
		LifecycleStage:    "active",
		AcquisitionSource: "walk-in",
		Birthday:          "1990-05-20",
		ConsentContact:    true,
		Custom:            "{}",
		CreatedAt:         utcTestNow(),
		UpdatedAt:         utcTestNow(),
	}
	if err := svc.UpsertProfile(ctx, p); err != nil {
		t.Fatalf("upsert profile: %v", err)
	}

	// Read it back.
	got, err = svc.GetProfile(ctx, partyID)
	if err != nil {
		t.Fatalf("get profile after upsert: %v", err)
	}
	if got == nil {
		t.Fatal("expected profile, got nil")
	}
	if got.LifecycleStage != "active" {
		t.Errorf("lifecycle_stage = %q; want active", got.LifecycleStage)
	}
	if got.Birthday != "1990-05-20" {
		t.Errorf("birthday = %q; want 1990-05-20", got.Birthday)
	}
	if !got.ConsentContact {
		t.Error("consent_contact should be true")
	}
}

// ─── UpdateCustom: valid values ───────────────────────────────────────────────

func TestUpdateCustom_ValidValues(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Upsert a minimal profile first.
	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID: partyID, Custom: "{}", ConsentContact: true,
		CreatedAt: utcTestNow(), UpdatedAt: utcTestNow(),
	}); err != nil {
		t.Fatalf("upsert profile: %v", err)
	}

	// skin_type is a seeded select field with options ["dầu","khô","hỗn hợp","nhạy cảm","thường"].
	if err := svc.UpdateCustom(ctx, partyID, map[string]string{
		"skin_type": "khô",
	}); err != nil {
		t.Fatalf("UpdateCustom valid: %v", err)
	}

	got, err := svc.GetProfile(ctx, partyID)
	if err != nil || got == nil {
		t.Fatalf("get profile: %v", err)
	}
	if !strings.Contains(got.Custom, "khô") {
		t.Errorf("custom JSON should contain 'khô', got: %s", got.Custom)
	}
}

// ─── UpdateCustom: invalid value → rejected ───────────────────────────────────

func TestUpdateCustom_InvalidValueRejected(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID: partyID, Custom: "{}", ConsentContact: true,
		CreatedAt: utcTestNow(), UpdatedAt: utcTestNow(),
	}); err != nil {
		t.Fatalf("upsert: %v", err)
	}

	// "invisible" is not a valid option for skin_type.
	err := svc.UpdateCustom(ctx, partyID, map[string]string{
		"skin_type": "invisible",
	})
	if err == nil {
		t.Fatal("expected validation error for invalid select value, got nil")
	}
	if !strings.Contains(err.Error(), "validation failed") {
		t.Errorf("expected 'validation failed' in error, got: %v", err)
	}
}

// ─── Tag attach / detach (idempotent) ─────────────────────────────────────────

func TestTagAttachDetach_Idempotent(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	userID, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Use a seeded tag (tag-00000000-0001 = VIP).
	tagID := "tag-00000000-0001"

	// Attach once.
	if err := svc.AttachTag(ctx, partyID, tagID, &userID); err != nil {
		t.Fatalf("first attach: %v", err)
	}
	// Attach again (must be idempotent — INSERT OR IGNORE).
	if err := svc.AttachTag(ctx, partyID, tagID, &userID); err != nil {
		t.Fatalf("second attach (idempotent): %v", err)
	}

	tags, err := svc.ListPartyTags(ctx, partyID)
	if err != nil {
		t.Fatalf("list party tags: %v", err)
	}
	if len(tags) != 1 {
		t.Errorf("expected 1 tag after duplicate attach, got %d", len(tags))
	}
	if tags[0].Name != "VIP" {
		t.Errorf("tag name = %q; want VIP", tags[0].Name)
	}

	// Detach.
	if err := svc.DetachTag(ctx, partyID, tagID); err != nil {
		t.Fatalf("detach tag: %v", err)
	}
	tagsAfter, _ := svc.ListPartyTags(ctx, partyID)
	if len(tagsAfter) != 0 {
		t.Errorf("expected 0 tags after detach, got %d", len(tagsAfter))
	}
}

// ─── Notes: add and list ──────────────────────────────────────────────────────

func TestNoteAddAndList(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	userID, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Empty list first.
	notes, err := svc.ListNotes(ctx, partyID)
	if err != nil {
		t.Fatalf("list notes (empty): %v", err)
	}
	if len(notes) != 0 {
		t.Errorf("expected 0 notes, got %d", len(notes))
	}

	// Add two notes.
	n1, err := svc.AddNote(ctx, partyID, "Khách thích sản phẩm dưỡng ẩm", &userID)
	if err != nil {
		t.Fatalf("add note 1: %v", err)
	}
	if n1.NoteID == "" {
		t.Error("expected non-empty note_id")
	}

	if _, err := svc.AddNote(ctx, partyID, "Gọi lại vào tuần sau", nil); err != nil {
		t.Fatalf("add note 2: %v", err)
	}

	// Empty body must be rejected.
	_, err = svc.AddNote(ctx, partyID, "   ", nil)
	if err == nil {
		t.Fatal("expected error for empty note body")
	}

	notes, err = svc.ListNotes(ctx, partyID)
	if err != nil {
		t.Fatalf("list notes: %v", err)
	}
	if len(notes) != 2 {
		t.Errorf("expected 2 notes, got %d", len(notes))
	}
	// ListNotes returns DESC — most recent first.
	// Order is by created_at DESC, so order may vary at millisecond resolution.
	// Just check all bodies are present.
	bodies := map[string]bool{notes[0].Body: true, notes[1].Body: true}
	if !bodies["Khách thích sản phẩm dưỡng ẩm"] || !bodies["Gọi lại vào tuần sau"] {
		t.Errorf("unexpected note bodies: %v", bodies)
	}
}

// ─── GetParty360: profile + tags in one query ─────────────────────────────────

func TestGetParty360_ProfileAndTags(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	userID, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Upsert a profile.
	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID:        partyID,
		OwnerUserID:    &userID,
		LifecycleStage: "new",
		ConsentContact: true,
		Custom:         "{}",
		CreatedAt:      utcTestNow(),
		UpdatedAt:      utcTestNow(),
	}); err != nil {
		t.Fatalf("upsert profile: %v", err)
	}

	// Attach two seeded tags.
	for _, tagID := range []string{"tag-00000000-0001", "tag-00000000-0003"} {
		if err := svc.AttachTag(ctx, partyID, tagID, &userID); err != nil {
			t.Fatalf("attach tag %s: %v", tagID, err)
		}
	}

	v, err := svc.GetParty360(ctx, partyID)
	if err != nil {
		t.Fatalf("get party360: %v", err)
	}
	if v == nil {
		t.Fatal("expected Party360, got nil")
	}

	// Profile fields should be present.
	if v.LifecycleStage != "new" {
		t.Errorf("lifecycle_stage = %q; want new", v.LifecycleStage)
	}
	if v.ConsentContact == nil || !*v.ConsentContact {
		t.Error("consent_contact should be true")
	}

	// Tags JSON should contain both tag names.
	if !strings.Contains(v.TagsJSON, "VIP") {
		t.Errorf("tags_json should contain 'VIP', got: %s", v.TagsJSON)
	}
	if !strings.Contains(v.TagsJSON, "Khách quen") {
		t.Errorf("tags_json should contain 'Khách quen', got: %s", v.TagsJSON)
	}
}

// ─── H1: PUT profile without custom_fields must preserve existing custom data ──

// TestH1_PutProfilePreservesCustom verifies fix #1: when UpsertProfile is called
// without updating custom_fields, previously-saved custom values survive unchanged.
func TestH1_PutProfilePreservesCustom(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// 1. Create a minimal profile.
	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID: partyID, Custom: "{}", ConsentContact: true,
		CreatedAt: utcTestNow(), UpdatedAt: utcTestNow(),
	}); err != nil {
		t.Fatalf("initial upsert: %v", err)
	}

	// 2. Set a custom field value (skin_type is a seeded select field).
	if err := svc.UpdateCustom(ctx, partyID, map[string]string{"skin_type": "khô"}); err != nil {
		t.Fatalf("set custom field: %v", err)
	}

	// Confirm it's stored.
	got, _ := svc.GetProfile(ctx, partyID)
	if !strings.Contains(got.Custom, "khô") {
		t.Fatalf("expected custom to contain 'khô' before PUT; got %s", got.Custom)
	}

	// 3. Simulate PUT profile (lifecycle_stage update only) with preserved custom JSON.
	// The handler reads existing.Custom before UpsertProfile; we replicate that here.
	existing, err := svc.GetProfile(ctx, partyID)
	if err != nil || existing == nil {
		t.Fatalf("get profile before preserve-upsert: %v", err)
	}
	updatedProfile := &domain.CustomerProfile{
		PartyID:        partyID,
		LifecycleStage: "active",
		ConsentContact: true,
		Custom:         existing.Custom, // preserve existing custom
		CreatedAt:      utcTestNow(),
		UpdatedAt:      utcTestNow(),
	}
	if err := svc.UpsertProfile(ctx, updatedProfile); err != nil {
		t.Fatalf("upsert profile (lifecycle only): %v", err)
	}

	// 4. Verify custom value is still present after the lifecycle-only upsert.
	after, err := svc.GetProfile(ctx, partyID)
	if err != nil || after == nil {
		t.Fatalf("get profile after upsert: %v", err)
	}
	if !strings.Contains(after.Custom, "khô") {
		t.Errorf("custom data was erased by lifecycle-only upsert; got: %s", after.Custom)
	}
	if after.LifecycleStage != "active" {
		t.Errorf("lifecycle_stage = %q; want active", after.LifecycleStage)
	}
}

// ─── H2: UpdateCustom validates against merged map (not just delta) ───────────

// TestH2_UpdateCustom_RequiredFieldSatisfiedByExisting verifies fix #2:
// a partial UpdateCustom on a DIFFERENT field succeeds when the required field
// is already satisfied in the stored (merged) map.
func TestH2_UpdateCustom_RequiredFieldSatisfied(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Seed a required custom field definition.
	reqFieldID := uuid.New().String()
	if err := svc.CreateCustomFieldDef(ctx, &domain.CustomFieldDef{
		FieldID:    reqFieldID,
		EntityType: "party",
		FieldKey:   "customer_code",
		Label:      "Mã khách hàng",
		DataType:   "text",
		IsRequired: true,
		IsActive:   true,
	}); err != nil {
		t.Fatalf("create required custom field def: %v", err)
	}

	// Create a profile.
	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID: partyID, Custom: "{}", ConsentContact: true,
		CreatedAt: utcTestNow(), UpdatedAt: utcTestNow(),
	}); err != nil {
		t.Fatalf("upsert profile: %v", err)
	}

	// Set the required field (customer_code).
	if err := svc.UpdateCustom(ctx, partyID, map[string]string{"customer_code": "CU-001"}); err != nil {
		t.Fatalf("set required field: %v", err)
	}

	// Now update a DIFFERENT field (note_internal) — must succeed because
	// required field customer_code is already present in the merged map.
	if err := svc.UpdateCustom(ctx, partyID, map[string]string{"note_internal": "ghi chú"}); err != nil {
		t.Errorf("partial update of non-required field should succeed when required field already stored; got: %v", err)
	}

	// Confirm both values are present.
	got, _ := svc.GetProfile(ctx, partyID)
	if !strings.Contains(got.Custom, "CU-001") {
		t.Errorf("required field lost after partial update; custom: %s", got.Custom)
	}
	if !strings.Contains(got.Custom, "ghi chú") {
		t.Errorf("new field not stored; custom: %s", got.Custom)
	}
}

// TestH2_UpdateCustom_RequiredFieldEmptied verifies that explicitly setting a
// required field to empty string in the delta is still rejected.
func TestH2_UpdateCustom_RequiredFieldEmptied(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// Seed a required custom field definition.
	reqFieldID := uuid.New().String()
	if err := svc.CreateCustomFieldDef(ctx, &domain.CustomFieldDef{
		FieldID:    reqFieldID,
		EntityType: "party",
		FieldKey:   "req_field",
		Label:      "Required Field",
		DataType:   "text",
		IsRequired: true,
		IsActive:   true,
	}); err != nil {
		t.Fatalf("create required custom field def: %v", err)
	}

	// Create a profile and set the required field.
	if err := svc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID: partyID, Custom: "{}", ConsentContact: true,
		CreatedAt: utcTestNow(), UpdatedAt: utcTestNow(),
	}); err != nil {
		t.Fatalf("upsert profile: %v", err)
	}
	if err := svc.UpdateCustom(ctx, partyID, map[string]string{"req_field": "value"}); err != nil {
		t.Fatalf("initial set: %v", err)
	}

	// Attempt to explicitly clear the required field — must fail.
	err := svc.UpdateCustom(ctx, partyID, map[string]string{"req_field": ""})
	if err == nil {
		t.Fatal("expected validation error when required field is explicitly cleared; got nil")
	}
	if !strings.Contains(err.Error(), "validation failed") {
		t.Errorf("expected 'validation failed' in error; got: %v", err)
	}
}

// ─── N6: crm_party_360 tags_json is '[]' (not NULL) for untagged parties ──────

// TestParty360_UntaggedParty_TagsJSONIsEmptyArray verifies the COALESCE fix:
// a party with no tags attached returns tags_json = "[]" rather than NULL/empty.
func TestParty360_UntaggedParty_TagsJSONIsEmptyArray(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildProfileSvc(db)

	// No tags attached — get 360.
	v, err := svc.GetParty360(ctx, partyID)
	if err != nil {
		t.Fatalf("get party360: %v", err)
	}
	if v == nil {
		t.Fatal("expected Party360, got nil")
	}
	// With COALESCE in view, TagsJSON must be "[]" not empty string / NULL.
	if v.TagsJSON != "[]" {
		t.Errorf("TagsJSON = %q; want \"[]\" for untagged party", v.TagsJSON)
	}
}

// ─── Party360 is CRM-only (no cache.* reference) ─────────────────────────────

// TestParty360ViewCRMOnly verifies the view executes without referencing cache.*
// tables. If the view joined cache.wh_customer_insight it would fail here because
// cache.db is empty (no wh_* tables). Success = CRM-only join.
func TestParty360ViewCRMOnly(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)

	// Query directly via raw SQL to confirm the view is reachable.
	row := db.SQLDB().QueryRowContext(ctx,
		`SELECT party_id FROM crm_party_360 WHERE party_id = ?`, partyID)
	var got string
	if err := row.Scan(&got); err != nil {
		t.Fatalf("crm_party_360 query failed (may reference cache.*): %v", err)
	}
	if got != partyID {
		t.Errorf("party_id = %q; want %q", got, partyID)
	}
}
