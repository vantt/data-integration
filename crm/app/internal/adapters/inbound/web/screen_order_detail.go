// Package web — S12 Order Detail screen handler.
// Reads order aggregates from olap.duckdb via the OrderReader interface.
// Routes: GET /orders/{orderCode} (full page) + GET /orders/{orderCode}/tabs/{tab} (HTMX fragments).
package web

import (
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		r.Get("/orders/{orderCode}", d.handleOrderDetail)
		r.Get("/orders/{orderCode}/tabs/{tab}", d.handleOrderTab)
	})
}

// validTabs is the set of recognised tab names for the order detail page.
var validTabs = map[string]bool{
	"financial":  true,
	"items":      true,
	"operations": true,
	"context":    true,
}

// handleOrderDetail serves GET /orders/{orderCode} — full order detail page.
// Reads the optional ?tab= query param so bookmarked/refreshed URLs land on the
// correct tab. Defaults to "financial" when the param is absent or unrecognised.
func (d *Deps) handleOrderDetail(w http.ResponseWriter, r *http.Request) {
	orderCode := chi.URLParam(r, "orderCode")

	if d.Orders == nil {
		http.Error(w, "Order reader unavailable — olap.duckdb not mounted", http.StatusServiceUnavailable)
		return
	}

	o, err := d.Orders.GetByCode(r.Context(), orderCode)
	if err != nil {
		log.Printf("order detail: get %s: %v", orderCode, err)
		http.Error(w, "Lỗi truy vấn đơn hàng", http.StatusInternalServerError)
		return
	}
	if o == nil {
		http.NotFound(w, r)
		return
	}

	activeTab := r.URL.Query().Get("tab")
	if !validTabs[activeTab] {
		activeTab = "financial"
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.OrderDetailPage(o, activeTab).Render(r.Context(), w); err != nil {
		log.Printf("order detail: render %s: %v", orderCode, err)
	}
}

// handleOrderTab serves GET /orders/{orderCode}/tabs/{tab} — HTMX tab fragments.
func (d *Deps) handleOrderTab(w http.ResponseWriter, r *http.Request) {
	orderCode := chi.URLParam(r, "orderCode")
	tab := chi.URLParam(r, "tab")

	if d.Orders == nil {
		http.Error(w, "Order reader unavailable", http.StatusServiceUnavailable)
		return
	}

	o, err := d.Orders.GetByCode(r.Context(), orderCode)
	if err != nil {
		log.Printf("order tab: get %s: %v", orderCode, err)
		http.Error(w, "Lỗi truy vấn đơn hàng", http.StatusInternalServerError)
		return
	}
	if o == nil {
		http.NotFound(w, r)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	switch tab {
	case "financial":
		if err := templates.OrderFinancialTab(o).Render(r.Context(), w); err != nil {
			log.Printf("order tab financial: render: %v", err)
		}
	case "items":
		if err := templates.OrderItemsTab(o).Render(r.Context(), w); err != nil {
			log.Printf("order tab items: render: %v", err)
		}
	case "operations":
		if err := templates.OrderOperationsTab(o).Render(r.Context(), w); err != nil {
			log.Printf("order tab operations: render: %v", err)
		}
	case "context":
		if err := templates.OrderContextTab(o).Render(r.Context(), w); err != nil {
			log.Printf("order tab context: render: %v", err)
		}
	default:
		http.NotFound(w, r)
	}
}
