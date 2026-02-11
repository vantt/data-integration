# Facebook Messenger Integration Guide

This guide details the integration of Facebook Messenger data to analyze customer interactions and support performance.

## 1. Overview

Unlike the Marketing API (Ads), Messenger data is accessed via the **Facebook Graph API**. This pipeline focuses on retrieving actual conversation history and page-level messaging insights.

### Data Types

- **Conversations**: The threads of chat between the Page and users.
- **Messages**: Individual messages within a conversation (Sender, Content, Timestamp).
- **Page Insights**: aggregated metrics like "Unique Conversations", "Response Time".

## 2. Ingestion Strategy

We leverage the `dlt` **Facebook Messenger** source.

### Setup Requirements

1.  **Facebook App**: Requires a standard Facebook App (Business Type).
2.  **Page Access Token**: A token generated specifically for the Facebook Page you want to read messages from.
3.  **Permissions**:
    - `pages_messaging`: To read messages.
    - `pages_read_engagement`: To read metadata.
    - `pages_manage_metadata`: (Sometimes required for webhooks).

### Pipeline Structure

Similar to Ads, we can iterate through multiple pages if necessary.

```python
# ingestion/run_facebook_messenger.py

import dlt
from facebook_messenger import facebook_messenger_source

def load_messenger_data():
    pipeline = dlt.pipeline(
        pipeline_name="messenger_pipeline",
        destination="duckdb",
        dataset_name="raw_messenger"
    )

    # Configure source with Page Access Token
    source = facebook_messenger_source(
        page_access_token="YOUR_PAGE_ACCESS_TOKEN"
    )

    pipeline.run(source)
```

## 3. Data Modeling (Star Schema)

### Raw Tables

- `conversations`: Thread ID, updated time, link to messages.
- `messages`: Message ID, created time, from/to, message text.

### Proposed Dim/Fact

- **`dim_conversations`**:
  - `thread_id`
  - `customer_id` (PSID - Page Scoped ID)
  - `updated_at`
- **`fact_messages`**:
  - `message_id`
  - `thread_id`
  - `sender_type` (User vs Page)
  - `timestamp`
  - `content_length`
- **`fact_page_messaging_insights`**:
  - `date`
  - `new_conversations_count`
  - `blocked_conversations_count`
