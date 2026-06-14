// Package application — ActivityService: log and retrieve activity touchpoints.
// Pure domain + ports only; no adapter imports.
package application

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ActivityService handles business logic for activity logging and timeline retrieval.
type ActivityService struct {
	repo ports.ActivityRepository
}

// NewActivityService constructs an ActivityService.
func NewActivityService(repo ports.ActivityRepository) *ActivityService {
	return &ActivityService{repo: repo}
}

// LogActivity validates and stores a new activity for a party.
func (s *ActivityService) LogActivity(ctx context.Context, a *domain.Activity) error {
	if a.PartyID == "" {
		return fmt.Errorf("activity service: party_id is required")
	}
	if strings.TrimSpace(a.ActivityType) == "" {
		return fmt.Errorf("activity service: activity_type is required")
	}
	if !domain.IsValidActivityType(a.ActivityType) {
		return fmt.Errorf("activity service: unknown activity_type %q", a.ActivityType)
	}

	now := utcNow()
	if a.ActivityID == "" {
		a.ActivityID = uuid.New().String()
	}
	if a.OccurredAt == "" {
		a.OccurredAt = now
	}
	a.CreatedAt = now

	return s.repo.Insert(ctx, a)
}

// ListTimeline returns a party's activities newest-first.
func (s *ActivityService) ListTimeline(ctx context.Context, partyID string) ([]domain.Activity, error) {
	if partyID == "" {
		return nil, fmt.Errorf("activity service: party_id is required")
	}
	acts, err := s.repo.ListByParty(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("activity service: list timeline: %w", err)
	}
	if acts == nil {
		acts = []domain.Activity{}
	}
	return acts, nil
}

// utcNow is defined in party_service.go (same package).
