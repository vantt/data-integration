// Package web — Mount wires the web adapter onto a chi router.
// Call from main.go after constructing Deps.
package web

import (
	"embed"
	"net/http"

	"github.com/go-chi/chi/v5"
)

//go:embed static
var staticFS embed.FS

// Mount registers the static file server and all screen routes.
// JSON API routes registered elsewhere (under /api) are not affected.
func Mount(r chi.Router, d *Deps) {
	// Serve embedded static assets: /static/htmx.min.js, /static/app.css, etc.
	r.Handle("/static/*", http.FileServer(http.FS(staticFS)))

	// Wire every screen registered via init().
	for _, fn := range registrations {
		fn(r, d)
	}
}
