# Product Requirements Document (PRD): Webhook Consumer & Log Processing

## 1. Project Overview

The **Webhook Logs Consumer** is a backend service designed to reliably ingest, process, and store webhook data. It operates as a consumer worker that polls a message queue, processes the data, and persists it into a storage backend (currently PostgreSQL via Supabase).

## 2. Problem Statement

Handling webhooks directly via synchronous HTTP endpoints can be unreliable due to traffic spikes, timeouts, or database unavailability. A decoupled, queue-based architecture is required to ensure:

- **Reliability:** No lost webhooks.
- **Scalability:** Ability to handle bursts of traffic.
- **Observability:** Tracking of processing status (success, duplicates, errors).

## 3. Goals & Objectives

- **Asynchronous Processing:** Decouple webhook reception from processing using a queue (Supabase RPC based queue).
- **Data Integrity:** Ensure exactly-once or at-least-once (with deduplication) processing.
- **Fault Tolerance:** Retry mechanisms for failed messages.
- **Maintainability:** Clear separation of concerns between queue consumption, processing logic, and storage.

## 4. Current Architecture (Supabase Consumer)

The current implementation (`webhook_logs_consumer`) is built with TypeScript and Node.js.

### 4.1. Core Components

1.  **Queue System (Supabase RPC):**
    - `read_queue`: Fetches a batch of pending messages.
    - `delete_message`: Removes a message from the queue after successful processing.
    - `release_message`: Returns a message to the queue if processing fails.
2.  **Consumer Service (`WebhookConsumer.ts`):**
    - Polls the queue at a configurable interval (currently 5s).
    - Processes messages in batches (default batch size: 20).
    - Handles lifecycle: Fetch -> Process -> Ack/Nack.
3.  **Storage Layer (`WebhookStorage.ts`):**
    - Responsible for mapping queue messages to the database schema.
    - Handles insertion and deduplication logic.

### 4.2. Functional Requirements

- **Polling:** The service must continuously poll the queue for new messages.
- **Batch Processing:** Support processing multiple messages concurrently or sequentially within a batch.
- **Error Handling:**
  - If an error occurs, the message must be released back to the queue (Nack).
  - If successful, the message is effectively removed (Ack).
- **Deduplication:** The system should detect and log duplicate messages to prevent data redundancy.

### 4.3. Technical Stack

- **Language:** TypeScript
- **Runtime:** Node.js
- **Database:** PostgreSQL (Supabase)
- **Libraries:** `@supabase/supabase-js`, `dotenv`, `pg`

## 5. Future Scope (Cloudflare D1 Consumer)

A new consumer implementation (`cloudflared1_consumer`) is planned to support Cloudflare D1 as an alternative or additional storage/processing backend, enabling edge-compatible architectures.
