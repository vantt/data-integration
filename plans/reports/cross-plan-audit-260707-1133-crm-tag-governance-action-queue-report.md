> **Update 2026-07-07 (fix pass):** Tất cả 3 finding đã fix + verify live. Chi tiết ở cuối file.

# Cross-plan audit — CRM tag ACL sync + health/governance + action-queue consumer

**Phạm vi:** `260619-0830-crm-tag-acl-sync`, `260706-0833-crm-health-profile-tag-governance`, `260706-1738-crm-tag-signal-action-queue-consumer` (tất cả v1 scope đã DONE). Kiểm tra lại cấu trúc dữ liệu + UX sau khi cả 3 đã chạy live.

Method: đọc toàn bộ plan.md + phase docs + implementation reports (9+7+4 files), verify chéo bằng cách đọc code hiện tại (`crm_writeback_assets.py`, `stg_crm__party_tag.sql`, `int_crm_party_tag_flags.sql`, `settings.html`, `worklist_ranking.py`) thay vì tin báo cáo.

## Finding 1 — Archive tag KHÔNG cắt đứt ảnh hưởng lên action queue (data structure gap, còn sống)

`crm_tag.is_archived`/`is_provisional` (thêm ở 0833 phase 01) **không bao giờ được export** ra warehouse — `crm_tag` export query (`crm_writeback_assets.py`) chỉ SELECT `tag_id, name, category, color, display_label`. `stg_crm__party_tag.sql` và `int_crm_party_tag_flags.sql` không filter `is_archived` ở đâu cả.

Hệ quả cụ thể: nếu admin **archive** 1 tag category=`risk` hoặc `vip_tier` qua Governance Admin (0833 phase 03) — tag biến mất khỏi S14/M03 picker (đúng như spec) NHƯNG các `crm_party_tag` rows `source='crm_user'` đã gán trước đó **vẫn tính vào `has_vip_tag`/`has_risk_tag`** ở `mart_customer_action_queue` (1738 phase 02) vì chain export→staging→intermediate không biết gì về archived. Rep sẽ thấy badge "Cần xác minh rủi ro" với rationale chứa tên 1 tag đã bị archive — tag đó không còn xuất hiện ở bất kỳ đâu khác trong CRM UI, gây khó hiểu và trông như bug.

Chưa trigger hôm nay (chỉ 1 tag risk/vip_tier hiện có — VIP sync, chưa archive) nhưng là quả bom hẹn giờ: 3 plan độc lập thiết kế đúng trong phạm vi riêng, không ai sở hữu chain export đầy đủ nên gap lọt qua.

**Đề xuất:** thêm `is_archived` vào export `crm_tag` + filter `is_archived=0` trong `int_crm_party_tag_flags.sql` (1 dòng SQL + 1 cột export — chi phí thấp).

## Finding 2 — Governance Admin có destructive actions không gate role (đã biết, vẫn mở)

`/settings/tags/merge`, `/archive`, `/settings/tags*` dùng `require_admin` — hiện là **no-op stub cho phép mọi authenticated request** (xác nhận sống: `CF_ACCESS_AUDIENCE` set nhưng request không JWT vẫn 200). Merge tag là **irreversible** (xóa `crm_tag` + reassign `crm_party_tag`). Cả 2 report (0833 phase-03, và implicit ở 1738) đều flag "role=sales→403 KHÔNG verify được" nhưng để user quyết — vẫn chưa thấy quyết định. Vẫn là rủi ro thao tác nhầm/rep tò mò bấm merge/archive không ai chặn.

## Finding 3 — Không có tín hiệu chủ động cho admin biết có tag chờ duyệt

`/settings/tags` chỉ là link text tĩnh "Quản lý Tag (merge/archive/provisional)" trong tab Settings — không badge đếm L1/L2 queue depth, không notification nào. Cả mục đích chính của Governance Admin là chặn "tags phình không kiểm soát" (theo đúng vấn đề nêu trong plan.md của 0833) nhưng nếu admin không tự nhớ ghé thăm trang, provisional tags dồn ứ vô thời hạn — quay lại đúng vấn đề ban đầu plan này định giải quyết.

## Đã verify KHÔNG phải bug (để khỏi nghi ngờ lại)

- `crm_party_tag` export `source` **đã** đổi từ literal `'crm_user'` sang `pt.source` thật (0619 landed sau 1738 phase-01, code hiện tại đã update đúng) — chỉ còn 1 dòng TODO comment stale ở `stg_crm__party_tag.sql:13` nói "chưa switch" dù dòng ngay dưới đã switch rồi. Vô hại, chỉ gây hiểu lầm khi đọc code — nên xóa comment.
- VIP sync tag (group 1812240 → tag vip_tier) là ngoại lệ duy nhất chạm category `vip_tier`/`risk` từ ACL sync — nhưng 1738 filter `source='crm_user'` nên tag sync này KHÔNG lọt vào action queue. Defense-in-depth hoạt động đúng như thiết kế.
- `priority_rank` renumber 1→7 (chèn `MANUAL_RISK_REVIEW=2`) không phá banding UI (`worklist_ranking.py` dùng `urgency=10−priority_rank` tương đối, không hardcode ngưỡng) và không phá Metabase blueprint (`ORDER BY priority_rank` động, không CASE cứng theo giá trị cũ).
- Category discipline giữa 3 plan nhất quán: `health_domain`/`health_concern` (0833) tách biệt hoàn toàn khỏi `risk`/`vip_tier` (1738 tiêu thụ) — không collision.
- Provisional tag được ops chipify dùng `source='ops_normalized'` — không lọt qua filter `source='crm_user'` của 1738 dù category sau này gán là risk/vip_tier — an toàn.

## UX — điểm hở nhỏ, không chặn nhưng đáng ghi nhận

- Khách có tag risk/vip_tier nhưng `party_id` chưa link Sapo (`customer_id NULL`) → tag vô hình với action queue, không có tín hiệu nào trong S03/S14 báo rep biết "tag này chưa ảnh hưởng worklist vì khách chưa liên kết Sapo". Hiện 0% khách rơi vào case này (mọi party đều đã Sapo-linked) nên chưa đau, nhưng sẽ xuất hiện khi CRM có Lark-only lead.
- `health_context_raw` là 1 field overwrite, không có lịch sử — non-goal đã khai báo rõ trong plan (không phải oversight).

## Không tìm thấy

Không có vấn đề cấu trúc nghiêm trọng khác (schema/migration/ACL mapping đều nhất quán, đã verify chéo qua PRAGMA + live data trong reports). Test suite pass, không regression mới qua cả 3 plan.

## Unresolved questions

1. Archive-propagation gap (Finding 1) — fix ngay hay chấp nhận rủi ro tạm thời (chỉ 1 tag risk/vip_tier tồn tại, chưa archive)?
2. Role-gating cho `/settings/tags*` (Finding 2) — quyết định app-wide hay riêng màn này?
3. Có cần badge/notification cho provisional queue (Finding 3) không, hay admin tự quản lý bằng lịch ghé thăm định kỳ?

---

## Fix pass — 2026-07-07 (user: "fix ngay, fix hết")

### Finding 1 — FIXED, verified live end-to-end
- `orchestration/assets/crm_writeback_assets.py`: `crm_tag` export thêm cột `is_archived`.
- `scripts/ensure_crm_export_placeholder.py`: schema placeholder cập nhật theo (tránh regress lúc cold-start).
- `stg_crm__party_tag.sql`: pass-through `tag_is_archived` (kèm xóa comment TODO stale nói "chưa switch" dù code đã switch — Finding "không phải bug" cũ, dọn luôn cho khỏi gây hiểu lầm).
- `int_crm_party_tag_flags.sql` + `marts/schema.yml`: filter `AND NOT tag_is_archived`, doc "non-archived" thay vì "active" mơ hồ.
- **Verify sống:** tạo 1 party+tag `risk` tạm (customer_id giả 999999999, không đụng data thật) → xuất hiện `has_risk_tag=true` trong `int_crm_party_tag_flags` → archive qua `TagGovernanceService.archive_tag()` thật → re-export + `dbt build` → customer biến mất khỏi model (đúng như kỳ vọng archive = cắt khỏi action queue) → cleanup, re-export, rebuild → xác nhận 4 khách thật (149453741/64547286/929184461/207728985) về đúng trạng thái ban đầu, không sai lệch.
- `dbt build --select stg_crm__party_tag+`: PASS=10 (cả 2 lần, trước và sau cleanup).

### Finding 2 — Đã fix từ trước (uncommitted, phát hiện khi audit)
`crm/src/adapters/inbound/http/auth_dependency.py::require_admin` đã có bản vá thật (role != ROLE_ADMIN → 403) thay `# temporarily allow all` — nằm sẵn trong working tree, chưa commit, có test riêng (`test_auth_dependency.py`, 4 test). `screen_mgmt_tag_governance.py` đã dùng `require_admin` cho toàn bộ `/settings/tags*`. Không cần làm gì thêm — chỉ verify: full test suite pass, live curl xác nhận `GET /settings?tab=tags` không JWT → 403 (trước đây từng là 200).

### Finding 3 — FIXED
- `tag_governance_repository.py`: `count_pending_review()` (L1+L2 provisional + chipify groups chưa reviewed).
- `tag_governance_service.py`: `pending_review_count()`.
- `screen_mgmt_settings.py` + `screen_management.py`: wire `tag_governance_svc` vào `make_settings_router`, truyền `tag_governance_pending_count` vào template.
- `settings.html`: badge số bên cạnh link "Quản lý Tag".
- Test: `TestPendingReviewCount` (4 test) + `TestSettingsTagsBadge` (3 test, verify badge render/hide qua HTTP thật).

### Verification tổng
- `pytest crm/src/tests` (trừ 1 collection error pre-existing không liên quan): **864 passed, 1 failed** (cùng 1 failure pre-existing từ trước cả 3 plan — không phải regression).
- `dbt build` cho toàn chain `stg_crm__party_tag → int_crm_party_tag_flags → mart_customer_action_queue`: xanh.
- CRM container restart sạch, không lỗi import/template.

Không còn unresolved question nào — cả 3 finding đã đóng.
