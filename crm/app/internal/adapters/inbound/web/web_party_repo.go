// Package web — WebPartyRepo: minimal party queries needed by the web adapter.
// Wraps the existing *sql.DB (same connection used by sqlite.PartyRepo) to add
// ListAll (paginated) without touching the ports layer or the sqlcgen layer.
//
// This is an inbound-adapter-local helper, not a new outbound port — it lives
// here to keep the ports layer clean and avoid YAGNI additions to the shared interface.
package web

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// WebPartyRepo satisfies PartyLister.
// It embeds ports.PartyRepository to re-use GetByID / SearchByName / ListByPhone,
// and adds ListAll via a raw query on the injected *sql.DB.
type WebPartyRepo struct {
	ports.PartyRepository           // GetByID, SearchByName, ListByPhone
	db                    *sql.DB  // shared connection — read-only queries only
}

// NewWebPartyRepo constructs a WebPartyRepo.
// db must be the same *sql.DB from sqlite.DB.SQLDB().
func NewWebPartyRepo(base ports.PartyRepository, db *sql.DB) PartyLister {
	return &WebPartyRepo{PartyRepository: base, db: db}
}

// ListAll returns a page of non-merged parties ordered by display_name, plus the total count.
func (r *WebPartyRepo) ListAll(ctx context.Context, offset, limit int) ([]domain.Party, int, error) {
	const countQ = `SELECT COUNT(*) FROM crm_party WHERE is_merged = 0`
	var total int
	if err := r.db.QueryRowContext(ctx, countQ).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("web party repo: count parties: %w", err)
	}

	const listQ = `
		SELECT party_id, party_type,
		       COALESCE(display_name,''), COALESCE(primary_phone,''), COALESCE(primary_email,''),
		       status, is_merged, COALESCE(merged_into,''), created_at, updated_at
		FROM crm_party
		WHERE is_merged = 0
		ORDER BY display_name ASC
		LIMIT ? OFFSET ?`

	rows, err := r.db.QueryContext(ctx, listQ, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("web party repo: list all: %w", err)
	}
	defer rows.Close()

	var out []domain.Party
	for rows.Next() {
		var p domain.Party
		var mergedInto string
		var isMerged int64
		if err := rows.Scan(
			&p.PartyID, &p.PartyType,
			&p.DisplayName, &p.PrimaryPhone, &p.PrimaryEmail,
			&p.Status, &isMerged, &mergedInto,
			&p.CreatedAt, &p.UpdatedAt,
		); err != nil {
			return nil, 0, fmt.Errorf("web party repo: scan: %w", err)
		}
		p.IsMerged = isMerged != 0
		if mergedInto != "" {
			p.MergedInto = &mergedInto
		}
		out = append(out, p)
	}
	if err := rows.Err(); err != nil {
		return nil, 0, fmt.Errorf("web party repo: rows: %w", err)
	}
	return out, total, nil
}

// GetByID delegates to the embedded PartyRepository.
func (r *WebPartyRepo) GetByID(ctx context.Context, partyID string) (*domain.Party, error) {
	return r.PartyRepository.GetByID(ctx, partyID)
}

// SearchByName delegates to the embedded PartyRepository.
func (r *WebPartyRepo) SearchByName(ctx context.Context, query string) ([]string, error) {
	return r.PartyRepository.SearchByName(ctx, query)
}

// ListByPhone delegates to the embedded PartyRepository.
func (r *WebPartyRepo) ListByPhone(ctx context.Context, phone string) ([]domain.Party, error) {
	return r.PartyRepository.ListByPhone(ctx, phone)
}
