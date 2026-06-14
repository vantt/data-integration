// Package domain — shared error types for CRM domain.
// Services wrap user-facing validation failures in ValidationError so HTTP
// handlers can distinguish them (400) from infrastructure errors (500).
package domain

import "errors"

// ErrNotFound is returned when a requested entity does not exist.
var ErrNotFound = errors.New("not found")

// ValidationError signals a request that violates a domain rule and is safe
// to surface to the caller (400 Bad Request).
type ValidationError struct {
	Message string
}

func (e *ValidationError) Error() string { return e.Message }

// NewValidationError wraps a user-visible message in a ValidationError.
func NewValidationError(msg string) error { return &ValidationError{Message: msg} }

// IsValidationError returns true when err is (or wraps) a *ValidationError.
func IsValidationError(err error) bool {
	var ve *ValidationError
	return errors.As(err, &ve)
}
