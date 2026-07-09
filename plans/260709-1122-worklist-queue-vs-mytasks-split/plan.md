# Plan — Worklist: Queue vs "Việc của tôi" Split

**Created:** 2026-07-09 · **Branch:** main · **Surface:** S01 Worklist/Dashboard (CRM)
**Goal:** Xóa nhầm lẫn task-vs-action-item bằng cách tách "cơ hội chưa ai claim" ra khỏi band
urgency, để band urgency chỉ còn chứa task đã có chủ (manual-assigned + claimed).

## Context

- User feedback: worklist trộn task (đã có chủ) và action-queue item (cơ hội chưa claim) trong
  cùng band urgency (Hôm nay/Khẩn, Trong hạn) → không phân biệt được cái nào cần "quyết định
  claim" vs cái nào cần "thực thi".
- Phát hiện: codebase đã có sẵn đúng pattern cần — `worklist_fragment.html:74-106` render
  "Hàng Đợi Chung" (unassigned manual task) như 1 section riêng phía trên band urgency, KHÔNG
  đi qua `rank_worklist()`. Action-queue item lại không được đối xử tương tự — bị trộn thẳng vào
  band 0-4 cùng task đã claim.
- Role thật của Worklist theo user: nơi system bắn cơ hội (action-queue) + cả team vào claim
  (chưa có lead-assign/auto-assign). S07 Tasks Board là nơi quản lý toàn bộ vòng đời task
  (assignee/status/campaign, kéo-thả) — 2 màn hình khác vai trò, không trùng nhau.

## Decisions (chốt)

- **KHÔNG đổi `worklist_ranking.py`'s band assignment/sort logic** (đã test kỹ — 79+ ranking
  test). Chỉ thêm 1 hàm thuần (`split_by_kind` hoặc tương đương) regroup output của
  `rank_worklist()` tại tầng trình bày.
- **3 section trên trang, KHÔNG tạo route/tab mới:**
  1. `📥 Hàng Đợi Chung` — custom task chưa ai nhận (đã có, redesign lại row cho polish — tái
     dùng `wl_row()` task-branch thay vì markup rời rạc hiện tại).
  2. `🎯 Cơ Hội Hệ Thống` — action-queue chưa claim (MỚI). Giữ nguyên row UI hiện tại
     (`wl_row()` action-branch, không đổi) — chỉ đổi CHỖ render (ra khỏi band loop).
  3. Band urgency (`_wl_bands.html`, không đổi cấu trúc file) — CHỈ còn `kind=='task'` rows.
     Band 4 (`Đã liên hệ`) giữ nguyên hành vi trộn cả 2 kind + vị trí đầu tiên + collapse mặc
     định (đã đúng như vậy — KHÔNG cần đổi, chỉ verify không bị phá khi filter theo kind).
- Action đã bị đưa vào Band 4 (recently contacted, `contacted_party_ids`) do
  `rank_worklist()` xử lý → KHÔNG xuất hiện trong "Cơ Hội Hệ Thống" (đã claimed hoặc đã
  contacted đều không nằm trong hàng đợi nữa). Tránh trùng lặp row.
- Ngoài phạm vi (deferred, user sẽ chốt riêng sau): giới hạn `my_tasks` theo due_date (hiện
  `list_tasks(uid, "open")` không giới hạn — task due xa tương lai dồn mãi vào "Trong hạn").
  Không đụng trong plan này.

## Phases

| # | Phase | Status | Depends |
|---|-------|--------|---------|
| 01 | [Ranking split helper (pure, testable)](phase-01-ranking-split-helper.md) | ✅ done | — |
| 02 | [Screen adapter + template: 2 queue sections](phase-02-screen-and-template-queue-sections.md) | ✅ done | 01 |
| 03 | [Hàng Đợi Chung row redesign](phase-03-hang-doi-chung-row-redesign.md) | ✅ done | 02 |
| 04 | [Tests + manual verify](phase-04-tests-and-verify.md) | ✅ done | 01,02,03 |

## Outcome (2026-07-09)

- 928 passed / 1 deselected (pre-existing, unrelated: `test_approach_script_file_repository.py`
  mtime-cache flake) in container. Live smoke test via curl against the running container
  confirmed the 3-section layout renders correctly (0 task rows inside "Cơ Hội Hệ Thống", 0
  `assign-me` buttons for an unauthenticated request).
- Code review (mandatory gate) caught one real bug not anticipated by the phase files: the
  existing `/worklist/band/{id}/more` overflow route always re-ranks actions-only and is keyed
  by band id — but `queue_action_bands` and `my_task_bands` both use ids 1/2, so the lazy "Xem
  thêm" toggle would have injected action rows into a task band. **Fixed**: `my_task_bands`
  now renders eager/uncapped (`show_overflow=false` in `_wl_bands.html`) instead of sharing that
  route; `queue_action_bands` keeps the lazy-paginated behavior unchanged (its overflow route
  was already correct — actions-only input matches actions-only output). 2 new regression tests
  added (`test_my_task_bands_never_show_xem_them_even_when_over_cap`,
  `test_queue_and_my_tasks_overflow_do_not_collide_on_shared_band_id`).
- Also fixed while touching `_wl_row.html`: the pre-existing hash-leak bug where task rows
  displayed the raw `party_id` UUID instead of the joined `party_name` (field-name typo:
  template read `customer_name`, Task only has `party_name`). Covered by
  `TestTaskRowLabelClarity`.
- Known accepted tradeoff (not a defect): "Cơ Hội Hệ Thống" and the urgency-band area below it
  share the same `_BAND_META` labels (both can show "Hôm nay / Khẩn" / "Trong hạn") since each
  section reuses the existing band metadata unchanged (open question #1 below) — each section
  has its own top-level heading, so this reads as "which sub-tier within this section" rather
  than reintroducing kind-ambiguity. Revisit if it proves confusing in practice.
- Not committed — awaiting user decision on commit split (hash-fix vs redesign as separate
  commits) and confirmation of the shared-label tradeoff above.

## Key files

- `crm/src/application/worklist_ranking.py` — add split helper, no change to `rank_worklist`
- `crm/src/adapters/inbound/web/screen_worklist.py` — `_load_worklist_data` wiring
- `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` — layout order
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` — reuse macro for queue rows
- `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` — unchanged (receives
  pre-filtered rows)
- `crm/src/tests/test_worklist_ranking.py`, `crm/src/tests/test_web_templating.py`

## Acceptance criteria

- Band 0-3 in the urgency area never render `row.kind == 'action'` rows.
- Every unclaimed, not-recently-contacted action renders exactly once, inside "Cơ Hội Hệ
  Thống" — not duplicated in urgency bands, not lost.
- Claiming an action (or self-assigning a queue task) removes it from its queue section and
  it appears in the correct urgency band on next load — end-to-end verified manually.
- Band 4 "Đã liên hệ" still mixes both kinds, still first, still collapsed by default.
- All existing tests pass; new tests cover the split helper and the two queue sections.

## Open questions

1. "Cơ Hội Hệ Thống" nội bộ có cần sub-group theo urgency tier (như band1/2/3 cũ) hay render
   phẳng 1 danh sách sort theo urgency desc? Plan hiện chọn: giữ 2 sub-nhóm ẩn/hiện đơn giản
   (Khẩn mở sẵn, phần còn lại — gồm cả "treo lâu" — collapse) để không mất tín hiệu neglect/VIP
   đã có. Xác nhận với user ở phase 02 nếu cách này không đúng ý.
2. `my_tasks` due_date scope — deferred, không thuộc plan này (xem Decisions).
