# Logistics Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Operations / Warehouse
> **Update Frequency:** Real-time / Hourly

Logistics domain bao gồm 5 contexts:

| Context | Grain | Status |
|---|---|---|
| [Order Processing & Fulfillment](#context-order-processing--fulfillment) | Per Order | `active` |
| [Shipment Operations](#context-shipment-operations) | Per Shipment | `planned` (`fact_shipments`) |
| [Carrier Performance](#context-carrier-performance) | Per Carrier per Day | `planned` (`fact_shipments` + `dim_carriers`) |
| [Shipment Cost & COD](#context-shipment-cost--cod) | Per Shipment | `planned` (mart) — sources partly `active` (Shopee fees, COD) |
| [Staff & Operations](#context-staff--operations) | Per Staff per Day | `active` |

---

## Context: Order Processing & Fulfillment

> **Description:** Hiệu quả xử lý đơn từ lúc tạo đơn đến lần xuất kho đầu tiên. Đo tốc độ pipeline ở cấp độ đơn hàng, chưa quan tâm chi tiết từng shipment.
> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) (join `std_fulfillments` qua `first_shipped_at`)
> **Grain:** Per Order

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|---|---|---|---|---|
| Pipeline Health | Bao nhiêu % đơn đã được xuất kho? Có đơn nào bị nghẽn không? | Fulfillment Rate, Orders Pending > 24h | `fact_orders.fulfillment_status`, `first_shipped_at`, `ordered_at` | Stage-level events (packed_at) |
| Processing Speed | Đơn mất bao lâu từ lúc tạo đến lúc ship? Có ship same-day không? | Order Cycle Time, Same-Day Ship Rate | `first_shipped_at - ordered_at` | Per-stage breakdown |
| Completion | Đơn hoàn thành nhanh hay chậm? | Time to Complete | `time_to_complete_hours` | Closure event timeline |

### Analytical Questions

#### Q1. Fulfillment đang nhanh chậm thế nào?

- **Question:** Tỷ lệ đơn đã xuất kho trên tổng đơn eligible đang ở mức bao nhiêu so với benchmark?
- **Definition:** Đo lường tỷ lệ đơn đã có ít nhất 1 fulfillment thành công trong cửa sổ thời gian phân tích.
- **Nature:** Operational, lagging — phản ánh kết quả pipeline đã xảy ra.
- **Why It Matters:** Là chỉ báo sức khỏe pipeline rõ nhất. Drop dưới 85% thường báo hiệu nghẽn kho, thiếu nhân sự, hoặc lỗi hệ thống.
- **Tradeoffs / Caveats:** Phụ thuộc cách định nghĩa "eligible" — phải loại DRAFT, CANCELLED khỏi mẫu số nếu không sẽ làm rate xuống ảo. Đơn vừa tạo trong vài giờ cuối chưa kịp xuất kho không nên tính.
- **Insight / Action Enabled:** Rate < 85% → drill xuống từng kênh/chi nhánh xem đâu là nguồn nghẽn; rate giảm DoD > 10pp → escalate Operations Manager.
- **Related Metrics:** Fulfillment Rate, Order Status Funnel.

#### Q2. Đơn mất bao lâu để xuất kho lần đầu?

- **Question:** Thời gian trung bình từ lúc tạo đơn đến lần ship đầu tiên là bao nhiêu giờ?
- **Definition:** Đo cycle time order-to-first-ship, là proxy cho tốc độ phản ứng của warehouse.
- **Nature:** Operational, lagging — đo tốc độ team kho.
- **Why It Matters:** Cycle time tăng = customer chờ lâu hơn = trải nghiệm xấu. Là input chính cho promised delivery date.
- **Tradeoffs / Caveats:** Đơn có thể có nhiều fulfillments (partial ship); chỉ dùng `first_shipped_at` để tránh skew. Đơn chưa ship sẽ NULL — phải loại khỏi mẫu khi tính avg.
- **Insight / Action Enabled:** Avg tăng > 30% DoD → review staffing/inventory; identify outlier hours trong ngày để rebalance shift.
- **Related Metrics:** Order Cycle Time, Same-Day Ship Rate.

#### Q3. Bao nhiêu % đơn được ship cùng ngày?

- **Question:** Tỷ lệ đơn được xuất kho trong cùng ngày tạo đơn (cùng calendar date)?
- **Definition:** Đo lường khả năng đáp ứng "same-day shipping" — yếu tố quan trọng với khách online.
- **Nature:** Operational, leading — chỉ báo sớm về customer satisfaction.
- **Why It Matters:** Same-day ship rate cao = competitive advantage với marketplaces. Là KPI mà nhiều sàn (Shopee, TikTok) đánh giá điểm shop.
- **Tradeoffs / Caveats:** Đơn tạo cuối ngày (sau 18h) thực tế không thể same-day ship — cần tách thành "eligible-window same-day rate" nếu muốn fair.
- **Insight / Action Enabled:** Rate drop → kiểm tra cutoff time của warehouse; check inventory cho SKU bị backorder.
- **Related Metrics:** Same-Day Ship Rate, Order Cycle Time.

#### Q4. Đơn hoàn thành cycle nhanh chậm thế nào?

- **Question:** Thời gian trung bình từ tạo đơn đến trạng thái COMPLETED là bao nhiêu giờ?
- **Definition:** End-to-end cycle time, bao gồm cả ship + giao hàng + thanh toán.
- **Nature:** Operational, lagging.
- **Why It Matters:** Khác với Cycle Time (chỉ đến ship), Time to Complete đại diện cho toàn bộ vòng đời đơn hàng. Cao kéo dài cash-in-transit.
- **Tradeoffs / Caveats:** Chỉ tính đơn đã COMPLETED — đơn còn OPEN không có completed_at sẽ skew nếu mix.
- **Insight / Action Enabled:** Phân tách bottleneck: nếu Cycle Time (Q2) thấp nhưng Time to Complete cao → vấn đề ở delivery hoặc collection, không phải warehouse.
- **Related Metrics:** Time to Complete, Order Cycle Time.

### Metrics

#### 1. Tỷ lệ xuất kho (Fulfillment Rate)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Phần trăm đơn eligible (đã có ít nhất 1 fulfillment với status `fulfilled`) trên tổng đơn được tạo trong kỳ. Loại DRAFT và CANCELLED khỏi mẫu số vì không thuộc pipeline fulfillment.
- **Business Logic:** Grain per order. Numerator = COUNT đơn có `fulfillment_status = 'fulfilled'`. Denominator = COUNT đơn `status NOT IN ('DRAFT', 'CANCELLED')`. Time basis = `ordered_at` (ICT).
- **Formula:** `Fulfillment Rate (%) = Fulfilled Orders / Eligible Orders × 100`
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN fulfillment_status = 'fulfilled' THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN status NOT IN ('DRAFT', 'CANCELLED') THEN 1 END), 0)
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Nhầm với "Delivery Rate" — fulfillment_status = `fulfilled` chỉ nghĩa là đã ship, không phải đã giao thành công. Tính cả DRAFT/CANCELLED vào mẫu số làm rate xuống ảo.
- **Pitfalls / Edge Cases:** Đơn `partial` fulfillment phải xử lý riêng — hiện đếm như không fulfilled; cần định nghĩa lại nếu partial chiếm tỉ trọng cao. Đơn vừa tạo trong cùng kỳ (chưa kịp ship) sẽ pull rate xuống — nên loại đơn tạo trong N giờ cuối.

#### 2. Thời gian xuất kho (Order Cycle Time — Hours to First Ship)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) (join `std_fulfillments` qua `first_shipped_at`)

- **Business Definition:** Thời gian trung bình (giờ) từ lúc tạo đơn (`ordered_at`) đến lần fulfillment thành công đầu tiên (`first_shipped_at`). Chỉ tính đơn đã ship — đơn chưa ship loại khỏi mẫu.
- **Business Logic:** Grain per order. AVG của `date_diff('hour', ordered_at, first_shipped_at)` với `first_shipped_at IS NOT NULL`. Loại DRAFT, CANCELLED.
- **Formula:** `Avg Hours to First Ship = AVG(first_shipped_at - ordered_at) WHERE first_shipped_at IS NOT NULL`
- **Logic (SQL):**
  ```sql
  AVG(date_diff('hour', ordered_at, first_shipped_at))
  -- WHERE first_shipped_at IS NOT NULL AND status NOT IN ('DRAFT', 'CANCELLED')
  ```
- **Unit:** Hours
- **Classification:** lagging | absolute
- **Common Misunderstandings:** Nhầm với `time_to_complete_hours` — Time to Complete đo đến status COMPLETED (bao gồm cả delivery), không phải đến ship lần đầu.
- **Pitfalls / Edge Cases:** Đơn có nhiều fulfillments — chỉ dùng `first_shipped_at` (MIN); nếu dùng ALL fulfillments sẽ skew. Negative hours (`first_shipped_at < ordered_at`) thường do timezone bug — cần filter.

#### 3. Tỷ lệ ship cùng ngày (Same-Day Ship Rate)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Phần trăm đơn được xuất kho cùng calendar date (ICT) với ngày tạo đơn. Đo lường khả năng same-day fulfillment — KPI quan trọng với khách online và marketplaces.
- **Business Logic:** Grain per order. Numerator = COUNT đơn `CAST(first_shipped_at AS DATE) = CAST(ordered_at AS DATE)`. Denominator = COUNT đơn đã ship (`first_shipped_at IS NOT NULL`).
- **Formula:** `Same-Day Ship Rate (%) = Same-Day Shipped Orders / Total Shipped Orders × 100`
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN CAST(first_shipped_at AS DATE) = CAST(ordered_at AS DATE) THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN first_shipped_at IS NOT NULL THEN 1 END), 0)
  ```
- **Unit:** %
- **Classification:** leading | relative
- **Common Misunderstandings:** "Same-day" tính theo calendar date, không phải "trong 24 giờ" — đơn tạo 23:30 ship 00:30 ngày sau = NOT same-day.
- **Pitfalls / Edge Cases:** Bug timezone phổ biến — nếu so sánh date của 2 timestamp khác zone sẽ sai 1 ngày. Dùng `Asia/Ho_Chi_Minh` consistently. Đơn tạo sau cutoff time của warehouse (vd: 18h) không thể same-day ship — nên track riêng "eligible-window rate".

#### 4. Thời gian hoàn thành đơn (Time to Complete)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Thời gian trung bình (giờ) từ tạo đơn đến lúc đơn chuyển sang `status = 'COMPLETED'` — đo end-to-end vòng đời đơn hàng (bao gồm ship + giao + thanh toán).
- **Business Logic:** Grain per order. AVG của `time_to_complete_hours` (pre-computed trong `fact_orders`). Chỉ tính đơn `status = 'COMPLETED'`.
- **Formula:** `Avg Time to Complete = AVG(completed_at - ordered_at) WHERE status = 'COMPLETED'`
- **Logic (SQL):**
  ```sql
  AVG(time_to_complete_hours)
  -- WHERE status = 'COMPLETED'
  ```
- **Unit:** Hours
- **Classification:** lagging | absolute
- **Common Misunderstandings:** Nhầm với Order Cycle Time (Q2) — Cycle Time chỉ đến lần ship đầu, Time to Complete đến status COMPLETED. Khoảng cách giữa 2 metric phản ánh delivery + collection time.
- **Pitfalls / Edge Cases:** Đơn không COMPLETED (OPEN, ARCHIVED) loại khỏi mẫu → có thể skew nếu mix với đơn dài-hạn. Đơn mở lâu rồi mới close (tồn kho cũ) có thể skew AVG — cân nhắc median hoặc trimmed mean.

---

## Context: Shipment Operations

> **Description:** Phân tích cấp độ từng shipment (1 đơn có thể có nhiều shipment khi partial fulfillment). Trả lời câu hỏi về volume shipment, multi-shipment rate, và phân bố status real-time.
> **dbt Source:** [`std_fulfillments`](../../../transformation/models/staging/standard/std_fulfillments.sql) — `fact_shipments` (planned)
> **Grain:** Per Shipment

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|---|---|---|---|---|
| Volume | Bao nhiêu shipment đã tạo? Tăng/giảm DoD thế nào? | Shipment Volume | `std_fulfillments.fulfillment_id` | `fact_shipments` mart |
| Partial Fulfillment | Bao nhiêu đơn cần ship nhiều lần? | Multi-Shipment Order Rate | `std_fulfillments.order_id` COUNT GROUP | `fact_shipments` mart |
| Status Pipeline | Shipment đang ở các stage nào? | Shipment Status Distribution, Shipment Status Funnel | `std_fulfillments.status` | `fact_shipments` mart |
| Delivery Outcome | Bao nhiêu % shipment giao thành công? Bao nhiêu thất bại? | Delivery Success Rate, Failed Delivery Rate | `std_fulfillments.status` (DELIVERED/FAILED proxy) | Chính xác delivered_at timestamp |

### Analytical Questions

#### Q5. Đang có bao nhiêu shipment trong pipeline?

- **Question:** Tổng shipment được tạo trong kỳ là bao nhiêu? Tăng giảm thế nào so với hôm qua/tuần trước?
- **Definition:** Đo throughput thực sự của warehouse ở granularity shipment, không phải order (vì 1 order có thể tạo nhiều shipments).
- **Nature:** Operational, lagging — đo workload đã xử lý.
- **Why It Matters:** Order count che giấu workload thực tế — đơn lớn split thành 5 shipments tốn nhân lực gấp 5 đơn nhỏ. Volume shipment phản ánh đúng warehouse capacity.
- **Tradeoffs / Caveats:** Volume tăng không có nghĩa hiệu suất tăng — có thể do partial fulfillment tăng (xấu). Phải xem kết hợp với Multi-Shipment Rate (Q6).
- **Insight / Action Enabled:** Volume tăng đột biến → cảnh báo capacity warehouse; identify peak hours để rebalance shift.
- **Related Metrics:** Shipment Volume, Multi-Shipment Order Rate.

#### Q6. Bao nhiêu % đơn phải ship nhiều lần (partial fulfillment)?

- **Question:** Tỷ lệ đơn có > 1 shipment trên tổng đơn đã ship là bao nhiêu?
- **Definition:** Đo lường rate of partial fulfillment — chỉ báo về inventory health và warehouse efficiency.
- **Nature:** Operational, lagging — chỉ báo về quality, không chỉ volume.
- **Why It Matters:** Multi-shipment rate cao = tốn phí ship gấp đôi, customer experience xấu (nhiều package), và thường do inventory shortage (item B chưa về kho khi ship item A). Là chỉ báo gián tiếp về stock-out.
- **Tradeoffs / Caveats:** Một số shop intentionally split (đơn cồng kềnh, COD risk) — không phải multi-shipment luôn xấu. Cần segment theo channel/category.
- **Insight / Action Enabled:** Rate > 15% → review inventory replenishment cycle; check SKU cụ thể bị split nhiều nhất.
- **Related Metrics:** Multi-Shipment Order Rate, Shipment Volume.

#### Q7. Shipment đang ở stage nào? Có bao nhiêu thất bại?

- **Question:** Phân bố status (PACKED/SHIPPING/DELIVERED/FAILED/CANCELLED) hiện tại của các shipment đang active là gì?
- **Definition:** Snapshot pipeline shipment để phát hiện nghẽn stage và failed shipments cần retry.
- **Nature:** Operational, leading — snapshot real-time để hành động ngay.
- **Why It Matters:** Identify bottleneck stage: nhiều shipment kẹt ở PACKED = chậm bàn giao carrier; nhiều ở SHIPPING quá lâu = carrier chậm hoặc lost; nhiều FAILED = vấn đề chất lượng địa chỉ hoặc carrier.
- **Tradeoffs / Caveats:** Shipment status từ Sapo có lag — không hoàn toàn real-time. FAILED có thể là transient (carrier retry sau) hoặc terminal — cần check shipment_status detail.
- **Insight / Action Enabled:** Stage SHIPPING aging > 7 ngày → escalate carrier; FAILED count cao → retry tự động hoặc CS contact khách.
- **Related Metrics:** Shipment Status Distribution, Delivery Success Rate, Failed Delivery Rate.

### Metrics

#### 5. Khối lượng shipment (Shipment Volume)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Tổng số shipment được tạo trong kỳ phân tích. Khác với Order Count: 1 đơn có thể tạo nhiều shipments khi fulfillment được split (partial ship), nên Shipment Volume phản ánh chính xác hơn workload kho.
- **Business Logic:** Grain per shipment. COUNT DISTINCT `fulfillment_id`. Time basis = `created_at` (lúc tạo fulfillment). Loại shipment có status = CANCELLED nếu muốn đo actual workload đã thực thi.
- **Formula:** `Shipment Volume = COUNT(DISTINCT fulfillment_id) WHERE created_at IN [period]`
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT fulfillment_id)
  -- WHERE date(created_at) = current_date
  -- AND status != 'CANCELLED'
  ```
- **Unit:** Count
- **Classification:** lagging | absolute
- **Common Misunderstandings:** Nhầm với Order Count — 1000 đơn không có nghĩa 1000 shipments. Tỉ lệ shipments/orders trung bình ~1.05-1.20 tùy ngành (consumer goods cao hơn).
- **Pitfalls / Edge Cases:** Tính theo `created_at` vs `shipped_at` cho kết quả khác nhau — shipment created hôm nay nhưng ship mai sẽ rơi vào khác kỳ. Quyết định time basis tùy use case (workload kho dùng `created_at`, throughput dùng `shipped_at`).

#### 6. Tỷ lệ đơn nhiều shipment (Multi-Shipment Order Rate)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` GROUP BY `order_id` → `fact_shipments` (planned)

- **Business Definition:** Phần trăm đơn cần được chia thành nhiều lần ship (partial fulfillment). Chỉ báo gián tiếp về inventory shortage và split-fulfillment policy của warehouse.
- **Business Logic:** Grain per order (sau khi GROUP từ shipment grain). Numerator = COUNT đơn có > 1 shipment. Denominator = COUNT đơn có ≥ 1 shipment. Loại shipment CANCELLED nếu chỉ muốn count actual shipments.
- **Formula:** `Multi-Shipment Rate (%) = Orders with > 1 Shipment / Total Shipped Orders × 100`
- **Logic (SQL):**
  ```sql
  WITH shipments_per_order AS (
      SELECT order_id, COUNT(DISTINCT fulfillment_id) as ship_count
      FROM std_fulfillments
      WHERE status != 'CANCELLED'
      GROUP BY order_id
  )
  SELECT COUNT(CASE WHEN ship_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)
  FROM shipments_per_order
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Nhầm với "% shipments có nhiều items" — đây là metric ở grain order, không phải item. Đơn 5 items ship 1 lần vẫn là single-shipment.
- **Pitfalls / Edge Cases:** Đơn lớn (B2B) thường intentionally split → tăng rate nhưng không phải vấn đề. Cần segment theo customer_type. Cancelled shipments tính hay không tùy intent (loại để đo actual workload, giữ để đo split policy).

#### 7. Phân bố trạng thái shipment (Shipment Status Distribution)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Phân bố % shipment theo từng status (PACKED / SHIPPING / DELIVERED / FAILED / CANCELLED). Snapshot real-time để identify nghẽn stage và shipment cần escalate.
- **Business Logic:** Grain per shipment. GROUP BY `status`, COUNT, chuyển thành %. Có 2 mode: snapshot (tất cả shipments active hiện tại, no time filter) hoặc cohort (shipments tạo trong kỳ X, status hiện tại của chúng).
- **Formula:** `Status % = COUNT(shipments WHERE status = X) / COUNT(all shipments) × 100`
- **Logic (SQL):**
  ```sql
  SELECT status,
         COUNT(*) as shipment_count,
         COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as pct
  FROM std_fulfillments
  -- WHERE date(created_at) = current_date  (cohort mode)
  GROUP BY status
  ```
- **Unit:** % (mỗi bucket)
- **Classification:** lagging | relative
- **Common Misunderstandings:** Snapshot vs cohort khác nhau — snapshot reflect tình trạng "ngay bây giờ" của all shipments (kể cả cũ); cohort reflect kết quả của 1 batch tạo trong kỳ. Mix lẫn dễ misleading.
- **Pitfalls / Edge Cases:** Shipment status `error` trong Sapo map thành FAILED ở std layer — kiểm tra mapping. Status có thể stale nếu Sapo webhook lag, không refresh kịp.

#### 8. Tỷ lệ giao hàng thành công (Delivery Success Rate)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Phần trăm shipment đạt status `DELIVERED` trong tổng shipment đã có outcome cuối (DELIVERED + FAILED + CANCELLED). Đo lường khả năng giao hàng thành công của toàn pipeline.
- **Business Logic:** Grain per shipment. Numerator = COUNT shipment `status = 'DELIVERED'`. Denominator = COUNT shipment với status terminal (DELIVERED/FAILED/CANCELLED). Loại shipments còn SHIPPING/PACKED vì chưa có outcome.
- **Formula:** `Delivery Success Rate (%) = Delivered / (Delivered + Failed + Cancelled) × 100`
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN status = 'DELIVERED' THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN status IN ('DELIVERED', 'FAILED', 'CANCELLED') THEN 1 END), 0)
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Nhầm với Fulfillment Rate (metric 1) — Fulfillment Rate đo % đơn được ship; Delivery Success Rate đo % shipment giao thành công. Một đơn fulfilled vẫn có thể failed delivery.
- **Pitfalls / Edge Cases:** Sapo status `success` được map sang DELIVERED ở std layer, nhưng `success` thực tế chỉ confirm carrier đã pick up — không phải khách đã nhận. Đây là proxy, không phải ground truth. Cần verify với carrier API nếu cần độ chính xác cao.

#### 9. Tỷ lệ giao thất bại (Failed Delivery Rate)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Phần trăm shipment có status `FAILED` trên tổng shipment đã có outcome. Cảnh báo về chất lượng địa chỉ, carrier reliability, hoặc khách không nhận hàng (NDR — non-delivery report).
- **Business Logic:** Grain per shipment. Numerator = COUNT shipment `status = 'FAILED'`. Denominator = COUNT shipment terminal (DELIVERED + FAILED + CANCELLED).
- **Formula:** `Failed Delivery Rate (%) = Failed Shipments / Terminal Shipments × 100`
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN status = 'FAILED' THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN status IN ('DELIVERED', 'FAILED', 'CANCELLED') THEN 1 END), 0)
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Nhầm với Return Rate — Failed Delivery = chưa giao được; Return = đã giao nhưng khách trả lại. Khác nhau hoàn toàn.
- **Pitfalls / Edge Cases:** Sapo `status = 'error'` map sang FAILED nhưng có thể là transient error (carrier retry sau) chứ không phải terminal failure. Cần check `shipment_status` detail để phân biệt retry vs final fail.

---

## Context: Carrier Performance

> **Description:** So sánh hiệu suất giữa các đơn vị vận chuyển (GHN, GHTK, J&T, ViettelPost, in-house...). Trả lời "carrier nào ship nhanh nhất?", "carrier nào fail nhiều?".
> **dbt Source:** `std_fulfillments` JOIN `dim_carriers` (planned) — `fact_shipments` (planned)
> **Grain:** Per Carrier per Day

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|---|---|---|---|---|
| Volume Share | Carrier nào đang ship nhiều nhất? | Carrier Volume Share | `std_fulfillments.carrier_id` | `dim_carriers` master seed |
| Speed | Carrier nào giao nhanh nhất? | Avg Delivery Time by Carrier | `shipped_at`, `modified_on` (proxy delivered_at) | Chính xác delivered_at; SLA matrix |
| Reliability | Carrier nào fail nhiều nhất? | Failed Delivery Rate by Carrier, Return Rate by Carrier | `status`, `fact_order_returns` | Carrier-level dim join |

### Analytical Questions

#### Q8. Carrier nào đang ship nhiều nhất?

- **Question:** Phân bố volume shipment theo từng carrier là gì? Có carrier nào dominant > 50% không?
- **Definition:** Đo lường mức độ tập trung carrier — concentration risk khi 1 carrier chiếm quá cao.
- **Nature:** Operational, lagging.
- **Why It Matters:** Concentration > 70% trên 1 carrier = rủi ro lớn nếu carrier đó gặp sự cố (peak season, strike, system down). Diversification giảm rủi ro nhưng có thể tăng chi phí (mất volume discount).
- **Tradeoffs / Caveats:** Volume share phụ thuộc cost structure — carrier rẻ tự nhiên chiếm phần lớn. Phải xem kèm cost per shipment và failure rate để đánh giá overall.
- **Insight / Action Enabled:** Concentration > 70% → đa dạng carrier; carrier mới < 5% volume → review SLA contract, có cần cắt hay không.
- **Related Metrics:** Carrier Volume Share, Shipment Volume.

#### Q9. Carrier nào giao nhanh nhất?

- **Question:** Thời gian trung bình từ ship đến delivered của từng carrier là bao nhiêu?
- **Definition:** Đo speed of delivery — chỉ tính shipments đã DELIVERED.
- **Nature:** Operational, lagging.
- **Why It Matters:** Speed là factor chính trong customer satisfaction. Speed khác biệt giữa carriers giúp route đơn ưu tiên (express order → carrier nhanh).
- **Tradeoffs / Caveats:** Speed phụ thuộc region — Hà Nội ship trong nội thành nhanh hơn ship đi tỉnh. Phải normalize theo destination geography để fair compare.
- **Insight / Action Enabled:** Carrier chậm gấp 2x trung bình → renegotiate SLA hoặc giảm allocation; route premium orders qua carrier nhanh nhất.
- **Related Metrics:** Avg Delivery Time by Carrier.

#### Q10. Carrier nào không đáng tin?

- **Question:** Failed delivery rate và return rate của từng carrier là bao nhiêu?
- **Definition:** Đo reliability — gộp 2 chỉ báo: tỷ lệ không giao được + tỷ lệ giao xong bị trả.
- **Nature:** Operational, lagging.
- **Why It Matters:** Failed delivery tốn cost ship 2 lần (re-ship); return tốn cost ship 2 chiều + lost item value. Carrier failure rate cao = hidden cost lớn.
- **Tradeoffs / Caveats:** Failure rate có thể do địa chỉ xấu (lỗi shop) hoặc carrier thực sự kém — khó tách. Cần kết hợp với customer complaint data.
- **Insight / Action Enabled:** Failure rate > 5% → escalate carrier; spike đột ngột → check incident (peak season, weather).
- **Related Metrics:** Failed Delivery Rate by Carrier, Return Rate by Carrier.

### Metrics

#### 10. Tỷ trọng carrier (Carrier Volume Share)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` JOIN `dim_carriers` (planned)

- **Business Definition:** Phần trăm shipment được thực hiện bởi mỗi carrier trên tổng shipment. Đo lường concentration risk và mức độ phụ thuộc vào từng đơn vị vận chuyển.
- **Business Logic:** Grain per carrier per period. Numerator = COUNT shipment per `carrier_id`. Denominator = TOTAL COUNT shipment. Loại CANCELLED nếu chỉ đo actual deliveries.
- **Formula:** `Carrier Share (%) = Shipments via Carrier X / Total Shipments × 100`
- **Logic (SQL):**
  ```sql
  SELECT c.carrier_name,
         COUNT(*) as shipment_count,
         COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as share_pct
  FROM std_fulfillments f
  JOIN dim_carriers c ON f.carrier_id = c.carrier_id
  WHERE f.status != 'CANCELLED'
  GROUP BY c.carrier_name
  ORDER BY share_pct DESC
  ```
- **Unit:** % (mỗi carrier)
- **Classification:** lagging | relative
- **Common Misunderstandings:** Share cao không có nghĩa carrier tốt — có thể chỉ vì rẻ. Phải xem kết hợp với speed + failure rate.
- **Pitfalls / Edge Cases:** `carrier_id` NULL với shipment self-delivery (giao bằng nhân viên shop) — cần map thành 'In-House' bucket. `dim_carriers` chưa tồn tại — phải seed thủ công từ Sapo carrier API hoặc hardcoded list.

#### 11. Thời gian giao trung bình theo carrier (Avg Delivery Time by Carrier)

> **Status:** `planned`
> **dbt Source:** `fact_shipments` JOIN `dim_carriers` (planned)

- **Business Definition:** Số giờ trung bình từ lúc `shipped_at` đến lúc shipment đạt status DELIVERED (`delivered_at`). Chỉ tính shipments đã DELIVERED. Yêu cầu mart `fact_shipments` derive `delivered_at` từ `stg_sapo_fulfillments.modified_on` khi `status = 'success'` (hiện chưa expose ở `std_fulfillments`).
- **Business Logic:** Grain per carrier per period. AVG `date_diff('hour', shipped_at, delivered_at)` WHERE status = 'DELIVERED' AND both timestamps NOT NULL. GROUP BY carrier.
- **Formula:** `Avg Delivery Hours = AVG(delivered_at - shipped_at) WHERE status = 'DELIVERED'`
- **Logic (SQL):**
  ```sql
  SELECT c.carrier_name,
         AVG(date_diff('hour', f.shipped_at, f.delivered_at)) as avg_delivery_hours
  FROM fact_shipments f
  JOIN dim_carriers c ON f.carrier_key = c.carrier_key
  WHERE f.status = 'DELIVERED'
    AND f.shipped_at IS NOT NULL
    AND f.delivered_at IS NOT NULL
  GROUP BY c.carrier_name
  ```
- **Unit:** Hours
- **Classification:** lagging | absolute
- **Common Misunderstandings:** `delivered_at` được derive từ `modified_on` (Sapo) tại thời điểm shipment chuyển sang `status = 'success'` — đây là proxy, không phải thời điểm khách thực sự nhận hàng. Có thể off vài giờ đến vài ngày tùy carrier update Sapo.
- **Pitfalls / Edge Cases:** Carrier slow update sẽ inflate delivery time ảo. Outliers (1-2 đơn delivered sau 30 ngày do dispute) skew AVG mạnh — cân nhắc median hoặc trimmed mean. Phải normalize theo destination region để fair compare giữa carriers ship vùng khác nhau.

#### 12. Tỷ lệ thất bại theo carrier (Failed Delivery Rate by Carrier)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` JOIN `dim_carriers` (planned)

- **Business Definition:** Phần trăm shipment FAILED của từng carrier trên tổng shipment terminal của carrier đó. Đo reliability — carrier nào không giao được nhiều nhất.
- **Business Logic:** Grain per carrier per period. Numerator = COUNT shipment `status = 'FAILED'` per carrier. Denominator = COUNT shipment terminal (DELIVERED + FAILED + CANCELLED) per carrier.
- **Formula:** `Carrier Failure Rate (%) = Failed Shipments / Terminal Shipments per Carrier × 100`
- **Logic (SQL):**
  ```sql
  SELECT c.carrier_name,
         COUNT(CASE WHEN f.status = 'FAILED' THEN 1 END) * 100.0
         / NULLIF(COUNT(CASE WHEN f.status IN ('DELIVERED', 'FAILED', 'CANCELLED') THEN 1 END), 0) as failure_rate
  FROM std_fulfillments f
  JOIN dim_carriers c ON f.carrier_id = c.carrier_id
  GROUP BY c.carrier_name
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Nhầm với cancellation rate — FAILED là carrier không giao được; CANCELLED là shop chủ động hủy shipment. Khác nhau về nguyên nhân.
- **Pitfalls / Edge Cases:** Failure có thể do địa chỉ xấu (lỗi shop nhập) không phải lỗi carrier — cần break down theo failure reason nếu có. Sample size nhỏ (< 50 shipments) cho failure rate không đáng tin.

#### 13. Tỷ lệ trả hàng theo carrier (Return Rate by Carrier)

> **Status:** `planned`
> **dbt Source:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) JOIN `fact_shipments` JOIN `dim_carriers` (planned)

- **Business Definition:** Phần trăm shipment được giao thành công nhưng sau đó bị trả lại, breakdown theo carrier. Bổ sung Failed Delivery Rate để đánh giá overall carrier quality (failed + returned = total bad outcome).
- **Business Logic:** Grain per carrier per period. Numerator = COUNT returns join với shipments của carrier. Denominator = COUNT shipments DELIVERED của carrier (cohort matching: returns trong N ngày sau shipped_at).
- **Formula:** `Return Rate by Carrier (%) = Returned Shipments / Delivered Shipments per Carrier × 100`
- **Logic (SQL):**
  ```sql
  SELECT c.carrier_name,
         COUNT(DISTINCT r.return_id) * 100.0
         / NULLIF(COUNT(DISTINCT CASE WHEN f.status = 'DELIVERED' THEN f.fulfillment_id END), 0) as return_rate
  FROM fact_shipments f
  JOIN dim_carriers c ON f.carrier_key = c.carrier_key
  LEFT JOIN fact_order_returns r ON f.order_id = r.order_id
       AND r.return_date BETWEEN f.shipped_at AND f.shipped_at + INTERVAL '30 days'
  GROUP BY c.carrier_name
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Return không hoàn toàn lỗi carrier — đa số returns là do khách đổi ý hoặc sản phẩm không đúng kỳ vọng. Carrier-level return rate phản ánh tổ hợp damage in transit + customer dissatisfaction.
- **Pitfalls / Edge Cases:** Return có thể không trace về đúng shipment (đơn có 2 shipments, return 1 item) — cần logic join cẩn thận. Time window matching (returns trong 30 ngày) là quy ước — điều chỉnh tùy category (electronics có warranty return dài hơn).

---

## Context: Shipment Cost & COD

> **Description:** Khía cạnh tài chính của shipment — chi phí ship, COD outstanding (tiền hộ thu), tác động subsidy từ marketplace. Liên kết logistics với finance domain.
> **dbt Source:** `std_fulfillments` (COD) + [`stg_shopee_order_revenue`](../../../transformation/models/staging/stg_shopee_order_revenue.sql) (shipping fee components) — `fact_shipments` (planned)
> **Grain:** Per Shipment

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|---|---|---|---|---|
| COD Cash Flow | Có bao nhiêu tiền COD đang ở carrier chưa thu về? | COD Outstanding | `std_fulfillments.cod_amount`, `status` | `fact_shipments` mart |
| COD Recovery | Bao nhiêu % COD đã thu về thành công? | COD Collection Rate | `cod_amount`, `status = DELIVERED` | `fact_shipments` mart |
| Cost Efficiency | Ship đang ăn bao nhiêu % doanh thu? | Shipping Cost as % Revenue | Shopee shipping fees `active`; Sapo `planned` | Sapo carrier rate seed |
| Subsidy Impact | Marketplace subsidy bù bao nhiêu cho shipping? | Net Shipping Cost After Subsidy | `stg_shopee_order_revenue.shipping_subsidy_*` | None (Shopee only) |

### Analytical Questions

#### Q11. Có bao nhiêu tiền COD đang ở ngoài đường?

- **Question:** Tổng `cod_amount` của các shipment đang SHIPPING (chưa DELIVERED) là bao nhiêu?
- **Definition:** Đo lường cash-in-transit — số tiền COD đang ở carrier, chưa về tài khoản shop.
- **Nature:** Financial, leading — chỉ báo về cash flow upcoming.
- **Why It Matters:** COD outstanding cao kéo dài → cash flow xấu, vốn lưu động bị giữ. Là risk nếu carrier phá sản giữa chừng (mất tiền hộ thu). Cũng là chỉ báo về batch ship nhiều mà chưa delivered.
- **Tradeoffs / Caveats:** COD outstanding gồm cả shipments lỗi (FAILED chưa update) — phải clean status để tính chính xác. Carrier có thể đã thu nhưng chưa transfer về shop — đây vẫn được tính outstanding.
- **Insight / Action Enabled:** Outstanding > X days threshold → escalate carrier yêu cầu transfer; outstanding tăng đột biến DoD → check ship pipeline có nghẽn không.
- **Related Metrics:** COD Outstanding, COD Collection Rate.

#### Q12. Phí ship đang ăn bao nhiêu % doanh thu?

- **Question:** Tổng chi phí shipping (sau subsidy) trên tổng net revenue là bao nhiêu %?
- **Definition:** Cost ratio đo hiệu quả shipping economics — chi phí phải hợp lý so với doanh thu.
- **Nature:** Financial, lagging.
- **Why It Matters:** Shipping cost ratio > 15% thường nuốt margin của FMCG/consumer goods. Chỉ báo sớm về cần renegotiate carrier hoặc adjust pricing strategy (charge shipping cho khách).
- **Tradeoffs / Caveats:** Shopee có subsidy lớn (giảm net cost) — không thể compare ratio cross-channel mà không normalize subsidy. Sapo offline orders thường shop chịu shipping → ratio cao hơn online.
- **Insight / Action Enabled:** Ratio > 15% → consider charge khách shipping; channel cụ thể spike → review pricing/subsidy contract của channel.
- **Related Metrics:** Shipping Cost as % Revenue, Net Shipping Cost After Subsidy.

### Metrics

#### 14. COD Outstanding (Tiền hộ thu chưa về)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Tổng giá trị COD (cash on delivery) của các shipments đã ship nhưng chưa được carrier giao thành công và chuyển tiền về shop. Đại diện cash-in-transit — vốn lưu động đang bị giữ ở phía carrier.
- **Business Logic:** Grain per shipment, aggregate to total. SUM `cod_amount` WHERE `status = 'SHIPPING'`. Time basis = snapshot at current moment (không có time filter).
- **Formula:** `COD Outstanding = SUM(cod_amount) WHERE shipment status = 'SHIPPING'`
- **Logic (SQL):**
  ```sql
  SUM(cod_amount)
  -- WHERE status = 'SHIPPING'  (chưa delivered)
  -- AND cod_amount > 0
  ```
- **Unit:** VND
- **Classification:** leading | absolute
- **Common Misunderstandings:** Outstanding không có nghĩa carrier đang giữ tiền — có thể carrier chưa thu vì chưa giao thành công. Outstanding = "tiền potentially còn ngoài đường", không phải "tiền carrier đang nợ".
- **Pitfalls / Edge Cases:** Shipment `status = SHIPPING` lâu (> 7 ngày) thường đã FAILED nhưng chưa update — sẽ inflate outstanding ảo. Aging analysis (outstanding by ship date age) cần thiết để clean. COD_amount NULL với prepaid shipments — loại khỏi mẫu.

#### 15. Tỷ lệ thu COD thành công (COD Collection Rate)

> **Status:** `planned`
> **dbt Source:** `std_fulfillments` → `fact_shipments` (planned)

- **Business Definition:** Phần trăm giá trị COD đã được thu thành công (shipment DELIVERED) trên tổng COD đã ship. Đo lường hiệu quả collection của carrier — proxy cho cash recovery quality.
- **Business Logic:** Grain per shipment, ratio aggregate. Numerator = SUM `cod_amount` WHERE `status = 'DELIVERED'`. Denominator = SUM `cod_amount` WHERE `status IN ('DELIVERED', 'FAILED', 'CANCELLED')` (terminal).
- **Formula:** `COD Collection Rate (%) = Collected COD / Total Terminal COD × 100`
- **Logic (SQL):**
  ```sql
  SUM(CASE WHEN status = 'DELIVERED' THEN cod_amount ELSE 0 END) * 100.0
  / NULLIF(SUM(CASE WHEN status IN ('DELIVERED', 'FAILED', 'CANCELLED') THEN cod_amount ELSE 0 END), 0)
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Collection rate < 100% không phải lỗi carrier hoàn toàn — đa số do khách không nhận (FAILED). Cần break down by carrier để đánh giá đúng.
- **Pitfalls / Edge Cases:** Prepaid orders có `cod_amount = 0` — loại khỏi mẫu để tránh skew. Same shipment có thể có cả attempted delivery (status changes) — chỉ count terminal state cuối.

#### 16. Chi phí shipping (Shipping Cost as % Revenue)

> **Status:** `planned`
> **dbt Source:** [`stg_shopee_order_revenue`](../../../transformation/models/staging/stg_shopee_order_revenue.sql) (Shopee components — `active`) + Sapo carrier rate seed (planned). Aggregate mart `fact_shipments` chưa tồn tại nên metric tổng hợp đa kênh `planned`.

- **Business Definition:** Phần trăm doanh thu (gross revenue) bị tiêu cho phí shipping ròng (sau subsidy từ marketplace, sau khi trừ phần khách trả). Đo hiệu quả shipping economics — quá cao = ăn margin.
- **Business Logic:** Numerator = SUM `total_shipping_net` (Shopee đã pre-compute từ 6 components: paid_by_buyer + actual + subsidy + return_refund + refund_by_piship + failed_delivery; dấu của từng component theo quy ước Shopee). Denominator = SUM `gross_revenue`. Time basis = `order_placed_at`. Sapo cần seed base rate per carrier × destination để cộng thêm trước khi aggregate đa kênh.
- **Formula:** `Shipping Cost % = SUM(Net Shipping Cost) / SUM(Gross Revenue) × 100`
- **Logic (SQL):**
  ```sql
  -- Shopee channel (active source)
  SELECT
      SUM(total_shipping_net) * 100.0
      / NULLIF(SUM(gross_revenue), 0) as shipping_cost_pct
  FROM stg_shopee_order_revenue
  -- WHERE order_placed_at >= current_date - INTERVAL '30 days'
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** "Shipping fee paid by buyer" KHÔNG phải chi phí của shop — đó là revenue offset (khách trả thay). `total_shipping_net` là tổng đại số 6 components theo dấu quy ước Shopee; cần đọc semantic mỗi component trong [`stg_shopee_order_revenue`](../../../transformation/models/staging/stg_shopee_order_revenue.sql) trước khi diễn giải.
- **Pitfalls / Edge Cases:** Sapo offline POS không có shipping cost (khách tự lấy) — phải filter ra hoặc tính 0. Subsidy có thể âm (Shopee charge phụ phí thay vì subsidy) — phải verify dấu trong từng kỳ. Cross-channel aggregate cần `fact_shipments` để align grain và normalize cost basis.

#### 17. Tỷ lệ trả hàng (Return Rate)

> **dbt Source:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) JOIN [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Phần trăm đơn đã ship bị trả lại trong N ngày (mặc định 30). Đo lường mức độ unsatisfactory delivery — bao gồm cả lỗi sản phẩm, khách đổi ý, damage in transit.
- **Business Logic:** Grain per order. Numerator = COUNT DISTINCT order_id có return record trong window. Denominator = COUNT DISTINCT order_id đã ship (`first_shipped_at IS NOT NULL`). Window thường 30 ngày sau ship.
- **Formula:** `Return Rate (%) = Returned Orders / Shipped Orders × 100`
- **Logic (SQL):**
  ```sql
  SELECT COUNT(DISTINCT r.order_id) * 100.0
       / NULLIF(COUNT(DISTINCT CASE WHEN o.first_shipped_at IS NOT NULL THEN o.order_id END), 0) as return_rate
  FROM fact_orders o
  LEFT JOIN fact_order_returns r ON o.order_id = r.order_id
       AND r.return_date BETWEEN o.first_shipped_at AND o.first_shipped_at + INTERVAL '30 days'
  ```
- **Unit:** %
- **Classification:** lagging | relative
- **Common Misunderstandings:** Return Rate đo customer experience + product quality, không chỉ logistics. Carrier damage chỉ chiếm phần nhỏ — đa số là khách đổi ý/sản phẩm không match.
- **Pitfalls / Edge Cases:** Window 30 ngày là quy ước — categories khác nhau có natural return window khác (electronics 7-14 ngày, apparel có thể 30-60 ngày). Đơn ship gần đây chưa đến cuối window sẽ làm rate xuống ảo — cần loại đơn ship trong N ngày cuối khỏi denominator.

---

## Context: Staff & Operations

> **Description:** Hiệu suất nhân viên xử lý đơn — ai làm nhanh nhất, ai nhiều nhất, có balanced không. Hỗ trợ workforce planning và staff incentive.
> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) JOIN [`dim_staff`](../../../transformation/models/marts/core/dim_staff.sql)
> **Grain:** Per Staff per Day

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|---|---|---|---|---|
| Productivity | Nhân viên nào xử lý nhiều đơn nhất? Có balanced không? | Staff Productivity (Orders Processed) | `fact_orders.seller_staff_key`, `dim_staff` | None |
| Speed | Nhân viên nào nhanh nhất? | Staff Avg Processing Time | `time_to_complete_hours` per staff | None |
| Pipeline | Đơn đang ở stage nào? Funnel drop-off ở đâu? | Order Status Funnel | `fact_orders.status` | None |

### Analytical Questions

#### Q13. Nhân viên nào xử lý hiệu quả nhất?

- **Question:** Phân bố volume đơn xử lý theo nhân viên là gì? Top performer xử lý gấp bao nhiêu lần bottom?
- **Definition:** Đo workload distribution + identify top/bottom performer.
- **Nature:** Operational, lagging.
- **Why It Matters:** Imbalance > 3x (top > 3x bottom) báo hiệu assignment không công bằng hoặc skill gap lớn. Top performer ốm/nghỉ → throughput dropping mạnh.
- **Tradeoffs / Caveats:** Volume cao không có nghĩa hiệu quả — đơn nhỏ dễ xử lý nhanh hơn đơn lớn. Cần xem kèm avg processing time và return rate per staff.
- **Insight / Action Enabled:** Imbalance → rebalance assignment; bottom performer cần training; top performer cần backup để giảm key-person risk.
- **Related Metrics:** Staff Productivity, Staff Avg Processing Time.

#### Q14. Đơn đang nghẽn ở stage nào của pipeline?

- **Question:** Phân bố đơn theo từng status (OPEN/COMPLETED/ARCHIVED/CANCELLED) là gì? Có drop-off bất thường ở stage nào không?
- **Definition:** Funnel analysis — đo conversion qua các stage của pipeline đơn hàng.
- **Nature:** Operational, leading — snapshot real-time.
- **Why It Matters:** Drop-off bất thường (ví dụ: OPEN → COMPLETED rate xuống) báo hiệu nghẽn xử lý. Là input chính cho weekly ops review.
- **Tradeoffs / Caveats:** Cohort vs snapshot khác nhau — snapshot mix đơn nhiều thời điểm; cohort theo dõi 1 batch. Mix dễ misleading.
- **Insight / Action Enabled:** OPEN → COMPLETED conversion < 80% sau 7 ngày → review backlog; CANCELLED rate spike → check root cause (inventory, payment fail).
- **Related Metrics:** Order Status Funnel, Fulfillment Rate.

### Metrics

#### 18. Năng suất nhân viên (Staff Productivity)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) JOIN [`dim_staff`](../../../transformation/models/marts/core/dim_staff.sql)

- **Business Definition:** Số đơn được xử lý bởi mỗi nhân viên trong kỳ phân tích, kèm thời gian xử lý trung bình. Đo workload + speed ở grain nhân viên.
- **Business Logic:** Grain per staff per period. COUNT DISTINCT `order_id` GROUP BY `seller_staff_key`. AVG `time_to_complete_hours` cho speed dimension. Loại DRAFT, CANCELLED khỏi mẫu.
- **Formula:** `Orders Processed per Staff = COUNT(DISTINCT order_id) per staff; Avg Processing Time = AVG(time_to_complete_hours) per staff`
- **Logic (SQL):**
  ```sql
  SELECT
      ds.staff_name,
      COUNT(DISTINCT fo.order_id) as total_orders,
      AVG(fo.time_to_complete_hours) as avg_processing_hours
  FROM fact_orders fo
  JOIN dim_staff ds ON fo.seller_staff_key = ds.staff_key
  WHERE fo.status NOT IN ('DRAFT', 'CANCELLED')
  GROUP BY ds.staff_name
  ORDER BY total_orders DESC
  ```
- **Unit:** Count (orders) + Hours (processing time)
- **Classification:** lagging | absolute
- **Common Misunderstandings:** Productivity = volume + speed, không chỉ volume. Nhân viên xử lý ít nhưng nhanh có thể vẫn hiệu quả nếu đơn được phân bố không đều.
- **Pitfalls / Edge Cases:** `seller_staff_key` có thể NULL với đơn được xử lý qua hệ thống tự động (Shopee auto-fulfillment) — phải loại hoặc map sang "System" bucket. Nhân viên chuyển team / nghỉ giữa kỳ có thể tính sai nếu dùng SCD2 snapshot không đúng date.

#### 19. Funnel trạng thái đơn (Order Status Funnel)

> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Số đơn ở từng stage của pipeline (OPEN → COMPLETED → ARCHIVED → CANCELLED). Funnel visualization để phát hiện drop-off bất thường.
- **Business Logic:** Grain per order. COUNT GROUP BY `status`. Loại DRAFT (chưa vào pipeline). Có 2 mode: snapshot (status hiện tại) hoặc cohort (đơn tạo trong kỳ, status cuối).
- **Formula:** `Funnel Count = COUNT(orders) per status`
- **Logic (SQL):**
  ```sql
  SELECT
      status,
      COUNT(*) as order_count
  FROM fact_orders
  WHERE status != 'DRAFT'
  GROUP BY status
  ORDER BY
      CASE status
          WHEN 'OPEN' THEN 1
          WHEN 'COMPLETED' THEN 2
          WHEN 'ARCHIVED' THEN 3
          WHEN 'CANCELLED' THEN 4
      END
  ```
- **Unit:** Count (mỗi status)
- **Classification:** lagging | absolute
- **Common Misunderstandings:** ARCHIVED không phải xấu — chỉ là đơn đã closed hoàn toàn (sau COMPLETED). Drop từ COMPLETED → ARCHIVED là natural.
- **Pitfalls / Edge Cases:** Snapshot vs cohort khác nhau — snapshot count đơn current status (mix nhiều cohort); cohort track 1 batch theo thời gian. Mix lẫn dễ misleading trong storytelling.
---

## Available Dashboards

| Dashboard | Audience | Purpose | Blueprint |
|-----------|----------|---------|-----------|
| Logistics Operations Center | Operations Manager | Real-time pipeline monitoring — fulfillment rate, processing speed, stuck orders | [`logistics_operations`](../blueprints/logistics_operations.md) |

## Related Playbooks

| Playbook | Uses Metrics |
|----------|-------------|
| [Logistics Operations](../playbooks/logistics_operations.md) | Fulfillment Rate, Order Cycle Time, Same-Day Ship Rate, Order Status Funnel, Staff Productivity |
| [Logistics Shipping (planned)](../playbooks/logistics_shipping.md) | Shipment Volume, Carrier Volume Share, Delivery Success Rate, COD Outstanding (planned) |

<!--
Metric Status Reference:
  - `active`     — dbt model exists, data available, ready to query
  - `planned`    — metric defined but dbt model not yet built
  - `mixed`      — partially active (some channels/sources active, others planned)
  - `deprecated` — no longer used, kept for historical reference
-->