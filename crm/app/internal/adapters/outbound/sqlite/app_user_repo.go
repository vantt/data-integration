// Package sqlite — AppUserRepository adapter.
// Implements ports.AppUserRepository using sqlc-generated queries.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// AppUserRepo satisfies ports.AppUserRepository.
type AppUserRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewAppUserRepo constructs an AppUserRepo.
func NewAppUserRepo(db *DB) ports.AppUserRepository {
	return &AppUserRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

// GetByEmail returns the AppUser with the given email, or nil if not found.
func (r *AppUserRepo) GetByEmail(ctx context.Context, email string) (*domain.AppUser, error) {
	row, err := r.q.GetAppUserByEmail(ctx, email)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("app user repo: get by email: %w", err)
	}
	return appUserFromRow(row), nil
}

// ListActive returns all active app users ordered by full_name.
func (r *AppUserRepo) ListActive(ctx context.Context) ([]domain.AppUser, error) {
	rows, err := r.q.ListActiveAppUsers(ctx)
	if err != nil {
		return nil, fmt.Errorf("app user repo: list active: %w", err)
	}
	out := make([]domain.AppUser, 0, len(rows))
	for _, row := range rows {
		out = append(out, *appUserFromRow(row))
	}
	return out, nil
}

// appUserFromRow maps a sqlcgen row to domain.AppUser.
func appUserFromRow(row sqlcgen.CrmAppUser) *domain.AppUser {
	u := &domain.AppUser{
		UserID:    row.UserID,
		Email:     row.Email,
		FullName:  row.FullName,
		Role:      row.Role,
		IsActive:  row.IsActive != 0,
		CreatedAt: row.CreatedAt,
		UpdatedAt: row.UpdatedAt,
	}
	if row.StaffID.Valid {
		v := row.StaffID.Int64
		u.StaffID = &v
	}
	return u
}
