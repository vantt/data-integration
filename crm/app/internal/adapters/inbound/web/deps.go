// Package web — inbound web adapter for the CRM (templ + HTMX).
// Auth: DEFERRED — LAN-trust only (per plan). No auth middleware here.
//
// Hexagonal boundary: this package depends only on narrow interfaces satisfied
// by the existing application services. No direct imports of sqlite adapters
// or application concrete types.
package web

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── narrow service interfaces ────────────────────────────────────────────────
// Each interface lists only the methods the web handlers actually call.
// The existing application services satisfy these without modification.

// ActionQueueReader reads all rows from the warehouse action queue.
// Satisfied by ports.CacheRepository (via sqlite.CacheRepo).
type ActionQueueReader interface {
	ListAllActionQueue(ctx context.Context) ([]domain.ActionQueueItem, error)
}

// TaskQuerier lists and fetches tasks.
// Satisfied by *application.TaskService.
type TaskQuerier interface {
	ListTasks(ctx context.Context, assigneeUserID, status string) ([]domain.Task, error)
	GetTask(ctx context.Context, taskID string) (*domain.Task, error)
}

// TaskWriter mutates task state.
// Satisfied by *application.TaskService.
type TaskWriter interface {
	TransitionStatus(ctx context.Context, taskID, newStatus string) error
}

// PartySearcher provides party lookup and search.
// Satisfied by the sqlite.PartyRepo (via its embedded *sql.DB for ListAll).
type PartySearcher interface {
	GetByID(ctx context.Context, partyID string) (*domain.Party, error)
	SearchByName(ctx context.Context, query string) ([]string, error)
	ListByPhone(ctx context.Context, phone string) ([]domain.Party, error)
}

// PartyLister provides paginated party listing.
// Satisfied by *WebPartyRepo (wraps sqlite *sql.DB with a hand-written ListAll query).
type PartyLister interface {
	ListAll(ctx context.Context, offset, limit int) ([]domain.Party, int, error)
	GetByID(ctx context.Context, partyID string) (*domain.Party, error)
	SearchByName(ctx context.Context, query string) ([]string, error)
	ListByPhone(ctx context.Context, phone string) ([]domain.Party, error)
}

// ProfileReader fetches the Customer 360 composed view.
// Satisfied by *application.ProfileService.
type ProfileReader interface {
	GetParty360(ctx context.Context, partyID string) (*domain.Party360, error)
}

// InsightReader fetches cached warehouse insight.
// Satisfied by ports.CacheRepository (via sqlite.CacheRepo).
type InsightReader interface {
	GetCustomerInsight(ctx context.Context, customerID int64) (*domain.CacheInsight, error)
}

// IdentityReader resolves party identities.
// Satisfied by ports.PartyRepository.
type IdentityReader interface {
	ListIdentities(ctx context.Context, partyID string) ([]domain.PartyIdentity, error)
}

// ActivityReader lists activities for a party.
// Satisfied by *application.ActivityService.
type ActivityReader interface {
	ListTimeline(ctx context.Context, partyID string) ([]domain.Activity, error)
}

// NoteReader lists and adds notes.
// Satisfied by *application.ProfileService.
type NoteReader interface {
	ListNotes(ctx context.Context, partyID string) ([]domain.Note, error)
	AddNote(ctx context.Context, partyID, body string, authorUserID *string) (*domain.Note, error)
}

// TaskPartyQuerier lists tasks for a specific party.
// Satisfied by *WebTaskRepo (wraps sqlite *sql.DB with a hand-written ListByParty query).
type TaskPartyQuerier interface {
	ListByParty(ctx context.Context, partyID string) ([]domain.Task, error)
}

// ─── Deps ─────────────────────────────────────────────────────────────────────

// Deps holds all service interfaces the web adapter needs.
// Wired in main.go from existing concrete service instances.
type Deps struct {
	ActionQueue   ActionQueueReader
	Tasks         TaskQuerier
	TaskWriter    TaskWriter
	Parties       PartyLister
	Profile       ProfileReader
	Insight       InsightReader
	Identities    IdentityReader
	Activities    ActivityReader
	Notes         NoteReader
	PartyTasks    TaskPartyQuerier
}
