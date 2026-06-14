// Package domain — Campaign and CampaignTarget entities + status-transition rules.
// Pure domain: no adapter or infrastructure imports.
package domain

import "fmt"

// Campaign is a reactivation / winback / upsell / cross-sell effort targeting a segment.
type Campaign struct {
	CampaignID  string  `json:"campaign_id"`
	Name        string  `json:"name"`
	Objective   string  `json:"objective"` // reactivation|winback|upsell|crosssell
	Channel     string  `json:"channel"`
	SegmentID   *string `json:"segment_id,omitempty"`
	Status      string  `json:"status"` // draft|running|done
	ScheduledAt *string `json:"scheduled_at,omitempty"`
	CreatedBy   *string `json:"created_by,omitempty"`
	CreatedAt   string  `json:"created_at"`
	UpdatedAt   string  `json:"updated_at"`
}

// CampaignTarget is one party in a campaign's outreach list.
type CampaignTarget struct {
	CampaignID           string  `json:"campaign_id"`
	PartyID              string  `json:"party_id"`
	Status               string  `json:"status"` // queued|sent|responded|converted|skipped
	AssignedUserID       *string `json:"assigned_user_id,omitempty"`
	LastTouchAt          *string `json:"last_touch_at,omitempty"`
	ConvertedOrderCode   *string `json:"converted_order_code,omitempty"`
	ConvertedRevenueVND  *int64  `json:"converted_revenue_vnd,omitempty"`
	ConvertedAt          *string `json:"converted_at,omitempty"`
}

// CampaignROI is the summary output of GetCampaignROI.
type CampaignROI struct {
	CampaignID          string         `json:"campaign_id"`
	StatusCounts        map[string]int `json:"status_counts"`
	TotalTargets        int            `json:"total_targets"`
	TotalConvertedRevVND int64         `json:"total_converted_revenue_vnd"`
}

// ValidCampaignObjectives enumerates allowed campaign objective values.
var ValidCampaignObjectives = map[string]struct{}{
	"reactivation": {},
	"winback":      {},
	"upsell":       {},
	"crosssell":    {},
}

// ValidCampaignStatuses enumerates allowed campaign status values.
var ValidCampaignStatuses = map[string]struct{}{
	"draft":   {},
	"running": {},
	"done":    {},
}

// ValidTargetStatuses enumerates allowed campaign_target status values.
var ValidTargetStatuses = map[string]struct{}{
	"queued":    {},
	"sent":      {},
	"responded": {},
	"converted": {},
	"skipped":   {},
}

// campaignTransitions maps current → allowed next statuses.
var campaignTransitions = map[string][]string{
	"draft":   {"running"},
	"running": {"done"},
	"done":    {}, // terminal
}

// targetTransitions maps current → allowed next statuses.
var targetTransitions = map[string][]string{
	"queued":    {"sent", "skipped"},
	"sent":      {"responded", "converted", "skipped"},
	"responded": {"converted", "skipped"},
	"converted": {}, // terminal
	"skipped":   {}, // terminal
}

// CanTransitionCampaign returns nil when the status transition is allowed,
// or a descriptive error otherwise.
func CanTransitionCampaign(current, next string) error {
	allowed, ok := campaignTransitions[current]
	if !ok {
		return fmt.Errorf("unknown campaign status %q", current)
	}
	for _, a := range allowed {
		if a == next {
			return nil
		}
	}
	return fmt.Errorf("campaign cannot transition from %q to %q", current, next)
}

// CanTransitionTarget returns nil when the target status transition is allowed.
func CanTransitionTarget(current, next string) error {
	allowed, ok := targetTransitions[current]
	if !ok {
		return fmt.Errorf("unknown target status %q", current)
	}
	for _, a := range allowed {
		if a == next {
			return nil
		}
	}
	return fmt.Errorf("target cannot transition from %q to %q", current, next)
}

// terminalTargetStatuses holds status values from which no further transitions are allowed.
// ScanConversions uses this to skip targets that are already in a terminal state.
var terminalTargetStatuses = map[string]struct{}{
	"converted": {},
	"skipped":   {},
}

// CanReceiveConversion returns true when a target in the given status is eligible
// to be auto-converted by ScanConversions. The scan is an automated process that can
// short-circuit the human workflow steps (queued→sent→responded), so any non-terminal
// status is considered eligible. Terminal states (converted, skipped) are not.
func CanReceiveConversion(status string) bool {
	_, isTerminal := terminalTargetStatuses[status]
	return !isTerminal
}
