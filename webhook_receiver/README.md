# Webhook Ingestion System

High-Performance Webhook Ingestion System for buffering incoming Sapo webhooks.

## Variant Status

| Variant | Path | Status | Tech |
|---------|------|--------|------|
| **Cloudflare Workers + D1** | `cloudflareD1/` | **Active** | TypeScript, Cloudflare Workers, SQLite (D1) |
| **Supabase Edge + PGMQ** | `supabase_queue/` | **Deprecated** | Edge Functions, PostgreSQL (pgmq) |

## Documentation

- [Product Requirements Document (PRD)](./docs/WEBHOOK_INGESTION_PRD.md) - Problem statement and solution analysis.
- [API Specification](./docs/API.md) - Webhook endpoint API
- [Security](./docs/SECURITY.md) - HMAC validation, access control

## Active: Cloudflare Workers + D1

- **Path:** `./cloudflareD1/`
- **Architecture:** Serverless Worker → SQLite D1 Database.
- **Characteristics:** Ultra-low latency (<100ms), High Availability, Cost-effective.
- **Docs:** [cloudflareD1/README.md](./cloudflareD1/README.md) | [Deployment](./cloudflareD1/docs/DEPLOYMENT.md)

## Deprecated: Supabase Edge + PGMQ

> **[DEPRECATED]** — This implementation is no longer in active use.

- **Path:** `./supabase_queue/`
- **Architecture:** Edge Functions → PostgreSQL (pgmq).
- **Docs:** [supabase_queue/README.md](./supabase_queue/README.md)
