// Package http — handler-level tests for AdminHandler (POST /admin/refresh,
// GET /admin/refresh/status). Uses net/http/httptest with a fake Refresher —
// never shells out.
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

func getStatus(handler http.Handler) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, "/admin/refresh/status", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	return w
}

// decodeStatus reads the GET /admin/refresh/status body's "state" field.
func decodeStatus(t *testing.T, w *httptest.ResponseRecorder) string {
	t.Helper()
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode status: %v", err)
	}
	state, _ := resp["state"].(string)
	return state
}

// waitForState polls GET /admin/refresh/status until it reaches want or times out.
func waitForState(t *testing.T, handler http.Handler, want string) {
	t.Helper()
	deadline := time.After(2 * time.Second)
	for {
		if decodeStatus(t, getStatus(handler)) == want {
			return
		}
		select {
		case <-deadline:
			t.Fatalf("status never reached %q", want)
		case <-time.After(5 * time.Millisecond):
		}
	}
}

// ─── tests ─────────────────────────────────────────────────────────────────

// TestRefresh_Accepted_Returns202Immediately — POST returns 202 BEFORE the fake
// Refresher (blocked on a channel) finishes, proving the call is async.
func TestRefresh_Accepted_Returns202Immediately(t *testing.T) {
	block := make(chan struct{})
	started := make(chan struct{})
	handler := buildAdminTestHandler(&fakeRefresher{block: block, started: started}, "")

	w := postRefresh(handler, "")

	// 202 must come back while the fake is still blocked (not yet released).
	if w.Code != http.StatusAccepted {
		t.Fatalf("status = %d; want 202", w.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "accepted" {
		t.Errorf("status = %v; want accepted", resp["status"])
	}

	// The refresh goroutine should have entered Refresh and be blocked.
	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("refresh goroutine did not start")
	}

	// Release and let it finish so the goroutine doesn't leak.
	close(block)
	waitForState(t, handler, "ok")
}

// TestRefresh_Async_StatusOk — after the fake completes successfully, GET
// /admin/refresh/status reports state ok.
func TestRefresh_Async_StatusOk(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "")

	if w := postRefresh(handler, ""); w.Code != http.StatusAccepted {
		t.Fatalf("status = %d; want 202", w.Code)
	}

	waitForState(t, handler, "ok")
}

// TestRefresh_Async_StatusError — when the fake returns an error, GET
// /admin/refresh/status eventually reports state error.
func TestRefresh_Async_StatusError(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{err: errors.New("boom")}, "")

	if w := postRefresh(handler, ""); w.Code != http.StatusAccepted {
		t.Fatalf("status = %d; want 202", w.Code)
	}

	waitForState(t, handler, "error")

	// Confirm the error message is surfaced in the status payload.
	var resp map[string]any
	if err := json.NewDecoder(getStatus(handler).Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["error"] == "" || resp["error"] == nil {
		t.Errorf("expected non-empty error field, got: %v", resp)
	}
}

// TestRefresh_InFlight_Returns409 — a second POST while the first is still
// running gets 409 busy.
func TestRefresh_InFlight_Returns409(t *testing.T) {
	block := make(chan struct{})
	started := make(chan struct{})
	handler := buildAdminTestHandler(&fakeRefresher{block: block, started: started}, "")

	// First request returns 202 immediately, but its goroutine blocks in Refresh.
	if w1 := postRefresh(handler, ""); w1.Code != http.StatusAccepted {
		t.Fatalf("first status = %d; want 202", w1.Code)
	}

	// Wait until the first refresh has actually entered Refresh (slot claimed).
	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("first refresh did not start in time")
	}

	// Second request must be rejected with 409 busy.
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

	// Release the first request and confirm it completed (status ok).
	close(block)
	waitForState(t, handler, "ok")
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

// TestRefresh_TokenSet_Correct_Returns202.
func TestRefresh_TokenSet_Correct_Returns202(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "secret-token")

	w := postRefresh(handler, "secret-token")

	if w.Code != http.StatusAccepted {
		t.Fatalf("status = %d; want 202", w.Code)
	}
	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "accepted" {
		t.Errorf("status = %v; want accepted", resp["status"])
	}

	waitForState(t, handler, "ok")
}

// TestStatus_InitiallyIdle — before any refresh, GET status reports idle.
func TestStatus_InitiallyIdle(t *testing.T) {
	handler := buildAdminTestHandler(&fakeRefresher{}, "")

	w := getStatus(handler)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d; want 200", w.Code)
	}
	if got := decodeStatus(t, w); got != "idle" {
		t.Errorf("state = %q; want idle", got)
	}
}
