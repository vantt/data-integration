# Phase Hug — Dynamic Touchpoint Platform

> Stage A · **Platform dùng chung** (A2 identity-capture, A3 đơn-2, loyalty, review, reorder…) · Status: 🔵 bàn sâu
> Context: [`discussion.md`](./discussion.md) §16–17 · `plans/reports/order-economics-incentive-sizing-260619-1054-report.md`
> 🧵 Dialogue thiết kế & quyết định: [`discussion-hug.md`](./discussion-hug.md)
> Tách từ A2: **Hug là CƠ CHẾ**; A2/A3/… là campaign *chạy trên* Hug.

## Hug là gì (1 câu)

> **"Mỗi kiện hàng kèm một cái ôm."** QR câm in 1 lần trên thẻ → server Hug quyết định **động lúc quét** → route tới campaign tốt nhất, nối định danh, phát ưu đãi, đo lường khép vòng. **In một lần, lập trình mãi mãi.**

## Nguyên tắc nền

- **Dumb QR, smart server (late binding):** bản in chỉ mang token đục ổn định; mọi hành vi quyết định lúc QUÉT, không phải lúc IN.
- **Always-on fallback:** kiện cũ quét sau nhiều tháng vẫn có trải nghiệm hữu ích (không dead-end).
- **Per-shipment token**, resolvable → customer (đủ context cho offer + attribution + phát hiện quét-lặp).
- **Campaign là DATA** (config), đổi bất cứ lúc nào, không in lại.

---

## 🔱 Năng lực cốt lõi (9 trụ) — map thẳng mục tiêu

### Mũi nhọn (3 năng lực nổi bật bạn nhấn)

**1. Best-Campaign Routing — Decision Engine**
Lúc quét, đánh giá rule active theo **context** (tier, kênh, giá trị đơn, **scan-count**, recency, geo, mùa vụ, thời gian-từ-lúc-giao) → chọn **đúng 1** campaign/đích/offer. Priority-ordered, first-match, có always-on fallback. Mỗi quyết định log kèm "vì sao".
→ *Hỗ trợ:* khách `MASKED_REPEAT` → opt-in capture; `LIVE_CORE` quét lại → reorder/loyalty; VIP ≠ one-timer.

**2. Concurrent Multi-Campaign — Targeting & Arbitration**
Nhiều campaign sống cùng lúc, mỗi cái có: **audience predicate + priority + lịch + quota/budget**. Hug *trọng tài* chọn campaign thắng cho từng lượt quét, không đụng nhau.
→ *Hỗ trợ:* chạy song song "capture opt-in" + "Tết sale" + "xin review" mà không xung đột; tách audience theo tier.

**3. Smart Tracking — Closed-Loop Attribution**
Mỗi quét = 1 event đầy context. Phễu: **scan → follow/opt-in → voucher issue → redemption → đơn lặp**. Quy revenue đơn lặp về **shipment / campaign / variant**. Cohort theo lô đóng gói.
→ *Hỗ trợ:* đo ROI thật của thẻ insert & từng campaign; feed lại tier + engine Stage B.

### Trụ nền (làm 3 mũi nhọn chạy được & mạnh)

**4. Identity Resolution Bridge** *(linchpin của A2)*
Per-shipment token map xác định scan → `customer_id` (không PII trên URL). Lúc opt-in: nối **SĐT/Zalo mới ↔ record Sapo cũ (đang masked)** → kế thừa ngay full RFM/history → tier tự nâng `masked → contactable`.
→ *Hỗ trợ:* **mở khóa 683M VND CM** đang treo sau 364 khách masked-repeat.

**5. Offer/Voucher Engine**
Phát mã **unique, gắn customer_id, single-use** lúc quét; **min-order + loại SKU lỗ** (chặn 12% đơn âm margin); track issue→redeem→đơn lặp. **Self-funding** (chỉ tốn khi redeem).
→ *Hỗ trợ:* ưu đãi A2 (50K) & A3 an toàn margin.

**6. Lifecycle Evolution — Scan-Aware**
Đích thay đổi theo **scan-count + trạng thái khách**: quét lần đầu = welcome + opt-in; quét sau = đặt-lại nhanh / loyalty / review / bảo hành.
→ *Hỗ trợ:* 1 tài sản vật lý phục vụ **cả vòng đời** (A3, loyalty, review) — không in thêm.

**7. Built-in Experimentation (A/B/MV)**
Server chia traffic theo biến thể offer/landing → đo conversion → promote winner. Không in lại.
→ *Hỗ trợ:* tối ưu ưu đãi opt-in (50K voucher vs quà), landing, CTA.

**8. Consent & Compliance Capture**
Ghi **consent per-channel** (phone/Zalo) ngay lúc opt-in → feed DNC gate cho mọi outreach (engine Stage B).
→ *Hỗ trợ:* outreach hợp pháp; tích hợp scoring sau.

**9. Channel Orchestration**
Đích chính = **Zalo OA deep-link** (hạ tầng đã có); fallback web landing / mini-form xin SĐT.
→ *Hỗ trợ:* capture VN-native, tỉ lệ cao.

---

## Luồng lúc quét (scan-time)

```
1. GET /h/{token}
2. resolve token → context {customer_id, order_code, channel, ship_date, tier, scan_count}
3. arbitrate campaigns active (predicate match × priority × lịch × quota) → chọn winner
4. render đích (Zalo OA deep-link / landing / lộ voucher / mini-form)
5. (nếu opt-in) nối định danh + ghi consent + nâng tier
6. (nếu campaign có offer) phát voucher unique gắn customer_id
7. log scan_event (full context + campaign + variant)  ← attribution
```

## Data model (sketch)

- `hug_token` — token (PK, **opaque random-12 Crockford-b32, unique index**) → customer_id (**nullable**), **op_type**, order_code (bind key), channel, ship_date, sku[], campaign_hint, status (printed→bound), batch_id, issued_at, revoked · *format/pre-print/claim: `discussion-hug.md` §11*
- `hug_customer` — customer_id (PK) → tier, recency_days, value_group, is_contactable, updated_at — **mutable, local refresh nightly** (replica nhỏ của `mart_customer_tier`; cho tier tươi mà token bất biến)
- `hug_campaign` — id, name, **targeting** (JSON: AND giữa điều kiện · OR list trong 1 điều kiện), destination_type, destination_url, offer_ref, priority (first-match), schedule_start/end, quota_total/used, status
- `hug_scan_event` — token, customer_id, campaign_id, variant, ts, outcome (view/follow/optin/redeem)
- `hug_voucher` — code (PK), customer_id, campaign_id, min_order, sku_guard, issued_at, redeemed_at, order_code
- `hug_consent` — customer_id, channel (phone/zalo), granted_at, source
- `hug_optin_event` — token, buyer_customer_id, phone?, zalo_uid?, name?, consent{}, ts (parquet, edge→local)
- `crm_identity_link` — token, buyer_customer_id, scanner_phone, scanner_zalo_uid, resolved_customer_id, confidence, status (linked | needs_review), ts
- **contactability 4 cấp:** masked → zalo_follower → phone_unverified → phone_verified

## Kiến trúc / nơi ở (KISS)

Public router trong CRM FastAPI: `GET /h/{token}`. 5 bảng trên (crm.db hoặc store riêng). Sinh token lúc đóng gói (API kéo order từ Sapo → tạo `hug_token` → render QR lên thẻ). Tách edge service sau nếu cần uptime/scale.

## Năng lực → Mục tiêu (matrix)

| Mục tiêu | Trụ Hug dùng |
|---|---|
| A2 capture masked-repeat (683M CM) | 4 bridge · 1 routing · 5 voucher · 8 consent · 9 zalo |
| A3 đẩy đơn-2 | 6 lifecycle · 1 routing · 5 voucher · 3 tracking |
| Loyalty / review / reorder (sau) | 6 lifecycle · 2 multi-campaign · 1 routing |
| Tối ưu liên tục | 7 A/B · 3 tracking |
| Feed engine Stage B | 4 bridge (nâng tier) · 8 consent · 3 attribution |

---

## Hosting Architecture (grounded — TÁI DÙNG hạ tầng có sẵn, chi phí ≈ 0)

Hạ tầng webhook hiện tại ĐÃ là ~90% Hug cần (scout xác nhận):
- CF Worker `webhook-receiver` (`webhook-receiver.admin-1d2.workers.dev`) — public edge, free tier.
- CF **D1** `fgcare-webhook-db` — SQLite ở edge, đang dùng làm FIFO queue (optimistic lock + visibility timeout 60s).
- Pattern **poll/buffer-drain**: sender → Worker → D1(status=NEW) → local `GET /poll` → xử lý → `/ack-batch` xóa. **Local KHÔNG lộ ra ngoài** (không tunnel).
- Local ingest: Dagster `ingest_sapo_v2_webhook_consumer_asset`, 3 phút/lần → dlt parquet theo `entity_type` → dbt → serving → crm_cache.
- **Tái dùng cho event mới = ĐƯỢC:** Worker nhận mọi `/webhook/<source>/<entity>/<action>`; consumer tự route → parquet. `source_system=hug` poll riêng → pipeline xử lý riêng.

### Hug = 2 path
- **WRITE (tracking) — TÁI DÙNG 100%:** scan/opt-in → `POST /webhook/hug/scan/created` → D1 buffer → local poll `source_system=hug` → parquet `hug_scan` → identity bridge + attribution. (Đúng "dùng webhook hiện có, pipeline xử lý riêng".)
- **READ (scan→route→redirect) — MỚI (nhỏ):** thêm route `GET /h/{token}` vào Worker:
  1. resolve token → context (xem fork)
  2. đọc `hug_campaign` (bảng D1 **persistent** riêng, vài dòng) → chọn campaign → url
  3. 302 redirect tới landing
  4. `waitUntil()` ghi scan vào D1 buffer (non-blocking → redirect tức thì)

### ⚠️ Correction cho flow đề xuất
"load dữ liệu liên quan" PHẢI đọc ở **EDGE** (token tự mang / D1 lookup), **KHÔNG gọi về local** — gọi local = phải lộ local + phụ thuộc PC bật. Edge giữ bản đọc nhỏ; local vẫn là brain.

### Landing pages
Mỗi campaign = 1 url: **Zalo OA deep-link** (follow, không cần page) / **Cloudflare Pages** (form opt-in, voucher reveal — free static). Thêm/đổi campaign = update `hug_campaign` row → không in lại, không redeploy.

### Chi phí
CF Worker free 100k req/ngày (volume vài trăm scan/tháng) · D1 free · CF Pages free · domain ngắn ~$10/năm (tùy chọn, QR đẹp) hoặc dùng workers.dev. **≈ $0.**

### Worker — routes & storage (recap)
Mở rộng Worker `webhook-receiver` hiện có (cùng deploy, cùng D1 `fgcare-webhook-db`).

| Route | Auth | Việc |
|---|---|---|
| `GET /h/{token}` | public | scan → resolve → arbitrate → 302 redirect + `waitUntil` ghi scan |
| `POST /webhook/hug/optin/created` | HMAC | opt-in (form/Zalo follow) → D1 queue |
| `GET /poll?source_system=hug` · `POST /ack-batch` | (có sẵn) | local drain hug events |
| `POST /hug/token/upsert` | admin HMAC | provision token (lúc đóng gói) |
| `POST /hug/customer/upsert` | admin HMAC | nightly tier từ `mart_customer_tier` |
| `POST /hug/campaign/upsert` | admin HMAC | admin UI lưu campaign |

**D1 — 2 loại bảng:**
- *Transient queue* (có sẵn): `webhooks` — FIFO, xóa khi ack; scan/opt-in events đổ vào (`source=hug`) → local drain.
- *Persistent read* (mới, KHÔNG drain): `hug_token` (**projection bound-only từ local master**) · `hug_customer` (nightly mutable) · `hug_campaign` (rules) · `hug_voucher` (issuance + quota). Master `hug_token` đầy đủ ở **local**; D1 chỉ giữ token đã bound — xem `discussion-hug.md` §11.

**Đọc (scan):** `/h` → D1 `hug_token` → D1 `hug_customer` → campaign list (cache ~60s) → redirect → `waitUntil` ghi queue (non-blocking).
**Ghi (tracking):** events → D1 queue → local poll (3') → xử lý → ack (xóa).
**Provision:** local → admin routes (HMAC) → upsert persistent tables.
**Auth:** `/h` public (opaque, rate-limited) · `/webhook/*` + `/hug/*` HMAC.

### Token scheme — ✅ CHỐT (A) opaque + D1 `hug_token`
Token = chuỗi random vô nghĩa; edge tra D1 → context. Không PII trên URL · revocable · tier refresh được. Local push token lúc đóng gói (admin route, reuse kênh CF).

**Token = handle tới (AI × OPERATION × CONTEXT):**
- 1 khách (PII) → **nhiều token**; mỗi token = 1 *operation/occasion* riêng (package insert · loyalty card · win-back flyer · hóa đơn…). Quan hệ token→customer là **N:1**.
- Token tự nó vô nghĩa; row D1 mang `op_type` = **ý nghĩa operation** → vừa định vị khách (map token↔customer_id) vừa biết "đang làm gì" → là **input cho routing**.
- Token có thể CHƯA gắn khách (flyer chung) → `op_type='acquire'`.
- → Hug tổng quát thành hệ **tokenized touchpoint**: mọi điểm chạm = 1 opaque token resolve về *(khách? + operation + context)*.

> Lưu ý: D1 `webhooks` xóa-khi-ack (queue) → ok cho scan events; nhưng `hug_token`/`hug_campaign` phải là bảng D1 **persistent riêng**. Depth-guard 10k NEW dùng chung Sapo → cân nhắc tách source nếu Sapo dồn.

## Open (bàn sâu kỳ tới)

1. ✅ **Token scheme:** CHỐT (A) opaque + D1; token = handle (ai × op_type × context). Xem Hosting Architecture.
2. ✅ **Routing rule model:** CHỐT — structured targeting (AND/OR) + priority first-match + admin UI. Xem `discussion-hug.md` §7.
3. ✅ **Arbitration:** CHỐT — priority first-match (tie-break campaign_id); quota đếm trên voucher issuance, soft counter. Xem `discussion-hug.md` §9.
4. ✅ **Identity bridge:** CHỐT — scanner≠buyer reframe; unclaimed→gán, conflict→review; no-OTP v1; contactability 4 cấp. Xem `discussion-hug.md` §8.
5. ✅ **Voucher guard:** CHỐT — ride Sapo coupon (enforce lúc redeem); min_order + loại SKU margin-âm. ⚠️ verify Sapo coupon API. Xem `discussion-hug.md` §9.
6. ✅ **Hosting:** chốt — reuse CF Worker + D1 (xem Hosting Architecture). Còn lại: chốt token scheme (A/B).
7. **Privacy/PII:** opaque token (A) → không PII edge; nếu signed (B) cân nhắc mã hóa. Consent/PDPD VN.
