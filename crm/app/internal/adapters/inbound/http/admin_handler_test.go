// Package http — handler-level tests for AdminHandler (POST /admin/refresh).
// Uses net/http/httptest with a fake Refresher — never shells out.
package http

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
)

// ─── fakes ─────────────────────────────────────────────────────────────────

// fakeRefresher implements Refresher. err controls success/failure; block, when
// non-nil, holds the refresh open until released (to simulate in-flight runs).
type fakeRefresher struct {
	err     error
	block   chan struct{} // if non-nil, Refresh waits on it before returning
	started chan struct{} // if non-nil, closed once Refresh is entered
}

func (f *fakeRefresher) Refresh(ctx context.Context) (RefreshResult, error) {
	if f.started != nil {
		close(f.started)
	}
	if f.block != nil {
		select {
		case <-f.block:
		case <-ctx.Done():
			return RefreshResult{}, ctx.Err()
		}
	}
	now := time.Now()
	return RefreshResult{
		StartedAt:  now,
		FinishedAt: now,
		DurationMs: 1,
		Output:     "[refresh] done.",
	}, f.err
}

func buildAdminTestHandler(refresher Refresher, token string) http.Handler {
	h := NewAdminHandler(refresher, token)
	r := chi.NewRouter()
	h.RegisterRoutes(r)
	return r
}

func postRefresh(handler http.Handler, token string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, "/admin/refresh", nil)
	if token != "" {
		req.Header.Set("X-Refresh-Token", token)
	}
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	return w
}

// ─── tests ─────────────────────────────────────────────────────────────────

// TestRefresh_Success_Returns200 — fake succeeds → 200 with status ok.
func TestRefresh_Success_Returns200(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "")

	w := postRefresh(handler, "")

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d; want 200", w.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %v; want ok", resp["status"])
	}
}

// TestRefresh_Error_Returns500 — fake returns error → 500 with status error.
func TestRefresh_Error_Returns500(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{err: errors.New("boom")}, "")

	w := postRefresh(handler, "")

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d; want 500", w.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "error" {
		t.Errorf("status = %v; want error", resp["status"])
	}
	if resp["error"] == "" || resp["error"] == nil {
		t.Errorf("expected non-empty error field, got: %v", resp)
	}
}

// TestRefresh_InFlight_Returns409 — second concurrent request while the first
// is still running gets 409 busy.
func TestRefresh_InFlight_Returns409(t *testing.T) {
	block := make(chan struct{})
	started := make(chan struct{})
	handler := buildAdminTestHandler(&fakeRefresher{block: block, started: started}, "")

	// Fire the first request in the background; it blocks inside Refresh.
	firstDone := make(chan *httptest.ResponseRecorder, 1)
	go func() { firstDone <- postRefresh(handler, "") }()

	// Wait until the first request has actually entered Refresh (slot claimed).
	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("first refresh did not start in time")
	}

	// Second request must be rejected with 409 immediately.
	w2 := postRefresh(handler, "")
	if w2.Code != http.StatusConflict {
		t.Fatalf("second status = %d; want 409", w2.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w2.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "busy" {
		t.Errorf("status = %v; want busy", resp["status"])
	}

	// Release the first request and confirm it succeeded (200).
	close(block)
	select {
	case w1 := <-firstDone:
		if w1.Code != http.StatusOK {
			t.Errorf("first status = %d; want 200", w1.Code)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("first refresh did not finish in time")
	}
}

// TestRefresh_TokenSet_WrongOrMissing_Returns401.
func TestRefresh_TokenSet_WrongOrMissing_Returns401(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "secret-token")

	// Missing header.
	if w := postRefresh(handler, ""); w.Code != http.StatusUnauthorized {
		t.Errorf("missing token: status = %d; want 401", w.Code)
	}
	// Wrong header.
	if w := postRefresh(handler, "wrong-token"); w.Code != http.StatusUnauthorized {
		t.Errorf("wrong token: status = %d; want 401", w.Code)
	}
}

// TestRefresh_TokenSet_Correct_Returns200.
func TestRefresh_TokenSet_Correct_Returns200(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "secret-token")

	w := postRefresh(handler, "secret-token")

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d; want 200", w.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %v; want ok", resp["status"])
	}
}
