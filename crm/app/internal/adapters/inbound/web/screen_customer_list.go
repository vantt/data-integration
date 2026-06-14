// Package web — S02 Customer List & Search screen handler.
// Inbound adapter: reads from PartyLister. No business logic.
package web

import (
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

const defaultPageSize = 30

func init() {
	register(func(r chi.Router, d *Deps) {
		r.Get("/customers", d.handleCustomerList)
		r.Get("/customers/search", d.handleCustomerSearch)
	})
}

// handleCustomerList serves GET /customers — full paginated list page.
func (d *Deps) handleCustomerList(w http.ResponseWriter, r *http.Request) {
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	page := queryInt(r, "page", 1)
	if page < 1 {
		page = 1
	}
	offset := (page - 1) * defaultPageSize

	var parties []domain.Party
	var total int

	if q != "" {
		parties, total = d.searchParties(r, q)
	} else {
		var err error
		parties, total, err = d.Parties.ListAll(r.Context(), offset, defaultPageSize)
		if err != nil {
			log.Printf("customer list: list all: %v", err)
			parties = []domain.Party{}
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CustomerListPage(parties, total, page, defaultPageSize, q).Render(r.Context(), w); err != nil {
		log.Printf("customer list: render: %v", err)
	}
}

// handleCustomerSearch serves GET /customers/search — HTMX live-search fragment.
// Returns only the <tbody> rows, not the full page shell.
func (d *Deps) handleCustomerSearch(w http.ResponseWriter, r *http.Request) {
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	var parties []domain.Party
	if q != "" {
		parties, _ = d.searchParties(r, q)
	} else {
		var err error
		parties, _, err = d.Parties.ListAll(r.Context(), 0, defaultPageSize)
		if err != nil {
			log.Printf("customer search: list: %v", err)
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CustomerListRows(parties).Render(r.Context(), w); err != nil {
		log.Printf("customer search: render rows: %v", err)
	}
}

// searchParties performs FTS name search + phone prefix search and deduplicates.
// Returns the merged slice and its length as total (no further pagination on search results).
func (d *Deps) searchParties(r *http.Request, q string) ([]domain.Party, int) {
	seen := map[string]bool{}
	var out []domain.Party

	// FTS name search → resolve each ID to a Party.
	if ids, err := d.Parties.SearchByName(r.Context(), q); err == nil {
		for _, id := range ids {
			if seen[id] {
				continue
			}
			p, err := d.Parties.GetByID(r.Context(), id)
			if err == nil && p != nil && !p.IsMerged {
				out = append(out, *p)
				seen[id] = true
			}
		}
	}

	// Phone prefix search.
	if parties, err := d.Parties.ListByPhone(r.Context(), q); err == nil {
		for _, p := range parties {
			if !seen[p.PartyID] && !p.IsMerged {
				out = append(out, p)
				seen[p.PartyID] = true
			}
		}
	}

	return out, len(out)
}

// queryInt extracts an integer query param with a fallback default.
func queryInt(r *http.Request, key string, def int) int {
	s := r.URL.Query().Get(key)
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return def
	}
	return n
}
