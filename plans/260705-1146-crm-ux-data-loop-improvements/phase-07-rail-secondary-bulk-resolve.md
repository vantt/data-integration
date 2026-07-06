# Phase 07 — Rail Secondary Bulk-Resolve (follow-up phase-02)

**Status:** DONE  **Priority:** P2  **Depends on:** 02, 06 (đụng cùng cockpit template)

## Context

Phase-02 giới hạn bulk-resolve chỉ gom ID của `rail_primary` (§Unresolved questions #1). NV có
nhiều action item trên rail "Tranh thủ nếu thuận" (`rail_secondary`) vẫn phải đóng riêng từng
cái. Phase này gom nốt secondary items vào cùng 1 lần ghi outcome.

## Decision

Chỉ item đã tick **"đã nói"** mới được gom vào bulk-resolve — không gom tất cả secondary items
mặc định. Lý do: tick "đã nói" là tín hiệu NV thực sự xác nhận đã trao đổi mục đó trong cuộc gọi;
gom mù toàn bộ rail có rủi ro đóng nhầm task/action NV chưa hề đề cập. `rail_primary` vẫn luôn
được gom mặc định (không cần tick) — hành vi cũ giữ nguyên.

## Files Modified

| File | Thay đổi |
|---|---|
| `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` | `s14ToggleReason()`: secondary item tick → fold/unfold `data-action-id`/`data-task-id` vào `#s14-resolve-action-ids`/`#s14-resolve-task-ids` qua helper mới `s14SetResolveId()`. Primary item bỏ qua (giữ default). Tooltip checkbox secondary cập nhật: "Đánh dấu đã nói — sẽ đóng cùng outcome cuộc gọi". |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Outcome bar note + A-S14-025 effects: ghi rõ hành vi fold-in mới. |

Không đổi backend — `bulk_resolve()` đã nhận list ID tuỳ ý từ phase-02, không cần sửa.
Không đổi M08 template — summary "Sẽ đóng N task · M hành động" đã tính bằng `split(',')`, tự
động phản ánh đúng khi hidden input có nhiều ID.

## Behavior

1. `rail_primary` → luôn nằm trong `#s14-resolve-action-ids`/`#s14-resolve-task-ids` (server-rendered default, không đổi).
2. NV tick "đã nói" trên 1 item trong `rail_secondary` → JS thêm `action_id`/`task_id` của item đó vào 2 hidden input (comma-separated, dedup theo `indexOf`).
3. Bỏ tick → JS gỡ ID đó khỏi hidden input.
4. Bấm outcome bar (Gọi được/Không nghe/Hẹn lại/Đã mua) → `s14OpenOutcome()` đọc giá trị hidden input hiện tại (đã gồm cả secondary đã tick), forward qua query string vào M08.
5. M08 hiển thị summary đúng tổng số N task/M action sẽ đóng, submit → `bulk_resolve()` đóng đủ.

## Tests & Validation

Thuần client-side JS (không có unit test framework cho template JS trong repo). Manual QA:
- Mở S14 cockpit của khách có ≥1 secondary rail item.
- Tick "đã nói" trên 1 secondary item → mở M08 (bất kỳ outcome nào) → summary hiện đúng
  "Sẽ đóng 2 task" (1 từ primary + 1 từ secondary) nếu cả 2 đều có task_id.
- Bỏ tick lại → mở lại M08 → summary trở về chỉ đếm primary.
- Submit M08 → cả 2 task/action đóng đúng (verify qua worklist/tasks board sau khi submit).

## Risks & Rollback

- Trùng ID (secondary item share `task_id` với primary) → `ids.indexOf` không dedup cross-source vì primary không đi qua `s14SetResolveId`; bulk_resolve xử lý per-item error-isolated nên gọi 2 lần cùng ID vẫn an toàn (đã có test idempotent ở phase-02).
- Rollback: revert 1 file template (JS function), 1 file spec. Không migration, không backend.

## Unresolved Questions

Không có.
