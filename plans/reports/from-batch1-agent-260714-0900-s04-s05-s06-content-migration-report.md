# S04/S05/S06 samples: → content: migration report

Migrated per `.skills/ui-spec/references/ui-layout-authoring.md` §8b recipe + §2b primitive table
(incl. Established idioms: kanban idiom N/A here; no link primitive; list/table rows display-only).

## S04 — Dedup Review (`crm/docs/ui-spec/screens/S04-dedup-review.md`)

Regions migrated: `sidebar`, `topbar`, `candidate_list`, `detail_pane` (all 4 that had `samples:`).

- `sidebar` → `slot: "C01 Sidebar Nav (global)"` — matches the established corpus idiom for the
  global-nav sidebar region (same pattern already used in S02, S07).
- `topbar` → `h` title + `text` pending-count + `select` filter (filter_match_rule, A-S04-007).
  `select` is not an actionable type per `layout-schema.mjs` (only `btn`/`tabs` carry `action:`),
  so no `action:` on the select — mirrors S02's topbar filter selects (A-S02-003..006), which are
  likewise unmapped-by-type in the existing corpus. Not a gap; established pattern.
- `candidate_list` → `list: { item: ..., rows: 4 }`. A-S04-001 (`candidate_row` click →
  `detail_pane.load_candidate`) is a per-item row interaction — intentionally not representable
  per §2b idiom ("Per-item interactions on list/table rows... intentionally NOT representable").
  Flagged, not a gap.
- `detail_pane` → Party A / Party B text lines + **added** `btn "Xem 360 A ›"` (A-S04-005) and
  `btn "Xem 360 B ›"` (A-S04-006), plus the 3 existing action buttons (Merge/Reject/Bỏ qua,
  A-S04-002/003/004, Merge marked `primary`). A-S04-005/006 existed in the contract but had **no**
  corresponding chip in the legacy `samples`/`elements` (pre-existing contract-to-UI gap, not
  introduced by this migration) — added real buttons since the contract clearly assigns them to
  `detail_pane` and the Purpose section describes viewing both parties' profiles.

All 7 detail_pane/topbar/candidate_list interactions now accounted for (5 mapped as btn, 1
select left unmapped-by-type per convention, 1 per-item row interaction left unmapped-by-idiom).

## S05 — Inbox (`crm/docs/ui-spec/screens/S05-inbox.md`)

Regions migrated: `sidebar`, `topbar`, `conv_list`, `preview_pane`.

- `sidebar` → `slot: "C01 Sidebar Nav (global)"` (same idiom as S04).
- `topbar` → `h "Inbox"` + `select "All"` (filter_assignee, A-S05-003, unmapped-by-type per
  convention above) + `tabs: ["Open","Pending","Closed"], action: A-S05-002` (filter_status —
  legacy sample rendered these as a pipe-separated 3-way toggle, which is exactly the `tabs`
  primitive; whole-bar `action:` since one interaction covers the group) + `btn "Gán cho tôi"`
  (A-S05-004).
- `conv_list` → `list: { item: ..., rows: 5 }`. Two per-item interactions —
  A-S05-001 (`conv_row` click → navigate S06) and A-S05-005 (`conv_assign_btn` click → open
  M09) — intentionally not representable per the same list/table-rows-are-display-only idiom.
  Flagged, not a gap.
- `preview_pane` → single `text` line (no interactions on this region in the contract).

All 5 interactions accounted for: 1 tabs mapped, 1 btn mapped, 1 select unmapped-by-type
(convention), 2 per-item row interactions unmapped-by-idiom (both flagged).

## S06 — Conversation Detail (`crm/docs/ui-spec/screens/S06-conversation-detail.md`)

Regions migrated: `topbar`, `message_thread`, `input_bar`, `customer_sidebar` (all 4).

- `topbar` → `btn "← Inbox"` (A-S06-001) + `text` PSID + `badge Pending` + `text` assignee +
  `btn "Đổi NV"` (A-S06-004) + `btn "Đóng hội thoại"` (A-S06-002) + `btn "Ghi note"` (A-S06-003).
- `message_thread` → `list: { item: ..., rows: 4 }`, display-only (only a `listens_to` LSN01
  append-message reaction on this region — no user-triggered interaction to map).
- `input_bar` → `input: "(disabled — read-only v1)"` (v1 read-only, matches Purpose section;
  no interactions).
- `customer_sidebar` → `row` of `h` name + 2 `badge`s (GOLD/active) + `text` "Mua gần: 3 ngày" +
  `btn "Mở hồ sơ đầy ›"` (A-S06-006) + `btn "Chưa link khách → 🔍 Tìm khách"` (A-S06-005). Both
  buttons kept side by side as in the legacy sample (they represent mutually-exclusive party-
  linked / not-linked states, same as the original samples/elements pair) — content model has no
  state-conditional element visibility beyond `floating`, so this is carried over as-is, matching
  prior behavior.

All 6 interactions mapped to `btn` elements; the only non-actionable regions (message_thread,
input_bar) have no contract interactions to lose.

## Verify summary

```
validate.mjs (pre-build):  0 errors, 5 warnings (all VR-ASCII-DRIFT on the 4 files build.mjs
                            was about to touch, incl. pre-existing S15 drift unrelated to this
                            task — expected, resolved by build)
build.mjs:                 ascii regenerated: S04, S05, S06 (+ pre-existing S15 drift, untouched
                            content-wise by this task); chip-audit: 240 tokens, 195 mapped,
                            45 unmapped (none in S04/S05/S06)
validate.mjs (post-build): 0 errors, 0 warnings
verify-runtime.mjs:        PASS — 54 surfaces exercised, 6 flows, 0 runtime errors
screenshot.mjs:            3/3 written —
  crm/docs/ui-spec/generated/screenshots/S04.png
  crm/docs/ui-spec/generated/screenshots/S05.png
  crm/docs/ui-spec/generated/screenshots/S06.png
```

Visual QA (read all 3 PNGs): column proportions match `columns:` fr ratios, sample/content text
dominant per cell with small muted region labels, airy spacing with no overlap, mapped buttons
render as distinct button shapes vs. plain text/badges, no raw contract text leaked into grid
cells, Vietnamese diacritics + emoji render cleanly (no tofu/mojibake). No visual regressions.

`generated/chip-audit.md`: grepped for S04/S05/S06 — zero entries in the Unmapped Chips section
for all three surfaces (checked against full unmapped list, which only contains M01-M16/P0x/S07+
entries unrelated to this task).

## Ambiguities / contract gaps (flagged, not fixed — per scope, no contract edits made)

1. **S04 A-S04-005/A-S04-006 pre-existing UI gap**: the contract has always defined
   `btn_view_party_a`/`btn_view_party_b` but the legacy `samples`/`elements` never exposed a chip
   for them. Resolved by adding visible buttons (uses existing action IDs only, no contract
   change) — flagging in case the intent was actually to drop these two interactions rather than
   surface them; if so, they should be removed from the contract instead in a follow-up.
2. **Per-item list/table interactions** (S04 A-S04-001, S05 A-S05-001/A-S05-005) are, per §2b,
   intentionally invisible in `content:` — visible only via region-level hover in the Contract
   Inspector. No action needed; noting for completeness per the recipe's step-7 report requirement.
3. **`select` elements with a mapped `change` interaction** (S04 filter_match_rule, S05
   filter_assignee) can't carry `action:` under the current `CONTENT_TYPES` registry (`select` is
   `actionable: false`). This mirrors existing S02 precedent, so treated as consistent-with-corpus
   rather than a new gap — flagging only because it means those two contract interactions are not
   chip-audited at all (neither mapped nor flagged unmapped, since selects are exempt by type).

## Files modified

- `D:\Vantt\app\data-integration\crm\docs\ui-spec\screens\S04-dedup-review.md`
- `D:\Vantt\app\data-integration\crm\docs\ui-spec\screens\S05-inbox.md`
- `D:\Vantt\app\data-integration\crm\docs\ui-spec\screens\S06-conversation-detail.md`

(build.mjs also regenerated ASCII for `screens/S15-task-detail.md` as a side effect of a
pre-existing, unrelated VR-ASCII-DRIFT warning that predated this task — that file's `content:`
model itself was not touched by this task, only its generated ASCII block was refreshed by the
same `build.mjs` run.)

Status: DONE
Summary: S04/S05/S06 fully migrated samples:/elements: → content: per §8b/§2b; validate 0/0,
verify-runtime PASS, chip-audit shows zero unmapped entries for all three surfaces, 3 screenshots
written and visually clean.
Concerns/Blockers: 2 pre-existing contract-vs-UI gaps flagged above (§ Ambiguities items 1 and 3)
— no contract edits made, per task scope.
