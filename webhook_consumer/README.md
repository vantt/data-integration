# Webhook Consumer

Workers that poll and consume buffered webhooks, loading them into the data warehouse.

## Variant Status

| Variant | Path | Status | Tech |
|---------|------|--------|------|
| **CloudflareD1 Consumer** | `cloudflared1_consumer/` | **Active** | Python, dlt — polls Cloudflare Worker API |
| **Supabase Consumer** | `supabase_consumer/` | **Deprecated** | TypeScript, Node.js |

## Active: CloudflareD1 Consumer

See [cloudflared1_consumer/README.md](./cloudflared1_consumer/README.md) for setup and usage.

The consumer is typically invoked by the ingestion layer:
```bash
python ingestion/run_webhook_consumer.py --once   # Single poll
python ingestion/run_webhook_consumer.py --loop    # Continuous polling
```

## Deprecated: Supabase Consumer

> **[DEPRECATED]** — The Supabase consumer is no longer in active use. See `supabase_consumer/` for historical reference.

→ See [Webhook Receiver](../webhook_receiver/README.md) for the upstream webhook buffering system.
