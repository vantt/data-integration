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
- Committed as 2 commits per user decision: `1c90e448` (hash-fix, isolated by hand-trimming
  git diffs — nothing had been committed yet, so partial-hunk staging via `git apply`/selective
  `git add` was safe) and `c4e5fdff` (the queue/my-tasks split + overflow-collision fix).
  Shared-label tradeoff confirmed acceptable by user, kept as-is.

## Follow-up (2026-07-09, same day) — Đã Claim section

- User asked for a distinct "Đã Claim" grouping (initially requested as an inline row label,
  then changed to "a section header before the claimed bands" instead — inline label reverted,
  never shipped).
- Added `claimed_task_bands`/`claimed_task_count` to `split_worklist_view()`: bands 0/1/2/3
  further partitioned by `payload.source == 'action_queue_claim'` (claimed) vs not (manual).
  `my_task_bands`'s bands 0/1/2/3 now manual-only; band 4 stays mixed-source untouched (out of
  scope, documented in the ui-spec doc). New 4th page section "🙋 Đã Claim", same
  `show_overflow=false` treatment as `my_task_bands` (shares band ids 0/1/2 with it and with
  `queue_action_bands` — same overflow-route collision risk applies).
- Regression caught during implementation (not by an external reviewer this time): the shared
  `_rebuild_band()` helper introduced for this refactor zeroed `vip_count` unconditionally,
  breaking `queue_action_bands`' VIP/GOLD signal (band 3 only, must be preserved there). Fixed
  with a `zero_vip` parameter, caught immediately by the existing
  `test_band3_vip_count_preserved_in_queue_action_bands` test — reinforces why that regression
  test was worth writing in the first place.
- The inline badge from `a3f746b0` was removed as part of this follow-up (not a separate
  revert commit — folded into the new commit below, which is the correct final state).
  Committed as `8276b209`. 936 tests passing, live-verified.

## Follow-up 2 (2026-07-09, same day) — collapsible sections, reorder

- User asked whether Cơ Hội Hệ Thống / Đã Claim should become tabs for easier use.
  Recommendation given (and accepted): no full tab — a real tab would hide the "just
  claimed → moved to Đã Claim" feedback the instant a rep clicks Nhận việc (item lands in a
  hidden tab instead of the same scroll), which mirrors the earlier decision against a
  full-page tab split. Went with the cheaper alternative instead: made both sections
  collapsible `<details>` (collapsed by default, same pattern already used for Hàng Đợi
  Chung) — page starts compact, expand only what's needed.
- Reordered: Đã Claim now renders before Cơ Hội Hệ Thống (work already claimed is more
  directly actionable than new opportunities still to be decided on).
- 937 tests passing, live-verified (collapsed-by-default + order confirmed against the
  running container).

## Follow-up 3 (2026-07-09, same day) — Quá hạn must not be hidden by Đã Claim collapse

- User caught a regression introduced by follow-up 2: making Đã Claim collapse-by-default
  meant an overdue (band 0, "Quá hạn") CLAIMED task was now hidden behind that collapsed
  toggle — undermining the whole point of band 0 always being open/prominent.
- Fix: band 0 is no longer split by source in `split_worklist_view()` — same treatment as
  band 4 now (mixed manual+claimed, stays in `my_task_bands`, always in the always-expanded
  urgency area). Only bands 1/2/3 are still split into `claimed_task_bands`.
  `claimed_task_bands` now covers ids 1/2/3 only (was 0/1/2/3).
- 939 tests passing (3 new: overdue-claimed-stays-in-my_task_bands, claimed-bands-ids-1-2-3,
  manual+claimed-overdue-grouped-together, plus a template-level regression test rendering
  an overdue claimed task and asserting it's visible without expanding Đã Claim).

## Follow-up 4 (2026-07-09, same day) — reframe to claimed/unclaimed as the PRIMARY axis

- User flagged a genuine miscommunication after follow-up 3: what they actually wanted was
  the opposite fix (band 0 items that happen to be claimed should live INSIDE Đã Claim, not
  in a separate always-visible area) — but going back and forth on band 0 in isolation kept
  producing contradictory patches. Root cause: the whole `split_worklist_view()` was built on
  a **kind** axis (action vs task) when the user's actual mental model is a **claim-status**
  axis (claimed vs unclaimed) — kind is only a sub-distinction that matters within the
  unclaimed side.
- New 2-section model, confirmed with the user via concrete preview before implementing
  (after 2 rounds of talking past each other on this exact point):
  - **🙋 Đã Claim** (secondary, collapsed by default, renders first): `claimed_bands` = ALL
    `kind='task'` rows (manual-assigned + `action_queue_claim`), NOT split by source —
    reverts to the ORIGINAL unsplit banding from phase 02, just relabeled/repositioned. This
    resolves the Quá hạn dilemma as a side effect: there's no more "which section does an
    overdue claimed task belong to" question, because claimed/manual is no longer a
    distinction made anywhere inside this section.
  - **🎯 Chưa Claim** (PRIMARY, expanded by default): everything with no owner. Two named
    sub-groups nested inside — Hàng Đợi Chung (unassigned manual tasks) FIRST per explicit
    user request, then Cơ Hội Hệ Thống (unclaimed actions, `queue_action_bands`) second.
  - Bonus correctness fix that fell out of the reframe: band 4 ("Đã liên hệ") now correctly
    splits into two independent sub-groups (contacted-unclaimed actions → inside Cơ Hội Hệ
    Thống; contacted-claimed tasks → inside Đã Claim) instead of awkwardly mixing both kinds
    under "my tasks" as it did in every earlier iteration — each half now lives in the
    section it conceptually belongs to.
  - Removed: `claimed_task_bands`/`claimed_task_count` (source-based split), `my_task_bands`
    (renamed/repurposed as `claimed_bands`, unsplit). `queue_action_bands` unchanged in
    shape, now also includes band 4.
- 948 tests passing (rewrote `TestSplitWorklistView`/`TestSplitWorklistViewClaimedTasks` into
  one coherent class; rewrote `TestClaimedTaskSection`'s now-inverted assumptions; added
  `TestChuaClaimWrapper` for the new wrapper's expand-by-default + sub-ordering + combined
  count). Live-verified against the restarted container (order, expand/collapse defaults
  confirmed via direct HTTP fetch).

## Key files

- `crm/src/application/worklist_ranking.py` — add split helper, no change to `rank_worklist`
- `crm/src/adapters/inbound/web/screen_worklist.py` — `_load_worklist_data` wiring
- `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` — layout order
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` — reuse macro for queue rows
- `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` — unchanged (receives
  pre-filtered rows)
- `crm/src/tests/test_worklist_ranking.py`, `crm/src/tests/test_web_templating.py`

## Acceptance criteria

**Superseded by Follow-up 4 — see that section for the final, correct model.** Kept here for
history; do not treat as current spec:

- ~~Band 0-3 in the urgency area never render `row.kind == 'action'` rows.~~
- ~~Every unclaimed, not-recently-contacted action renders exactly once, inside "Cơ Hội Hệ
  Thống" — not duplicated in urgency bands, not lost.~~ (still true, unchanged by follow-up 4)
- Claiming an action (or self-assigning a queue task) removes it from its queue section and
  it appears in Đã Claim on next load — end-to-end verified manually.
- ~~Band 4 "Đã liên hệ" still mixes both kinds, still first, still collapsed by default.~~
  Superseded: band 4 now splits into 2 independent sub-groups, one per section (see
  Follow-up 4) — this was a correctness improvement, not a regression.
- All existing tests pass; new tests cover the split helper and both top-level sections.

## Open questions

1. "Cơ Hội Hệ Thống" nội bộ có cần sub-group theo urgency tier (như band1/2/3 cũ) hay render
   phẳng 1 danh sách sort theo urgency desc? Plan hiện chọn: giữ 2 sub-nhóm ẩn/hiện đơn giản
   (Khẩn mở sẵn, phần còn lại — gồm cả "treo lâu" — collapse) để không mất tín hiệu neglect/VIP
   đã có. Xác nhận với user ở phase 02 nếu cách này không đúng ý.
2. `my_tasks` due_date scope — deferred, không thuộc plan này (xem Decisions).
