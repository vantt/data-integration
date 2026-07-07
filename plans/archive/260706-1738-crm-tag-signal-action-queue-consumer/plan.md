# Plan — CRM Tag Signal → Action Queue Consumer (AI-9)

**Status:** TODO
**Created:** 2026-07-06
**Nguồn:** `plans/260705-1146-crm-ux-data-loop-improvements/phase-08-reassessment-fixes.md` AI-9
**Goal:** Đóng nốt vòng lặp dữ liệu CRM: tag (`risk`/`vip_tier`) NV gắn tay quay lại ảnh hưởng thật đến `mart_customer_action_queue` — mắt xích cuối cùng của thiết kế "NV nhập → gợi ý tốt hơn → NV thấy giá trị → nhập nhiều hơn" (`crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §5).

## Bối cảnh — vì sao cần plan riêng

Phase-01 (05/07) xây 4 export + staging model CRM (`stg_crm__note`, `stg_crm__party_tag`, `stg_crm__party_insight`, `stg_crm__customer_profile_custom`) nhưng cố tình chưa nối consumer nào (YAGNI, chờ staging ổn định). Đánh giá lại 06/07 xác nhận staging chạy xanh nhưng **không ai đọc** — vòng lặp khép tới nửa chừng.

**Phát hiện quan trọng khi khảo sát để viết plan này:** `stg_crm__party_tag` hiện chỉ có `party_id` (UUID CRM nội bộ), KHÔNG có `customer_id` (khóa Sapo mà `mart_customer_action_queue` dùng làm grain). Mọi export CRM khác cần nối vào mart Sapo (`crm_last_contact`, `crm_activity_log`, `crm_task`) đều đã resolve `customer_id` ngay lúc export bằng `LEFT JOIN crm_party_identity` (trong `orchestration/assets/crm_writeback_assets.py`) — nhưng export `crm_party_tag`/`crm_note`/`crm_party_insight`/`crm_customer_profile_custom` viết ở phase-01 thiếu bước này. `crm_party_identity` KHÔNG được export riêng thành dbt source, nên dbt-side không có cách nào tự bridge được — bắt buộc phải sửa ở lớp export Python trước, không phải lựa chọn.

## Quyết định đã chốt (user, 2026-07-06)

1. **Tag `vip_tier` boost priority như VIP tự động** — khách NV gắn tay `vip_tier` được xử lý như `value_group='VALUE_VIP'` trong CASE logic action_type (dù RFM tự động chưa kịp phản ánh) — vẫn nhận `CALL_NOW`/`REORDER_NUDGE` ưu tiên cao.
2. **Tag `risk` thêm action_type mới `MANUAL_RISK_REVIEW`** (tách biệt khỏi `HIGH_CANCEL_RISK` tự động dựa `cancel_rate`) — tín hiệu NGƯỜI đánh giá, hiện riêng để NV thấy lý do khác; KHÔNG chặn khách khỏi các nhắc nhở khác.
3. **Sửa customer_id resolution cho CẢ 4 export** (không chỉ `crm_party_tag`) — cùng pattern, cùng file, chi phí thêm rất nhỏ, tránh phải quay lại đúng chỗ này khi làm thread "recommender" (skin_type/insight preference) sau này.
4. **Chỉ tin tag người gán (`source='crm_user'`)** — bổ sung 2026-07-06 khi khớp thiết kế với `260619-0830-crm-tag-acl-sync` (sync tag từ Sapo group vào `crm_party_tag`). Không filter thì tag sync giả dạng phán đoán NV (MANUAL_RISK_REVIEW) và wholesale boost nhầm vào queue outreach. Phase-01 export thêm cột `source` (fallback literal `'crm_user'` nếu 260619 chưa land); phase-02 filter trong int model. **Plan này vẫn độc lập vận hành với 260619** — chạy trước hay sau đều đúng.

## Phases

| # | Phase file | Scope | Depends on | Priority |
|---|---|---|---|---|
| 01 | `phase-01-crm-export-customer-id-resolution.md` | Sửa 4 export query (`crm_party_tag`, `crm_note`, `crm_party_insight`, `crm_customer_profile_custom`) thêm `LEFT JOIN crm_party_identity` → cột `customer_id`; cập nhật 4 staging model pass-through | — | P0 (chặn cứng phase 02) |
| 02 | `phase-02-tag-signal-action-queue-consumer.md` | Intermediate model gộp tag risk/vip_tier theo customer_id; sửa `mart_customer_action_queue.sql` (vip boost + action_type mới `MANUAL_RISK_REVIEW`); badge_catalog.py entry mới; 2 bước deploy thủ công | 01 | P1 |

**Execution order:** 01 → 02 (cứng, không song song được — 02 không compile nếu thiếu cột `customer_id`).

## Acceptance criteria

1. `stg_crm__party_tag`/`stg_crm__note`/`stg_crm__party_insight`/`stg_crm__customer_profile_custom` có cột `customer_id` (INTEGER, nullable khi party chưa link Sapo), dbt build xanh.
2. Khách có tag `category='vip_tier'` nhưng `value_group` chưa phải VIP/GOLD/SILVER vẫn xuất hiện action_type ưu tiên cao (CALL_NOW/REORDER_NUDGE/REORDER_PREEMPT/WIN_BACK) đúng logic hiện có.
3. Khách có tag `category='risk'` xuất hiện action_type `MANUAL_RISK_REVIEW` riêng biệt, không lẫn với `HIGH_CANCEL_RISK`; đồng thời vẫn nhận các action_type khác nếu đủ điều kiện (không bị chặn).
4. `MANUAL_RISK_REVIEW` có badge tiếng Việt trong `badge_catalog.py` + `_ACTION_TYPE_SHORT_LABEL` (phase-09) — không lộ mã thô ra worklist.
5. Row-count sanity: số khách có tag risk/vip_tier trong action queue mart ≈ số party có tag đó trong CRM (trừ phần chưa link Sapo).
6. `crm/docs/ui-spec/` không cần cập nhật (đây là thay đổi warehouse/mart, không đổi UI surface ngoài badge mới — badge mới đã có convention từ phase-09).

## Constraints

- Export/dbt: đụng `orchestration/assets/crm_writeback_assets.py` + `transformation/models/staging/` + `transformation/models/marts/customer/`.
- dbt node/cột mới → **restart `data_platform`** trước `dbt build` (manifest pre-parsed, không hot-reload).
- Mart mới cho CRM đọc (nếu CRM UI cần hiển thị field mới từ action queue) → 2 bước thủ công: (1) dừng Metabase, chạy `bootstrap_serving_views.py`; (2) `docker compose up -d --build crm`. Xác nhận scope thực tế ở phase-02 (khả năng không cần rebuild crm nếu chỉ thêm action_type mới — badge đã generic theo key).
- `crm_party_tag`/`crm_customer_profile_custom` là snapshot mode → sau đổi export query, re-run asset sẽ ghi đè file cũ hoàn toàn (không cần backfill script). `crm_note`/`crm_party_insight` là incremental_append — cột mới CHỈ xuất hiện ở batch mới, dữ liệu batch cũ không có `customer_id` (chấp nhận, note trong phase-01: xử lý bằng cách xóa cursor để re-export từ đầu, vì volume nhỏ).

## Risks

- Nếu 1 party có nhiều tag cùng category (vd 2 tag đều risk) → intermediate model cần GROUP BY/aggregate đúng (boolean OR, không nhân bản dòng action queue).
- `party_id` chưa link `crm_party_identity` (identity_type='sapo_customer') → `customer_id` NULL → tag đó vô hình với action queue (chấp nhận, ghi rõ trong phase-01 risk).
- `MANUAL_RISK_REVIEW` là action_type mới → cần review với NV thực tế xem rationale/priority_rank đặt ở đâu trong thang ưu tiên hiện có (1-6, ELSE 9) — đề xuất priority_rank tạm = 2 (ngay sau CALL_NOW) trong phase-02, có thể chỉnh sau khi NV dùng thử.

## Reports

`plans/260706-1738-crm-tag-signal-action-queue-consumer/reports/` (chưa có — tạo khi triển khai xong)
