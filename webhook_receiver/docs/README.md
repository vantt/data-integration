# Webhook Receiver Documentation

> Cloudflare Workers + D1 for high-availability webhook buffering

## Overview

The webhook receiver buffers incoming Sapo webhooks using Cloudflare Workers and D1 (serverless SQLite). This provides high availability and prevents data loss when the local consumer is offline.

## Architecture

```
Sapo Platform
      │
      │ POST /webhook/{source}/{entity}/{action}
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE EDGE                               │
│                                                                 │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │   Cloudflare Worker │      │       D1 Database           │  │
│  │                     │      │       (SQLite)              │  │
│  │  • Validate HMAC    │      │                             │  │
│  │  • Parse payload    │◄────►│  messages table:            │  │
│  │  • Insert to D1     │      │  • id (UUID)                │  │
│  │  • Return 200 OK    │      │  • status                   │  │
│  │                     │      │  • source, entity, action   │  │
│  └─────────────────────┘      │  • payload (JSON)           │  │
│                               │  • created_at               │  │
│                               │  • locked_until             │  │
│                               └─────────────────────────────┘  │
└───────────────────────────────────────┬─────────────────────────┘
                                        │
             Poll every 1 minute        │ GET /poll
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL CONSUMER                                │
│                                                                 │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │  dlt Webhook        │      │    Parquet Files            │  │
│  │  Consumer           │─────►│    ingest_method=webhook    │  │
│  │                     │      └─────────────────────────────┘  │
│  │  • Poll messages    │                                       │
│  │  • Transform        │                                       │
│  │  • Write Parquet    │      ┌─────────────────────────────┐  │
│  │  • ACK to D1        │─────►│    POST /ack-batch          │  │
│  └─────────────────────┘      └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Deploy Worker

```bash
cd webhook_receiver/cloudflareD1

# Install dependencies
npm install

# Configure wrangler.toml with your Cloudflare credentials

# Deploy
npx wrangler deploy
```

### Test Endpoint

```bash
# Health check
curl https://your-worker.workers.dev/health

# Test webhook (requires HMAC signature in production)
curl -X POST https://your-worker.workers.dev/webhook/sapo/order/update \
  -H "Content-Type: application/json" \
  -d '{"id": 123, "status": "confirmed"}'
```

## Directory Structure

```
webhook_receiver/
├── cloudflareD1/
│   ├── src/
│   │   ├── index.ts        # Worker entry point
│   │   ├── routes.ts       # Route handlers
│   │   └── db.ts           # D1 operations
│   ├── schema.sql          # D1 table definitions
│   ├── wrangler.toml       # Cloudflare configuration
│   ├── package.json        # Dependencies
│   └── tsconfig.json       # TypeScript config
└── docs/
    ├── README.md           # This file
    ├── API.md              # API documentation
    └── SECURITY.md         # Security configuration
```

## Documentation

| Document | Description |
|----------|-------------|
| [API.md](./API.md) | API endpoint documentation |
| [SECURITY.md](./SECURITY.md) | HMAC validation and security |

## Key Features

### High Availability

- Cloudflare's global edge network (99.99% uptime)
- No local server dependency for receiving webhooks
- Automatic failover and load balancing

### At-Least-Once Delivery

- Messages persisted in D1 before acknowledgment
- Locked messages auto-release after timeout
- Consumer can retry failed messages

### Message Locking

Prevents duplicate processing:

1. Consumer calls `GET /poll` → messages locked for 5 minutes
2. Consumer processes and writes to Parquet
3. Consumer calls `POST /ack-batch` → messages deleted
4. If consumer fails, lock expires → messages available again

## Message Lifecycle

```
PENDING ──► PROCESSING ──► DONE (deleted)
    │            │
    │            └── (timeout) ──► PENDING (retry)
    │
    └── (manual release) ──► PENDING
```

## Configuration

### wrangler.toml

```toml
name = "sapo-webhook-receiver"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[[d1_databases]]
binding = "DB"
database_name = "webhook-buffer"
database_id = "your-database-id"

[vars]
ENVIRONMENT = "production"
```

### Environment Variables

Set in Cloudflare dashboard:

| Variable | Description |
|----------|-------------|
| `HMAC_SECRET` | Sapo webhook signature secret |
| `ALLOWED_ORIGINS` | CORS allowed origins |

## Monitoring

### Cloudflare Dashboard

- **Workers Analytics**: Request count, errors, latency
- **D1 Analytics**: Query count, row count, storage

### Custom Metrics

```typescript
// In worker code
console.log(JSON.stringify({
  metric: "webhook_received",
  source: source,
  entity: entity,
  action: action,
  timestamp: Date.now()
}));
```

View in Cloudflare Workers logs.

## Troubleshooting

### Messages Not Being Received

1. Check worker is deployed: `curl https://your-worker.workers.dev/health`
2. Check D1 binding in wrangler.toml
3. Check Sapo webhook configuration

### Consumer Not Processing

1. Check consumer is running: `ps aux | grep webhook_consumer`
2. Check D1 queue: `curl https://your-worker.workers.dev/poll?limit=1&dry_run=true`
3. Check consumer logs

### Messages Stuck in Processing

```bash
# Release all locked messages
curl -X POST https://your-worker.workers.dev/release-all
```

## Related

- [Main Documentation](../../docs/README.md)
- [Ingestion Layer](../../ingestion/docs/README.md)
- [Data Flow](../../docs/DATA_FLOW.md)
