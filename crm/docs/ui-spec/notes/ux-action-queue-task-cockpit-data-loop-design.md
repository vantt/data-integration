# Thiết kế UX & vòng lặp dữ liệu — Action Queue → Task → Worklist → Cockpit

**Ngày:** 2026-07-05
**Trạng thái:** Đã chốt quyết định D1–D4, chờ triển khai
**Phạm vi:** S01, S07, S14, S15, M08, P05, M03/M14/M06/M16, reverse-ETL `crm/sync` + `orchestration/assets/crm_writeback_assets.py`
**Nguồn:** phiên rà soát UX 2026-07-05 (3 khảo sát song song spec + code)

---

## §1. Bối cảnh & mục tiêu

**Mục tiêu sản phẩm:** NV CSKH biết làm gì, như thế nào, đúng thời điểm, đúng việc; ghi notes/tags dễ để thu thập dữ liệu tối đa; dữ liệu có cấu trúc rành mạch để warehouse thống kê, báo cáo, đưa chiến lược kịp thời.

**Chuỗi chức năng liên quan:**

```
action-queue-item (warehouse gợi ý)
  → task/claim-task
  → worklist (S01) + tasks board (S07)
  → call cockpit (S14) / task detail (S15)
  → outcome (M08)
  → reverse-ETL về warehouse
```

---

## §2. Sơ đồ tổng thể pipeline

### 2.1 Pipeline đầu-cuối

```
WAREHOUSE (DuckDB mart)                    CRM (SQLite)
mart_customer_action_queue ─┐
mart_customer_sku_action_q ─┴→ cache.db (wh_action_queue, wh_sku_action_queue)
                                    │
                                    ▼
                    S01 WORKLIST ── action rows (chưa nhận) + task rows (đã nhận)
                    │  [Nhận việc] → tạo 1 crm_task gom TẤT CẢ action của khách đó
                    │  [Trả việc]  → huỷ task, action hiện lại trong queue
                    ▼
        ┌─── S15 TASK DETAIL (đọc ngữ cảnh, "vì sao gọi") ──┐
        │                    "Vào phiên gọi"                 │
        ▼                                                    ▼
    S14 CALL COCKPIT (kịch bản nói gì · lý do gọi · snapshot RFM · thu thập Zalo/email inline)
        │  Outcome bar: ✓Gọi được / ✗Không nghe / ⏳Hẹn lại / 🛒Đã mua
        ▼
    M08 LOG ACTIVITY → crm_activity_log (outcome ENUM) + đóng task + tạo follow-up
        │
        ▼
    Reverse-ETL: crm_activity_log, crm_task, crm_last_contact → warehouse
    ❌ HIỆN THIẾU (D1): crm_note, crm_tag/crm_party_tag, crm_party_insight, custom fields
```

### 2.2 Vòng đời claim

```
  wh_action_queue / wh_sku_action_queue
        │
        │  hiện trên S01 (action rows — chưa nhận)
        │
        ▼
  [Nhận việc] ── claim per-customer
        │         tạo 1 crm_task: "Gọi {tên} · N hành động"
        │         source='action_queue_claim'
        │         idempotent: UNIQUE(source, source_ref)
        │         bấm đúp không tạo trùng
        │
        ▼
  action tự ẨN bằng SQL filter (không cần dọn tay)
        │
        ▼
  task: open → doing → done / cancelled
        │       (transitions cho phép re-open)
        │
        ├── [Trả việc] = cancel task
        │       → action tự HIỆN LẠI trên S01
        │
        ├── snooze: CHỈ có trên action row
        │       crm_action_state.snoozed_until
        │       (task đã claim: cần A4 để snooze trực tiếp)
        │
        └── dismiss: crm_action_state.status = 'dismissed'
```

---

## §3. Điểm mạnh hiện tại (giữ nguyên, không đụng)

- **Claim theo KHÁCH không theo action** → chống 2 NV gọi trùng 1 khách; idempotent, bấm đúp không tạo trùng.
- **Action tự ẩn sau claim, tự hiện lại khi Trả việc** (SQL filter, không cần dọn tay).
- **Worklist chia band:** B0 quá hạn → B1 hôm nay/khẩn → B2 đúng tiến độ → B3 treo lâu 7+ ngày → B4 đã liên hệ; sort urgency + value.
- **"Vì sao gọi, vì sao bây giờ":** `rationale_vi` + 💰 `value_at_stake` + `pending_since` trên dòng worklist; Reason Rail (PRIMARY ★ + SECONDARY) trong cockpit (`assemble_reason_rail()`).
- **Outcome là ENUM theo kênh** (call: answered/no_answer/callback/refused; messaging: replied/no_reply/pending_reply; visit: met/not_met); "Hẹn lại" tự đề xuất tạo task nhắc.
- **2 đường vào phù hợp 2 trình độ:** NV cứng bấm "📞 Gọi" thẳng từ S01 (1 click); NV mới qua S15 đọc ngữ cảnh rồi "Vào phiên gọi" (2 click).
- **Cockpit 2 cột:** TRÁI "nói gì" (talk-track AI, talking points, objection handling, guardrails) / PHẢI "vì sao & bối cảnh" (reason rail, snapshot RFM, Collect inline thu thập Zalo/email/sinh nhật ngay lúc gọi).
- **Notes 6 loại** (general/preference/contact_pref/warning/outcome/internal) + pin có hạn; **Tags có taxonomy 6 category** (behavioral/demographic/preference/vip_tier/risk/source) + audit `tagged_by`/`tagged_at`.

---

## §4. Vấn đề & giải pháp cho người dùng

### Nhóm A — Mất ngữ cảnh giữa chừng

| # | Vấn đề | Ảnh hưởng đến NV | Giải pháp | Ưu tiên |
|---|--------|------------------|-----------|---------|
| A1 | Sau "Nhận việc", `value_at_stake_vnd` + `top_affinity_product` KHÔNG lưu vào task | NV mất căn cứ ưu tiên & gợi ý sản phẩm mở lời, phải mở lại C360 | Denormalize 2 trường này vào task lúc claim (hoặc join hiển thị lúc render) | P1 |
| A2 | Cockpit thiếu bộ đếm hàng đợi #n/N; nút "Khách kế →" có render nhưng logic queue chưa nối | NV không nhịp được tốc độ buổi làm việc | Truyền queue context từ worklist session vào S14 template, hiện #n/N ở topbar | P1 |
| A3 | Bulk-resolve (Phase 04b) chưa nối: NV gọi 1 cuộc giải quyết 3 action + 2 task nhưng M08 chỉ đóng 1 task; skeleton `resolve_action_ids`/`resolve_task_ids` có sẵn (`outcome_resolve_helpers.py`), endpoint chưa bind | Số liệu completion sai, NV bấm đóng từng cái | Hoàn tất bind endpoint + M08 nhận mảng IDs | P0 |
| A4 | Không snooze được task đã claim (snooze chỉ có trên action row) | Workaround 3 bước Trả việc→snooze→claim lại cho nhu cầu rất phổ biến "tuần sau gọi lại" | Thêm snooze trực tiếp trên task claim | P1 |

### Nhóm B — Khả năng phát hiện & minh bạch

| # | Vấn đề | Ảnh hưởng đến NV | Giải pháp | Ưu tiên |
|---|--------|------------------|-----------|---------|
| B1 | Band 3 "Treo lâu" mặc định thu gọn, hé 5 dòng | Khách VIP bỏ quên "mục" không ai thấy | Auto-mở band khi có khách VIP/GOLD bên trong, hoặc badge đếm + tổng value trên header band | P2 |
| B2 | Snooze hết hạn "thức dậy" im lặng ở lần cache refresh kế | NV quên đã hoãn gì | Badge "⏰ vừa thức dậy" trên row trong 1 ngày đầu | P2 |
| B3 | Chưa có filter "Của tôi" (deferred, chưa wired auth context vào filter) | Chưa chí mạng với 10 user, đau khi đội đông | Wire auth context vào filter | P2 |
| B4 | Task claim không có badge nguồn (`[AUTO]` chỉ hiện cho `source='action_queue'`, không hiện cho `'action_queue_claim'`) | Khó phân biệt task máy gợi ý vs tạo tay | Thêm badge `[AUTO]` cho `action_queue_claim` | P2 |
| B5 | Dismiss action không "nhớ" qua tuần — warehouse sinh `action_id` mới cùng nội dung, dismiss cũ gắn `action_id` cũ | NV thấy việc đã bỏ quay lại, mất niềm tin | Cân nhắc dismiss theo `(party_id, action_type)` có TTL thay vì theo `action_id` | P2 (cần bàn thêm) |
| B6 | R14 STOP gate → xem D3 | — | — | — |

### Nhóm C — Nhỏ (ít block NV nhưng cần ghi nhận)

- Collect inline lưu thành công không có toast.
- Tick talking-points là client-side, mất khi reload (chấp nhận, cần cảnh báo khi rời trang giữa cuộc gọi).
- Nút back cockpit đổi đích theo ngữ cảnh — cần tooltip.
- Snapshot RFM không hiện timestamp dữ liệu.

### Điểm số mục tiêu

| Tiêu chí | Điểm | Ghi chú |
|----------|------|---------|
| Biết làm gì | 7/10 | B1, B3 làm mờ ưu tiên |
| Biết làm thế nào | 8/10 | Talk-track + reason rail tốt |
| Đúng thời điểm | 6/10 | **Yếu nhất** — A2, B1, B2 |

---

## §5. Vòng lặp dữ liệu: đứt gãy → đóng vòng

### BEFORE — vòng lặp chết

```
  NV nhập activity / task / last_contact
        │
        ▼
  crm_writeback_assets.py export → warehouse ✓
        │
        ▼
  dashboard + chiến lược nhìn thấy dữ liệu ✓
  ─────────────────────────────────────────
  NV nhập note / tag / insight / custom-field
        │
        ▼
  CRM lưu vào SQLite ✓
        │
        ✗  KHÔNG CÓ EXPORT
        │
        ▼
  dashboard / chiến lược MÙ với dữ liệu này
        │
        ▼
  NV thấy "nhập không ai dùng" → bỏ nhập
        │
        ▼
  ◀── vòng lặp chết ──▶
```

### AFTER — vòng lặp khép kín (D1)

```
  NV nhập note / tag / insight / custom-field
        │
        ▼
  4 export mới:
    stg_crm__note
    stg_crm__party_tag  (+crm_tag)
    stg_crm__party_insight
    stg_crm__customer_profile_custom
        │
        ▼
  mart / segmentation / recommender tiêu thụ:
    • segmentation dùng tag category risk/vip_tier
    • recommender dùng preference + custom skin_type
        │
        ▼
  insight quay lại action queue (gợi ý tốt hơn)
        │
        ▼
  NV thấy dữ liệu mình nhập tạo ra gợi ý tốt hơn
        │
        ▼
  ◀── động lực nhập tăng ──▶
```

### Hiện trạng export — `orchestration/assets/crm_writeback_assets.py`

| Bảng | Mode | Watermark | Ghi chú |
|------|------|-----------|---------|
| `crm_activity_log` | incremental_append | `created_at` | → `mart_crm_activity_log` |
| `crm_task` | incremental_append | `updated_at` | |
| `crm_last_contact` | snapshot | — | |
| `crm_app_user` | snapshot | — | |
| `crm_campaign_target` | snapshot | — | |
| `crm_hug_voucher` | snapshot | — | |
| **`crm_note`** | ❌ thiếu | — | |
| **`crm_tag` + `crm_party_tag`** | ❌ thiếu | — | |
| **`crm_party_insight`** | ❌ thiếu | — | |
| **`crm_customer_profile.custom`** | ❌ thiếu | — | |

> Lưu ý: `dim_customer_notes` / `dim_customer_tags` hiện chỉ lấy từ **Sapo**, không phải CRM.

### Friction capture cần giảm

| Luồng hiện tại | Vấn đề | Giải pháp |
|---------------|--------|-----------|
| insight: activity → note → P05 → M16 (4 bước) | Quá dài, NV bỏ qua | Nút "★ Đúc kết" ngay trong M08 (1 bước) |
| custom fields: chỉ sửa qua M06 trên S03 | Không làm giữa cuộc gọi | Đưa 2–3 field hay dùng (skin_type, preferred_contact) vào khối Collect của cockpit |
| tạo tag: modal lồng modal | Không ai làm giữa cuộc gọi | Chấp nhận — tạo tag ở S13/M03/M14 lúc rảnh |

---

## §6. Quyết định thiết kế (đã chốt 2026-07-05)

### D1 — Export bổ sung về warehouse

**Xác nhận: là bỏ sót, không phải chủ đích.**

Bổ sung 4 export vào `orchestration/assets/crm_writeback_assets.py`:

| Export | Mode | Watermark | Ghi chú |
|--------|------|-----------|---------|
| `crm_note` | incremental_append | `created_at` | Loại `visibility='private'` khỏi export hoặc mask body — **quyết định khi triển khai** |
| `crm_tag` + `crm_party_tag` | snapshot | — | |
| `crm_party_insight` | incremental_append | `created_at` | Loại `deleted_at IS NOT NULL` |
| `crm_customer_profile.custom` | snapshot | — | Warehouse pivot theo `crm_custom_field_def` |

Kèm staging models `stg_crm__*`. Kế hoạch tiêu thụ: segmentation dùng tag category `risk`/`vip_tier`; recommender dùng `preference` + custom `skin_type`.

**Ưu tiên: P0.**

> Lưu ý vận hành: mart mới cho CRM đọc cần 2 bước thủ công — bootstrap serving view (khi Metabase dừng) + rebuild crm container — theo bài học tích hợp trước.

---

### D2 — Chuẩn hoá outcome: bỏ free-text, dùng enum MỞ RỘNG

**Quyết định:** `contact_outcome` (enum) là trường chuẩn duy nhất; trường `outcome` free-text ngừng ghi mới (giữ đọc để hiển thị dữ liệu cũ), body vẫn là ghi chú tự do.

**Tầng 1 — `contact_outcome` (kết quả tiếp cận, theo kênh)**

| Kênh | Giá trị |
|------|---------|
| call | `answered` / `no_answer` / `busy` / `wrong_number` / `callback` / `refused` |
| messaging (zalo/fb/email) | `replied` / `no_reply` / `pending_reply` / `refused` / `blocked` |
| visit | `met` / `not_met` |

**Tầng 2 — `outcome_reason` (lý do — mới, nullable)**

Chỉ bắt buộc khi `refused` hoặc khi `answered`-không-chốt:

| Giá trị | Ý nghĩa |
|---------|---------|
| `budget` | giá / ngân sách |
| `timing` | chưa tới lúc |
| `product_fit` | không hợp nhu cầu |
| `competitor` | đã mua chỗ khác |
| `stock` | hết hàng / chờ hàng |
| `trust` | nghi ngại |
| `no_need` | hết nhu cầu |
| `other` | khác |

**UI M08:** pill 2 bước — chọn outcome rồi hiện hàng pill reason theo ngữ cảnh; không dropdown.

**Warehouse:** `mart_crm_activity_log` thêm cột `outcome_reason`, giữ `is_reached` (`answered|replied|met`).

**Nguyên tắc mở rộng enum:** thêm giá trị = sửa `VALID_*` constant + pill M08 + mapping mart, không thêm cột.

---

### D3 — R14 gate = CẢNH BÁO có xác nhận (warn-with-ack), KHÔNG hard-block

**Lý do:** dữ liệu warehouse có thể sai (B2B gán nhầm, margin mâu thuẫn) — NV cần quyền quyết định sau khi xác minh; hệ thống chưa có dữ liệu consent thật (mặc định contactable) nên hard-block sẽ chặn oan.

**Thiết kế:**

1. `recommended=false` → banner đỏ sticky "⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH" + hiển thị RÕ LÝ DO máy đưa ra (rationale từ `wh_approach_script`) để NV biết xác minh cái gì.
2. Talk-track + reason rail bị thu gọn/che mờ; nút "Tôi đã xác minh — vẫn tiếp tục" mở khoá (1 click friction có chủ đích).
3. Ghi acknowledgment vào activity audit: `activity_type='other'`, `custom_fields={"r14_ack": true, "script_id": ..., "reason_shown": ...}` → manager đo được tần suất override.
4. Báo cáo: tỉ lệ override cao ở 1 loại rationale = tín hiệu model sai → feedback loop chỉnh warehouse.
5. **Hard-block CHỈ khi** tương lai có `consent='denied'` thật (hiện chưa tồn tại record nào).

---

### D4 — `activity.custom_fields` = structured event payload (có chủ đích, giữ và lập quy ước)

**Hiện trạng đã xác minh:** migration `0030_activity_log_custom_fields.up.sql` thêm cột `custom_fields TEXT` (JSON) vào `crm_activity_log` — comment: *"Stores structured metadata (owner_user_id, etc.) separate from display subject"*.

Nơi dùng duy nhất hiện nay: M04 Gán phụ trách (`screen_modals.py:190`) ghi audit activity `subject="Gán phụ trách → {tên}"` kèm `custom_fields={"owner_user_id": ...}` → lịch sử gán owner query được bằng máy, không phải parse text.

**Quy ước chốt:**

- (a) `custom_fields` là payload **MÁY-ĐỌC** cho activity dạng event/audit, KHÔNG cho NV nhập tự do qua M08.
- (b) Key phải đăng ký trong registry bên dưới trước khi code.
- (c) Key mới = thêm dòng vào registry.
- (d) Export: cột này đi kèm `crm_activity_log` export sẵn có, warehouse đọc bằng `json_extract`.

**Registry `custom_fields` keys:**

| Key | Nguồn | Ghi chú |
|-----|-------|---------|
| `owner_user_id` | M04 Gán phụ trách | audit owner assignment |
| `r14_ack` | D3 R14 warn-with-ack | `true` khi NV xác nhận override |
| `script_id` | D3 R14 warn-with-ack | ID script bị override |
| `reason_shown` | D3 R14 warn-with-ack | rationale hiển thị lúc ack |
| `resolve_task_ids` | A3 bulk-resolve | snapshot các task_id đóng trong 1 outcome |
| `resolve_action_ids` | A3 bulk-resolve | snapshot các action_id dismiss trong 1 outcome |

> `outcome_reason` KHÔNG vào đây — là cột riêng theo D2.

---

## §7. Lộ trình ưu tiên

### P0 — Đóng vòng dữ liệu + số liệu đúng

- **D1** — 4 export mới + staging models (`crm_note`, `crm_tag`/`crm_party_tag`, `crm_party_insight`, `crm_customer_profile.custom`)
- **A3** — bulk-resolve: bind endpoint + M08 nhận mảng IDs

### P1 — Giữ ngữ cảnh cho NV

- **A1** — denormalize `value_at_stake_vnd` + `top_affinity_product` vào task claim
- **A2** — queue counter #n/N + nút "Khách kế →" nối logic
- **A4** — snooze trực tiếp trên task claim
- **D2** — outcome enum 2 tầng (`contact_outcome` + `outcome_reason`) + pill M08
- **D3** — R14 warn-with-ack + acknowledgment audit

### P2 — Thu thập & phát hiện

- Custom fields đưa vào khối Collect cockpit (skin_type, preferred_contact)
- Nút "★ Đúc kết" insight inline trong M08
- **B1** — band "Treo lâu": auto-mở khi có VIP/GOLD, hoặc badge + tổng value
- **B2** — badge "⏰ vừa thức dậy" khi snooze hết hạn
- **B4** — badge `[AUTO]` cho `source='action_queue_claim'`
- **B5** — dismiss theo `(party_id, action_type)` + TTL (cần bàn thêm)
- **B3** — filter "Của tôi" (wire auth context)
- Toast khi Collect inline lưu thành công
- Tooltip nút back cockpit

---

## §8. Câu hỏi mở

1. **`crm_note` `visibility='private'`:** export có loại trừ hoàn toàn hay chỉ mask `body`? (chốt khi triển khai D1)
2. **B5 dismiss theo `(party_id, action_type)` + TTL:** TTL bao lâu hợp lý? Có cho manager xem danh sách dismissed không?
3. **`outcome_reason` enum:** cần NV dùng thử 2 tuần rồi hiệu chỉnh (thêm/bớt) trước khi khoá mapping mart — ai là người thu thập feedback giai đoạn pilot?
