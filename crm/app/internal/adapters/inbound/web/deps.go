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

// ─── new interfaces for operational screens ───────────────────────────────────

// ConversationLister lists and fetches conversations (S05 inbox, S06 detail).
// Satisfied by *application.ConversationService.
type ConversationLister interface {
	ListInbox(ctx context.Context, assigneeUserID, status string) ([]domain.Conversation, error)
	GetMessages(ctx context.Context, conversationID string) ([]domain.Message, error)
}

// ConversationWriter mutates conversation state (assign, set status).
// Satisfied by *application.ConversationService.
// Named Writer because all methods modify state; the previous name ConversationReader was misleading.
type ConversationWriter interface {
	AssignConversation(ctx context.Context, conversationID, assigneeUserID string) error
	SetStatus(ctx context.Context, conversationID, newStatus string) error
}

// ConversationPartyLinker links a party to a conversation.
// Thin wrapper around the ConversationRepo — implemented by WebConvRepo (same pattern as WebPartyRepo).
type ConversationPartyLinker interface {
	LinkParty(ctx context.Context, conversationID, partyID string) error
	GetByID(ctx context.Context, conversationID string) (*domain.Conversation, error)
}

// AppUserLister lists active staff users (for assign-conversation dropdown).
// Satisfied by *sqlite.AppUserRepo.
type AppUserLister interface {
	ListActive(ctx context.Context) ([]domain.AppUser, error)
}

// TaskCreator creates a new task.
// Satisfied by *application.TaskService.
type TaskCreator interface {
	CreateTask(ctx context.Context, t *domain.Task) error
}

// TaskGenerator converts action-queue items to tasks.
// Satisfied by *application.TaskService.
type TaskGenerator interface {
	GenerateTasksFromActionQueue(ctx context.Context) (int, error)
}

// DedupCandidateLister lists dedup candidates and updates their status.
// Satisfied by sqlite.DedupRepo (via ports.DedupRepository).
type DedupCandidateLister interface {
	ListCandidates(ctx context.Context, status string) ([]domain.DedupCandidate, error)
	GetCandidate(ctx context.Context, candidateID string) (*domain.DedupCandidate, error)
	UpdateCandidateStatus(ctx context.Context, candidateID, status string, reviewedBy *string) error
}

// PartyMerger executes party merge (M01).
// Satisfied by *application.MergeService.
type PartyMerger interface {
	Merge(ctx context.Context, survivingPartyID, mergedPartyID, reason string, mergedBy *string) (string, error)
}

// ActivityLogger logs activities for a party (M08).
// Satisfied by *application.ActivityService.
type ActivityLogger interface {
	LogActivity(ctx context.Context, a *domain.Activity) error
}

// PartyCreator creates a new party with its initial identities (M02).
// Satisfied by *sqlite.PartyRepo (via ports.PartyRepository).
type PartyCreator interface {
	CreateWithIdentities(ctx context.Context, p *domain.Party, identities []*domain.PartyIdentity) error
}

// OwnerAssigner upserts a customer profile to set the owner (M04).
// Satisfied by *application.ProfileService.
type OwnerAssigner interface {
	UpsertProfile(ctx context.Context, p *domain.CustomerProfile) error
}

// OrderReader fetches a single order aggregate from olap.duckdb (read-only).
// Satisfied by *duckdbadapter.OrderRepo.
type OrderReader interface {
	GetByCode(ctx context.Context, orderCode string) (*domain.OrderDetail, error)
}

// ─── management screen interfaces ─────────────────────────────────────────────

// SegmentManager covers all segment operations needed by S08/S09.
// Satisfied by *application.SegmentService.
type SegmentManager interface {
	ListSegments(ctx context.Context) ([]domain.Segment, error)
	GetSegment(ctx context.Context, segmentID string) (*domain.Segment, error)
	CreateSegment(ctx context.Context, seg *domain.Segment) error
	UpdateSegment(ctx context.Context, seg *domain.Segment) error
	RefreshDynamicSegment(ctx context.Context, segmentID string) (int, error)
	ListMembers(ctx context.Context, segmentID string) ([]domain.SegmentMember, error)
	AddMember(ctx context.Context, segmentID, partyID string) error
	RemoveMember(ctx context.Context, segmentID, partyID string) error
}

// CampaignManager covers all campaign operations needed by S10/S11.
// Satisfied by *application.CampaignService.
type CampaignManager interface {
	ListCampaigns(ctx context.Context) ([]domain.Campaign, error)
	GetCampaign(ctx context.Context, campaignID string) (*domain.Campaign, error)
	CreateCampaign(ctx context.Context, c *domain.Campaign) error
	UpdateCampaign(ctx context.Context, campaignID string, patch *domain.Campaign) error
	GenerateTargets(ctx context.Context, campaignID string) (int, error)
	ListTargets(ctx context.Context, campaignID, status string) ([]domain.CampaignTarget, error)
	GetTarget(ctx context.Context, campaignID, partyID string) (*domain.CampaignTarget, error)
	UpdateTargetStatus(ctx context.Context, campaignID, partyID, newStatus string) error
	RecordConversion(ctx context.Context, t *domain.CampaignTarget) error
	ScanConversions(ctx context.Context, campaignID string) (int, error)
	GetROI(ctx context.Context, campaignID string) (*domain.CampaignROI, error)
}

// SettingsManager covers custom field def + tag management for S13.
// Satisfied by *application.ProfileService.
type SettingsManager interface {
	ListCustomFieldDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error)
	GetCustomFieldDef(ctx context.Context, fieldID string) (*domain.CustomFieldDef, error)
	CreateCustomFieldDef(ctx context.Context, d *domain.CustomFieldDef) error
	UpdateCustomFieldDef(ctx context.Context, d *domain.CustomFieldDef) error
	ListTags(ctx context.Context, category string) ([]domain.Tag, error)
	CreateTag(ctx context.Context, t *domain.Tag) error
}

// ─── Deps ─────────────────────────────────────────────────────────────────────

// Deps holds all service interfaces the web adapter needs.
// Wired in main.go from existing concrete service instances.
type Deps struct {
	ActionQueue   ActionQueueReader
	Tasks         TaskQuerier
	TaskWriter    TaskWriter
	TaskCreator   TaskCreator
	TaskGen       TaskGenerator
	Parties       PartyLister
	Profile       ProfileReader
	Insight       InsightReader
	Identities    IdentityReader
	Activities    ActivityReader
	Notes         NoteReader
	PartyTasks    TaskPartyQuerier
	// Operational screens (S04, S05, S06, S07).
	Conversations ConversationLister
	ConvWriter    ConversationWriter
	ConvLinker    ConversationPartyLinker
	AppUsers      AppUserLister
	Dedup         DedupCandidateLister
	Merger        PartyMerger
	ActivityLog   ActivityLogger
	// Shared modals (M02, M04).
	PartyCreator PartyCreator
	OwnerAssigner OwnerAssigner
	// Management screens (S08, S09, S10, S11, S13).
	Segments    SegmentManager
	Campaigns   CampaignManager
	SettingsMgr SettingsManager
	// Order detail (S12 — reads olap.duckdb via CGO-backed go-duckdb).
	Orders OrderReader
}
