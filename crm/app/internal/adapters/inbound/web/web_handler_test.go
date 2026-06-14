// Package web — httptest-level tests for the web inbound adapter.
// Uses temp SQLite + embedded migrations (same pattern as sqlite integration tests)
// to seed a party and verify all three screens render correctly.
package web_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web"
	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ── test fixture ──────────────────────────────────────────────────────────────

type testFixture struct {
	server  http.Handler
	partyID string
}

// newTestFixture opens a temp SQLite DB, runs migrations, seeds one party,
// and wires the full web adapter on a chi router.
func newTestFixture(t *testing.T) *testFixture {
	t.Helper()

	// Temp data directory.
	dir := t.TempDir()

	db, err := sqlite.Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	if err := sqlite.MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	// Repositories.
	partyRepo := sqlite.NewPartyRepo(db)
	profileRepo := sqlite.NewProfileRepo(db)
	customFieldRepo := sqlite.NewCustomFieldRepo(db)
	tagRepo := sqlite.NewTagRepo(db)
	noteRepo := sqlite.NewNoteRepo(db)
	activityRepo := sqlite.NewActivityRepo(db)
	taskRepo := sqlite.NewTaskRepo(db)
	cacheRepo := sqlite.NewCacheRepo(db)

	// Application services.
	profileSvc := application.NewProfileService(profileRepo, customFieldRepo, tagRepo, noteRepo)
	activitySvc := application.NewActivityService(activityRepo)
	taskSvc := application.NewTaskService(taskRepo, partyRepo, cacheRepo)

	// Seed one party.
	now := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
	party := &domain.Party{
		PartyID:      "test-party-001",
		PartyType:    "person",
		DisplayName:  "Nguyễn Thị Test",
		PrimaryPhone: "+84901234567",
		Status:       "active",
		CreatedAt:    now,
		UpdatedAt:    now,
	}
	if err := partyRepo.Create(context.Background(), party); err != nil {
		t.Fatalf("seed party: %v", err)
	}

	// Build web deps.
	deps := &web.Deps{
		ActionQueue: cacheRepo,
		Tasks:       taskSvc,
		TaskWriter:  taskSvc,
		Parties:     web.NewWebPartyRepo(partyRepo, db.SQLDB()),
		Profile:     profileSvc,
		Insight:     cacheRepo,
		Identities:  partyRepo,
		Activities:  activitySvc,
		Notes:       profileSvc,
		PartyTasks:  web.NewWebTaskRepo(db.SQLDB()),
	}

	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	web.Mount(r, deps)

	// Also mount static files path check.
	_ = os.MkdirAll(dir, 0o755)

	return &testFixture{server: r, partyID: party.PartyID}
}

// ── tests ─────────────────────────────────────────────────────────────────────

// TestWebWorklist_GracefulEmpty verifies GET / returns 200 even when cache is empty.
func TestWebWorklist_GracefulEmpty(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET / status = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Worklist") {
		t.Errorf("GET / body missing 'Worklist'; got snippet: %.200s", body)
	}
}

// TestWebWorklist_Fragment verifies GET /worklist/fragment returns 200 HTML fragment.
func TestWebWorklist_Fragment(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/worklist/fragment", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /worklist/fragment status = %d; want 200", w.Code)
	}
}

// TestWebCustomerList_Renders verifies GET /customers returns 200 with the seeded party name.
func TestWebCustomerList_Renders(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /customers status = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Nguyễn Thị Test") {
		t.Errorf("GET /customers body missing seeded party name; snippet: %.300s", body)
	}
}

// TestWebCustomerList_SearchFragment verifies GET /customers/search returns rows fragment.
func TestWebCustomerList_SearchFragment(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers/search?q=Nguyễn", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /customers/search status = %d; want 200", w.Code)
	}
	// Fragment returns tbody rows — not a full HTML page.
	body := w.Body.String()
	if body == "" {
		t.Error("GET /customers/search returned empty body")
	}
}

// TestWebCustomerList_SearchFragment_Empty verifies graceful empty when no match.
func TestWebCustomerList_SearchFragment_Empty(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers/search?q=zzznomatch999", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /customers/search (no match) status = %d; want 200", w.Code)
	}
}

// TestWebCustomer360_Renders verifies GET /customers/{id} returns 200 with the party's name.
func TestWebCustomer360_Renders(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers/"+f.partyID, nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /customers/%s status = %d; want 200", f.partyID, w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Nguyễn Thị Test") {
		t.Errorf("GET /customers/%s body missing party name; snippet: %.300s", f.partyID, body)
	}
}

// TestWebCustomer360_NotFound verifies GET /customers/{bad-id} returns 404.
func TestWebCustomer360_NotFound(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers/does-not-exist-999", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("GET /customers/bad-id status = %d; want 404", w.Code)
	}
}

// TestWebCustomer360_InsightPanel_GracefulEmpty verifies the insight panel returns 200
// with the empty-state message when cache has no data for this party.
func TestWebCustomer360_InsightPanel_GracefulEmpty(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/customers/"+f.partyID+"/panels/insight", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("panel insight status = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "phân tích") {
		t.Errorf("insight panel empty state missing 'phân tích'; snippet: %.300s", body)
	}
}

// TestWebCustomer360_AllPanels verifies all five panels return 200 without error.
func TestWebCustomer360_AllPanels(t *testing.T) {
	f := newTestFixture(t)
	panels := []string{"insight", "orders", "timeline", "tasks", "notes"}

	for _, panel := range panels {
		t.Run(panel, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet,
				"/customers/"+f.partyID+"/panels/"+panel, nil)
			w := httptest.NewRecorder()
			f.server.ServeHTTP(w, req)
			if w.Code != http.StatusOK {
				t.Errorf("panel %s status = %d; want 200", panel, w.Code)
			}
		})
	}
}

// TestWebStatic_HTMX verifies /static/htmx.min.js is served with 200.
func TestWebStatic_HTMX(t *testing.T) {
	f := newTestFixture(t)

	req := httptest.NewRequest(http.MethodGet, "/static/htmx.min.js", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("GET /static/htmx.min.js status = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Header().Get("Content-Type"), "javascript") {
		// Some servers return application/octet-stream for .js — accept both.
		ct := w.Header().Get("Content-Type")
		if !strings.Contains(ct, "javascript") && !strings.Contains(ct, "octet-stream") && ct != "" {
			t.Errorf("htmx.min.js Content-Type = %q; expected javascript or octet-stream", ct)
		}
	}
	if w.Body.Len() < 10000 {
		t.Errorf("htmx.min.js seems too small: %d bytes", w.Body.Len())
	}
}

// TestWebAddNote_PostReturnsFragment verifies POST /customers/{id}/notes
// returns 200 with the note body in the response fragment.
func TestWebAddNote_PostReturnsFragment(t *testing.T) {
	f := newTestFixture(t)

	form := strings.NewReader("body=Ghi+ch%C3%BA+th%E1%BB%AD+nghi%E1%BB%87m")
	req := httptest.NewRequest(http.MethodPost,
		"/customers/"+f.partyID+"/notes", form)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("POST notes status = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	body := w.Body.String()
	if !strings.Contains(body, "Ghi chú thử nghiệm") {
		t.Errorf("POST notes response missing note body; got: %.300s", body)
	}
}
