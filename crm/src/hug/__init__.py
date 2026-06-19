"""Hug — local-side token provisioning package.

Owns a dedicated SQLite master (``hug.db``) for the Hug touchpoint token
lifecycle (printed -> bound). Kept separate from ``crm.db`` because Hug has a
distinct lifecycle: tokens are minted/printed offline (CLI), bound at a claim
station, and pushed one-way to the Cloudflare D1 edge cache. Decoupling the
schema avoids coupling Hug to the crm.db migration chain and the warehouse
sync, and prevents write contention with the CRM server's single writer.

Modules:
  config        — env-driven settings (data dir, HUG_DOMAIN, Worker URL/secret)
  tokens        — Crockford base32 token generation + human-readable formatting
  db            — hug.db connection + schema bootstrap (hug_token master)
  repository    — mint / claim / query operations on hug_token
  d1_push       — config-gated HMAC push of bound tokens to the Worker admin route
"""
