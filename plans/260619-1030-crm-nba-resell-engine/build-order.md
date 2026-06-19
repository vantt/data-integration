# Build-Order — Stage A + Hug (implementation sequencing)

> Thứ tự triển khai + dependency. Spine chính = đường tới prize **A2 (683M CM)**; A3/A4 là track revenue-reachable-now chạy song song. Context: [`plan.md`](./plan.md) · [`discussion-hug.md`](./discussion-hug.md) · [`phase-hug`](./phase-hug-dynamic-touchpoint-platform.md).

## Nguyên tắc

- **Walking skeleton trước:** thông 1 đường end-to-end với 1 token test (scan→redirect→log→opt-in→resolve→contactable) TRƯỚC khi scale. De-risk sớm.
- **Risk-first verify:** chốt mấy ẩn số tích hợp (Sapo coupon, Zalo deep-link) ngay M0 — chúng ảnh hưởng thiết kế.
- **Config trước UI:** A2 launch bằng campaign config-row; admin UI là nicety sau (đừng để UI chặn prize).
- **Spine không bị A3/A4 cướp băng thông**; A3/A4 chỉ chạy song song nếu còn sức.

## Dependency graph

```
M0 Foundation (tier mart + verifies)
   │
   ├─────────────► M1 Quick revenue (A4/A3 reachable)   [song song, optional]
   │
   ▼
M2 Hug skeleton (D1 + /h read + admin routes + nightly push)
   │                         │
   ▼                         ▼
M3 Token @ packing      M4 Capture loop (landing + ingest + resolution + feedback)
   │                         │
   └────────────┬────────────┘
                ▼
        M5 A2 go-live (voucher + campaign) ◄── prize
                │
                ▼
        M6 Optimize (admin UI · A/B · A3 auto · lifecycle · Stage B engine)
```

## Verify V1/V2 — KẾT QUẢ (2026-06-19) ✅

Chi tiết: `plans/reports/hug-verify-sapo-coupon-zalo-deeplink-260619-1432-report.md`.

**V1 — coupon:**
- ✅ `order_coupon_code` ĐÃ có trong raw Sapo payload (mẫu OFF100/OFF500/OFF1M + min-order). Chưa extract vào `fact_orders` → **thêm 1 `json_extract` ở staging** là match redeem được. Coupon Sapo đã dùng sẵn.
- ⚠️ Sapo API client read-only (cookie/session); tạo mã qua API (`/admin/price_rules`, có `once_per_customer`/min/scope/expiry) **write-auth chưa verify** (có thể OAuth).
- → **v1 = flavor C+**: mã **shared-per-campaign** tạo tay trong Sapo admin (`once_per_customer` + min-order) → Hug log issuance per customer → **match redeem theo (customer_id + code)**. Flavor B (per-customer qua API) hoãn tới khi spike write-auth.

**V2 — Zalo:**
- ✅ Token-tie = **web landing form** (nhập SĐT) — XÁC NHẬN. OA follow KHÔNG mang ref/token → chỉ kênh bonus, không phải đường nối định danh.
- ⚠️ **ZNS sending VẮNG** (no client/token/env). → A2 capture KHÔNG cần ZNS (web đủ). A3/A4 nhắn tự động cần build ZNS (verify OA + duyệt template, có timeline) → **v1 A4 = export list CS/nhắn tay**, ZNS sau.

**V3 — Sapo order barcode: ✅ RESOLVED** — Sapo không có barcode mã đơn → **inject nút "Claim Hug" lên trang đơn Sapo** (userscript đọc mã đơn từ URL/DOM) đẩy mã đơn vào URL claim UI → quét tem để bind. 🔎 verify nhỏ: mã đơn ở URL hay DOM Sapo. Xem `discussion-hug.md` §11.

---

## M0 — Foundation (chặn tất cả)

| Task | Mô tả | Depends |
|---|---|---|
| A1-mart | ✅ `mart_customer_tier.sql` (**7 tier**) — viết + parse + validate xong (56/27/122/1144/433/1598/4183) | dim_customers |
| A1-sync | ✅ DONE — `wh_customer_tier` 7563 rows synced; `strategic_tier` badge hiện trong customer 360 (Signals + Segments) + customer list; tests 97/97 pass | A1-mart |
| V1, V2 | ✅ done (xem Verify ở trên) | — |
| extract-coupon | ✅ DONE — `$.order_coupon_code.coupon_code` (**nested object!**) → src/std/fact; full-refresh backfill: 25 đơn OFF100/500/1M trong fact_orders | — |

**Deliverable:** mọi khách có tier, hiện trong CRM. **Unblocks:** mọi thứ.

## M1 — Quick revenue (song song, optional) — khách reachable

| Task | Mô tả | Depends |
|---|---|---|
| send-channel | ⚠️ ZNS chưa có → v1 **export list CS / nhắn tay**; build ZNS (OA verify + duyệt template) sau | — |
| A4-winback | DORMANT_VALUABLE (122, ưu tiên) + LAPSED_VALUABLE (1.144, thử→đo→suppress) → 1 ưu đãi theo value | A1, send-channel, V1 |
| A3-second (sớm) | SECOND_ORDER (~27) → nudge ngày 7–10 | A1, send-channel |

**Deliverable:** doanh thu win-back sớm từ ~1,180 dormant reachable, KHÔNG cần Hug. Chạy trong lúc build Hug.

## M2 — Hug skeleton (edge)

| Task | Mô tả | Depends |
|---|---|---|
| W1-schema | D1 persistent tables: hug_token/hug_customer/hug_campaign/hug_voucher (tách khỏi `webhooks` queue) | — |
| W2-read | `GET /h/{token}`: resolve → arbitrate → 302 + waitUntil log scan (campaign DEFAULT hardcode trước) | W1 |
| W3-admin | `/hug/{token\|customer\|campaign}/upsert` + HMAC | W1 |
| push-customer | nightly job: mart_customer_tier → `hug_customer` upsert | A1-mart, W3 |

**Deliverable:** token (chèn tay) → scan → redirect + log. **Thin slice** test được end-to-end edge.

> ✅ **DEPLOYED + verified** (2026-06-19): D1 schema applied · HUG_ADMIN_SECRET set · `wrangler deploy` xong. 18 tests PASS. **2 trigger live:** `webhook-receiver.admin-1d2.workers.dev` (webhook) + `hug.fjp.vn` (Hug). Verify: `hug.fjp.vn/h/test` → 302 → finejapanvietnam.com ✓; webhook route nguyên (POST → 200), hug admin HMAC ✓ (401).
> ⚠️ **Bài học deploy:** thêm `routes` mà thiếu `workers_dev = true` → wrangler TẮT workers.dev (webhook đứt) → đã fix (`workers_dev = true` + redeploy). Và ĐỪNG POST thử lên `/webhook/*` (chèn row rác vào queue — đã xảy ra + dọn ngay; sapo_v2 route KHÔNG enforce HMAC).
> ✅ **DEFAULT campaign seeded** (`campaign_id=default`, targeting `{}`, priority max, → finejapanvietnam.com). **Edge verified end-to-end:** scan token bound → 302 → dest + `?hug_token=&hug_campaign=` attribution. Test token + test events dọn sạch.
> ✅ **M3 push ENABLED + full loop verified** (2026-06-19): CRM env set (`HUG_WORKER_URL=https://hug.fjp.vn`, `HUG_ADMIN_SECRET` via root `.env` substitution — gitignored, không vào git). **End-to-end:** mint (CLI) → claim (POST /hug/claim, bind local) → **push D1 (200)** → scan `hug.fjp.vn/h/{token}` → 302 → DEFAULT + `?hug_token=&hug_campaign=` attribution. Test data dọn sạch (D1 + hug.db).
> 🐛 **Fix quan trọng:** Cloudflare **Bot Fight Mode 403 (error 1010)** chặn UA mặc định `Python-urllib` của d1_push → thêm header `User-Agent: FineJapan-Hug-Push/1.0` vào `d1_push.py`. (Sapo webhook không bị vì UA khác.)
> ⏳ **Chờ deploy phối hợp** (chưa chạy): `wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql` → `wrangler secret put HUG_ADMIN_SECRET` → set `HUG_FALLBACK_URL=https://finejapanvietnam.com` (✅ chốt) → `wrangler deploy`. Còn chốt: seed 1 DEFAULT campaign (`targeting='{}'`, priority cao) trước scan đầu.

## M3 — Token provisioning (pre-print + claim @ packing)

> Chi tiết: `discussion-hug.md` §11. Token = random-12 Crockford-b32 (unique index). Bind key = Sapo `order_code`.

| Task | Mô tả | Depends |
|---|---|---|
| mint+print | local mint batch (random-12, UNIQUE index, batch_id) → in cuộn sticker QR (status=printed) | M2 |
| claim-station | userscript inject nút trên đơn Sapo (mã đơn→URL) + web **local** + máy quét 2D: **bấm nút → quét tem → bind local (order_code) + op_type/is_gift → push D1 async**. bíp+xanh | mint+print, M2 |
| async-resolve | pipeline: `order_code → customer_id` điền vào hug_token | M4-ingest |

**Deliverable:** kho dán tem in sẵn; 2-quét claim tức thì; token bound + lên D1.

> ✅ **CODE DONE + validated** (2026-06-19, local): `crm/src/hug/` (tokens random-12 b32, hug.db master, repository, d1_push config-gated) · `hug_mint.py` CLI · `hug_qr_print.py` · `screen_hug_claim.py` (kiosk /hug/claim) · `sapo-hug-claim-button.user.js` · 12 tests pass. D1-push gated sau HUG_WORKER_URL (bật sau M2 deploy). `is_gift` local-only (Worker hug_token không có cột này — đúng, nó feed identity bridge chứ không routing).
> **Config go-live:** ✅ HUG_DOMAIN=`hug.fjp.vn` (custom domain cùng Worker; QR=`https://hug.fjp.vn/h/{token}`; zone fjp.vn ĐÃ trên CF → `wrangler deploy` tự tạo DNS+SSL) · ✅ HUG_FALLBACK_URL=`https://finejapanvietnam.com` · ✅ CLAIM_BASE=`https://crm.lan.fwg.vn/hug/claim` (Caddy). ⏳ còn: Sapo order-page DOM selector (URL_ORDER_RE — cần 1 đơn thật) · `docker compose build crm` (qrcode lib).
⚠️ **V3 (mở):** Sapo có barcode mã đơn lúc đóng? → 2-scan; nếu không → in Code128 mã đơn / gõ đuôi.

## M4 — Capture loop (landing + ingest + resolution)

| Task | Mô tả | Depends |
|---|---|---|
| L1-landing | CF Pages: opt-in (Zalo follow CTA + form SĐT), biết `token` | M2 |
| ingest-hug | opt-in/scan event → D1 queue (`source=hug`) → local poll → parquet | có sẵn pattern |
| I2-resolve | identity resolution: crm_identity_link + enrich + contact_quality; conflict→needs_review | ingest-hug, Sapo data |
| I4-feedback | enrich → dim_customers.is_contactable → tier → nightly push hug_customer | I2, A1 |
| C1-review | CS queue UI cho needs_review | I2 |

**Deliverable:** scan → opt-in → khách thành contactable (lõi A2, chưa voucher).

## M5 — A2 go-live (prize)

| Task | Mô tả | Depends |
|---|---|---|
| voucher | flavor C+: mã Sapo shared-per-campaign (tạo tay, once_per_customer+min) · log issuance · match redeem theo (customer_id+code) | extract-coupon, W1 |
| A2-campaign | config-row: op_type=package_insert × tier=MASKED_REPEAT → Zalo follow + 50K | M3, M4, voucher |

**Deliverable:** 364 masked-repeat targeted → identity capture live → **683M CM bắt đầu mở khóa**.

## M6 — Optimize & expand

- C2 admin UI campaign (self-serve, UX preview/cảnh báo chồng lấp) · A/B experimentation · A3 auto sequence · multi-campaign · lifecycle scan-aware (loyalty/review) · Stage B engine v1 thin (khi active base lớn).

---

## Sequence khuyến nghị (solo + AI)

`M0 → M2 → M4 (thin slice 1 token test) → M3 → M5` = spine tới prize.
Chèn **M1** song song sau M0 nếu còn băng thông (revenue sớm). **M6** sau khi A2 chạy ổn.

## Critical path

A1-mart → W1 → W2/W3 → (M3 token ∥ M4 capture) → M5. Nút nghẽn rủi ro: **V1 Sapo coupon · V2 Zalo deep-link · I2 resolution correctness** → verify/test sớm.

## Open

- Khâu đóng gói hiện in thẻ thế nào (tích hợp P1-print)?
- send-channel ZNS: đã có khả năng gửi chưa (ảnh hưởng M1)?
