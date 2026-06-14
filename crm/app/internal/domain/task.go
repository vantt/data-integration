// Package domain — Task entity and status transition rules.
// No adapter imports allowed here.
package domain

import "fmt"

// Task is a follow-up work item assigned to a staff member.
// Tasks can be created manually or auto-generated from wh_action_queue.
type Task struct {
	TaskID          string  // UUID
	PartyID         *string // FK → crm_party (nullable — task may not be linked yet)
	Title           string
	Description     string
	DueAt           *string // UTC ISO-8601 nullable
	Priority        int     // 0=normal, higher=more urgent
	Status          string  // open|doing|done|cancelled
	AssigneeUserID  *string // FK → crm_app_user nullable
	Source          string  // manual|action_queue|campaign
	SourceRef       *string // action_id or campaign_id (idempotency key)
	CreatedBy       *string // FK → crm_app_user nullable
	CreatedAt       string  // UTC ISO-8601
	UpdatedAt       string  // UTC ISO-8601
	CompletedAt     *string // UTC ISO-8601 nullable
}

// ValidTaskStatuses lists accepted status values in declaration order.
var ValidTaskStatuses = []string{"open", "doing", "done", "cancelled"}

// ValidTaskSources lists accepted source values.
var ValidTaskSources = []string{"manual", "action_queue", "campaign"}

// IsValidTaskStatus returns true when s is an accepted task status.
func IsValidTaskStatus(s string) bool {
	for _, v := range ValidTaskStatuses {
		if v == s {
			return true
		}
	}
	return false
}

// allowedTransitions maps current status → set of reachable next statuses.
var allowedTransitions = map[string][]string{
	"open":      {"doing", "done", "cancelled"},
	"doing":     {"done", "cancelled", "open"},
	"done":      {"open"},       // allow re-open
	"cancelled": {"open"},       // allow re-open
}

// CanTransitionTo returns nil when the transition from current → next is valid,
// or a descriptive error when it is forbidden.
func CanTransitionTo(current, next string) error {
	if current == next {
		return nil // no-op is always allowed
	}
	targets, ok := allowedTransitions[current]
	if !ok {
		return fmt.Errorf("task: unknown current status %q", current)
	}
	for _, t := range targets {
		if t == next {
			return nil
		}
	}
	return fmt.Errorf("task: transition %q → %q is not allowed", current, next)
}
