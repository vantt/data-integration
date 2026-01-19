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
Page size: 250
Total pages: ceil(15,892 / 250) = 64 pages

Pagination rules:
- Page numbers: 1-indexed
- Fixed page size: 250 items/page
- Last page: May contain < 250 items
- Stable ordering: Within single request session
```

### 3.3 Constraints Summary

| Constraint          | Impact                          | Workaround                    |
| ------------------- | ------------------------------- | ----------------------------- |
| No timestamp filter | Cannot skip old data directly   | Use client-side filtering     |
| Only sort support   | Must load pages sequentially    | Choose optimal sort direction |
| Fixed page size     | Cannot adjust for performance   | Optimize early stopping       |
| Pagination drift    | New items shift page boundaries | Implement overlap strategy    |

### 3.4 Pagination Drift Phenomenon

```
BEFORE (Run 1):
┌────────────────────────────────────────┐
│ Page 1: Items [60 → 41] (20 items)    │
│ Page 2: Items [40 → 21] (20 items)    │
│ Page 3: Items [20 → 1]  (20 items)    │
└────────────────────────────────────────┘

[11 new items created: 61-71]

AFTER (Run 2):
┌────────────────────────────────────────┐
│ Page 1: Items [71 → 52] (20 items) ← SHIFTED │
│ Page 2: Items [51 → 32] (20 items) ← SHIFTED │
│ Page 3: Items [31 → 12] (20 items) ← SHIFTED │
└────────────────────────────────────────┘

Problem: Items 41-51 existed in Page 1 (Run 1)
         Now in Page 2 (Run 2)
         Could be MISSED without proper handling!
```

---

## 4. DESC Strategy

### 4.1 Core Concept

```
DESC Strategy = Sort Descending + Client Filter + Early Stop + Overlap Safety

Components:
1. Sort by created_on DESC (newest first)
2. Filter client-side: items where created_on > last_checkpoint
3. Early stop: When consecutive pages have no new items
4. Overlap buffer: Continue N pages after first empty page
```

### 4.2 Strategy Flow Diagram

```mermaid
flowchart TD
    Start[Start Incremental Load] --> GetCheckpoint[Get Last Checkpoint]
    GetCheckpoint --> InitState[Initialize: page=1, no_new_pages=0]

    InitState --> FetchPage[Fetch Page with DESC sort]
    FetchPage --> CheckEmpty{Page Empty?}

    CheckEmpty -->|Yes| Stop[Stop Loading]
    CheckEmpty -->|No| FilterItems[Filter: created_on > checkpoint]

    FilterItems --> CheckNewItems{Has New Items?}

    CheckNewItems -->|Yes| YieldItems[Yield New Items]
    YieldItems --> ResetCounter[no_new_pages = 0]
    ResetCounter --> NextPage[page++]

    CheckNewItems -->|No| IncrementCounter[no_new_pages++]
    IncrementCounter --> CheckStop{no_new_pages > OVERLAP<br/>AND page > OVERLAP?}

    CheckStop -->|Yes| Stop
    CheckStop -->|No| NextPage

    NextPage --> FetchPage

    Stop --> SaveCheckpoint[Save New Checkpoint]
    SaveCheckpoint --> End[End]

    style Start fill:#90EE90
    style Stop fill:#FFB6C1
    style End fill:#90EE90
    style YieldItems fill:#87CEEB
    style CheckStop fill:#FFD700
```

### 4.3 Why DESC?

#### 4.3.1 Efficiency Comparison

```
Scenario: 10,000 total items, checkpoint at item 9,900, 100 new items

┌─────────────────────────────────────────────────────────┐
│ DESC Strategy (Recommended)                             │
├─────────────────────────────────────────────────────────┤
│ Direction: 10,000 → 9,901 → ... → 1                   │
│                                                         │
│ Page 1: [10,000 → 9,751] → 100 new items found ✅     │
│ Page 2: [9,750 → 9,501]  → 0 new (all old)            │
│ Page 3: [9,500 → 9,251]  → 0 new (all old)            │
│ → STOP (triggered by overlap logic)                    │
│                                                         │
│ Result:                                                 │
│ - Pages loaded: 3                                       │
│ - Items fetched: 750                                    │
│ - API calls: 3                                          │
│ - Time: ~3 seconds                                      │
│ - Efficiency: ★★★★★                                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ASC Strategy (NOT Recommended without filter)          │
├─────────────────────────────────────────────────────────┤
│ Direction: 1 → 2 → ... → 9,900 → 10,000               │
│                                                         │
│ Page 1: [1 → 250]         → 0 new (all old)           │
│ Page 2: [251 → 500]       → 0 new (all old)           │
│ ...                                                     │
│ Page 39: [9,501 → 9,750]  → 0 new (all old)           │
│ Page 40: [9,751 → 10,000] → 100 new items found ✅    │
│ → STOP                                                  │
│                                                         │
│ Result:                                                 │
│ - Pages loaded: 40                                      │
│ - Items fetched: 10,000                                 │
│ - API calls: 40                                         │
│ - Time: ~40 seconds                                     │
│ - Efficiency: ★                                         │
└─────────────────────────────────────────────────────────┘

Conclusion: DESC is 13x more efficient!
```

#### 4.3.2 Advantages

| Aspect            | DESC            | ASC                       |
| ----------------- | --------------- | ------------------------- |
| **Early Stop**    | ✅ Possible     | ❌ Must load all old data |
| **API Calls**     | 3-5 calls       | 40-500 calls              |
| **Data Transfer** | ~1 MB           | ~25 MB                    |
| **Latency**       | 3-5 seconds     | 40-500 seconds            |
| **Gap Handling**  | ✅ With overlap | ❌ Difficult              |
| **Simplicity**    | ✅ Simple logic | ❌ Complex calculation    |

#### 4.3.3 Trade-offs

**Disadvantages of DESC:**

- ❌ Data processed in reverse chronological order (newest first)
- ❌ Need to reverse if natural order required downstream
- ❌ Slightly more complex stop logic

**Why These Are Acceptable:**

- Data order can be fixed in memory before yielding
- Complexity is minimal compared to efficiency gains
- Production systems prioritize performance over simplicity

### 4.4 Overlap Strategy Explained

#### 4.4.1 Why Overlap Is Needed

```
Problem: Pagination Drift + Race Conditions

Timeline:
─────────────────────────────────────────────────────────
T0: Run 1 starts
    Database: [1...49]

T1: Run 1 at Page 3
    Last item seen: Item 49

T2: Run 1 completes
    Checkpoint saved: Item 49 (created_on = "2024-01-20T10:00:00")

T3: [GAP] 11 new items created (Items 50-60)
    Database: [1...60]

T4: Run 2 starts
    Page 1: [60→41] contains BOTH new (60-50) and old (49-41)

T5: Run 2 Page 1 filters
    Filter: created_on > "2024-01-20T10:00:00"
    Result: Items 60-50 (11 items) ✅

T6: Run 2 Page 2
    Page 2: [40→21] - all old

T7: Run 2 Page 3
    Page 3: [20→1] - all old

Without Overlap: Stop at Page 3
With Overlap (N=2): Continue 2 more pages after first empty
→ Ensures we catch any items that may have been in the gap
```

#### 4.4.2 Overlap Configuration

```python
# Conservative (Recommended for production)
OVERLAP = 3
# - Handles up to 3 pages of gap (750 items)
# - Safe for high-frequency updates
# - Slight overhead but maximum safety

# Balanced (Good for stable systems)
OVERLAP = 2
# - Handles up to 2 pages of gap (500 items)
# - Good balance of safety and efficiency
# - Recommended for ~1000 orders/day

# Aggressive (Only for low-update systems)
OVERLAP = 1
# - Minimal safety buffer
# - Maximum efficiency
# - Only use if update frequency is very low
```

#### 4.4.3 Overlap Logic Flow

```python
"""
Overlap Stop Logic:

State variables:
- no_new_pages: Counter of consecutive pages with zero new items
- page: Current page number
- OVERLAP: Configuration constant

Stop Condition:
    (no_new_pages > OVERLAP) AND (page > OVERLAP)

Why this condition?
1. no_new_pages > OVERLAP: We've seen enough empty pages
2. page > OVERLAP: We've processed enough total pages (safety)

Examples with OVERLAP = 2:

Scenario A: Quick stop
  Page 1: 10 new → no_new_pages=0
  Page 2: 0 new → no_new_pages=1 (1 > 2? No)
  Page 3: 0 new → no_new_pages=2 (2 > 2? No, equal!)
  Page 4: 0 new → no_new_pages=3 (3 > 2? Yes, page=4 > 2? Yes) → STOP ✓

Scenario B: Late stop
  Page 1: 0 new → no_new_pages=1
  Page 2: 5 new → no_new_pages=0 (reset!)
  Page 3: 0 new → no_new_pages=1
  Page 4: 0 new → no_new_pages=2
  Page 5: 0 new → no_new_pages=3 (3 > 2? Yes) → STOP ✓
"""
```

---

## 5. Implementation

### 5.1 Basic Implementation

```python
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
    print(load_info)
```

### 5.2 Enhanced Implementation with Metrics

```python
import dlt
import requests
from typing import Iterator, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LoadMetrics:
    """Metrics tracking for load operation"""
    pages_processed: int = 0
    total_items_fetched: int = 0
    total_items_new: int = 0
    total_items_duplicate: int = 0
    api_calls: int = 0
    start_time: datetime = None
    end_time: datetime = None

    @property
    def efficiency(self) -> float:
        """Percentage of fetched items that were new"""
        if self.total_items_fetched == 0:
            return 0.0
        return (self.total_items_new / self.total_items_fetched) * 100

    @property
    def duration_seconds(self) -> float:
        """Load duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dlt.resource(
    primary_key="id",
    write_disposition="merge",
    columns={
        "id": {"data_type": "bigint"},
        "code": {"data_type": "text"},
        "created_on": {"data_type": "timestamp"},
        "modified_on": {"data_type": "timestamp"}
    }
)
def orders_with_metrics(
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[Dict[Any, Any]]:
    """
    Enhanced version with comprehensive metrics tracking
    """
    base_url = "https://api.sapo.vn/orders"

    # Configuration
    PAGE_SIZE = 250
    OVERLAP = 2
    MAX_PAGES = 100

    # State
    page = 1
    no_new_pages = 0
    metrics = LoadMetrics(start_time=datetime.now())

    print(f"\n{'='*60}")
    print(f"🚀 DESC Strategy Incremental Load")
    print(f"   Checkpoint: {created_on.last_value}")
    print(f"   Overlap: {OVERLAP} pages")
    print(f"   Max pages: {MAX_PAGES}")
    print(f"{'='*60}\n")

    try:
        while page <= MAX_PAGES:
            # Fetch page
            params = {
                "page": page,
                "limit": PAGE_SIZE,
                "sort": "created_on",
                "order": "desc"
            }

            try:
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                metrics.api_calls += 1
            except requests.RequestException as e:
                print(f"❌ API Error at page {page}: {e}")
                break

            orders = data.get("orders", [])

            if not orders:
                print(f"📭 Page {page}: Empty (API exhausted)")
                break

            metrics.pages_processed = page
            metrics.total_items_fetched += len(orders)

            # Filter new items
            new_orders = []
            for order in orders:
                if order["created_on"] > created_on.last_value:
                    new_orders.append(order)
                    metrics.total_items_new += 1
                else:
                    metrics.total_items_duplicate += 1

            # Log progress
            efficiency = (len(new_orders) / len(orders) * 100) if orders else 0
            print(f"📄 Page {page}: {len(new_orders)}/{len(orders)} new "
                  f"({efficiency:.1f}% efficiency) "
                  f"[no_new_streak={no_new_pages}]")

            # Yield new items
            if new_orders:
                yield new_orders
                no_new_pages = 0
            else:
                no_new_pages += 1

            # Stop condition check
            if no_new_pages > OVERLAP and page > OVERLAP:
                print(f"\n✅ Early stop triggered")
                print(f"   Pages with no new items: {no_new_pages}")
                print(f"   Overlap threshold: {OVERLAP}")
                break

            page += 1

    finally:
        # Finalize metrics
        metrics.end_time = datetime.now()

        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 Load Summary")
        print(f"{'='*60}")
        print(f"Duration: {metrics.duration_seconds:.2f}s")
        print(f"Pages processed: {metrics.pages_processed}")
        print(f"API calls: {metrics.api_calls}")
        print(f"Items fetched: {metrics.total_items_fetched}")
        print(f"Items new: {metrics.total_items_new}")
        print(f"Items duplicate: {metrics.total_items_duplicate}")
        print(f"Overall efficiency: {metrics.efficiency:.1f}%")
        print(f"{'='*60}\n")
```

### 5.3 Error Handling & Retry Logic

```python
import dlt
import requests
from typing import Iterator, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class SapoAPIError(Exception):
    """Custom exception for Sapo API errors"""
    pass


@dlt.resource(
    primary_key="id",
    write_disposition="merge"
)
def orders_with_retry(
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[Dict[Any, Any]]:
    """
    Production-ready version with retry logic
    """
    base_url = "https://api.sapo.vn/orders"
    api_key = dlt.secrets.get("sources.sapo.api_key")

    # Configuration
    PAGE_SIZE = 250
    OVERLAP = 2
    MAX_PAGES = 100

    # State
    page = 1
    no_new_pages = 0
    consecutive_errors = 0
    MAX_ERRORS = 3

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_page_with_retry(page_num: int) -> Dict[str, Any]:
        """Fetch single page with exponential backoff retry"""
        params = {
            "page": page_num,
            "limit": PAGE_SIZE,
            "sort": "created_on",
            "order": "desc"
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=30
        )

        # Handle specific status codes
        if response.status_code == 429:
            # Rate limit - wait longer
            raise requests.RequestException("Rate limit exceeded")
        elif response.status_code >= 500:
            # Server error - retry
            raise requests.RequestException(f"Server error: {response.status_code}")
        elif response.status_code >= 400:
            # Client error - don't retry
            raise SapoAPIError(f"Client error: {response.status_code}")

        response.raise_for_status()
        return response.json()

    print(f"🚀 Starting load with retry logic from: {created_on.last_value}")

    while page <= MAX_PAGES:
        try:
            # Fetch with retry
            data = fetch_page_with_retry(page)
            consecutive_errors = 0  # Reset error counter on success

        except SapoAPIError as e:
            # Client error - don't retry, stop load
            print(f"❌ Client error at page {page}: {e}")
            break

        except requests.RequestException as e:
            # Retry exhausted
            print(f"❌ Failed to fetch page {page} after retries: {e}")
            consecutive_errors += 1

            if consecutive_errors >= MAX_ERRORS:
                print(f"❌ Too many consecutive errors ({MAX_ERRORS}), stopping")
                break

            # Skip this page and continue
            page += 1
            continue

        orders = data.get("orders", [])

        if not orders:
            print(f"📭 Page {page}: Empty")
            break

        # Filter new items
        new_orders = [
            order for order in orders
            if order["created_on"] > created_on.last_value
        ]

        print(f"📄 Page {page}: {len(new_orders)}/{len(orders)} new")

        if new_orders:
            yield new_orders
            no_new_pages = 0
        else:
            no_new_pages += 1

        # Early stop
        if no_new_pages > OVERLAP and page > OVERLAP:
            print(f"✅ Early stop at page {page}")
            break

        page += 1

    print(f"🏁 Load completed")
```

---

## 6. Production Pipeline

### 6.1 Complete Source Definition

```python
"""
Sapo Orders Source - Production Implementation
DESC Strategy with Full Features
"""

import dlt
import requests
from typing import Iterator, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LoadConfig:
    """Configuration for incremental load"""
    page_size: int = 250
    overlap_pages: int = 2
    max_pages: int = 100
    initial_load_date: str = "2020-01-01T00:00:00Z"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 2


@dataclass
class LoadStats:
    """Statistics for load operation"""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    checkpoint_start: Optional[str] = None
    checkpoint_end: Optional[str] = None
    pages_processed: int = 0
    items_fetched: int = 0
    items_new: int = 0
    items_skipped: int = 0
    api_calls: int = 0
    api_errors: int = 0
    early_stop_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        # Convert datetimes to ISO strings
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
            data['duration_seconds'] = (
                self.end_time - self.start_time
            ).total_seconds()
        return data


@dlt.source
class SapoOrdersSource:
    """
    Sapo Orders data source with DESC incremental loading strategy
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.sapo.vn",
        config: Optional[LoadConfig] = None
    ):
        """
        Initialize Sapo Orders source

        Args:
            api_key: Sapo API authentication key
            base_url: API base URL
            config: Load configuration (uses defaults if not provided)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = config or LoadConfig()

        logger.info("Initialized SapoOrdersSource")
        logger.info(f"Config: {asdict(self.config)}")

    @dlt.resource(
        primary_key="id",
        write_disposition="merge",
        columns={
            "id": {"data_type": "bigint"},
            "code": {"data_type": "text"},
            "created_on": {"data_type": "timestamp"},
            "modified_on": {"data_type": "timestamp"},
            "issued_on": {"data_type": "timestamp"},
            "status": {"data_type": "text"},
            "tenant_id": {"data_type": "bigint"}
        }
    )
    def orders(
        self,
        created_on=dlt.sources.incremental("created_on")
    ) -> Iterator[Dict[Any, Any]]:
        """
        Load orders incrementally using DESC strategy

        Strategy Details:
        1. Sort by created_on DESC (newest first)
        2. Client-side filter: created_on > checkpoint
        3. Early stop after N consecutive empty pages
        4. Overlap safety buffer

        Yields:
            Batches of new order dictionaries
        """
        # Initialize stats
        stats = LoadStats(
            run_id=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            start_time=datetime.now(),
            checkpoint_start=created_on.last_value
        )

        # Set initial checkpoint if not exists
        if created_on.initial_value is None:
            created_on.initial_value = self.config.initial_load_date

        logger.info(f"Starting incremental load: {stats.run_id}")
        logger.info(f"Checkpoint: {created_on.last_value}")

        # State variables
        page = 1
        no_new_pages = 0

        try:
            while page <= self.config.max_pages:
                # Fetch page
                try:
                    orders_batch = self._fetch_page(page)
                    stats.api_calls += 1
                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    stats.api_errors += 1
                    break

                # Check for end of data
                if not orders_batch:
                    logger.info(f"No data at page {page}")
                    break

                stats.pages_processed = page
                stats.items_fetched += len(orders_batch)

                # Filter new items
                new_orders = self._filter_new_orders(
                    orders_batch,
                    created_on.last_value
                )

                stats.items_new += len(new_orders)
                stats.items_skipped += len(orders_batch) - len(new_orders)

                # Log progress
                efficiency = (
                    len(new_orders) / len(orders_batch) * 100
                    if orders_batch else 0
                )
                logger.info(
                    f"Page {page}: {len(new_orders)}/{len(orders_batch)} new "
                    f"({efficiency:.1f}%) [no_new={no_new_pages}]"
                )

                # Yield new items
                if new_orders:
                    yield new_orders
                    no_new_pages = 0
                else:
                    no_new_pages += 1

                # Check early stop condition
                if self._should_stop(page, no_new_pages):
                    stats.early_stop_triggered = True
                    logger.info(
                        f"Early stop triggered at page {page} "
                        f"(no_new_pages={no_new_pages})"
                    )
                    break

                page += 1

        finally:
            # Finalize stats
            stats.end_time = datetime.now()
            stats.checkpoint_end = created_on.last_value

            # Log summary
            self._log_summary(stats)

    def _fetch_page(self, page: int) -> list:
        """
        Fetch single page from API with retry logic

        Args:
            page: Page number to fetch

        Returns:
            List of order dictionaries
        """
        url = f"{self.base_url}/orders"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "page": page,
            "limit": self.config.page_size,
            "sort": "created_on",
            "order": "desc"
        }

        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                return data.get("orders", [])

            except requests.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying: {e}"
                    )
                    import time
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    logger.error(f"All retry attempts failed: {e}")
                    raise

    def _filter_new_orders(
        self,
        orders: list,
        checkpoint: str
    ) -> list:
        """
        Filter orders created after checkpoint

        Args:
            orders: List of order dictionaries
            checkpoint: ISO timestamp string

        Returns:
            List of new orders
        """
        return [
            order for order in orders
            if order["created_on"] > checkpoint
        ]

    def _should_stop(self, page: int, no_new_pages: int) -> bool:
        """
        Determine if loading should stop

        Args:
            page: Current page number
            no_new_pages: Count of consecutive pages with no new items

        Returns:
            True if should stop, False otherwise
        """
        return (
            no_new_pages > self.config.overlap_pages
            and page > self.config.overlap_pages
        )

    def _log_summary(self, stats: LoadStats):
        """Log comprehensive load summary"""
        logger.info("="*60)
        logger.info("Load Summary")
        logger.info("="*60)

        summary = stats.to_dict()
        for key, value in summary.items():
            logger.info(f"{key}: {value}")

        # Calculate derived metrics
        if stats.items_fetched > 0:
            efficiency = (stats.items_new / stats.items_fetched) * 100
            logger.info(f"efficiency_percent: {efficiency:.2f}")

        logger.info("="*60)


# Pipeline setup
def create_pipeline(
    pipeline_name: str = "sapo_orders",
    destination: str = "postgres",
    dataset_name: str = "sapo_raw"
) -> dlt.Pipeline:
    """
    Create and configure dlt pipeline

    Args:
        pipeline_name: Name of the pipeline
        destination: Destination database type
        dataset_name: Target dataset/schema name

    Returns:
        Configured dlt Pipeline instance
    """
    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=destination,
        dataset_name=dataset_name,
        progress="log",
        full_refresh=False
    )


# Main execution
if __name__ == "__main__":
    # Configuration
    config = LoadConfig(
        page_size=250,
        overlap_pages=2,
        max_pages=100,
        initial_load_date="2024-01-01T00:00:00Z"
    )

    # Initialize source
    source = SapoOrdersSource(
        api_key=dlt.secrets.get("sources.sapo.api_key"),
        base_url="https://api.sapo.vn",
        config=config
    )

    # Create pipeline
    pipeline = create_pipeline()

    # Run load
    logger.info("Starting pipeline execution")
    load_info = pipeline.run(source.orders())

    # Log results
    logger.info(f"Pipeline completed: {load_info}")
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
