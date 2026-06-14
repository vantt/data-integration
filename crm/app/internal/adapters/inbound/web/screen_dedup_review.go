// Package web — S04 Dedup Review screen handler.
// Inbound adapter: reads from DedupCandidateLister, PartyLister; executes merge via PartyMerger.
// No business logic here — delegates to application.MergeService / DedupRepo.
package web

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		// S04 — Dedup review list.
		r.Get("/dedup", d.handleDedupReview)

		// M01 — Merge confirm modal + submit.
		r.Get("/dedup/{candidateID}/modal/merge", d.handleModalMergeConfirm)
		r.Post("/dedup/{candidateID}/merge", d.handleMergeParties)

		// Reject candidate (HTMX POST).
		r.Post("/dedup/{candidateID}/reject", d.handleRejectCandidate)
	})
}

// handleDedupReview serves GET /dedup — S04 full page.
func (d *Deps) handleDedupReview(w http.ResponseWriter, r *http.Request) {
	matchRule := r.URL.Query().Get("match_rule")

	candidates, err := d.Dedup.ListCandidates(r.Context(), "pending")
	if err != nil {
		log.Printf("dedup review: list: %v", err)
		candidates = []domain.DedupCandidate{}
	}

	// Filter by match_rule if requested.
	if matchRule != "" {
		filtered := candidates[:0]
		for _, c := range candidates {
			if c.MatchRule == matchRule {
				filtered = append(filtered, c)
			}
		}
		candidates = filtered
	}

	// Pre-fetch party display names for both sides.
	partyNames := d.dedupPartyNames(r, candidates)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.DedupReviewPage(candidates, partyNames, matchRule).Render(r.Context(), w); err != nil {
		log.Printf("dedup review: render: %v", err)
	}
}

// handleModalMergeConfirm serves GET /dedup/{candidateID}/modal/merge — M01 fragment.
func (d *Deps) handleModalMergeConfirm(w http.ResponseWriter, r *http.Request) {
	candidateID := chi.URLParam(r, "candidateID")

	cand, err := d.Dedup.GetCandidate(r.Context(), candidateID)
	if err != nil || cand == nil {
		http.Error(w, "Không tìm thấy candidate", http.StatusNotFound)
		return
	}

	partyA, _ := d.Parties.GetByID(r.Context(), cand.PartyA)
	partyB, _ := d.Parties.GetByID(r.Context(), cand.PartyB)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalMergeConfirm(cand, partyA, partyB).Render(r.Context(), w); err != nil {
		log.Printf("modal merge confirm: render: %v", err)
	}
}

// handleMergeParties serves POST /dedup/{candidateID}/merge — M01 submit.
// Surviving party = PartyA (per spec: "Merge B → A").
func (d *Deps) handleMergeParties(w http.ResponseWriter, r *http.Request) {
	candidateID := chi.URLParam(r, "candidateID")

	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	// Guard: the form must include the confirm checkbox.
	if r.FormValue("confirm") != "1" {
		http.Error(w, "xác nhận bắt buộc", http.StatusBadRequest)
		return
	}

	cand, err := d.Dedup.GetCandidate(r.Context(), candidateID)
	if err != nil || cand == nil {
		http.Error(w, "candidate not found", http.StatusNotFound)
		return
	}

	// Execute merge: Party A survives, Party B is absorbed.
	reason := "manual dedup review"
	_, mergeErr := d.Merger.Merge(r.Context(), cand.PartyA, cand.PartyB, reason, nil)
	if mergeErr != nil {
		log.Printf("merge %s: %v", candidateID, mergeErr)
		http.Error(w, "merge failed: "+mergeErr.Error(), http.StatusInternalServerError)
		return
	}

	// Mark candidate as merged.
	if updErr := d.Dedup.UpdateCandidateStatus(r.Context(), candidateID, "merged", nil); updErr != nil {
		log.Printf("update candidate %s status merged: %v", candidateID, updErr)
	}

	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.Header().Set("HX-Redirect", "/dedup")
	w.WriteHeader(http.StatusOK)
}

// handleRejectCandidate serves POST /dedup/{candidateID}/reject — inline reject action.
func (d *Deps) handleRejectCandidate(w http.ResponseWriter, r *http.Request) {
	candidateID := chi.URLParam(r, "candidateID")

	if err := d.Dedup.UpdateCandidateStatus(r.Context(), candidateID, "rejected", nil); err != nil {
		log.Printf("reject candidate %s: %v", candidateID, err)
		http.Error(w, "failed to reject", http.StatusInternalServerError)
		return
	}

	// HTMX: trigger candidateRejected event so the row can be removed.
	// Use json.Marshal to safely encode the candidateID (avoids injection via path param).
	triggerPayload, err := json.Marshal(map[string]string{"candidateRejected": candidateID})
	if err != nil {
		log.Printf("reject candidate %s: marshal trigger: %v", candidateID, err)
		triggerPayload = []byte(`{"candidateRejected":""}`)
	}
	w.Header().Set("HX-Trigger", string(triggerPayload))
	// Return an empty 200 — the caller uses hx-target + hx-swap="outerHTML" to remove the row.
	w.WriteHeader(http.StatusOK)
}

// ── helpers ───────────────────────────────────────────────────────────────────

// dedupPartyNames builds a partyID → displayName map for all parties referenced in candidates.
func (d *Deps) dedupPartyNames(r *http.Request, candidates []domain.DedupCandidate) map[string]string {
	seen := make(map[string]bool, len(candidates)*2)
	out := make(map[string]string, len(candidates)*2)
	for _, c := range candidates {
		for _, pid := range []string{c.PartyA, c.PartyB} {
			if seen[pid] {
				continue
			}
			seen[pid] = true
			if p, err := d.Parties.GetByID(r.Context(), pid); err == nil && p != nil {
				out[pid] = p.DisplayName
			}
		}
	}
	return out
}

