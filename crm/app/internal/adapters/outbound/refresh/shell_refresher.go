// Package refresh provides the outbound adapter that runs the reverse-ETL +
// syncparties refresh by shelling out to /app/refresh.sh inside the container.
//
// It implements the inbound http.Refresher port. Only used at runtime in the
// container — handler tests use a fake Refresher, so this adapter is never
// exercised in unit tests (it would actually shell out).
package refresh

import (
	"context"
	"fmt"
	"os/exec"
	"time"

	inboundhttp "github.com/vantt/data-integration/crm/app/internal/adapters/inbound/http"
)

// defaultScriptPath is the in-container path to the refresh script (baked into
// the image by Dockerfile.crm). Overridable via CRM_REFRESH_SCRIPT.
const defaultScriptPath = "/app/refresh.sh"

// outputTailBytes caps how much combined output we retain in the result, so a
// chatty sync run doesn't bloat the JSON response / logs. Keeps the tail.
const outputTailBytes = 4096

// ShellRefresher runs the refresh script via exec.CommandContext.
type ShellRefresher struct {
	scriptPath string
}

// NewShellRefresher constructs the adapter. An empty scriptPath falls back to
// the default /app/refresh.sh.
func NewShellRefresher(scriptPath string) *ShellRefresher {
	if scriptPath == "" {
		scriptPath = defaultScriptPath
	}
	return &ShellRefresher{scriptPath: scriptPath}
}

// Refresh runs the script, captures combined stdout/stderr, and returns the
// result. A non-zero exit (or context timeout) yields an error; the captured
// output tail is returned in the result either way for diagnosis.
func (s *ShellRefresher) Refresh(ctx context.Context) (inboundhttp.RefreshResult, error) {
	started := time.Now()

	cmd := exec.CommandContext(ctx, s.scriptPath)
	out, err := cmd.CombinedOutput()

	finished := time.Now()
	res := inboundhttp.RefreshResult{
		StartedAt:  started,
		FinishedAt: finished,
		DurationMs: finished.Sub(started).Milliseconds(),
		Output:     tail(string(out), outputTailBytes),
	}

	if err != nil {
		return res, fmt.Errorf("refresh script %q failed: %w", s.scriptPath, err)
	}
	return res, nil
}

// tail returns the last n bytes of s, prefixed with an ellipsis when truncated.
func tail(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return "…" + s[len(s)-n:]
}
