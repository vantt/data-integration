// Package web — registry pattern for parallel-safe screen registration.
//
// Each screen file calls register() in its init() function to add its route
// registration callback. Mount() iterates the slice and wires every screen
// onto the chi router. This lets future agents add new screens in their own
// files without ever editing a shared routes file.
package web

import "github.com/go-chi/chi/v5"

// registrationFn is the signature each screen's init() must provide.
type registrationFn func(r chi.Router, d *Deps)

// registrations collects all screen registration callbacks.
// Populated via register() called from each screen's init().
var registrations []registrationFn

// register appends one or more registration callbacks to the global list.
// Call from init() inside each screen file.
func register(fns ...registrationFn) {
	registrations = append(registrations, fns...)
}
