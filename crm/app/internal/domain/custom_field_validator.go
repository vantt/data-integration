// Package domain — pure custom-field validation logic.
// No adapter imports; unit-testable without a database.
package domain

import (
	"fmt"
	"strconv"
	"strings"
	"time"
)

// CustomFieldError describes a single validation failure for one field key.
type CustomFieldError struct {
	FieldKey string
	Message  string
}

func (e CustomFieldError) Error() string {
	return fmt.Sprintf("custom field %q: %s", e.FieldKey, e.Message)
}

// ValidateCustomField validates a single (def, rawValue) pair.
//
// Rules:
//   - If is_required and rawValue is empty-string → error.
//   - If rawValue is "" and not required → skip type check (allow clearing).
//   - text: any non-nil string is valid.
//   - number: must parse as float64.
//   - date: must match YYYY-MM-DD.
//   - bool: must be "true" or "false" (case-insensitive).
//   - select: rawValue must be in def.Options.
//   - multiselect: rawValue is a comma-separated list; each item must be in def.Options.
func ValidateCustomField(def CustomFieldDef, rawValue string) error {
	// Required check.
	if def.IsRequired && strings.TrimSpace(rawValue) == "" {
		return CustomFieldError{FieldKey: def.FieldKey, Message: "required field is missing or empty"}
	}
	// Allow clearing optional fields.
	if rawValue == "" {
		return nil
	}

	switch def.DataType {
	case "text":
		// Any non-empty string is valid.
		return nil

	case "number":
		if _, err := strconv.ParseFloat(rawValue, 64); err != nil {
			return CustomFieldError{
				FieldKey: def.FieldKey,
				Message:  fmt.Sprintf("expected a number, got %q", rawValue),
			}
		}

	case "date":
		// Expect YYYY-MM-DD (10 chars, basic format check).
		if !isValidDate(rawValue) {
			return CustomFieldError{
				FieldKey: def.FieldKey,
				Message:  fmt.Sprintf("expected date YYYY-MM-DD, got %q", rawValue),
			}
		}

	case "bool":
		lower := strings.ToLower(rawValue)
		if lower != "true" && lower != "false" {
			return CustomFieldError{
				FieldKey: def.FieldKey,
				Message:  fmt.Sprintf("expected true or false, got %q", rawValue),
			}
		}

	case "select":
		if !containsOption(def.Options, rawValue) {
			return CustomFieldError{
				FieldKey: def.FieldKey,
				Message:  fmt.Sprintf("value %q not in allowed options %v", rawValue, def.Options),
			}
		}

	case "multiselect":
		items := splitCSV(rawValue)
		for _, item := range items {
			if !containsOption(def.Options, item) {
				return CustomFieldError{
					FieldKey: def.FieldKey,
					Message:  fmt.Sprintf("value %q not in allowed options %v", item, def.Options),
				}
			}
		}

	default:
		// Unknown data_type: skip validation (forward-compatible).
		return nil
	}

	return nil
}

// ValidateCustomMap validates a map of field-key→value against a slice of active defs.
//
// Behaviour:
//   - Unknown keys (not in defs) are allowed but not validated (forward-compatible).
//   - Required active fields missing from customMap are flagged.
//   - Known keys are validated by data_type and options.
//
// Returns a slice of all errors (not short-circuit) so the caller can surface all issues at once.
func ValidateCustomMap(defs []CustomFieldDef, customMap map[string]string) []CustomFieldError {
	defsByKey := make(map[string]CustomFieldDef, len(defs))
	for _, d := range defs {
		if d.IsActive {
			defsByKey[d.FieldKey] = d
		}
	}

	var errs []CustomFieldError

	// Validate known keys present in the incoming map.
	for key, val := range customMap {
		def, known := defsByKey[key]
		if !known {
			continue // unknown key — allowed, not validated
		}
		if err := ValidateCustomField(def, val); err != nil {
			var cfe CustomFieldError
			if asCustomFieldError(err, &cfe) {
				errs = append(errs, cfe)
			}
		}
	}

	// Check required active fields absent from the map.
	for key, def := range defsByKey {
		if !def.IsRequired {
			continue
		}
		val, present := customMap[key]
		if !present || strings.TrimSpace(val) == "" {
			errs = append(errs, CustomFieldError{
				FieldKey: key,
				Message:  "required field is missing or empty",
			})
		}
	}

	return errs
}

// --- helpers ---

// isValidDate checks YYYY-MM-DD using time.Parse for full calendar validation
// (rejects 2024-02-31, impossible month/day combos, etc.).
func isValidDate(s string) bool {
	_, err := time.Parse("2006-01-02", s)
	return err == nil
}

// containsOption returns true if item (trimmed) is present in options (case-sensitive).
func containsOption(options []string, item string) bool {
	item = strings.TrimSpace(item)
	for _, o := range options {
		if o == item {
			return true
		}
	}
	return false
}

// splitCSV splits a comma-separated string, trimming whitespace from each element.
func splitCSV(s string) []string {
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		t := strings.TrimSpace(p)
		if t != "" {
			out = append(out, t)
		}
	}
	return out
}

// asCustomFieldError type-asserts err to CustomFieldError and fills dst.
func asCustomFieldError(err error, dst *CustomFieldError) bool {
	if cfe, ok := err.(CustomFieldError); ok {
		*dst = cfe
		return true
	}
	return false
}
