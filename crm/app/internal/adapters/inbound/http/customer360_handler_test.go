// Package http — handler-level tests for Customer360Handler.
// Uses net/http/httptest with lightweight mock implementations of the service interfaces.
package http

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── stubs ────────────────────────────────────────────────────────────────────

// stubProfileQuerier implements ProfileQuerier for tests.
type stubProfileQuerier struct {
	profile *domain.CustomerProfile
	v360    *domain.Party360
}

func (s *stubProfileQuerier) GetProfile(_ context.Context, _ string) (*domain.CustomerProfile, error) {
	return s.profile, nil
}
func (s *stubProfileQuerier) GetParty360(_ context.Context, _ string) (*domain.Party360, error) {
	return s.v360, nil
}

// stubProfileWriter implements ProfileWriter for tests.
type stubProfileWriter struct{}

func (s *stubProfileWriter) UpsertProfile(_ context.Context, _ *domain.CustomerProfile) error {
	return nil
}
func (s *stubProfileWriter) UpdateCustom(_ context.Context, _ string, _ map[string]string) error {
	return nil
}

// stubTagManager implements TagManager.
type stubTagManager struct{}

func (s *stubTagManager) AttachTag(_ context.Context, _, _ string, _ *string) error { return nil }
func (s *stubTagManager) DetachTag(_ context.Context, _, _ string) error            { return nil }
func (s *stubTagManager) ListPartyTags(_ context.Context, _ string) ([]domain.Tag, error) {
	return nil, nil
}

// stubNoteManager implements NoteManager.
type stubNoteManager struct{}

func (s *stubNoteManager) AddNote(_ context.Context, _, _ string, _ *string) (*domain.Note, error) {
	return nil, nil
}
func (s *stubNoteManager) ListNotes(_ context.Context, _ string) ([]domain.Note, error) {
	return nil, nil
}

// stubCustomFieldAdmin implements CustomFieldAdmin.
type stubCustomFieldAdmin struct {
	createErr error
}

func (s *stubCustomFieldAdmin) ListCustomFieldDefs(_ context.Context, _ string) ([]domain.CustomFieldDef, error) {
	return nil, nil
}
func (s *stubCustomFieldAdmin) CreateCustomFieldDef(_ context.Context, _ *domain.CustomFieldDef) error {
	return s.createErr
}

// stubPartyLookup implements PartyLookup for tests.
type stubPartyLookup struct {
	party *domain.Party
}

func (s *stubPartyLookup) GetByID(_ context.Context, _ string) (*domain.Party, error) {
	return s.party, nil
}

// buildTestHandler wires all stubs into a Customer360Handler and registers its routes on a new chi router.
func buildTestHandler(
	pq ProfileQuerier,
	pw ProfileWriter,
	tm TagManager,
	nm NoteManager,
	cfa CustomFieldAdmin,
	pl PartyLookup,
) http.Handler {
	h := NewCustomer360Handler(pq, pw, tm, nm, cfa, pl)
	r := chi.NewRouter()
	h.RegisterRoutes(r)
	return r
}

// ─── M2: createCustomField with invalid data_type → 400 ──────────────────────

// TestM2_CreateCustomField_InvalidDataType verifies that POST /api/custom-fields
// with an unknown data_type returns HTTP 400 and never reaches the DB layer.
// Note: domain.CustomFieldDef has no JSON tags; the handler decodes into the struct
// directly, so we use Go field names (FieldKey, Label, DataType).
func TestM2_CreateCustomField_InvalidDataType(t *testing.T) {
	handler := buildTestHandler(
		&stubProfileQuerier{},
		&stubProfileWriter{},
		&stubTagManager{},
		&stubNoteManager{},
		&stubCustomFieldAdmin{},
		&stubPartyLookup{},
	)

	// domain.CustomFieldDef has no json tags → use Go field names exactly.
	body := map[string]any{
		"FieldKey": "bad_type_field",
		"Label":    "Bad Type",
		"DataType": "uuid", // not in ValidCustomDataTypes
	}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/api/custom-fields", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("status = %d; want 400 for invalid data_type", w.Code)
	}

	var resp map[string]string
	_ = json.NewDecoder(w.Body).Decode(&resp)
	if !strings.Contains(resp["error"], "data_type") {
		t.Errorf("error body should mention 'data_type'; got: %v", resp)
	}
}

// TestM2_CreateCustomField_ValidDataType verifies that a valid data_type (e.g. "text")
// passes the front-door check and reaches the service layer (returns 201).
func TestM2_CreateCustomField_ValidDataType(t *testing.T) {
	handler := buildTestHandler(
		&stubProfileQuerier{},
		&stubProfileWriter{},
		&stubTagManager{},
		&stubNoteManager{},
		&stubCustomFieldAdmin{},
		&stubPartyLookup{},
	)

	body := map[string]any{
		"FieldKey": "note_internal",
		"Label":    "Ghi chú nội bộ",
		"DataType": "text",
	}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/api/custom-fields", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("status = %d; want 201 for valid data_type", w.Code)
	}
}

// ─── L2: GetParty360 on a merged party → 409 with distinct signal ─────────────

// TestL2_GetParty360_MergedParty_Returns409 verifies that when the crm_party_360
// view returns no row (is_merged=1 filtered out) but the party exists and is merged,
// the handler returns HTTP 409 with {"error":"party_merged","merged_into":"<id>"}.
func TestL2_GetParty360_MergedParty_Returns409(t *testing.T) {
	survivingID := "party-surviving-001"
	mergedInto := survivingID

	handler := buildTestHandler(
		// GetParty360 returns nil (merged parties are excluded by the view).
		&stubProfileQuerier{v360: nil},
		&stubProfileWriter{},
		&stubTagManager{},
		&stubNoteManager{},
		&stubCustomFieldAdmin{},
		// GetByID reveals the party exists and is merged.
		&stubPartyLookup{party: &domain.Party{
			PartyID:    "party-merged-001",
			IsMerged:   true,
			MergedInto: &mergedInto,
		}},
	)

	req := httptest.NewRequest(http.MethodGet, "/api/parties/party-merged-001/360", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusConflict {
		t.Errorf("status = %d; want 409 for merged party", w.Code)
	}

	var resp map[string]string
	_ = json.NewDecoder(w.Body).Decode(&resp)
	if resp["error"] != "party_merged" {
		t.Errorf("error field = %q; want party_merged", resp["error"])
	}
	if resp["merged_into"] != survivingID {
		t.Errorf("merged_into = %q; want %q", resp["merged_into"], survivingID)
	}
}

// TestL2_GetParty360_NotFound_Returns404 verifies that when neither the view
// nor the party table has a record, a plain 404 is returned.
func TestL2_GetParty360_NotFound_Returns404(t *testing.T) {
	handler := buildTestHandler(
		&stubProfileQuerier{v360: nil},
		&stubProfileWriter{},
		&stubTagManager{},
		&stubNoteManager{},
		&stubCustomFieldAdmin{},
		// GetByID returns nil — party genuinely absent.
		&stubPartyLookup{party: nil},
	)

	req := httptest.NewRequest(http.MethodGet, "/api/parties/does-not-exist/360", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("status = %d; want 404 for absent party", w.Code)
	}
}
