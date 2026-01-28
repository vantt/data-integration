# Sapo API Sources

> Sapo e-commerce platform API reference

## API Overview

### Base URL

```
https://{store_name}.mysapo.net/admin/
```

### Authentication

```http
GET /admin/orders.json
Authorization: Basic {base64(api_key:api_secret)}
```

### Rate Limits

| Tier | Requests/minute | Burst |
|------|-----------------|-------|
| Standard | 40 | 80 |
| Premium | 120 | 240 |

**Handling:** Implement exponential backoff on 429 responses.

---

## Orders API

### List Orders

```http
GET /admin/orders.json
```

**Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (1-indexed) |
| `limit` | int | Items per page (max 250) |
| `modified_on_min` | datetime | Filter by modification time |
| `modified_on_max` | datetime | Upper bound |
| `status` | string | Order status filter |
| `created_on_min` | datetime | Filter by creation time |

**Example:**

```bash
curl "https://store.mysapo.net/admin/orders.json?limit=250&modified_on_min=2026-01-01T00:00:00Z" \
  -H "Authorization: Basic $(echo -n 'key:secret' | base64)"
```

**Response:**

```json
{
  "orders": [
    {
      "id": 12345678,
      "code": "SON000001",
      "status": "confirmed",
      "fulfillment_status": "pending",
      "payment_status": "paid",
      "total": 500000,
      "total_discount": 50000,
      "customer_id": 9876543,
      "location_id": 12345,
      "source_name": "web",
      "created_on": "2026-01-28T10:00:00Z",
      "modified_on": "2026-01-28T10:30:00Z",
      "order_line_items": [...]
    }
  ],
  "metadata": {
    "total": 1234,
    "page": 1,
    "limit": 250
  }
}
```

### Get Single Order

```http
GET /admin/orders/{id}.json
```

---

## Customers API

### List Customers

```http
GET /admin/customers.json
```

**Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number |
| `limit` | int | Items per page (max 250) |
| `created_on_min` | datetime | Filter by creation time |

> **Note:** No reliable `modified_on` filter for customers.

**Response:**

```json
{
  "customers": [
    {
      "id": 9876543,
      "code": "KH000001",
      "name": "Nguyen Van A",
      "email": "customer@example.com",
      "phone": "0901234567",
      "customer_group_name": "VIP",
      "total_spent": 5000000,
      "orders_count": 10,
      "created_on": "2025-01-01T00:00:00Z",
      "modified_on": "2026-01-28T09:00:00Z"
    }
  ]
}
```

### Get Single Customer

```http
GET /admin/customers/{id}.json
```

---

## Accounts API

### List Accounts

```http
GET /admin/accounts.json
```

**Response:**

```json
{
  "accounts": [
    {
      "id": 1001,
      "email": "staff@company.com",
      "full_name": "Nguyen Van B",
      "role": "sales",
      "status": "active"
    }
  ]
}
```

---

## History Log API

### Get Logs

```http
GET /admin/settings/get_logs
```

**Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `from_date` | datetime | Start time (occur_at) |
| `to_date` | datetime | End time |
| `limit` | int | Max items |

**Response:**

```json
{
  "logs": [
    {
      "id": 15132336653,
      "subject_type": "Order",
      "subject_id": 12345678,
      "action": "update",
      "occur_at": "2026-01-28T10:30:00Z",
      "account_id": 1001,
      "changes": {
        "status": ["pending", "confirmed"]
      }
    }
  ]
}
```

### Subject Types

| Subject Type | Entity | API Endpoint |
|--------------|--------|--------------|
| Order | order | /admin/orders/{id}.json |
| Customer | customer | /admin/customers/{id}.json |
| Product | product | /admin/products/{id}.json |
| CustomerAddress | - | Not fetchable directly |
| AccountAuthentication | - | Not fetchable directly |

---

## Webhooks

### Subscribed Events

| Topic | Event | Description |
|-------|-------|-------------|
| `orders/create` | Order created | New order placed |
| `orders/update` | Order updated | Any field changed |
| `orders/paid` | Payment received | Payment status → paid |
| `orders/fulfilled` | Order shipped | Fulfillment status changed |
| `orders/cancelled` | Order cancelled | Status → cancelled |
| `customers/create` | Customer created | New registration |
| `customers/update` | Customer updated | Profile changed |

### Webhook Payload

```json
{
  "webhook_id": "abc123",
  "topic": "orders/update",
  "store_id": 12345,
  "created_at": "2026-01-28T10:30:00Z",
  "data": {
    "id": 12345678,
    "code": "SON000001",
    "status": "confirmed",
    "...": "full order object"
  }
}
```

### HMAC Validation

```javascript
const crypto = require('crypto');

function validateWebhook(payload, signature, secret) {
  const hash = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(payload))
    .digest('hex');
  return hash === signature;
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 401 | Unauthorized | Check credentials |
| 404 | Not found | Entity deleted or invalid ID |
| 429 | Rate limited | Backoff and retry |
| 500 | Server error | Retry with backoff |

### Retry Strategy

```python
import time
from typing import Callable

def with_retry(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except ServerError:
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    raise MaxRetriesExceeded()
```

---

## Data Mapping

### Order Status Values

| Status | Description |
|--------|-------------|
| `draft` | Not yet submitted |
| `pending` | Awaiting confirmation |
| `confirmed` | Order confirmed |
| `processing` | Being prepared |
| `completed` | Delivered |
| `cancelled` | Cancelled |

### Payment Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting payment |
| `partial` | Partial payment received |
| `paid` | Fully paid |
| `refunded` | Refunded |

### Fulfillment Status Values

| Status | Description |
|--------|-------------|
| `pending` | Not shipped |
| `partial` | Partially shipped |
| `fulfilled` | Fully shipped |

---

## Related

- [Pipelines](./PIPELINES.md)
- [Configuration](./CONFIGURATION.md)
- [Incremental Strategies](./INCREMENTAL.md)
