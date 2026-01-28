# Incremental Loading với DESC Strategy cho Sapo API

## Table of Contents

- [1. Overview](#1-overview)
- [2. Cấu trúc dữ liệu](#2-cấu-trúc-dữ-liệu)
- [3. Hạn chế của API](#3-hạn-chế-của-api)
- [4. DESC Strategy](#4-desc-strategy)
- [5. Implementation](#5-implementation)
- [6. Production Pipeline](#6-production-pipeline)
- [7. Monitoring & Optimization](#7-monitoring--optimization)

---

## 1. Overview

### Business Context

- **Data Source**: Sapo E-commerce API
- **Volume**: ~1,000 orders/day
- **Update Frequency**: Hourly incremental loads
- **Data Tool**: dlt (data load tool) - Python library

### Problem Statement

API chỉ hỗ trợ **sorting** theo `created_on` nhưng **KHÔNG hỗ trợ filtering** theo `created_on`. Làm sao để load incremental hiệu quả mà không phải fetch toàn bộ old data?

---

## 2. Cấu trúc dữ liệu

### 2.1 API Response Structure

```json
{
  "metadata": {
    "total": 15892,
    "page": 1,
    "limit": 250
  },
  "orders": [
    {
      "id": 12345,
      "code": "US24A00342",
      "created_on": "2024-01-20T10:30:00Z",
      "modified_on": "2024-01-20T10:35:00Z",
      "issued_on": "2024-01-20T10:32:00Z",
      "status": "completed",
      ...
    }
  ]
}
```

### 2.2 Order Entity Schema

```typescript
interface Order {
  // Identification
  id: number; // Unique identifier
  code: string; // Human readable code

  // Critical Timestamps
  created_on: string; // ISO 8601 timestamp - IMMUTABLE
  modified_on: string; // ISO 8601 timestamp - MUTABLE
  issued_on: string; // ISO 8601 timestamp

  // Status & Classification
  status:
    | "draft"
    | "pending"
    | "confirmed"
    | "processing"
    | "completed"
    | "cancelled";
  fulfillment_status: string;
  payment_status: string;

  // Relations
  customer_id: number;
  tenant_id: number;
  location_id: number;

  // Financial
  total: number;
  total_tax: number;
  total_discount: number;

  // Other fields...
}
```

### 2.3 Key Timestamp Fields

| Field         | Description                 | Characteristics                  |
| ------------- | --------------------------- | -------------------------------- |
| `created_on`  | Order creation timestamp    | **IMMUTABLE** - Never changes    |
| `modified_on` | Last modification timestamp | **MUTABLE** - Changes on updates |
| `issued_on`   | Order issue timestamp       | Semi-mutable                     |

**Critical Insight**: `created_on` là timestamp immutable → Ideal cho incremental loading checkpoint!

---

## 3. Hạn chế của API

### 3.1 API Capabilities

```python
# ✅ API HỖ TRỢ:
GET /orders?page=1&limit=250&sort=created_on&order=desc
GET /orders?page=1&limit=250&sort=created_on&order=asc

# ❌ API KHÔNG HỖ TRỢ:
GET /orders?created_on_min=2024-01-20T00:00:00Z  # No filter support!
GET /orders?created_on_gt=2024-01-20T00:00:00Z   # No filter support!
```

### 3.2 Pagination Characteristics

```
Total items: 15,892
Page size (limit): Flexible (Client controlled, 1-250)
Total pages: depends on limit

Pagination rules:
- Page numbers: 1-indexed
- Page size: Client can request limit=10, 50, 100, 250...
- Last page: May contain < limit items
- Stable ordering: Within single request session
```

### 3.3 Constraints Summary

| Constraint             | Impact                          | Workaround                       |
| ---------------------- | ------------------------------- | -------------------------------- |
| No timestamp filter    | Cannot skip old data directly   | Use client-side filtering        |
| Only sort support      | Must load pages sequentially    | Choose optimal sort direction    |
| **Flexible Page Size** | **Safety buffer changes size**  | **Use ITEM-based safety buffer** |
| Pagination drift       | New items shift page boundaries | Implement overlap strategy       |

### 3.4 Pagination Drift Phenomenon

```
BEFORE (Run 1): (đang sort theo DESC)
┌────────────────────────────────────────┐
│ Page 1: Items [60 → 41] (20 items)     │
│ Page 2: Items [40 → 21] (20 items)     │
│ Page 3: Items [20 → 1]  (20 items)     │
└────────────────────────────────────────┘

[11 new items created: 61-71]

AFTER (Run 2): (đang sort theo DESC)
┌──────────────────────────────────────────────┐
│ Page 1: Items [71 → 52] (20 items) ← SHIFTED │
│ Page 2: Items [51 → 32] (20 items) ← SHIFTED │
│ Page 3: Items [31 → 12] (20 items) ← SHIFTED │
└──────────────────────────────────────────────┘

Problem: Items 41-51 existed in Page 1 (Run 1)
         Now in Page 2 (Run 2)
         Could be MISSED without proper handling!
```

---

## 4. DESC Strategy (Flexible Page Size)

### 4.1 New Mindset: Items over Pages

**Old Mindset (Fixed Page Size):**

> "Trang là đơn vị cố định (250 items). Vậy ta cứ check 2 trang (500 items) là an toàn."
> ❌ **Rủi ro:** Nếu ai đó giảm page_size xuống 10, ta chỉ check 20 items. Quá ít! Dễ mất dữ liệu.

**New Mindset (Flexible Page Size):**

> "Page size là biến số. Ta không tin vào số trang. Ta tin vào số lượng bản ghi (Items)."
> ✅ **Giải pháp:** "Tôi muốn check đủ 500 items cũ rồi mới dừng, bất kể bạn chia nó thành 2 trang (size 250) hay 50 trang (size 10)."

### 4.2 Core Concept

```
DESC Strategy = Sort Descending + Client Filter + Items-based Early Stop
```

**Components:**

1.  **Sort by created_on DESC** (newest first).
2.  **Filter client-side:** items where `created_on > last_checkpoint`.
3.  **Count Old Items:** Track how many consecutive items we have seen that are <= checkpoint.
4.  **Early Stop:** When `consecutive_old_items >= MIN_OVERLAP_ITEMS`.

### 4.3 Strategy Flow Diagram

```mermaid
flowchart TD
    Start[Start Incremental Load] --> GetCheckpoint[Get Last Checkpoint]
    GetCheckpoint --> InitState[Init: page=1, old_items_count=0]

    InitState --> FetchPage[Fetch Page (limit=N, sort=DESC)]
    FetchPage --> CheckEmpty{Page Empty?}

    CheckEmpty -->|Yes| Stop[Stop Loading]
    CheckEmpty -->|No| ProcessItems[Process Items in Page]

    ProcessItems --> Iterate{Iterate Item}

    Iterate -->|Item > Checkpoint| Yield[Yield New Item]
    Yield --> ResetCount[old_items_count = 0]
    ResetCount --> NextItem

    Iterate -->|Item <= Checkpoint| IncCount[old_items_count++]
    IncCount --> CheckSafety{old_items_count >= MIN_OVERLAP_ITEMS?}

    CheckSafety -->|Yes| Stop
    CheckSafety -->|No| NextItem

    NextItem --> Iterate
    Iterate -->|End of Page| NextPage[page++]
    NextPage --> FetchPage

    Stop --> SaveCheckpoint[Save New Checkpoint]

    style Start fill:#90EE90
    style Stop fill:#FFB6C1
    style Yield fill:#87CEEB
    style CheckSafety fill:#FFD700
```

### 4.4 Overlap Strategy Explained

#### 4.4.1 The "Net" Analogy (Cái Lưới)

Hãy tưởng tượng **Overlap (Vùng an toàn)** như một cái lưới để hứng dữ liệu bị trôi.

- **Logic cũ (Page-based):**
  - Kích thước lưới = `OVERLAP_PAGES * page_size`
  - ⚠️ Lưới **co giãn** theo page_size.
  - Lưới to (size 250) -> An toàn.
  - Lưới bé (size 10) -> **Thủng lưới (Mất dữ liệu)!**

- **Logic mới (Items-based):**
  - Kích thước lưới = `MIN_OVERLAP_ITEMS` (ví dụ: 500 items).
  - 🔒 Lưới **cố định**, không phụ thuộc page_size.
  - Dù bạn dùng gáo múc nước to hay nhỏ (page_size), tôi vẫn chăng cái lưới 500 lỗ. Đảm bảo không con cá nào lọt lưới.

#### 4.4.2 Configuration

```python
# MIN_OVERLAP_ITEMS: Số lượng bản ghi cũ tối thiểu cần check trước khi dừng
# Recommendation:
# - Low traffic (<100/day): 50 items
# - Medium traffic (~1000/day): 200 items
# - High traffic (>10000/day): 500-1000 items

MIN_OVERLAP_ITEMS = 500

# Tại sao 500?
# Trung bình 1 ngày có 1000 đơn.
# 500 đơn tương đương nửa ngày dữ liệu.
# Rất khó có chuyện pagination drift trôi quá nửa ngày dữ liệu.
```

#### 4.4.3 Example Scenario

**Setup:** `MIN_OVERLAP_ITEMS = 50`.
**Scenario:** Chạy pipeline với `page_size = 10`.

- **Page 1:** 10 new items. (old_count = 0).
- **Page 2:** 5 new, 5 old. (old_count = 5).
- **Page 3:** 10 old. (old_count = 15).
- **Page 4:** 10 old. (old_count = 25).
- **Page 5:** 10 old. (old_count = 35).
- **Page 6:** 10 old. (old_count = 45).
- **Page 7:** 10 old. (old_count = 55).
  - -> **STOP!** Vì 55 >= 50.

-> **Kết quả:** Ta đã quét qua 55 bản ghi cũ, đảm bảo an toàn tuyệt đối dù `page_size` rất nhỏ.

---

## 5. Implementation

### 5.1 Basic Implementation

````python
import dlt
import requests
from typing import Iterator, Dict, Any

@dlt.resource(
    primary_key="id",
    write_disposition="merge"  # Critical: Handles deduplication
)
def orders(
    created_on=dlt.sources.incremental(
        "created_on",
        initial_value="2020-01-01T00:00:00Z"
    )
) -> Iterator[Dict[Any, Any]]:
    """
    Load orders incrementally using DESC strategy

    Strategy:
    1. Sort DESC (newest first)
    2. Filter client-side by created_on > checkpoint
    3. Early stop with overlap safety

    Args:
        created_on: dlt incremental state manager

    Yields:
        List of new order dictionaries
    """
    base_url = "https://api.sapo.vn/orders"

    # Configuration
    PAGE_SIZE = 250
    OVERLAP = 2  # Safety buffer pages
    MAX_PAGES = 100  # Circuit breaker

    # State
    page = 1
    no_new_pages = 0

    print(f"🚀 Starting incremental load from: {created_on.last_value}")

    while page <= MAX_PAGES:
        # Fetch page
        params = {
            "page": page,
            "limit": PAGE_SIZE,
            "sort": "created_on",
            "order": "desc"  # Key: Newest first
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
            break

        orders = data.get("orders", [])

        # Check for end of data
        if not orders:
            print(f"📭 No data at page {page}")
            break

        # Client-side filter: Only items created after checkpoint
        new_orders = [
            order for order in orders
            if order["created_on"] > created_on.last_value
        ]

        print(f"📄 Page {page}: {len(new_orders)}/{len(orders)} new items "
              f"(no_new_pages={no_new_pages})")

        # Yield new items
        if new_orders:
            yield new_orders
            no_new_pages = 0  # Reset counter
        else:
            no_new_pages += 1  # Increment counter

        # Early stop condition
        if no_new_pages > OVERLAP and page > OVERLAP:
            print(f"✅ Early stop triggered at page {page}")
            print(f"   Reason: {no_new_pages} consecutive pages with no new items")
            break

        page += 1

    print(f"🏁 Load completed: {page} pages processed")


# Simple usage
if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="sapo_orders",
        destination="postgres",
        dataset_name="sapo_raw"
    )

    load_info = pipeline.run(orders())

## 5. Implementation

### 5.1 Basic Implementation (Concepts)

```python
import dlt
import requests
from typing import Iterator, Dict, Any, List

@dlt.resource(primary_key="id", write_disposition="merge")
def orders(
    limit: int = 250,  # Flexible Page Size
    min_overlap_items: int = 500,  # Items-based Safety
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[List[Dict[str, Any]]]:

    # ... setup code ...

    page = 1
    # Counter for consecutive old items (<= checkpoint)
    # We count items, NOT pages!
    consecutive_old_items = 0

    last_value = created_on.last_value or "2000-01-01T00:00:00Z"

    while True:
        # 1. Fetch Page with limit
        data = fetch_orders(page=page, limit=limit, sort="created_on desc")
        if not data: break

        # 2. Process Items
        new_items_in_page = []

        for item in data:
            if item["created_on"] > last_value:
                # New Item found!
                new_items_in_page.append(item)

                # RESET the counter because we found a gap-filler!
                consecutive_old_items = 0
            else:
                # Old Item found
                consecutive_old_items += 1

        # 3. Yield New Items
        if new_items_in_page:
            yield new_items_in_page

        # 4. Check Stop Condition (Items-based)
        # "Stop if we've seen enough continuous old items"
        if consecutive_old_items >= min_overlap_items:
            print(f"✅ Safe to stop. Seen {consecutive_old_items} old items.")
            break

        page += 1
````

### 5.2 Why this is better?

| Feature             | Old Logic (Pages)              | New Logic (Items)        |
| :------------------ | :----------------------------- | :----------------------- |
| **Logic**           | `no_new_pages > 2`             | `consecutive_old >= 500` |
| **Case: limit=250** | Buffer = 500 items             | Buffer = 500 items       |
| **Case: limit=10**  | ⚠️ Buffer = 20 items (Danger!) | ✅ Buffer = 500 items    |
| **Conclusion**      | **Unsafe** if limit changes    | **Always Safe**          |

---

## 6. Production Pipeline

### 6.1 Complete Source Definition

```python
import dlt
import requests
from typing import Iterator, Dict, Any, List, Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class SapoConfig:
    page_size: int = 250
    min_overlap_items: int = 500
    max_pages: int = 1000

@dlt.source
def sapo_source(
    config: SapoConfig = SapoConfig()
):
    return orders(config=config)

@dlt.resource(
    primary_key="id",
    write_disposition="merge",
    table_format="delta"
)
def orders(
    config: SapoConfig,
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[List[Dict[str, Any]]]:

    client = get_sapo_client() # Assume this exists

    page = 1
    consecutive_old_items = 0
    last_value = created_on.last_value

    print(f"🚀 Starting Load. Checkpoint: {last_value}")
    print(f"   Config: size={config.page_size}, overlap_items={config.min_overlap_items}")

    while page <= config.max_pages:
        try:
            # Fetch
            data = client.fetch_orders(
                page=page,
                limit=config.page_size,
                sort_by="created_on desc"
            )

            if not data:
                print("End of data stream.")
                break

            # Process
            batch_new_items = []

            for item in data:
                item_date = item["created_on"]

                if last_value is None or item_date > last_value:
                    batch_new_items.append(item)
                    consecutive_old_items = 0 # RESET counter
                else:
                    consecutive_old_items += 1 # Increment counter

            # Yield
            if batch_new_items:
                yield batch_new_items

            print(f"Page {page}: {len(batch_new_items)} new. "
                  f"Consecutive Old: {consecutive_old_items}/{config.min_overlap_items}")

            # Stop Condition
            if consecutive_old_items >= config.min_overlap_items:
                print(f"✅ Early Stop Triggered. Safety buffer satisfied.")
                break

            page += 1

        except exception as e:
            # Handle error...
            break
```

### 6.2 Configuration Management

Now you can adjust safety without changing code:

```yaml
# config.yaml

sources:
  sapo:
    config:
      page_size: 250 # Can change to 50 if timeout
      min_overlap_items: 500 # Safety always guaranteed!
```

---

## 7. Metrics & Monitoring

Changes in metrics tracking:

- **Remove:** `no_new_pages_streak` (No longer relevant).
- **Add:** `current_overlap_buffer` (Current count of consecutive old items).
- **Alert:** If `current_overlap_buffer` resets to 0 frequently deep in pagination, it means we have "gaps" or "drift" happening effectively.

### 7.1 New Key Metrics

```python
@dataclass
class LoadMetrics:
    # ...
    max_consecutive_old_items: int = 0
    overlap_resets_count: int = 0 # How many times we found new items after old items
```

### 6.2 Configuration File

```yaml
# config.yaml
# dlt configuration for Sapo Orders pipeline

sources:
  sapo:
    # API credentials (use secrets.toml for actual values)
    api_key: ${SAPO_API_KEY}
    base_url: "https://api.sapo.vn"

    # Load configuration
    load_config:
      page_size: 250
      overlap_pages: 2
      max_pages: 100
      initial_load_date: "2024-01-01T00:00:00Z"
      timeout_seconds: 30
      max_retries: 3
      retry_delay_seconds: 2

# Destination configuration
destination:
  postgres:
    credentials: ${POSTGRES_CONNECTION_STRING}

# Pipeline settings
pipeline:
  name: "sapo_orders"
  dataset_name: "sapo_raw"
  progress: "log"
  full_refresh: false

# Logging
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 6.3 Secrets Management

```toml
# secrets.toml (DO NOT commit to git!)
# Store in ~/.dlt/secrets.toml or set as environment variables

[sources.sapo]
api_key = "your_sapo_api_key_here"

[destination.postgres.credentials]
database = "your_database"
username = "your_username"
password = "your_password"
host = "localhost"
port = 5432

# Alternative: Use connection string
# connection_string = "postgresql://user:pass@localhost:5432/dbname"
```

### 6.4 Deployment Scripts

#### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  dlt-sapo:
    build: .
    environment:
      - SAPO_API_KEY=${SAPO_API_KEY}
      - POSTGRES_CONNECTION_STRING=${POSTGRES_CONNECTION_STRING}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    command: python main.py
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=sapo_data
      - POSTGRES_USER=dlt_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs

# Run application
CMD ["python", "main.py"]
```

#### Requirements

```txt
# requirements.txt
dlt[postgres]>=0.4.0
requests>=2.31.0
tenacity>=8.2.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

---

## 7. Monitoring & Optimization

### 7.1 Performance Metrics

```python
"""
Key metrics to track for DESC strategy optimization
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""

    # Efficiency metrics
    fetch_efficiency: float  # % of fetched items that are new
    api_call_efficiency: float  # avg new items per API call

    # Resource metrics
    total_api_calls: int
    total_data_transferred_mb: float
    avg_response_time_ms: float

    # Strategy effectiveness
    early_stop_rate: float  # % of runs that early stopped
    avg_pages_before_stop: float
    overlap_effectiveness: float  # % of overlapped items that were new

    # Business metrics
    avg_new_items_per_run: int
    load_frequency_hours: float
    data_freshness_minutes: float

    def evaluate_strategy(self) -> Dict[str, str]:
        """
        Evaluate strategy performance and provide recommendations

        Returns:
            Dictionary of recommendations
        """
        recommendations = {}

        # Check efficiency
        if self.fetch_efficiency < 50:
            recommendations['efficiency'] = (
                f"Low fetch efficiency ({self.fetch_efficiency:.1f}%). "
                f"Consider increasing OVERLAP or adjusting load frequency."
            )
        elif self.fetch_efficiency > 90:
            recommendations['efficiency'] = (
                f"High fetch efficiency ({self.fetch_efficiency:.1f}%). "
                f"Strategy is well-tuned."
            )

        # Check overlap effectiveness
        if self.overlap_effectiveness < 10:
            recommendations['overlap'] = (
                f"Overlap rarely catches new items ({self.overlap_effectiveness:.1f}%). "
                f"Consider reducing OVERLAP to save API calls."
            )
        elif self.overlap_effectiveness > 30:
            recommendations['overlap'] = (
                f"Overlap frequently catches items ({self.overlap_effectiveness:.1f}%). "
                f"Current overlap setting is appropriate."
            )

        # Check early stop rate
        if self.early_stop_rate < 70:
            recommendations['early_stop'] = (
                f"Low early stop rate ({self.early_stop_rate:.1f}%). "
                f"Most runs load many pages. Review load frequency."
            )

        return recommendations


# Example usage
def calculate_metrics(load_stats_history: list) -> PerformanceMetrics:
    """
    Calculate performance metrics from load statistics history

    Args:
        load_stats_history: List of LoadStats from past runs

    Returns:
        PerformanceMetrics instance
    """
    if not load_stats_history:
        return None

    # Calculate aggregates
    total_fetched = sum(s.items_fetched for s in load_stats_history)
    total_new = sum(s.items_new for s in load_stats_history)
    total_calls = sum(s.api_calls for s in load_stats_history)
    early_stops = sum(1 for s in load_stats_history if s.early_stop_triggered)

    return PerformanceMetrics(
        fetch_efficiency=(total_new / total_fetched * 100) if total_fetched > 0 else 0,
        api_call_efficiency=total_new / total_calls if total_calls > 0 else 0,
        total_api_calls=total_calls,
        total_data_transferred_mb=(total_fetched * 2) / 1024,  # Rough estimate
        avg_response_time_ms=500,  # Would calculate from actual timing data
        early_stop_rate=(early_stops / len(load_stats_history) * 100),
        avg_pages_before_stop=sum(s.pages_processed for s in load_stats_history) / len(load_stats_history),
        overlap_effectiveness=15.0,  # Would calculate from actual overlap data
        avg_new_items_per_run=total_new / len(load_stats_history),
        load_frequency_hours=1.0,  # From configuration
        data_freshness_minutes=30.0  # From monitoring
    )
```

### 7.2 Optimization Guidelines

```python
"""
Guidelines for optimizing DESC strategy based on data patterns
"""

def optimize_overlap_setting(
    avg_items_per_hour: int,
    page_size: int,
    load_frequency_hours: float,
    safety_margin: float = 1.5
) -> int:
    """
    Calculate optimal overlap setting

    Args:
        avg_items_per_hour: Average new items created per hour
        page_size: Items per page
        load_frequency_hours: Hours between loads
        safety_margin: Safety multiplier (default 1.5 = 50% buffer)

    Returns:
        Recommended overlap pages
    """
    # Calculate expected new items per load
    expected_new_items = avg_items_per_hour * load_frequency_hours

    # Calculate expected new pages
    expected_new_pages = expected_new_items / page_size

    # Apply safety margin
    recommended_overlap = int(expected_new_pages * safety_margin)

    # Constraints
    min_overlap = 1
    max_overlap = 5

    return max(min_overlap, min(recommended_overlap, max_overlap))


# Example scenarios
scenarios = [
    {
        "name": "Low Frequency",
        "avg_items_per_hour": 40,
        "load_frequency_hours": 1,
        "expected": "OVERLAP=1 (40 items/hour = 0.16 pages)"
    },
    {
        "name": "Medium Frequency",
        "avg_items_per_hour": 100,
        "load_frequency_hours": 1,
        "expected": "OVERLAP=2 (100 items/hour = 0.4 pages * 1.5)"
    },
    {
        "name": "High Frequency",
        "avg_items_per_hour": 500,
        "load_frequency_hours": 1,
        "expected": "OVERLAP=3 (500 items/hour = 2 pages * 1.5)"
    },
    {
        "name": "Batch Load",
        "avg_items_per_hour": 100,
        "load_frequency_hours": 24,
        "expected": "OVERLAP=5 (2400 items/day = 9.6 pages * 1.5 = capped)"
    }
]

for scenario in scenarios:
    overlap = optimize_overlap_setting(
        scenario["avg_items_per_hour"],
        250,
        scenario["load_frequency_hours"]
    )
    print(f"{scenario['name']}: OVERLAP={overlap}")
    print(f"  Expected: {scenario['expected']}\n")
```

### 7.3 Alerting & Monitoring

```python
"""
Monitoring and alerting for DESC strategy pipeline
"""

from enum import Enum
from typing import Optional

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Alert for monitoring system"""
    def __init__(
        self,
        level: AlertLevel,
        message: str,
        metric_name: str,
        metric_value: Any,
        threshold: Any
    ):
        self.level = level
        self.message = message
        self.metric_name = metric_name
        self.metric_value = metric_value
        self.threshold = threshold
        self.timestamp = datetime.now()


def check_load_health(stats: LoadStats, config: LoadConfig) -> list[Alert]:
    """
    Check load health and generate alerts

    Args:
        stats: Load statistics
        config: Load configuration

    Returns:
        List of alerts
    """
    alerts = []

    # Check 1: Low efficiency
    if stats.items_fetched > 0:
        efficiency = (stats.items_new / stats.items_fetched) * 100
        if efficiency < 30:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                message=f"Low fetch efficiency: {efficiency:.1f}%",
                metric_name="fetch_efficiency",
                metric_value=efficiency,
                threshold=30
            ))

    # Check 2: High page count without early stop
    if not stats.early_stop_triggered and stats.pages_processed > 20:
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            message=f"High page count ({stats.pages_processed}) without early stop",
            metric_name="pages_processed",
            metric_value=stats.pages_processed,
            threshold=20
        ))

    # Check 3: API errors
    if stats.api_errors > 0:
        level = AlertLevel.ERROR if stats.api_errors > 3 else AlertLevel.WARNING
        alerts.append(Alert(
            level=level,
            message=f"API errors occurred: {stats.api_errors}",
            metric_name="api_errors",
            metric_value=stats.api_errors,
            threshold=0
        ))

    # Check 4: No new items found
    if stats.items_new == 0 and stats.pages_processed > 0:
        alerts.append(Alert(
            level=AlertLevel.INFO,
            message="No new items found in this run",
            metric_name="items_new",
            metric_value=0,
            threshold=1
        ))

    # Check 5: Checkpoint not advancing
    if stats.checkpoint_start == stats.checkpoint_end:
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            message="Checkpoint did not advance",
            metric_name="checkpoint_progress",
            metric_value=False,
            threshold=True
        ))

    return alerts


# Example monitoring integration
def send_alerts(alerts: list[Alert]):
    """
    Send alerts to monitoring system
    (Integrate with Slack, PagerDuty, etc.)
    """
    for alert in alerts:
        if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            logger.error(f"ALERT: {alert.message}")
            # send_to_pagerduty(alert)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"ALERT: {alert.message}")
            # send_to_slack(alert)
        else:
            logger.info(f"ALERT: {alert.message}")
```

---

## Summary

### Key Takeaways

1. **DESC Strategy is Optimal** for APIs without incremental filter support
   - 10-100x more efficient than ASC
   - Enables early stop capability
   - Simple and reliable

2. **Overlap is Critical** for handling pagination drift
   - Recommended: OVERLAP = 2 for most cases
   - Adjust based on data frequency

3. **Production Considerations**
   - Retry logic for API failures
   - Comprehensive metrics tracking
   - Health checks and alerting
   - Proper state management with dlt

4. **Performance Tuning**
   - Monitor fetch efficiency
   - Optimize overlap based on patterns
   - Balance frequency vs. overlap

### Quick Reference

```python
# Minimal working example
@dlt.resource(primary_key="id", write_disposition="merge")
def orders(created_on=dlt.sources.incremental("created_on")):
    page, no_new_pages, OVERLAP = 1, 0, 2
    while True:
        orders = fetch_page(page, order="desc")
        if not orders: break
        new = [o for o in orders if o["created_on"] > created_on.last_value]
        if new: yield new; no_new_pages = 0
        else: no_new_pages += 1
        if no_new_pages > OVERLAP and page > OVERLAP: break
        page += 1
```
