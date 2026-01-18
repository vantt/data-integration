# PRD: High-Performance Webhook Ingestion System

## 1. Context & Problem Statement

The system needs to receive high-volume webhooks from external providers (e.g., Payment Gateways, ERPs). The requirements have evolved to prioritize **Ingestion Speed** and **Reliability**.

### Key Challenges:

- **Strict Latency Requirement:** The receiver must respond with `200 OK` immediately (ideal < 100ms) to prevent sender retries or timeouts.
- **Reliability:** No data loss is tolerated. Messages must be buffered safely even if the downstream consumer (Local App) is offline or slow.
- **Cost Efficiency:** The solution must be cost-effective for a "Receive & Store" buffer mechanism.
- **Process:**
  1.  **Receive:** External System sends JSON payload.
  2.  **Buffer:** System stores payload reliably.
  3.  **Process (Async):** Local Consumer polls/pulls data from Buffer to process.

## 2. Requirements

### Functional

- **Ingestion endpoint:** Review webhooks securely (HMAC support).
- **Buffer Storage:** Persistent storage "forever" (until processed).
- **Consumer Interface:** API for Local App to "Pull" messages with support for:
  - **Leasing (Locking):** Prevent multiple consumers from processing the same message.
  - **Retry:** Logic to handle crashed consumers (messages locked but not deleted).
  - **Release:** Explicitly NACK/release a message if processing fails, making it available again immediately.
  - **Delete:** Remove message after successful processing.

### Non-Functional

- **Latency:** < 100ms response time to Sender.
- **Availability:** High availability (Serverless preferred).
- **Maintenance:** Minimal ops (No physical server management).

## 3. Solution Evolution

### Solution A: Supabase Edge + PGMQ (Current Legacy)

- **Stack:** Supabase Edge Functions + PostgreSQL (pgmq extension).
- **Pros:** Strong consistency, rich SQL features.
- **Cons:** Higher write latency (~200-500ms) due to database region distance. Overkill for simple buffering.
- **Status:** Moved to `supabase_queue/`.

### Solution B: Cloudflare Workers + D1 (Recommended)

- **Stack:** Cloudflare Workers (Edge Compute) + D1 (SQLite Edge Database).
- **Pros:**
  - **Ultra-low latency:** ~50-80ms (Worker & DB potentially co-located at Edge).
  - **Cost:** Practically free for medium volume (5GB storage, 1M writes/month free).
  - **Reliability:** Serverless, no cold start issues, durable disk storage.
- **Status:** New implementation in `cloudflare_webhook/`.

## 4. Architecture: Cloudflare + D1 (The "Smart Buffer")

**Flow:**

1.  **Push:** Sender -> CF Worker -> `INSERT INTO webhooks` (D1) -> Respond 200 OK.
2.  **Pull:** Local App -> CF Worker (GET /poll) -> `UPDATE ... RETURNING` (Locking) -> App.
3.  **Ack:** Local App -> CF Worker (DELETE /ack) -> `DELETE FROM webhooks`.
