// Package sqlite — Customer360 repository adapter.
// Implements ports.ProfileRepository, ports.CustomFieldRepository,
// ports.TagRepository, ports.NoteRepository using sqlc-generated queries.
package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ─── ProfileRepo ─────────────────────────────────────────────────────────────

// ProfileRepo satisfies ports.ProfileRepository.
type ProfileRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewProfileRepo constructs a ProfileRepo.
func NewProfileRepo(db *DB) ports.ProfileRepository {
	return &ProfileRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *ProfileRepo) GetProfile(ctx context.Context, partyID string) (*domain.CustomerProfile, error) {
	row, err := r.q.GetCustomerProfile(ctx, partyID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("profile repo: get: %w", err)
	}
	return rowToProfile(row), nil
}

func (r *ProfileRepo) UpsertProfile(ctx context.Context, p *domain.CustomerProfile) error {
	err := r.q.UpsertCustomerProfile(ctx, sqlcgen.UpsertCustomerProfileParams{
		PartyID:           p.PartyID,
		OwnerUserID:       toNullStringPtr(p.OwnerUserID),
		LifecycleStage:    toNullString(p.LifecycleStage),
		AcquisitionSource: toNullString(p.AcquisitionSource),
		Birthday:          toNullString(p.Birthday),
		Address:           toNullString(p.Address),
		Preferences:       toNullString(p.Preferences),
		Custom:            p.Custom,
		ConsentContact:    boolToInt(p.ConsentContact),
		CreatedAt:         p.CreatedAt,
		UpdatedAt:         p.UpdatedAt,
	})
	if err != nil {
		return fmt.Errorf("profile repo: upsert: %w", err)
	}
	return nil
}

func (r *ProfileRepo) UpdateCustomJSON(ctx context.Context, partyID, customJSON string) error {
	err := r.q.UpdateCustomJSON(ctx, sqlcgen.UpdateCustomJSONParams{
		Custom:  customJSON,
		PartyID: partyID,
	})
	if err != nil {
		return fmt.Errorf("profile repo: update custom json: %w", err)
	}
	return nil
}

func (r *ProfileRepo) GetParty360(ctx context.Context, partyID string) (*domain.Party360, error) {
	row, err := r.q.GetParty360(ctx, partyID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("profile repo: get party360: %w", err)
	}
	return rowToParty360(row), nil
}

// ─── CustomFieldRepo ──────────────────────────────────────────────────────────

// CustomFieldRepo satisfies ports.CustomFieldRepository.
type CustomFieldRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewCustomFieldRepo constructs a CustomFieldRepo.
func NewCustomFieldRepo(db *DB) ports.CustomFieldRepository {
	return &CustomFieldRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *CustomFieldRepo) ListActiveDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error) {
	rows, err := r.q.ListActiveCustomFieldDefs(ctx, entityType)
	if err != nil {
		return nil, fmt.Errorf("customfield repo: list active: %w", err)
	}
	return rowsToCustomFieldDefs(rows), nil
}

func (r *CustomFieldRepo) ListAllDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error) {
	rows, err := r.q.ListAllCustomFieldDefs(ctx, entityType)
	if err != nil {
		return nil, fmt.Errorf("customfield repo: list all: %w", err)
	}
	return rowsToCustomFieldDefs(rows), nil
}

func (r *CustomFieldRepo) GetDef(ctx context.Context, fieldID string) (*domain.CustomFieldDef, error) {
	row, err := r.q.GetCustomFieldDef(ctx, fieldID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("customfield repo: get def: %w", err)
	}
	d := rowToCustomFieldDef(row)
	return &d, nil
}

func (r *CustomFieldRepo) CreateDef(ctx context.Context, d *domain.CustomFieldDef) error {
	err := r.q.InsertCustomFieldDef(ctx, sqlcgen.InsertCustomFieldDefParams{
		FieldID:    d.FieldID,
		EntityType: d.EntityType,
		FieldKey:   d.FieldKey,
		Label:      d.Label,
		DataType:   d.DataType,
		Options:    optionsToNullString(d.Options),
		IsRequired: boolToInt(d.IsRequired),
		IsActive:   boolToInt(d.IsActive),
		SortOrder:  int64(d.SortOrder),
	})
	if err != nil {
		return fmt.Errorf("customfield repo: create def: %w", err)
	}
	return nil
}

func (r *CustomFieldRepo) UpdateDef(ctx context.Context, d *domain.CustomFieldDef) error {
	err := r.q.UpdateCustomFieldDef(ctx, sqlcgen.UpdateCustomFieldDefParams{
		FieldID:    d.FieldID,
		Label:      d.Label,
		Options:    optionsToNullString(d.Options),
		IsRequired: boolToInt(d.IsRequired),
		IsActive:   boolToInt(d.IsActive),
		SortOrder:  int64(d.SortOrder),
	})
	if err != nil {
		return fmt.Errorf("customfield repo: update def: %w", err)
	}
	return nil
}

// ─── TagRepo ──────────────────────────────────────────────────────────────────

// TagRepo satisfies ports.TagRepository.
type TagRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewTagRepo constructs a TagRepo.
func NewTagRepo(db *DB) ports.TagRepository {
	return &TagRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *TagRepo) ListTags(ctx context.Context, category string) ([]domain.Tag, error) {
	var rows []sqlcgen.CrmTag
	var err error
	if category == "" {
		rows, err = r.q.ListAllTags(ctx)
	} else {
		rows, err = r.q.ListTagsByCategory(ctx, toNullString(category))
	}
	if err != nil {
		return nil, fmt.Errorf("tag repo: list: %w", err)
	}
	out := make([]domain.Tag, 0, len(rows))
	for _, row := range rows {
		out = append(out, rowToTag(row))
	}
	return out, nil
}

func (r *TagRepo) GetTag(ctx context.Context, tagID string) (*domain.Tag, error) {
	row, err := r.q.GetTag(ctx, tagID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("tag repo: get: %w", err)
	}
	t := rowToTag(row)
	return &t, nil
}

func (r *TagRepo) CreateTag(ctx context.Context, t *domain.Tag) error {
	err := r.q.CreateTag(ctx, sqlcgen.CreateTagParams{
		TagID:    t.TagID,
		Name:     t.Name,
		Category: toNullString(t.Category),
		Color:    toNullString(t.Color),
	})
	if err != nil {
		return fmt.Errorf("tag repo: create: %w", err)
	}
	return nil
}

func (r *TagRepo) AttachTag(ctx context.Context, pt *domain.PartyTag) error {
	err := r.q.AttachPartyTag(ctx, sqlcgen.AttachPartyTagParams{
		PartyID:  pt.PartyID,
		TagID:    pt.TagID,
		TaggedBy: toNullStringPtr(pt.TaggedBy),
		TaggedAt: pt.TaggedAt,
	})
	if err != nil {
		return fmt.Errorf("tag repo: attach: %w", err)
	}
	return nil
}

func (r *TagRepo) DetachTag(ctx context.Context, partyID, tagID string) error {
	err := r.q.DetachPartyTag(ctx, sqlcgen.DetachPartyTagParams{
		PartyID: partyID,
		TagID:   tagID,
	})
	if err != nil {
		return fmt.Errorf("tag repo: detach: %w", err)
	}
	return nil
}

func (r *TagRepo) ListPartyTags(ctx context.Context, partyID string) ([]domain.Tag, error) {
	rows, err := r.q.ListPartyTags(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("tag repo: list party tags: %w", err)
	}
	out := make([]domain.Tag, 0, len(rows))
	for _, row := range rows {
		out = append(out, rowToTag(row))
	}
	return out, nil
}

// ─── NoteRepo ─────────────────────────────────────────────────────────────────

// NoteRepo satisfies ports.NoteRepository.
type NoteRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewNoteRepo constructs a NoteRepo.
func NewNoteRepo(db *DB) ports.NoteRepository {
	return &NoteRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *NoteRepo) AddNote(ctx context.Context, n *domain.Note) error {
	err := r.q.InsertNote(ctx, sqlcgen.InsertNoteParams{
		NoteID:       n.NoteID,
		PartyID:      n.PartyID,
		Body:         n.Body,
		AuthorUserID: toNullStringPtr(n.AuthorUserID),
		CreatedAt:    n.CreatedAt,
	})
	if err != nil {
		return fmt.Errorf("note repo: add: %w", err)
	}
	return nil
}

func (r *NoteRepo) ListNotes(ctx context.Context, partyID string) ([]domain.Note, error) {
	rows, err := r.q.ListNotesByParty(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("note repo: list: %w", err)
	}
	out := make([]domain.Note, 0, len(rows))
	for _, row := range rows {
		n := domain.Note{
			NoteID:    row.NoteID,
			PartyID:   row.PartyID,
			Body:      row.Body,
			CreatedAt: row.CreatedAt,
		}
		if row.AuthorUserID.Valid {
			s := row.AuthorUserID.String
			n.AuthorUserID = &s
		}
		out = append(out, n)
	}
	return out, nil
}

// ─── mapping helpers ──────────────────────────────────────────────────────────

func rowToProfile(r sqlcgen.CrmCustomerProfile) *domain.CustomerProfile {
	p := &domain.CustomerProfile{
		PartyID:           r.PartyID,
		LifecycleStage:    r.LifecycleStage.String,
		AcquisitionSource: r.AcquisitionSource.String,
		Birthday:          r.Birthday.String,
		Address:           r.Address.String,
		Preferences:       r.Preferences.String,
		Custom:            r.Custom,
		ConsentContact:    r.ConsentContact != 0,
		CreatedAt:         r.CreatedAt,
		UpdatedAt:         r.UpdatedAt,
	}
	if r.OwnerUserID.Valid {
		s := r.OwnerUserID.String
		p.OwnerUserID = &s
	}
	return p
}

func rowToParty360(r sqlcgen.CrmParty360) *domain.Party360 {
	v := &domain.Party360{
		PartyID:           r.PartyID,
		PartyType:         r.PartyType,
		DisplayName:       r.DisplayName.String,
		PrimaryPhone:      r.PrimaryPhone.String,
		PrimaryEmail:      r.PrimaryEmail.String,
		Status:            r.Status,
		IsMerged:          r.IsMerged != 0,
		PartyCreatedAt:    r.PartyCreatedAt,
		PartyUpdatedAt:    r.PartyUpdatedAt,
		LifecycleStage:    r.LifecycleStage.String,
		AcquisitionSource: r.AcquisitionSource.String,
		Birthday:          r.Birthday.String,
		Address:           r.Address.String,
		Preferences:       r.Preferences.String,
		Custom:            r.Custom.String,
		ProfileUpdatedAt:  r.ProfileUpdatedAt.String,
	}
	if r.OwnerUserID.Valid {
		s := r.OwnerUserID.String
		v.OwnerUserID = &s
	}
	if r.ConsentContact.Valid {
		b := r.ConsentContact.Int64 != 0
		v.ConsentContact = &b
	}
	// tags_json comes back as interface{} from sqlc (JSON aggregate); convert to string.
	if r.TagsJson != nil {
		switch tv := r.TagsJson.(type) {
		case string:
			v.TagsJSON = tv
		case []byte:
			v.TagsJSON = string(tv)
		default:
			if b, err := json.Marshal(r.TagsJson); err == nil {
				v.TagsJSON = string(b)
			}
		}
	}
	return v
}

func rowToCustomFieldDef(r sqlcgen.CrmCustomFieldDef) domain.CustomFieldDef {
	d := domain.CustomFieldDef{
		FieldID:    r.FieldID,
		EntityType: r.EntityType,
		FieldKey:   r.FieldKey,
		Label:      r.Label,
		DataType:   r.DataType,
		IsRequired: r.IsRequired != 0,
		IsActive:   r.IsActive != 0,
		SortOrder:  int(r.SortOrder),
	}
	if r.Options.Valid && r.Options.String != "" {
		_ = json.Unmarshal([]byte(r.Options.String), &d.Options)
	}
	return d
}

func rowsToCustomFieldDefs(rows []sqlcgen.CrmCustomFieldDef) []domain.CustomFieldDef {
	out := make([]domain.CustomFieldDef, 0, len(rows))
	for _, r := range rows {
		out = append(out, rowToCustomFieldDef(r))
	}
	return out
}

func rowToTag(r sqlcgen.CrmTag) domain.Tag {
	return domain.Tag{
		TagID:    r.TagID,
		Name:     r.Name,
		Category: r.Category.String,
		Color:    r.Color.String,
	}
}

// optionsToNullString serialises []string → JSON NullString for storage.
func optionsToNullString(opts []string) sql.NullString {
	if len(opts) == 0 {
		return sql.NullString{}
	}
	b, err := json.Marshal(opts)
	if err != nil {
		return sql.NullString{}
	}
	return sql.NullString{String: string(b), Valid: true}
}

