# Cloudflare D1 Webhook Consumer

This project is a `dlt` (Data Load Tool) pipeline designed to consume webhooks buffered in Cloudflare D1 by the `cloudflare_webhook` Worker.

## Overview

The consumer:

1.  **Polls** the Cloudflare Worker endpoint (`GET /poll`) to fetch a batch of "NEW" webhooks.
2.  **Locks** the messages server-side (handled by the Worker).
3.  **Loads** the data into a destination (default: Parquet files in `_storage` folder).
4.  **Acknowledges** (`POST /ack-batch`) the messages upon successful load, which deletes them from the D1 buffer.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    Copy `.env.example` to `.env` and set your Worker URL.

    ```bash
    cp .env.example .env
    ```

    Edit `.env`:

    ```ini
    WORKER_URL=https://your-worker-subdomain.workers.dev
    SOURCE_SYSTEM=stripe  # Optional: to filter only specific sources
    ```

## Usage

Run the consumer:

```bash
python src/main.py
```

The script will enter a continuous loop, polling for data.

## Output

Data will be stored in the `_storage` directory (by default) in Parquet format, organized by table name (`webhooks`).
