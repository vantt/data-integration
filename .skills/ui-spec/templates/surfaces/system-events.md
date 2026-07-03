---
id: system-events
type: cross-cutting
name: "System Events"
status: active
---

# System Events

## Purpose
Defines system-initiated interactions — events the app handles autonomously without direct user
input. Examples: WebSocket push, polling refresh, auth token expiry, background sync completion.

## How to Use
- Add one interaction per system event.
- Use `trigger: system_event` and `listens_to` to name the event source.
- Reference the surface(s) affected in the `effects` array or via a separate surface contract.

## Events

```yaml {project}-contract
system: core

interactions:
  # Auth token expiry — redirect to login
  # - element: auth_guard
  #   listens_to: auth.token_expired
  #   action: navigate
  #   target: S01
  #   effects: ["clear_session", "show_toast_session_expired"]
  #
  # WebSocket push — refresh data table
  # - element: data_table
  #   listens_to: ws.records_updated
  #   action: mutate
  #   effects: ["reload_table_data"]
  #
  # Background sync complete — show notification
  # - element: notification_bar
  #   listens_to: sync.completed
  #   action: mutate
  #   effects: ["show_sync_success_banner"]
  #
  # Connection lost — show offline banner
  # - element: status_bar
  #   listens_to: network.offline
  #   action: mutate
  #   effects: ["show_offline_banner", "disable_write_actions"]
```

## Event Catalogue

| Event | Source | Surfaces Affected | Notes |
|-------|--------|-------------------|-------|
| `auth.token_expired` | Auth service | All authenticated screens | Forces re-login |
| `ws.records_updated` | WebSocket | Dashboard, list screens | Incremental update |
| `sync.completed` | Sync worker | Any screen with sync indicator | |
| `network.offline` | Browser API | All screens | Disables writes |
