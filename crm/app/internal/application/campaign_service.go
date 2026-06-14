// Package application — CampaignService: campaign CRUD, target generation,
// status transitions, conversion scanning, and ROI summary.
// Pure domain + ports only; no adapter imports.
package application

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ictZone is Asia/Ho_Chi_Minh (UTC+7, no DST). Used for date_key derivation.
// A fixed zone avoids the tzdata dependency on Windows while remaining accurate
// for Vietnam (which has used UTC+7 exclusively since 1975).
var ictZone = time.FixedZone("ICT", 7*3600)

// CampaignService handles campaign lifecycle and target management.
type CampaignService struct {
	campaignRepo ports.CampaignRepository
	segmentRepo  ports.SegmentRepository
	partyRepo    ports.PartyRepository
	db           sqlQuerier // raw *sql.DB for cache queries (wh_order_hdr)
}

// NewCampaignService constructs a CampaignService.
func NewCampaignService(
	campaignRepo ports.CampaignRepository,
	segmentRepo ports.SegmentRepository,
	partyRepo ports.PartyRepository,
	db sqlQuerier,
) *CampaignService {
	return &CampaignService{
		campaignRepo: campaignRepo,
		segmentRepo:  segmentRepo,
		partyRepo:    partyRepo,
		db:           db,
	}
}

// CreateCampaign validates and stores a new campaign.
func (s *CampaignService) CreateCampaign(ctx context.Context, c *domain.Campaign) error {
	if strings.TrimSpace(c.Name) == "" {
		return domain.NewValidationError("campaign name is required")
	}
	if _, ok := domain.ValidCampaignObjectives[c.Objective]; !ok {
		return domain.NewValidationError(fmt.Sprintf("invalid objective %q — must be one of: reactivation, winback, upsell, crosssell", c.Objective))
	}
	now := utcNow()
	if c.CampaignID == "" {
		c.CampaignID = uuid.New().String()
	}
	if c.Status == "" {
		c.Status = "draft"
	}
	c.CreatedAt = now
	c.UpdatedAt = now
	return s.campaignRepo.Insert(ctx, c)
}

// GetCampaign returns a campaign by ID, or nil if not found.
func (s *CampaignService) GetCampaign(ctx context.Context, campaignID string) (*domain.Campaign, error) {
	return s.campaignRepo.GetByID(ctx, campaignID)
}

// UpdateCampaign applies mutable field changes with status-transition validation.
func (s *CampaignService) UpdateCampaign(ctx context.Context, campaignID string, patch *domain.Campaign) error {
	c, err := s.campaignRepo.GetByID(ctx, campaignID)
	if err != nil {
		return fmt.Errorf("campaign service: update: %w", err)
	}
	if c == nil {
		return domain.NewValidationError(fmt.Sprintf("campaign %q not found", campaignID))
	}
	// Validate status transition when status changes.
	if patch.Status != "" && patch.Status != c.Status {
		if err := domain.CanTransitionCampaign(c.Status, patch.Status); err != nil {
			return domain.NewValidationError(err.Error())
		}
		c.Status = patch.Status
	}
	if patch.Name != "" {
		c.Name = patch.Name
	}
	if patch.Objective != "" {
		if _, ok := domain.ValidCampaignObjectives[patch.Objective]; !ok {
			return domain.NewValidationError(fmt.Sprintf("invalid objective %q", patch.Objective))
		}
		c.Objective = patch.Objective
	}
	if patch.Channel != "" {
		c.Channel = patch.Channel
	}
	if patch.SegmentID != nil {
		c.SegmentID = patch.SegmentID
	}
	if patch.ScheduledAt != nil {
		c.ScheduledAt = patch.ScheduledAt
	}
	c.UpdatedAt = utcNow()
	return s.campaignRepo.Update(ctx, c)
}

// ListCampaigns returns all campaigns.
func (s *CampaignService) ListCampaigns(ctx context.Context) ([]domain.Campaign, error) {
	return s.campaignRepo.List(ctx)
}

// GenerateTargets creates crm_campaign_target rows from the campaign's segment members.
// COMPLIANCE: parties with consent_contact=0 are excluded.
// Idempotent: existing targets are left unchanged (ON CONFLICT DO NOTHING).
// Returns the number of targets created.
func (s *CampaignService) GenerateTargets(ctx context.Context, campaignID string) (int, error) {
	c, err := s.campaignRepo.GetByID(ctx, campaignID)
	if err != nil {
		return 0, fmt.Errorf("campaign service: generate targets: %w", err)
	}
	if c == nil {
		return 0, domain.NewValidationError(fmt.Sprintf("campaign %q not found", campaignID))
	}
	if c.SegmentID == nil {
		return 0, domain.NewValidationError("campaign has no segment")
	}

	members, err := s.segmentRepo.ListMembers(ctx, *c.SegmentID)
	if err != nil {
		return 0, fmt.Errorf("campaign service: list segment members: %w", err)
	}

	// Fetch consent status for all parties in one pass using raw SQL.
	// Non-consenting parties must be excluded (GDPR/compliance rule).
	consentMap, err := s.fetchConsentMap(ctx)
	if err != nil {
		return 0, fmt.Errorf("campaign service: fetch consent: %w", err)
	}

	created := 0
	for _, m := range members {
		// Skip non-consenting parties (default consent=1 when profile absent).
		if consent, ok := consentMap[m.PartyID]; ok && !consent {
			continue
		}
		err := s.campaignRepo.UpsertTarget(ctx, &domain.CampaignTarget{
			CampaignID: campaignID,
			PartyID:    m.PartyID,
			Status:     "queued",
		})
		if err != nil {
			return created, fmt.Errorf("campaign service: upsert target %s: %w", m.PartyID, err)
		}
		created++
	}
	return created, nil
}

// UpdateTargetStatus applies a status transition to a campaign target.
func (s *CampaignService) UpdateTargetStatus(ctx context.Context, campaignID, partyID, newStatus string) error {
	if _, ok := domain.ValidTargetStatuses[newStatus]; !ok {
		return domain.NewValidationError(fmt.Sprintf("invalid target status %q", newStatus))
	}
	t, err := s.campaignRepo.GetTarget(ctx, campaignID, partyID)
	if err != nil {
		return fmt.Errorf("campaign service: update target: %w", err)
	}
	if t == nil {
		return domain.NewValidationError(fmt.Sprintf("target (%s, %s) not found", campaignID, partyID))
	}
	if err := domain.CanTransitionTarget(t.Status, newStatus); err != nil {
		return domain.NewValidationError(err.Error())
	}
	now := utcNow()
	t.Status = newStatus
	t.LastTouchAt = &now
	return s.campaignRepo.UpdateTarget(ctx, t)
}

// AssignTarget sets or changes the assigned staff user for a campaign target.
func (s *CampaignService) AssignTarget(ctx context.Context, campaignID, partyID, userID string) error {
	t, err := s.campaignRepo.GetTarget(ctx, campaignID, partyID)
	if err != nil {
		return fmt.Errorf("campaign service: assign target: %w", err)
	}
	if t == nil {
		return domain.NewValidationError(fmt.Sprintf("target (%s, %s) not found", campaignID, partyID))
	}
	t.AssignedUserID = &userID
	return s.campaignRepo.UpdateTarget(ctx, t)
}

// ListTargets returns all targets for a campaign, optionally filtered by status.
// Returns a ValidationError (→ 400) when status is non-empty and not a known value.
func (s *CampaignService) ListTargets(ctx context.Context, campaignID, status string) ([]domain.CampaignTarget, error) {
	if status != "" {
		if _, ok := domain.ValidTargetStatuses[status]; !ok {
			return nil, domain.NewValidationError(fmt.Sprintf("invalid target status %q — must be one of: queued, sent, responded, converted, skipped", status))
		}
	}
	return s.campaignRepo.ListTargetsByCampaignAndStatus(ctx, campaignID, status)
}

// ScanConversions checks cache.wh_order_hdr for orders placed after the campaign's
// scheduled_at by each queued/sent/responded target party.
//
// Conversion rule: earliest qualifying order (date_key >= campaign scheduled_at date) → converted.
// Idempotent: already-converted targets are not overwritten.
// Graceful-empty: if cache tables are absent, returns (0, nil).
func (s *CampaignService) ScanConversions(ctx context.Context, campaignID string) (int, error) {
	c, err := s.campaignRepo.GetByID(ctx, campaignID)
	if err != nil {
		return 0, fmt.Errorf("campaign service: scan conversions: %w", err)
	}
	if c == nil {
		return 0, domain.NewValidationError(fmt.Sprintf("campaign %q not found", campaignID))
	}

	// Compute the date_key threshold (ICT YYYYMMDD integer) from scheduled_at.
	// date_key in wh_order_hdr is ICT (Asia/Ho_Chi_Minh = UTC+7); must compare in ICT
	// to avoid ±1 day drift on the conversion window boundary.
	// If scheduled_at is nil, use today in ICT.
	scheduledDateKey := todayICTDateKey()
	if c.ScheduledAt != nil && len(*c.ScheduledAt) >= 10 {
		// scheduled_at is RFC3339; parse then convert to ICT date for date_key comparison.
		scheduledDateKey = dateToICTKey(*c.ScheduledAt)
	}

	// Fetch all non-converted targets.
	targets, err := s.campaignRepo.ListTargets(ctx, campaignID)
	if err != nil {
		return 0, fmt.Errorf("campaign service: list targets: %w", err)
	}

	converted := 0
	for _, t := range targets {
		// Skip targets that cannot accept a conversion — specifically terminal states
		// (converted, skipped) and any unknown state. queued/sent/responded are eligible
		// because ScanConversions is an automated process that can short-circuit the
		// human workflow (e.g. a party places an order before the agent contacts them).
		if !domain.CanReceiveConversion(t.Status) {
			continue
		}

		orderCode, revenue, orderDate, found, qErr := s.findEarliestOrder(ctx, t.PartyID, scheduledDateKey)
		if qErr != nil {
			if isCacheMissingTable(qErr) {
				return converted, nil // cache absent — graceful exit
			}
			return converted, fmt.Errorf("campaign service: find order for party %s: %w", t.PartyID, qErr)
		}
		if !found {
			continue
		}

		t.Status = "converted"
		t.ConvertedOrderCode = &orderCode
		t.ConvertedRevenueVND = &revenue
		t.ConvertedAt = &orderDate
		if err := s.campaignRepo.UpdateTarget(ctx, &t); err != nil {
			return converted, fmt.Errorf("campaign service: mark converted %s: %w", t.PartyID, err)
		}
		converted++
	}
	return converted, nil
}

// GetTarget returns a single campaign target by (campaignID, partyID), or nil if not found.
// Used by the web adapter to load target state before recording a manual conversion.
func (s *CampaignService) GetTarget(ctx context.Context, campaignID, partyID string) (*domain.CampaignTarget, error) {
	t, err := s.campaignRepo.GetTarget(ctx, campaignID, partyID)
	if err != nil {
		return nil, fmt.Errorf("campaign service: get target: %w", err)
	}
	return t, nil
}

// RecordConversion persists a manually confirmed conversion for a target.
// Sets status=converted, stores order_code and revenue when provided.
// Returns a ValidationError when the target is already in a terminal state.
func (s *CampaignService) RecordConversion(ctx context.Context, t *domain.CampaignTarget) error {
	if t == nil {
		return domain.NewValidationError("target must not be nil")
	}
	existing, err := s.campaignRepo.GetTarget(ctx, t.CampaignID, t.PartyID)
	if err != nil {
		return fmt.Errorf("campaign service: record conversion get target: %w", err)
	}
	if existing == nil {
		return domain.NewValidationError(fmt.Sprintf("target (%s, %s) not found", t.CampaignID, t.PartyID))
	}
	if !domain.CanReceiveConversion(existing.Status) {
		return domain.NewValidationError(fmt.Sprintf("target already in terminal status %q", existing.Status))
	}
	now := utcNow()
	existing.Status = "converted"
	existing.LastTouchAt = &now
	existing.ConvertedAt = &now
	if t.ConvertedOrderCode != nil {
		existing.ConvertedOrderCode = t.ConvertedOrderCode
	}
	if t.ConvertedRevenueVND != nil {
		existing.ConvertedRevenueVND = t.ConvertedRevenueVND
	}
	return s.campaignRepo.UpdateTarget(ctx, existing)
}

// GetROI returns a summary of a campaign's target statuses and total converted revenue.
func (s *CampaignService) GetROI(ctx context.Context, campaignID string) (*domain.CampaignROI, error) {
	targets, err := s.campaignRepo.ListTargets(ctx, campaignID)
	if err != nil {
		return nil, fmt.Errorf("campaign service: roi: %w", err)
	}

	counts := map[string]int{}
	var totalRev int64
	for _, t := range targets {
		counts[t.Status]++
		if t.Status == "converted" && t.ConvertedRevenueVND != nil {
			totalRev += *t.ConvertedRevenueVND
		}
	}
	return &domain.CampaignROI{
		CampaignID:           campaignID,
		StatusCounts:         counts,
		TotalTargets:         len(targets),
		TotalConvertedRevVND: totalRev,
	}, nil
}

// ─── helpers ──────────────────────────────────────────────────────────────────

// fetchConsentMap returns a map[partyID]bool from crm_customer_profile.consent_contact.
// Parties with no profile row default to consented (true).
// crm_customer_profile is created by migration 0003 and is always present in production.
// Only a genuine missing-table error (sqlite no such table) is silently tolerated —
// any other error is propagated to prevent silently treating all parties as consenting
// (which would be a compliance bypass).
func (s *CampaignService) fetchConsentMap(ctx context.Context) (map[string]bool, error) {
	const q = `SELECT party_id, consent_contact FROM crm_customer_profile`
	rows, err := s.db.QueryContext(ctx, q)
	if err != nil {
		if isCacheMissingTable(err) {
			// Bare test environment without migrations — treat everyone as consenting.
			return map[string]bool{}, nil
		}
		return nil, fmt.Errorf("campaign service: fetch consent map: %w", err)
	}
	defer rows.Close()

	out := map[string]bool{}
	for rows.Next() {
		var partyID string
		var consent int64
		if err := rows.Scan(&partyID, &consent); err != nil {
			return nil, fmt.Errorf("campaign service: scan consent: %w", err)
		}
		out[partyID] = consent != 0
	}
	return out, rows.Err()
}

// findEarliestOrder looks up the earliest order in cache.wh_order_hdr for a party
// (via sapo_customer identity) with date_key >= scheduledDateKey.
// Returns (orderCode, netRevenue, date, found, error).
func (s *CampaignService) findEarliestOrder(ctx context.Context, partyID string, scheduledDateKey int) (string, int64, string, bool, error) {
	const q = `
		SELECT oh.order_code, oh.net_revenue, oh.date_key
		FROM cache.wh_order_hdr oh
		JOIN crm_party_identity pi2
			ON pi2.identity_type = 'sapo_customer'
			AND oh.customer_id = CAST(pi2.identity_value AS INTEGER)
		WHERE pi2.party_id = ?
		  AND oh.date_key >= ?
		ORDER BY oh.date_key ASC
		LIMIT 1`

	resultRows, qErr := s.db.QueryContext(ctx, q, partyID, scheduledDateKey)
	if qErr != nil {
		return "", 0, "", false, qErr
	}
	defer resultRows.Close()

	if !resultRows.Next() {
		return "", 0, "", false, resultRows.Err()
	}

	var orderCode sql.NullString
	var netRevenue sql.NullInt64
	var dateKey int64
	if err := resultRows.Scan(&orderCode, &netRevenue, &dateKey); err != nil {
		return "", 0, "", false, err
	}

	// Convert date_key YYYYMMDD int → UTC ISO-8601 string for converted_at.
	dk := fmt.Sprintf("%d", dateKey)
	var dateStr string
	if len(dk) == 8 {
		dateStr = dk[:4] + "-" + dk[4:6] + "-" + dk[6:] + "T00:00:00.000Z"
	} else {
		dateStr = utcNow()
	}

	return orderCode.String, netRevenue.Int64, dateStr, true, nil
}

// todayICTDateKey returns today's date as an ICT YYYYMMDD integer.
// Uses ictZone (Asia/Ho_Chi_Minh = UTC+7) to match wh_order_hdr.date_key semantics.
func todayICTDateKey() int {
	return timeToDateKey(time.Now().In(ictZone))
}

// dateToICTKey parses an RFC3339 timestamp string and returns its ICT date as YYYYMMDD int.
// If the string cannot be parsed as RFC3339, falls back to treating the first 10 characters
// as a YYYY-MM-DD literal (UTC-aligned; acceptable for fixed historical campaign dates).
func dateToICTKey(ts string) int {
	if t, err := time.Parse(time.RFC3339, ts); err == nil {
		return timeToDateKey(t.In(ictZone))
	}
	// Fallback: treat "2026-01-15..." as a local date (no TZ drift for date-only strings).
	if len(ts) < 10 {
		return 0
	}
	var key int
	fmt.Sscanf(ts[0:4]+ts[5:7]+ts[8:10], "%d", &key)
	return key
}

// timeToDateKey formats a time.Time as YYYYMMDD integer.
func timeToDateKey(t time.Time) int {
	var key int
	fmt.Sscanf(t.Format("20060102"), "%d", &key)
	return key
}
