// Package http contains the inbound HTTP handlers for the CRM server.
package http

import (
	"context"
	"encoding/json"
	"net/http"
)

// HealthChecker is the minimal interface the health handler needs from the database layer.
// *sqlite.DB satisfies this interface via its Ping and CacheAttached methods.
type HealthChecker interface {
	Ping(ctx context.Context) error
	CacheAttached(ctx context.Context) bool
}

type healthResponse struct {
	Status        string `json:"status"`
	CrmDB         bool   `json:"crm_db"`
	CacheAttached bool   `json:"cache_attached"`
}

// HealthHandler returns an HTTP handler for GET /healthz.
// Returns 200 if both crm.db is reachable and cache schema is attached; 503 otherwise.
func HealthHandler(db HealthChecker) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		resp := healthResponse{}

		// Check crm.db reachability.
		if err := db.Ping(r.Context()); err == nil {
			resp.CrmDB = true
		}

		// Confirm cache schema is attached and readable.
		resp.CacheAttached = db.CacheAttached(r.Context())

		resp.Status = "ok"
		statusCode := http.StatusOK
		if !resp.CrmDB || !resp.CacheAttached {
			resp.Status = "degraded"
			statusCode = http.StatusServiceUnavailable
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)
		_ = json.NewEncoder(w).Encode(resp)
	}
}
