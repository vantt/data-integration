# Webhook Receiver API

> API endpoint documentation for Cloudflare Worker

## Base URL

```
https://your-worker.workers.dev
```

---

## Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-01-28T10:30:00Z"
}
```

---

### Receive Webhook

```http
POST /webhook/{source}/{entity}/{action}
```

**Path Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `source` | Source system | `sapo` |
| `entity` | Entity type | `order`, `customer` |
| `action` | Event action | `create`, `update` |

**Headers:**

| Header | Description | Required |
|--------|-------------|----------|
| `Content-Type` | Must be `application/json` | Yes |
| `X-Sapo-Hmac-SHA256` | HMAC signature | Yes (production) |

**Request Body:**

Raw webhook payload from Sapo.

**Example:**

```bash
curl -X POST https://your-worker.workers.dev/webhook/sapo/order/update \
  -H "Content-Type: application/json" \
  -H "X-Sapo-Hmac-SHA256: abc123..." \
  -d '{
    "id": 12345678,
    "code": "SON000001",
    "status": "confirmed",
    "total": 500000
  }'
```

**Response (Success):**

```json
{
  "status": "ok",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "received_at": "2026-01-28T10:30:00Z"
}
```

**Response (Error):**

```json
{
  "status": "error",
  "message": "Invalid HMAC signature"
}
```

---

### Poll Messages

```http
GET /poll
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 1000 | Max messages to return |
| `dry_run` | bool | false | If true, don't lock messages |

**Example:**

```bash
curl "https://your-worker.workers.dev/poll?limit=500"
```

**Response:**

```json
{
  "messages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "sapo",
      "entity": "order",
      "action": "update",
      "payload": {
        "id": 12345678,
        "code": "SON000001",
        "status": "confirmed"
      },
      "created_at": "2026-01-28T10:30:00Z"
    }
  ],
  "count": 1,
  "locked_until": "2026-01-28T10:35:00Z"
}
```

**Behavior:**
- Returns pending messages
- Locks messages for 5 minutes (configurable)
- Locked messages won't appear in subsequent polls

---

### Acknowledge Messages

```http
POST /ack-batch
```

**Request Body:**

```json
{
  "ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Example:**

```bash
curl -X POST https://your-worker.workers.dev/ack-batch \
  -H "Content-Type: application/json" \
  -d '{"ids": ["550e8400-e29b-41d4-a716-446655440000"]}'
```

**Response:**

```json
{
  "status": "ok",
  "acknowledged": 1
}
```

**Behavior:**
- Deletes acknowledged messages from D1
- Only works for messages in "processing" status
- Idempotent (acknowledging non-existent ID is OK)

---

### Release Message

```http
POST /release
```

Release a single message for retry.

**Request Body:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**

```json
{
  "status": "ok",
  "released": true
}
```

---

### Release All

```http
POST /release-all
```

Release all locked messages (emergency recovery).

**Response:**

```json
{
  "status": "ok",
  "released": 42
}
```

**Use with caution:** May cause duplicate processing.

---

### Stats

```http
GET /stats
```

**Response:**

```json
{
  "pending": 100,
  "processing": 5,
  "total_received_24h": 1234,
  "oldest_pending": "2026-01-28T08:00:00Z"
}
```

---

## Error Codes

| Status | Message | Cause |
|--------|---------|-------|
| 400 | Invalid request | Malformed JSON |
| 401 | Unauthorized | Missing/invalid HMAC |
| 404 | Not found | Invalid endpoint |
| 500 | Internal error | D1 or worker error |

---

## Rate Limits

| Operation | Limit |
|-----------|-------|
| Webhook receive | 1000/min per source |
| Poll | 60/min |
| Ack | 60/min |

---

## Message Schema

### D1 Table

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    entity TEXT NOT NULL,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    locked_until TEXT,
    lock_id TEXT
);

CREATE INDEX idx_status ON messages(status);
CREATE INDEX idx_created ON messages(created_at);
```

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Waiting to be processed |
| `processing` | Locked by consumer |
| `error` | Processing failed (manual retry needed) |

---

## Consumer Flow

```python
import requests

WORKER_URL = "https://your-worker.workers.dev"

def process_webhooks():
    # 1. Poll messages
    response = requests.get(f"{WORKER_URL}/poll?limit=1000")
    messages = response.json()["messages"]

    # 2. Process each message
    processed_ids = []
    for msg in messages:
        try:
            write_to_parquet(msg)
            processed_ids.append(msg["id"])
        except Exception as e:
            log.error(f"Failed to process {msg['id']}: {e}")

    # 3. Acknowledge processed messages
    if processed_ids:
        requests.post(
            f"{WORKER_URL}/ack-batch",
            json={"ids": processed_ids}
        )
```

---

## Related

- [Security](./SECURITY.md)
- [Main Documentation](../../docs/README.md)
