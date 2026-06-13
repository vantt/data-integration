// Package sqlite — PartyRepository adapter.
// Implements ports.PartyRepository using sqlc-generated queries + one hand-written FTS5 query.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// PartyRepo satisfies ports.PartyRepository.
type PartyRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewPartyRepo constructs a PartyRepo.
func NewPartyRepo(db *DB) ports.PartyRepository {
	return &PartyRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *PartyRepo) FindByIdentity(ctx context.Context, identityType, identityValue string) (*domain.Party, error) {
	row, err := r.q.FindPartyByIdentity(ctx, sqlcgen.FindPartyByIdentityParams{
		IdentityType:  identityType,
		IdentityValue: identityValue,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("party repo: find by identity: %w", err)
	}
	return rowToParty(row), nil
}

func (r *PartyRepo) Create(ctx context.Context, p *domain.Party) error {
	err := r.q.CreateParty(ctx, sqlcgen.CreatePartyParams{
		PartyID:      p.PartyID,
		PartyType:    p.PartyType,
		DisplayName:  toNullString(p.DisplayName),
		PrimaryPhone: toNullString(p.PrimaryPhone),
		PrimaryEmail: toNullString(p.PrimaryEmail),
		Status:       p.Status,
		IsMerged:     boolToInt(p.IsMerged),
		MergedInto:   toNullStringPtr(p.MergedInto),
		CreatedAt:    p.CreatedAt,
		UpdatedAt:    p.UpdatedAt,
	})
	if err != nil {
		return fmt.Errorf("party repo: create: %w", err)
	}
	return nil
}

func (r *PartyRepo) GetByID(ctx context.Context, partyID string) (*domain.Party, error) {
	row, err := r.q.GetPartyByID(ctx, partyID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("party repo: get by id: %w", err)
	}
	return rowToParty(row), nil
}

func (r *PartyRepo) Update(ctx context.Context, p *domain.Party) error {
	err := r.q.UpdateParty(ctx, sqlcgen.UpdatePartyParams{
		PartyID:      p.PartyID,
		DisplayName:  toNullString(p.DisplayName),
		PrimaryPhone: toNullString(p.PrimaryPhone),
		PrimaryEmail: toNullString(p.PrimaryEmail),
		Status:       p.Status,
		IsMerged:     boolToInt(p.IsMerged),
		MergedInto:   toNullStringPtr(p.MergedInto),
	})
	if err != nil {
		return fmt.Errorf("party repo: update: %w", err)
	}
	return nil
}

func (r *PartyRepo) ListByPhone(ctx context.Context, phone string) ([]domain.Party, error) {
	rows, err := r.q.ListPartiesByPhone(ctx, toNullString(phone))
	if err != nil {
		return nil, fmt.Errorf("party repo: list by phone: %w", err)
	}
	return rowsToParties(rows), nil
}

func (r *PartyRepo) ListByEmail(ctx context.Context, email string) ([]domain.Party, error) {
	rows, err := r.q.ListPartiesByEmail(ctx, toNullString(email))
	if err != nil {
		return nil, fmt.Errorf("party repo: list by email: %w", err)
	}
	return rowsToParties(rows), nil
}

// ftsQuote wraps s as a quoted FTS5 phrase, escaping internal double-quotes by doubling them.
// This prevents FTS5 query injection from untrusted name input.
func ftsQuote(s string) string {
	return `"` + strings.ReplaceAll(s, `"`, `""`) + `"`
}

// SearchByName runs an FTS5 MATCH query against crm_party_fts.
// Hand-written because sqlc cannot parse FTS5 virtual table syntax.
// Returns nil (no error) for empty query to avoid an invalid MATCH expression.
func (r *PartyRepo) SearchByName(ctx context.Context, query string) ([]string, error) {
	if query == "" {
		return nil, nil
	}

	const ftsSQL = `
SELECT party_id FROM crm_party_fts
WHERE crm_party_fts MATCH ?
ORDER BY rank
LIMIT 50`

	// Wrap as a quoted phrase to prevent FTS5 operator injection.
	rows, err := r.db.SQLDB().QueryContext(ctx, ftsSQL, ftsQuote(query))
	if err != nil {
		return nil, fmt.Errorf("party repo: fts search: %w", err)
	}
	defer rows.Close()

	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, fmt.Errorf("party repo: fts scan: %w", err)
		}
		ids = append(ids, id)
	}
	return ids, rows.Err()
}

// CreateWithIdentities inserts a party and all supplied identities atomically.
// A mid-way failure rolls back entirely — no orphan party with missing identities.
func (r *PartyRepo) CreateWithIdentities(ctx context.Context, p *domain.Party, identities []*domain.PartyIdentity) error {
	tx, err := r.db.SQLDB().BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("party repo: begin create-with-identities tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	qtx := sqlcgen.New(tx)

	if err := qtx.CreateParty(ctx, sqlcgen.CreatePartyParams{
		PartyID:      p.PartyID,
		PartyType:    p.PartyType,
		DisplayName:  toNullString(p.DisplayName),
		PrimaryPhone: toNullString(p.PrimaryPhone),
		PrimaryEmail: toNullString(p.PrimaryEmail),
		Status:       p.Status,
		IsMerged:     boolToInt(p.IsMerged),
		MergedInto:   toNullStringPtr(p.MergedInto),
		CreatedAt:    p.CreatedAt,
		UpdatedAt:    p.UpdatedAt,
	}); err != nil {
		return fmt.Errorf("party repo: create party in tx: %w", err)
	}

	for _, id := range identities {
		var verifiedAt sql.NullString
		if id.VerifiedAt != nil {
			verifiedAt = sql.NullString{String: *id.VerifiedAt, Valid: true}
		}
		if err := qtx.UpsertPartyIdentity(ctx, sqlcgen.UpsertPartyIdentityParams{
			IdentityID:    id.IdentityID,
			PartyID:       id.PartyID,
			SourceSystem:  id.SourceSystem,
			IdentityType:  id.IdentityType,
			IdentityValue: id.IdentityValue,
			Confidence:    id.Confidence,
			IsPrimary:     boolToInt(id.IsPrimary),
			VerifiedAt:    verifiedAt,
			CreatedAt:     id.CreatedAt,
		}); err != nil {
			return fmt.Errorf("party repo: upsert identity %s in tx: %w", id.IdentityType, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("party repo: commit create-with-identities tx: %w", err)
	}
	return nil
}

func (r *PartyRepo) UpsertIdentity(ctx context.Context, id *domain.PartyIdentity) error {
	var verifiedAt sql.NullString
	if id.VerifiedAt != nil {
		verifiedAt = sql.NullString{String: *id.VerifiedAt, Valid: true}
	}
	err := r.q.UpsertPartyIdentity(ctx, sqlcgen.UpsertPartyIdentityParams{
		IdentityID:    id.IdentityID,
		PartyID:       id.PartyID,
		SourceSystem:  id.SourceSystem,
		IdentityType:  id.IdentityType,
		IdentityValue: id.IdentityValue,
		Confidence:    id.Confidence,
		IsPrimary:     boolToInt(id.IsPrimary),
		VerifiedAt:    verifiedAt,
		CreatedAt:     id.CreatedAt,
	})
	if err != nil {
		return fmt.Errorf("party repo: upsert identity: %w", err)
	}
	return nil
}

func (r *PartyRepo) ListIdentities(ctx context.Context, partyID string) ([]domain.PartyIdentity, error) {
	rows, err := r.q.ListIdentitiesByParty(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("party repo: list identities: %w", err)
	}
	out := make([]domain.PartyIdentity, 0, len(rows))
	for _, row := range rows {
		out = append(out, rowToIdentity(row))
	}
	return out, nil
}

// --- mapping helpers ---

func rowToParty(r sqlcgen.CrmParty) *domain.Party {
	p := &domain.Party{
		PartyID:      r.PartyID,
		PartyType:    r.PartyType,
		DisplayName:  r.DisplayName.String,
		PrimaryPhone: r.PrimaryPhone.String,
		PrimaryEmail: r.PrimaryEmail.String,
		Status:       r.Status,
		IsMerged:     r.IsMerged != 0,
		CreatedAt:    r.CreatedAt,
		UpdatedAt:    r.UpdatedAt,
	}
	if r.MergedInto.Valid {
		s := r.MergedInto.String
		p.MergedInto = &s
	}
	return p
}

func rowsToParties(rows []sqlcgen.CrmParty) []domain.Party {
	out := make([]domain.Party, 0, len(rows))
	for _, r := range rows {
		out = append(out, *rowToParty(r))
	}
	return out
}

func rowToIdentity(r sqlcgen.CrmPartyIdentity) domain.PartyIdentity {
	id := domain.PartyIdentity{
		IdentityID:    r.IdentityID,
		PartyID:       r.PartyID,
		SourceSystem:  r.SourceSystem,
		IdentityType:  r.IdentityType,
		IdentityValue: r.IdentityValue,
		Confidence:    r.Confidence,
		IsPrimary:     r.IsPrimary != 0,
		CreatedAt:     r.CreatedAt,
	}
	if r.VerifiedAt.Valid {
		s := r.VerifiedAt.String
		id.VerifiedAt = &s
	}
	return id
}

func toNullString(s string) sql.NullString {
	return sql.NullString{String: s, Valid: s != ""}
}

func toNullStringPtr(s *string) sql.NullString {
	if s == nil {
		return sql.NullString{}
	}
	return sql.NullString{String: *s, Valid: true}
}

func boolToInt(b bool) int64 {
	if b {
		return 1
	}
	return 0
}
