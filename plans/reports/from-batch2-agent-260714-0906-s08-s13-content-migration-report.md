# S08-S13 samples/elements -> content: migration report

Scope: crm/docs/ui-spec/screens/{S08,S09,S10,S11,S12,S13}.md. Followed
.skills/ui-spec/references/ui-layout-authoring.md §8b recipe + §2b primitives/idioms.
No .skills/, no other surfaces, no crm-contract yaml touched.

## S08 — Segments List

- Regions migrated: sidebar, topbar, segment_list (all 3; samples/elements deleted).
- sidebar -> `slot: "C01 Sidebar Nav (global)"`.
- topbar -> `row` of `h` + `btn "+ Tạo segment"` (mapped A-S08-001, primary) + `input` search
  (non-actionable per idiom; A-S08-004 stays contract-only).
- segment_list -> `table` (Tên/Loại/Thành viên/Cập nhật cuối/Trạng thái, rows:4). Per-row
  interactions (A-S08-002 navigate S09, A-S08-003 navigate S10) intentionally NOT represented
  as row buttons — idiom: table rows are display-only skeletons.
- Added `row_heights: [auto, "minmax(300px,auto)"]` (segment_list dominates).
- Actions mapped: A-S08-001. Actions idiom-exempt (non-actionable type or per-row): A-S08-002/003/004.
- Gaps/ambiguities: none.

## S09 — Segment Builder

- Regions migrated: topbar, rule_editor, preview_panel, actions_bar (all 4).
- topbar -> `row`: `btn "← Segments"` (A-S09-001), `text` label, `input` name field, `chips: ["Lưu"]`,
  `text` label, `select "Dynamic"` (segment_type_toggle A-S09-008, non-actionable per idiom).
- rule_editor -> `h` + `list` (condition-row skeleton, rows:2) + `btn "+ Thêm điều kiện"` (A-S09-002).
  Per-condition interactions (A-S09-003 field select, A-S09-004 remove) are per-item list
  interactions — idiom-exempt, not represented as fake per-row controls.
- preview_panel -> `kpi` + `text` (excluded-by-consent note) + `btn "Preview danh sách"` (A-S09-005)
  + `list` (member preview skeleton, rows:3).
- actions_bar -> `row`: `btn "Hủy"` (A-S09-007), `btn "Lưu & Materialize"` (A-S09-006, primary).
- Added `row_heights: [auto, "minmax(250px,auto)", auto]`.
- **Contract gap / ambiguity**: the old samples line showed a standalone `[Lưu]` button next to the
  segment-name field in topbar, but the legacy `elements:` map never mapped it (only "← Segments",
  "+ Thêm điều kiện", "Preview danh sách", "Hủy", "Lưu & Materialize" were mapped) — pre-existing gap,
  not introduced by this migration. No interaction in the contract distinguishes an inline
  rename-save from the actions_bar full "Lưu & Materialize" (A-S09-006). Rendered as a display-only
  `chips: ["Lưu"]` (no action invented, per recipe step 3). Needs a product decision: (a) this is a
  duplicate affordance that should be removed from the design, or (b) a real quick-save interaction
  is missing from the contract and should be added.
- **Tooling bug found and fixed** (not spec content): my first draft used inline block-mapping
  syntax `- btn: "x", action: A-...` (invalid YAML — bad indentation of a mapping entry). js-yaml
  throws, `extractLayout()` catches it and returns `null`, and both `validate.mjs`'s VR-ASCII-DRIFT
  check and `build.mjs`'s ascii-injection loop treat a `null` layout as "no layout to check/skip" —
  so the error was silently swallowed with **no warning and no build output**, and stale ASCII from
  the old samples model stayed in the file looking untouched. Root-caused via a temporary debug
  script (created and deleted inside `.skills/ui-spec/tools/`, not committed) that called
  `extractLayout()` directly. Fixed by switching to flow-style `{ btn: "...", action: ... }` for all
  such single-line entries (also hit in S12, see below). Flagging this as a real gap in the tool
  chain: a malformed `content:` fence currently fails **silent** instead of surfacing
  VR-LAYOUT-PARSE-style feedback — worth a follow-up in the skill itself (out of scope here, no
  `.skills/` file was touched).

## S10 — Campaigns List

- Regions migrated: sidebar, topbar, campaign_list (all 3).
- topbar -> `row`: `h`, `btn "+ Tạo chiến dịch"` (A-S10-001, primary), `select` status filter
  (A-S10-003, non-actionable per idiom).
- campaign_list -> `table` (Tên/Objective/Channel/Targets/Converted/Rate/Trạng thái, rows:4).
  Per-row A-S10-002 (navigate S11) idiom-exempt.
- Added `row_heights: [auto, "minmax(300px,auto)"]`.
- Gaps/ambiguities: none.

## S11 — Campaign Detail / Targets

- Regions migrated: topbar, summary_bar, target_list, conversion_stats (all 4, single-column, no
  `columns:` key — unchanged from original).
- topbar -> `row`: `btn "← Chiến dịch"` (A-S11-001), `h` campaign name, `btn "Sửa"` (A-S11-007),
  `btn "Kích hoạt"` (A-S11-008, primary).
- summary_bar -> `row` of 5 `kpi` (Targets/Sent/Converted/Rate/Revenue attr.).
- target_list -> `row` (`h` + `select` status filter, A-S11-005 non-actionable per idiom) + `table`
  (Khách hàng/Trạng thái/NV phụ trách/Mã đơn, rows:4). Per-row A-S11-002 (navigate S03), A-S11-003
  (open M12 mark converted), A-S11-004 (mark skipped) idiom-exempt — explicitly NOT faked as
  per-row buttons.
- conversion_stats -> `slot` (hosted SSE-driven tracker, matches old "(...)" placeholder sample).
- Added `row_heights: [auto, auto, "minmax(250px,auto)", auto]`.
- **Contract gap flagged**: A-S11-006 `filter_assignee` (target_list, change) has no visible chip
  in the old sample/elements either — pre-existing, not surfaced in content (select type is
  non-actionable per idiom regardless, so no action loss either way).

## S12 — Ads Tracking

- Regions migrated: sidebar, topbar, ad_campaign_list, stats_panel (all 4).
- topbar -> `row`: `h`, `select "Date range: 30 ngày"` (A-S12-002), `select "Ad platform: Facebook"`
  (A-S12-003) — both non-actionable per idiom.
- ad_campaign_list -> `table` (Chiến dịch/Spend/Leads/Converted/CPC, rows:4). Per-row A-S12-001
  (mutate stats_panel.load_campaign_detail) idiom-exempt.
- stats_panel -> `row` of 4 `kpi` + `btn "Xem leads"` (A-S12-004) + `list` (lead preview, rows:3).
  Per-item A-S12-005 (`lead_party_link`, navigate S03) idiom-exempt.
- Added `row_heights: [auto, "minmax(280px,auto)"]`.
- **Ambiguity flagged**: A-S12-004 (`btn_view_leads`) and A-S12-005 (`lead_party_link`) existed in
  the contract but had **no** corresponding chip text anywhere in the old `samples:`/`elements:` —
  the legacy one-liner never surfaced them at all. I added a "Xem leads" button labelled from the
  contract's `element: btn_view_leads` name (action ID already existed, not invented) so the real
  interaction has a visible affordance; A-S12-005 stays an unmapped per-item list link by idiom. If
  "Xem leads" isn't the intended label, a human should adjust — I did not have a design reference.
- Same YAML block-mapping bug as S09 (`- btn: "Xem leads", action: A-S12-004` was invalid) — fixed
  to flow-style `{ btn: ..., action: ... }`.

## S13 — Settings

- Regions migrated: sidebar, topbar, settings_nav, settings_content (all 4).
- topbar -> `h: "Cài đặt"`.
- settings_nav -> `tabs: ["Custom Fields", "Tags", "Người dùng"]` with per-tab `actions:` map
  (A-S13-001/002/003). Original ASCII drew this as a vertical nav list, not a horizontal tab bar —
  per §2b guidance ("nav/section switch -> tabs, per-label actions: when each tab has its own
  interaction") this is the documented idiom translation regardless of original visual orientation;
  flagging as a deliberate, not silent, choice.
- settings_content -> only the **default** "Custom Fields" tab state (`row` with `h` + `btn "+ Thêm"`
  mapped A-S13-004, primary; `table` Nhãn/Kiểu/Bắt buộc/Actions, rows:3) — matches the "(default)"
  marker in the prose. The Tags-tab column spec (## Tab: Tags section) and Users tab remain
  documented in prose only; a static single-content-array region can only show one snapshot state.
  Per-row edit/delete (A-S13-005/006/008/009/010) are per-item table interactions — idiom-exempt,
  not faked as row buttons.
- Added `row_heights: [auto, "minmax(280px,auto)"]`.
- Gaps/ambiguities: none beyond the tabs-idiom note above.

## Cross-cutting notes

- Every `select`/`input` filter/toggle across all 6 surfaces was rendered **without** `action:`,
  per the task's stated established idiom ("select/input are non-actionable") — confirmed against
  `layout-schema.mjs` `CONTENT_TYPES` (`input`/`select` both `actionable: false`), matching S02's
  canonical pattern. The underlying `crm-contract` interactions (A-S08-004, A-S09-008, A-S10-003,
  A-S11-005/006, A-S12-002/003) are untouched and still real — they are simply exempt from the
  content/chip-audit coverage check by primitive type, not dropped.
- Every per-row/per-item table/list interaction across all 6 surfaces (row click → navigate,
  per-row action buttons like "mark converted"/"mark skipped"/edit/delete) was deliberately left
  unrepresented in `content:`, per §2b: "collections are display-only skeletons... do not work
  around this with fake per-row buttons." None of these are chip-audit findings since `table`/`list`
  are non-actionable types.
- Discovered and worked around a real tool gap: a malformed `content:` YAML block (single-line
  block-mapping with a trailing `, key: value`) causes `extractLayout()` to catch the YAML parse
  error and return `null`; both `validate.mjs` (VR-ASCII-DRIFT) and `build.mjs` (ascii injection)
  then silently skip the file instead of surfacing any error — first `build.mjs` run reported
  "all up to date" for S09/S12 while their ASCII was actually stale from the pre-migration model.
  Caught only by manually calling `extractLayout()` on the raw file. Recommend the skill add a
  VR-LAYOUT-PARSE-style warning specifically for `content:`-block YAML failures (currently that rule
  only fires for the whole fence, and even then only "warn", not surfaced when `!Array.isArray(model.areas)`
  short-circuits earlier). No `.skills/` file was modified to fix this — flagging only.

## Verification

```
node .skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec   # 0 errors, 0 warnings (final run)
node .skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec      # regenerated ASCII for all 6 files across 2 passes
node .skills/ui-spec/tools/wireframe/verify-runtime.mjs --root crm/docs/ui-spec   # PASS, 0 errors, 54 surfaces, 6 flows
node .skills/ui-spec/tools/wireframe/screenshot.mjs --root crm/docs/ui-spec --surface S08,S09,S10,S11,S12,S13 --width 1920 --height 2100
  # all 6 PNGs written to crm/docs/ui-spec/generated/screenshots/
```

chip-audit.md: S08-S13 have **zero** entries (mapped or unmapped) — confirming zero unmapped
actionable chips for all 6 surfaces. All 43 unmapped tokens in the audit belong to other,
untouched surfaces (M01-M14, O03, P03-P05) still on the legacy samples path.

Visual QA (read all 6 PNGs): proportions match declared `columns`/`row_heights`, sample/content
text dominant per cell, airy spacing, no chip overflow, Vietnamese diacritics render cleanly, no
mojibake, Contract Inspector panel present, no horizontal scroll. One cosmetic (pre-existing, not
introduced by this migration) observation: S13's `settings_nav` column (`1fr` of `[1fr,1fr,4fr]`)
is narrow enough that the third tab label "Người dùng" clips to "Ngư…" — a column-width choice
already present in the original spec's `columns:` declaration, unchanged here.

Status: DONE
Summary: All 6 surfaces migrated samples:/elements: -> content: per §8b/§2b; validate 0/0,
verify-runtime PASS, 6 screenshots written, chip-audit clean for S08-S13.
Concerns/Blockers: S09's topbar "Lưu" button has no contract interaction (pre-existing gap, flagged
not fixed); S12's "Xem leads" label was authored from the contract element name since no prior
sample text existed for it — a human should confirm the label; found (and worked around, not fixed
in `.skills/`) a silent-failure gap in `extractLayout()`/build tooling for malformed `content:` YAML.
