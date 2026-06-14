// Package http — handler-level tests for InsightHandler.
// Uses net/http/httptest with lightweight mock implementations of the handler interfaces.
// No real SQLite; domain objects are constructed directly.
package http

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── stubs ───────────────────────────────────────────────────────────────────

// stubIdentityReader implements IdentityReader for tests.
type stubIdentityReader struct {
	identities []domain.PartyIdentity
	err        error
}

func (s *stubIdentityReader) ListIdentities(_ context.Context, _ string) ([]domain.PartyIdentity, error) {
	return s.identities, s.err
}

// stubInsightReader implements InsightReader for tests.
type stubInsightReader struct {
	insight *domain.CacheInsight
	err     error
}

func (s *stubInsightReader) GetCustomerInsight(_ context.Context, _ int64) (*domain.CacheInsight, error) {
	return s.insight, s.err
}

// buildInsightTestHandler wires stubs into an InsightHandler and registers routes on a chi router.
func buildInsightTestHandler(ir IdentityReader, cache InsightReader) http.Handler {
	h := NewInsightHandler(ir, cache)
	r := chi.NewRouter()
	h.RegisterRoutes(r)
	return r
}

// ─── helpers ─────────────────────────────────────────────────────────────────

// sapoIdentity builds a minimal PartyIdentity for a sapo_customer.
func sapoIdentity(partyID, customerIDStr string) domain.PartyIdentity {
	return domain.PartyIdentity{
		IdentityID:    "iid-001",
		PartyID:       partyID,
		SourceSystem:  "sapo",
		IdentityType:  "sapo_customer",
		IdentityValue: customerIDStr,
		Confidence:    1.0,
	}
}

// ─── tests ───────────────────────────────────────────────────────────────────

// TestInsight_NoSapoIdentity_Returns404 covers case (a):
// party exists but has no sapo_customer identity → 404.
func TestInsight_NoSapoIdentity_Returns404(t *testing.T) {
	handler := buildInsightTestHandler(
		// Party has only a phone identity, no sapo_customer.
		&stubIdentityReader{identities: []domain.PartyIdentity{
			{IdentityID: "iid-phone", PartyID: "party-001",
				SourceSystem: "manual", IdentityType: "phone",
				IdentityValue: "+84901000001", Confidence: 1.0},
		}},
		&stubInsightReader{},
	)

	req := httptest.NewRequest(http.MethodGet, "/api/parties/party-001/insight", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("status = %d; want 404 for party with no sapo_customer identity", w.Code)
	}

	var resp map[string]string
	_ = json.NewDecoder(w.Body).Decode(&resp)
	if resp["error"] == "" {
		t.Errorf("expected non-empty error field in response body, got: %v", resp)
	}
}

// TestInsight_CacheEmpty_Returns200NullInsight covers case (b):
// sapo_customer identity exists but cache returns nil (wh_* tables absent) → 200 {"insight":null}.
func TestInsight_CacheEmpty_Returns200NullInsight(t *testing.T) {
	handler := buildInsightTestHandler(
		&stubIdentityReader{identities: []domain.PartyIdentity{
			sapoIdentity("party-001", "1001"),
		}},
		// GetCustomerInsight returns nil — cache is empty (graceful-empty contract).
		&stubInsightReader{insight: nil},
	)

	req := httptest.NewRequest(http.MethodGet, "/api/parties/party-001/insight", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d; want 200 when cache is empty", w.Code)
	}

	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	// "insight" key must be present and null.
	insightVal, ok := resp["insight"]
	if !ok {
		t.Errorf("response body missing 'insight' key: %v", resp)
	}
	if insightVal != nil {
		t.Errorf("insight = %v; want null when cache is empty", insightVal)
	}
}

// TestInsight_CachePopulated_Returns200WithData covers case (c):
// sapo_customer identity resolves + cache has data → 200 with insight populated.
func TestInsight_CachePopulated_Returns200WithData(t *testing.T) {
	populated := &domain.CacheInsight{
		Insight: &domain.CustomerInsight{
			CustomerKey:    "key-cust-001",
			CustomerID:     1001,
			ValueGroup:     "VIP",
			CustomerStatus: "active",
		},
		Actions: []domain.ActionQueueItem{
			{
				ActionID:    "act-001",
				CustomerKey: "key-cust-001",
				ActionType:  "REORDER_NUDGE",
				RationaleVI: "Khach sap den chu ky mua",
				Priority:    1,
			},
		},
		RecentOrders: []domain.RecentOrder{
			{
				OrderID:    "ord-001",
				OrderCode:  "HD001",
				CustomerID: 1001,
				DateKey:    20260601,
				NetRevenue: 850000,
				Status:     "completed",
				Channel:    "online",
				ItemCount:  2,
			},
		},
		RefreshedAt: "2026-06-14T00:00:00.000Z",
	}

	handler := buildInsightTestHandler(
		&stubIdentityReader{identities: []domain.PartyIdentity{
			sapoIdentity("party-001", "1001"),
		}},
		&stubInsightReader{insight: populated},
	)

	req := httptest.NewRequest(http.MethodGet, "/api/parties/party-001/insight", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d; want 200 with populated cache", w.Code)
	}

	var resp map[string]any
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	insightVal, ok := resp["insight"]
	if !ok {
		t.Fatalf("response body missing 'insight' key: %v", resp)
	}
	if insightVal == nil {
		t.Fatal("insight is null; want populated insight data")
	}
	// Verify at least one sub-field is present (CustomerInsight.ValueGroup).
	insightMap, ok := insightVal.(map[string]any)
	if !ok {
		t.Fatalf("insight is not a JSON object: %T", insightVal)
	}
	// CacheInsight.Insight is serialised under key "Insight" (Go field name, no json tag).
	// Verify the insight sub-object is not nil via the key set.
	if len(insightMap) == 0 {
		t.Errorf("insight map is empty; want populated data: %v", insightMap)
	}
}
