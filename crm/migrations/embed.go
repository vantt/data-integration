// Package migrations embeds all SQL migration files for use with golang-migrate iofs source.
package migrations

import "embed"

// FS holds all *.sql migration files embedded at compile time.
//
//go:embed *.sql
var FS embed.FS
