# Hug — Design Discussion (rationale & decisions)

> Bản ghi *dialogue thiết kế* riêng cho Hug (tách khỏi spec). Spec đầy đủ: [`phase-hug-dynamic-touchpoint-platform.md`](./phase-hug-dynamic-touchpoint-platform.md). Bối cảnh tổng: [`discussion.md`](./discussion.md) §16–17.
> Date: 2026-06-19 · Branch: main

---

## 1. Hug là gì & vì sao tách thành platform riêng

Hug = **dynamic touchpoint platform**: QR câm in 1 lần trên điểm chạm → server quyết định động lúc quét → route campaign tốt nhất, nối định danh, phát ưu đãi, đo khép vòng. *In một lần, lập trình mãi mãi.*

Tách khỏi A2 vì Hug là **cơ chế dùng chung**; A2 (identity capture), A3 (đơn-2), loyalty, review… là campaign *chạy trên* Hug. 3 năng lực nổi bật: **route campaign tốt nhất · đa-campaign song song · smart tracking**.

---

## 2. QUYẾT ĐỊNH — Hosting architecture: tái dùng hạ tầng CF có sẵn (≈ $0)

**Bối cảnh ràng buộc:** CRM/warehouse chạy **local, không host online** (tiết kiệm chi phí); Hug phải **online** (khách quét mọi nơi). Ngân sách thấp. Hướng Cloudflare/Vercel.

**Phát hiện then chốt (scout):** hạ tầng webhook hiện tại ĐÃ là ~90% Hug cần:
- CF Worker `webhook-receiver` (`*.workers.dev`) + CF **D1** `fgcare-webhook-db` (edge SQLite, FIFO queue + optimistic lock + visibility timeout 60s).
- Pattern **poll/buffer-drain**: sender → Worker → D1(`NEW`) → local `GET /poll` → xử lý → `/ack-batch` xóa. **Local không lộ ra ngoài, không tunnel.**
- Local ingest: Dagster `ingest_sapo_v2_webhook_consumer_asset`, 3 phút/lần → dlt parquet theo `entity_type` → dbt → serving → crm_cache.
- **Worker nhận mọi `/webhook/<source>/<entity>/<action>`; poll lọc theo `source_system`** → `source_system=hug` poll riêng, pipeline xử lý riêng.

**Hug = 2 path:**
- **WRITE (tracking) — TÁI DÙNG 100%:** scan/opt-in → `POST /webhook/hug/scan/created` → D1 buffer → local poll `source=hug` → parquet `hug_scan` → identity bridge + attribution. (Đúng ý "dùng webhook hiện có, pipeline xử lý riêng".)
- **READ (scan→route→redirect) — MỚI, nhỏ:** thêm route `GET /h/{token}` vào Worker: resolve token → đọc `hug_campaign` (D1 persistent) → 302 redirect → `waitUntil()` ghi scan (non-blocking).

**⚠️ Correction cho flow ban đầu:** "load dữ liệu liên quan" phải đọc ở **EDGE** (D1/token), **KHÔNG gọi về local** — gọi local = phải lộ local + phụ thuộc PC bật lúc khách quét. Edge giữ bản đọc nhỏ; local vẫn là brain.

**Landing pages:** mỗi campaign = 1 url — Zalo OA deep-link (follow) / Cloudflare Pages (form, voucher reveal — free). Đổi/thêm campaign = update `hug_campaign` row → không in lại, không redeploy.

**Chi phí:** Worker free 100k req/ngày · D1 free · CF Pages free · domain ngắn ~$10/năm (tùy chọn). **Không cần Vercel** — CF đang có là fit hoàn hảo.

> Lưu ý kỹ thuật: D1 `webhooks` xóa-khi-ack (queue) → ok cho scan events; `hug_token`/`hug_campaign` phải là bảng D1 **persistent riêng**. Depth-guard 10k NEW dùng chung Sapo → cân nhắc tách source nếu Sapo dồn.

---

## 3. QUYẾT ĐỊNH — Token scheme = (A) opaque + D1 lookup

Chọn **opaque** (token random vô nghĩa, edge tra D1 → context) thay vì signed token, vì:
- **Không PII trên URL** (signed token lộ `customer_id` khi decode; URL QR dễ lộ qua ảnh/log). PII nặng (SĐT) vẫn chỉ ở local.
- **Revocable** + **tier refresh được** (local cập nhật context bất cứ lúc nào) → mở đường tier-routing v2 không phải làm lại.
- Provisioning rẻ: local push token lúc đóng gói qua 1 admin route, tái dùng kênh CF.
- Hợp hướng giảm phơi PII (VN Nghị định 13/2023 PDPD).

### Insight: Token = handle tới (AI × OPERATION × CONTEXT)
```
token (random) → row D1 {
   customer_id  ← AI        (nullable — flyer chung thì chưa gắn khách)
   op_type      ← OPERATION (package_insert / loyalty_card / winback_flyer / receipt / acquire …)
   context      ← order_code, channel, ship_date, sku, campaign_hint
}
```
- **1 khách → N token** (mỗi điểm chạm/lần đóng gói = 1 token). `token→customer` = **N:1**.
- **1 token → 1 operation** (`op_type`); token là khóa join ghim đúng *(khách, operation, lần)* → **attribution theo từng operation**.
- Token tự nó vô nghĩa; ý nghĩa nằm ở `op_type` trong D1 → vừa định vị khách (map token↔customer_id) vừa biết "đang làm gì".
- Token chưa gắn khách → `op_type='acquire'` (operation = đi tìm danh tính).

### Hệ quả: Hug = hệ "tokenized touchpoint"
Mô hình không bó trong thẻ-trong-kiện. **Mọi điểm chạm** (kiện, thẻ loyalty, QR hóa đơn, flyer, mã KOL) = 1 opaque token resolve về *(khách? + operation + context)*. Một platform, vô số điểm chạm. `op_type` là **input mạnh cho routing** (cùng 1 khách, op khác → trải nghiệm khác).

---

## 4. Quyết định đã chốt

- ✅ Hosting: **reuse CF Worker + D1** (poll/buffer-drain). Write-path tái dùng 100%; chỉ thêm read route `GET /h/{token}`.
- ✅ Edge đọc context ở chỗ edge (D1), **không gọi local** ở hot path.
- ✅ Token scheme = **(A) opaque + D1 `hug_token`**.
- ✅ Token model = handle *(customer_id nullable × op_type × context)*; 1 khách → N token.
- ✅ Landing pages = CF Pages / Zalo deep-link; campaign đổi qua data, không redeploy/in lại.
- ✅ Chi phí ≈ $0; không dùng Vercel.

---

## 5. Open threads (mổ tiếp)

2. ✅ **Routing rule model** — CHỐT (§7).
3. ✅ **Arbitration** — CHỐT (§9).
4. ✅ **Identity bridge** — CHỐT (§8).
5. ✅ **Voucher guard** — CHỐT (§9; ⚠️ verify Sapo coupon API khi implement).
6. ✅ **Provisioning push** — CHỐT (§9).

→ **Khung thiết kế Hug ĐÓNG.** Việc còn lại thuộc implement: verify Sapo coupon API · build admin UI · build Worker read-route + admin routes · local resolution + nightly push.

---

## 6. Số liên quan (từ probe)

- Prize A2: **364 masked-repeat = 683M VND CM** treo sau định danh; ~1.88M CM/khách.
- Trần ưu đãi an toàn: Shopee ≤30–50K · overall ≤50–100K (12.2% đơn âm margin → voucher cần min-order + loại SKU lỗ).

---

## 7. QUYẾT ĐỊNH — Routing rule model (#2)

**Mô hình:** *structured declarative targeting + priority first-match* (pattern feature-flag/ad-targeting). Loại: JSONLogic/CEL (để escape hatch v2), SQL fragment (unsafe), hardcode (redeploy).

**Context 2 bảng** (tier tươi mà token bất biến):
- `hug_token` — **bất biến**, ghi lúc đóng gói (customer_id?, op_type, order_code, channel, ship_date, sku).
- `hug_customer` — **đổi được**, local refresh **nightly** (customer_id → tier, recency_days, value_group, is_contactable) = replica nhỏ của `mart_customer_tier` (~7.5k dòng).
- context lúc quét = `join(hug_token, hug_customer)` + `now` + `scan_index`.

**Matching semantics (CHỐT):**
- targeting = tập điều kiện; **giữa các điều kiện = AND** (qua hết mới khớp).
- **list trong 1 điều kiện = OR** (trúng 1 giá trị là pass).
- thiếu điều kiện = không lọc thuộc tính đó.
- cần **OR giữa 2 thuộc tính** → tách thành nhiều campaign cùng đích.
- 1 quét có thể khớp **nhiều** campaign → chỉ chạy **priority cao nhất**; `DEFAULT` (targeting rỗng, priority đáy) always-on → không dead-end.

**Catalog cố định (an toàn):** attributes {op_type, tier, channel, value_group, recency_days, order_value, scan_index, is_contactable, geo} · operators {in, gte, gt, lte, lt, eq, ne}.

**Eval edge (~10 dòng):** active (status=active, trong schedule, còn quota) → sort priority asc → first-match → DEFAULT. Cache campaign list trong Worker TTL ~60s.

**Authoring — CHỐT Admin UI** (không Google Sheet; có AI support build). UX trọng tâm: chọn điều kiện bằng **dropdown** (không gõ JSON), **preview** "khớp ~bao nhiêu khách + khách mẫu", cảnh báo **chồng lấp** campaign. Validate-on-write theo catalog.

**An toàn:** catalog cố định + validate-on-write + DEFAULT always-on + versioning (updated_at + history → rollback).

**Arbitration:** priority first-match (minh bạch). Score-based để v2. → đào sâu #3.

---

## 8. QUYẾT ĐỊNH — Identity Bridge (#4)

**Reframe cốt lõi:** opt-in định danh **NGƯỜI QUÉT** (SĐT họ để lại); token cho **CONTEXT đơn** (`buyer_customer_id`). **Không ép scanner==buyer** → hết corruption.

**Happy path (≈90% của 364 masked-repeat):** masked buyer tự quét kiện → để SĐT chưa thuộc ai → gán vào buyer → contactable + kế thừa full history. Rủi ro thấp (đang masked, không có SĐT để ghi đè; SĐT chưa ai nhận).

**Policy edge case** (unclaimed→gán · conflict→review · quà→người quét · KHÔNG ghi đè SĐT người khác):
| Tình huống | Resolve |
|---|---|
| SĐT khớp đúng buyer | confirm → `phone_verified` |
| SĐT chưa thuộc ai + buyer masked | **gán buyer** → contactable |
| SĐT đã thuộc C khác | KHÔNG merge tự động → opt-in về **C**; link cross-signal (quà/hộ) → `needs_review` |
| Quà (B quét kiện A) | opt-in về **B**; A không đụng |
| Chỉ follow Zalo, không SĐT | `zalo_uid` → `zalo_follower` |
| Nhiều SĐT / đổi số | thêm identity, không xóa (crm_party_identity multi-identity) |
| Opt-in lại | idempotent theo (token+phone) → update |

**Contactability 4 cấp (CHỐT)** — thay nhị phân, nối lại contactability ladder (main §8):
`masked → zalo_follower → phone_unverified → phone_verified`. NBA engine Stage B dùng chung (ZNS/call cần phone; OA broadcast chỉ cần zalo).

**Chạy ở đâu + đóng vòng:** edge chỉ *bắt* event opt-in thô (`POST /webhook/hug/optin/created` → D1). **LOCAL** resolve (có Sapo + crm_party_identity) → `crm_identity_link` + enrich contact + nâng `contact_quality`; conflict → `needs_review` CS queue. Đóng vòng: enrich → `dim_customers.is_contactable` → tier → nightly → `hug_customer`.

**3 quyết định chốt:**
- **OTP lúc opt-in: KHÔNG (v1)** — tối đa capture (đang là bottleneck); để `phone_unverified`, xác minh lười khi liên hệ đầu thành công. Chấp nhận ít SĐT rác.
- **Auto-gán SĐT chưa-thuộc-ai vào buyer masked: CÓ** (happy path, rủi ro thấp); conflict→review; monitor gift.
- **Contactability 4 cấp: CÓ.**

**Data model thêm:** `hug_optin_event` (parquet: token, buyer_customer_id, phone?, zalo_uid?, name?, consent{}, ts) · `crm_identity_link` (token, buyer_customer_id, scanner_phone, scanner_zalo_uid, resolved_customer_id, confidence, status[linked|needs_review], ts).

---

## 9. CHỐT NHANH — #3 Arbitration · #5 Voucher guard · #6 Provisioning

### #3 Arbitration
- **Priority first-match**: priority unique (admin UI enforce), tie-break `campaign_id`; first-match **dừng** → 1 trải nghiệm/quét.
- **Quota** đếm trên **voucher issuance** (tiền), KHÔNG trên raw scan. v1 = lifetime cap optional (`quota_total`); `quota_period` (day/month) để v2. Soft counter (eventual) — over-issue biên nhỏ chấp nhận; strict budget → Durable Object (v2).
- **A/B**: campaign thắng → variant split bằng `hash(token)` → bucket.

### #5 Voucher guard — ride Sapo coupon
- Offer fields: discount(amount/pct), `min_order_value`, eligible/excluded SKUs, `valid_days`, `single_use`, channel_scope.
- **Ranh giới Hug vs Sapo:** Sapo = *engine giảm giá* (rule %/amount, min-order, scope, single-use, expiry + ENFORCE lúc checkout). Hug = *quyết-phát + gắn-danh-tính + đo-redeem* (cái Sapo không biết). Hug KHÔNG build redemption engine.
- **`hug_voucher` = sổ phát hành** `{code, customer_id, token, campaign_id, issued_at, redeemed_at?, order_code?}` — không phải engine giảm giá.
- **Vòng redeem đi nhờ pipeline Sapo có sẵn:** khách dùng mã → đơn Sapo ghi coupon code → ingest đơn (webhook→parquet) → match về hug_voucher → mark redeemed → attribute. Không tích hợp redeem riêng.
- **3 flavor tạo mã (V1 verify chốt):** (B) per-customer qua Sapo API — sạch nhất; (A) pool mã tạo sẵn, Hug phát lẻ + ghi binding; (C) 1 mã chung "HUG50" — fallback, mất binding/attribution per-customer.
- Economics guard (probe): Shopee voucher 50K → `min_order` 300K; auto loại SKU `is_margin_negative`.
- ✅ **Verify (2026-06-19):** `order_coupon_code` có sẵn trong raw đơn (thêm `json_extract` ở staging → match được). Sapo write-API chưa verify → **v1 flavor C+**: mã shared-per-campaign tạo tay (`once_per_customer`+min), **match redeem theo (customer_id + code)**. Token-tie = **web form** (OA follow không mang token); **ZNS vắng** → A4 nhắn tay v1. Chi tiết: `plans/reports/hug-verify-sapo-coupon-zalo-deeplink-260619-1432-report.md`.

### #6 Provisioning push (local → D1)
- Admin routes trên Worker hiện có (HMAC như pattern Sapo):
  - `POST /hug/token/upsert` — lúc đóng gói (per shipment/batch)
  - `POST /hug/customer/upsert` — nightly từ `mart_customer_tier` (changed rows)
  - `POST /hug/campaign/upsert` — khi admin UI lưu
- **Token sinh LOCAL** (random base62/nanoid ~10 ký tự) lúc đóng gói → tạo `hug_token` local → push D1 → in QR. **Integration point = bước in thẻ/label.**
- Idempotent upsert theo PK; fail→retry; token thiếu ở D1 → scan rơi DEFAULT (graceful).
- Cùng Worker; bảng `hug_*` persistent **tách** khỏi `webhooks` queue (khác lifecycle).

---

## 10. Worker — cơ chế kỹ thuật (recap đầy đủ)

**Nền:** mở rộng Worker `webhook-receiver` đang chạy (1 deploy, 1 D1 `fgcare-webhook-db`). Không dựng mới.

**3 bề mặt:**
```
        ┌──────────── CLOUDFLARE WORKER ────────────┐
KHÁCH → │ ① READ (public)   GET /h/{token}          │ → 302 → landing
        │ ② WRITE (ingest)  POST /webhook/hug/...    │ → D1 queue
LOCAL ← │ ③ ADMIN (HMAC)    POST /hug/.../upsert     │
        └──────────────────┬────────────────────────┘
                     D1 fgcare-webhook-db
```

**D1 — 2 loại bảng (khác vòng đời):**
- *Transient queue* (có sẵn): `webhooks` — FIFO, NEW→PROCESSING, **xóa khi ack**. Scan + opt-in events đổ vào (`source=hug`).
- *Persistent read* (mới, KHÔNG drain): `hug_token` (immutable) · `hug_customer` (nightly) · `hug_campaign` (admin) · `hug_voucher` (issuance+quota).

### ① ĐỌC (scan — hot path)
```
GET /h/{token}
  1. D1 SELECT hug_token WHERE token → context (customer_id, op_type, order)
        (không thấy → DEFAULT page, vẫn log)
  2. D1 SELECT hug_customer WHERE customer_id → tier, recency, value...
  3. campaign list (cache Worker ~60s) → match predicate × priority → winner
  4. 302 redirect → winner.destination_url (Zalo deep-link / CF Pages)
  5. ctx.waitUntil( INSERT scan event vào webhooks queue )  ← KHÔNG chặn redirect
```
→ Edge quyết hết bằng data đã đẩy sẵn ở D1, **không gọi local** → redirect tức thì, không phụ thuộc PC local.

### ② GHI (tracking — async, đóng vòng)
```
scan event (do /h ghi) ─┐
opt-in event (landing POST) ─┤→ D1 webhooks queue (source=hug, NEW)
LOCAL GET /poll?source=hug (3') → xử lý (resolution, attribution) → POST /ack-batch → D1 xóa
```
Local = brain: event thô → identity bridge + attribution + cập nhật tier → vòng sau push xuống `hug_customer`.

### ③ ADMIN / provisioning (local → edge, HMAC)
- **Token** (đóng gói): local sinh token random → tạo `hug_token` local → `POST /hug/token/upsert` → D1 → in QR.
- **Tier** (nightly): sau build `mart_customer_tier` → `POST /hug/customer/upsert` (changed) → D1.
- **Campaign** (sửa): admin UI → `POST /hug/campaign/upsert` → D1.
- Idempotent upsert theo PK; fail→retry.

**Bảo mật:** `/h` public + token opaque (không PII) + CF rate-limit · `/webhook/*` & `/hug/*` HMAC (pattern Sapo).

---

## 11. Token format + Pre-print + Claim station (P1)

### Token format — CHỐT
- **Random 12 ký tự Crockford base32** (HOA+số, bỏ I/L/O/0/1). **KHÔNG** Sqids/counter (mã đặc → đoán được).
- Unique: random + **UNIQUE index** ở `hug_token` (trùng → sinh lại). Space `32^12 ≈ 1.1e18`.
- URL ngắn: `https://hug.fjp.vn/h/{token}` (~27 ký tự → QR version 2). In kèm mã người-đọc `HUG-XXXX-XXXX-XXXX` (fallback gõ tay). Path `/h/` khớp Worker route; `hug.fjp.vn` = custom domain trên CÙNG Worker webhook-receiver.
- Worker KHÔNG decode — chỉ tra D1; format thuần việc generate ở local (`secrets`/nanoid).

### Chống đoán/phá — 5 lớp
1. Token **thưa** (random-12): xác suất đoán trúng 1 token thật ≈ `10^-9`/lần → ~tỉ lần mới trúng.
2. CF **rate-limit** `/h`.
3. **Voucher không khuếch đại**: mã shared + Sapo `once_per_customer`/min-order → trúng token cũng không lấy thêm tiền.
4. Landing **không hiện PII** → trúng cũng không lộ gì.
5. Opt-in rác → `needs_review`.

### Pre-print — không trùng giữa các lần in
- `hug_token` local = **xưởng đúc duy nhất**, UNIQUE index. Mỗi mẻ in = generate M + insert (gắn `batch_id`/`printed_at`). **DB là sổ đăng ký** → không cần nhớ counter (random).
- Quy tắc vàng: **không in token chưa ghi DB.**
- Vòng đời: `printed` (đã in, chưa gắn) → `bound` (claim vào đơn) → live. **D1 chỉ nhận khi `bound`** (tem printed rớt → quét rơi DEFAULT, vô hại).

### Claim station — bind nhanh nhất
- **Bind key = Sapo `order_code`** (lúc đóng chưa có tracking, chỉ có mã đơn). Resolve `order→customer` **async** ở pipeline.
- **V3 đã rõ:** Sapo KHÔNG có QR/barcode mã đơn → lấy mã đơn từ **context trang Sapo**: **inject 1 nút "Claim Hug" lên trang đơn** (userscript/Tampermonkey đọc mã đơn từ URL/DOM) → mở UI claim với **mã đơn truyền sẵn qua URL** `claim.local/?order=SO1234`.
- Trạm: tablet/PC + **máy quét 2D USB** + web **local**.
- Flow: bấm nút trên đơn Sapo (mã đơn vào sẵn) → **quét tem → auto-bind (local tức thì) → bíp+xanh → dán**. Publish D1 **async nền**.
- **Gán thuộc tính lúc claim:** `op_type` (default `package_insert`) + toggle **`is_gift`** (feed identity-bridge — quà thì scanner≠buyer) + campaign override/ghi chú (tùy chọn).
- **Mọi đơn dán tem giống nhau**; server quyết trải nghiệm theo tier sau (dumb QR, smart server).
- 🔎 verify nhỏ: mã đơn nằm ở URL hay DOM trang Sapo (để viết userscript).

### Storage: master local + D1 projection (KHÔNG phải 2 pool độc lập)
| Store | Vai trò | Chứa | Ghi khi |
|---|---|---|---|
| **Local `hug_token`** | MASTER (brain) | printed + bound, đủ thuộc tính (op_type, is_gift, batch_id, status, customer_id sau resolve) | mint · claim · resolve |
| **D1 `hug_token`** | PROJECTION (cache edge) | **chỉ token bound** + field routing tối thiểu | push 1 chiều lúc bind |
- Edge không gọi được local → cần bản sao D1. Local là brain (resolve/bind/attribution cần Sapo). D1 **dựng lại được từ local**.
- Vòng đời: `printed` (LOCAL only) → `bound` (LOCAL + push D1) → scan đọc D1. Tem printed-chưa-bound **không lên D1** → rớt ra quét = DEFAULT (an toàn) + D1 gọn.
- 1 chiều local→D1 lúc bind; không sync 2 chiều phức tạp.

---

## 12. Coupon — giải thích đầy đủ

**1 câu:** coupon = **mã giảm giá TẶNG khách làm "mồi"** để họ chịu opt-in (để SĐT / follow Zalo). Là *củ cà rốt* của A2, không phải mục đích. **Không bắt buộc** (xem dưới).

### Ba việc tách bạch — ai làm gì (gốc của sự rối)
| Việc | Ai | Ở đâu |
|---|---|---|
| **Định nghĩa mã giảm** (giảm 50k · đơn ≥300k · 1 lần/khách · hạn) | **SAPO** | Sapo admin (tạo tay 1 lần) |
| **TẶNG mã** (quyết ai/khi nào, hiện mã) | **HUG** | landing/CRM |
| **DÙNG mã** (giảm tiền lúc thanh toán) | **SAPO** | checkout |
| **BIẾT đã dùng + của ai** (attribution) | **HUG/warehouse** | pipeline |
→ Hug KHÔNG tính giảm giá; Sapo lo. Hug lo *quyết-tặng + nhớ-tặng-ai + đo-ai-dùng*.

### Vòng đời — ví dụ "Chị Lan" (Shopee masked, mua lặp)
```
B0 setup (1 lần): Sapo admin tạo mã "HUG50" = giảm 50k · đơn ≥300k · 1 lần/khách
                  (y như OFF100/OFF500/OFF1M đang có)
B1 ship:  đơn Lan đóng → dán tem → token bound → resolve customer_id=Lan (masked,repeat)
B2 quét+opt-in: Lan quét QR → landing "Follow Zalo + để SĐT, nhận mã 50k"
        → nhập SĐT → Hug HIỆN "HUG50" → ghi hug_voucher{code=HUG50,customer=Lan,campaign=optin,issued}
        → identity bridge: SĐT gắn Lan → Lan CONTACTABLE ✅ (mở khóa CM)
B3 mua lại (vài ngày sau): Lan đặt đơn nhập HUG50 → SAPO giảm 50k (đơn≥300k, chưa dùng)
B4 phát hiện: đơn về (webhook→parquet) có order_coupon_code=HUG50
        → MATCH (customer_id=Lan + HUG50) ↔ hug_voucher → redeemed + order_code → đo ROI
```
→ **Tặng mã (B2, trước mua) → Sapo giảm (B3) → ta match (B4, sau mua, ở warehouse).**

### Mã CHUNG hay RIÊNG — v1 chọn CHUNG
| | Mã CHUNG "HUG50" (v1) ⭐ | Mã RIÊNG/khách |
|---|---|---|
| Tạo | 1 lần Sapo admin (tay) | gọi Sapo API/khách |
| Chống lạm dụng | Sapo `once_per_customer` + min-order chặn | mạnh hơn (chỉ khách đó dùng) |
| Attribution | theo **(customer_id + code)** | theo code |
| Cần Sapo write-API | **KHÔNG** ✅ | CÓ (chưa verify) |
→ v1 = **mã chung mỗi campaign** (HUG50 opt-in, WINBACK100 cho A4…). Code = campaign nào, customer_id = ai.

### Đã verify (V1) + ĐÃ DEPLOY (2026-06-19)
- ✅ `order_coupon_code` **đã deploy** vào `fact_orders` (src/std/fact + backfill 25 đơn OFF100/500/1M). ⚠️ là **JSON object** lồng nhau — code thật ở `$.order_coupon_code.coupon_code` (kèm `coupon_promotion_id`, `order_total_required`, `discount_amount` nếu cần).
- ✅ Sapo API tạo coupon được (`price_rules`+`discount_codes`) nhưng **quyền ghi chưa verify** → v1 né, tạo tay.

### Hug lưu gì — `hug_voucher` (sổ phát hành)
`{code, customer_id, token, campaign_id, issued_at, redeemed_at?, order_code?}` = sổ *"tặng mã X cho Y từ campaign Z, dùng chưa"*. KHÔNG phải engine giảm giá.

### Coupon KHÔNG bắt buộc
A2 capture chạy được không cần coupon ("Follow Zalo nhận tin ưu đãi"). Coupon chỉ **tăng opt-in rate**. → có thể v1 launch không coupon, thêm sau. *Enhancer, không phải blocker.*

### Quota (tùy chọn)
Cap số mã phát/campaign (soft counter). Mã-chung ít ý nghĩa quota; v1 bỏ qua được.
