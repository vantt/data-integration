// Package application — shared helpers for reading cache.db (wh_* tables).
// Kept separate so segment_service and campaign_service don't duplicate logic.
package application

import "strings"

// isCacheMissingTable returns true when a query error from cache.wh_* indicates
// the table has not yet been created by the Python reverse-ETL sync.
// Mirrors the sqlite adapter's isMissingTable but lives in the application layer
// so services can use it without importing the adapter package.
func isCacheMissingTable(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "no such table")
}
