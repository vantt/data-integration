# Webhook Ingestion System

Repository contains two implementation strategies for a High-Performance Webhook Ingestion System.

## Documentation

- [Product Requirements Document (PRD)](./docs/WEBHOOK_INGESTION_PRD.md) - Problem statement and solution analysis.

## Solutions

### 1. [Cloudflare Workers + D1 (Recommended)](./cloudflare_webhook/TECHNICAL_DOCS.md)

- **Path:** `./cloudflare_webhook`
- **Architecture:** Serverless Worker -> SQLite D1 Database.
- **Characteristics:** Ultra-low latency (<100ms), High Availability, Cost-effective.
- **Best for:** High-volume webhooks requiring instant ACK and durable buffering.

### 2. [Supabase Edge + PGMQ (Legacy)](./supabase_queue/README.md)

- **Path:** `./supabase_queue`
- **Architecture:** Edge Functions -> PostgreSQL (pgmq).
- **Characteristics:** Robust SQL features, slightly higher latency.
- **Status:** Archived/Legacy implementation.
