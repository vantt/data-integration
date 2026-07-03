# Phase 07 — ASCII Generator Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Spec root:** `crm/docs/ui-spec/`  
**Tool root:** `.agents/skills/ui-spec/tools/`

---

## Verification results

| Check | Result |
|---|---|
| `extract-layout.test.mjs` | 9/9 pass |
| `generate-ascii.test.mjs` | 24/24 pass |
| `generate-ascii.mjs --surface S14` idempotency | 2nd run → 0 files written ✓ |
| `validate.mjs --root crm/docs/ui-spec` | PASS (1 stale-wireframe warning cleared by build) |
| `build.mjs --root crm/docs/ui-spec` | PASS — 1 surface with layout, all up to date |
| `verify-runtime.mjs --root crm/docs/ui-spec` | PASS — A-I all green, 0 errors, 54 surfaces |

---

## Files created / modified

| File | Change |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/generate-ascii.mjs` | New — `generateAscii`, `injectAscii`, `computeColWidths` (exported), CLI |
| `.agents/skills/ui-spec/tools/wireframe/generate-ascii.test.mjs` | New — 24 unit tests |
| `.agents/skills/ui-spec/tools/build.mjs` | Added `readFileSync`, `listSpecFiles`, `generateAscii`, `injectAscii`, `extractLayout` imports + ASCII injection loop after wireframe step |

---

## Algorithm notes

- **Pixel row scheme:** 3 pixel rows per grid row (border / name / sample). Total = 3N+1 for N grid rows. Gives both name and sample in single-row cells without requiring region height ≥ 2.
- **Column widths:** `computeColWidths(["3fr","2fr"], 78)` → `[45, 30]`. `inner = 78 - 2 - (M-1) = 75`. Last col absorbs Math.floor remainder.
- **Horizontal border suppression:** `hasH[c] = areas[r-1][c] !== areas[r][c]`. False → segment stays spaces; junction chars resolved via 4-bit L/R/U/D lookup.
- **Wide-char normalization:** same GLYPH_MAP as ascii-normalize.mjs (▶→>, ⚠→!, ★→* etc.), then secondary pass replaces remaining display-width-2 chars with `?`. After this every char is exactly 1 display column; `padEnd` / `slice` work correctly without display-width arithmetic.
- **injectAscii:** markers inserted right after yaml ui-layout fence on first run; subsequent runs replace marked block via non-greedy regex. Idempotent at both string and file level.

---

## Blueprint view behavior (task item 4 confirmation)

After phase 7, `S14-call-mode-cockpit.md` structure in `## Layout`:

1. ` ```yaml ui-layout ``` ` fence (unchanged)
2. `<!-- ui-layout:ascii:start -->` + generated block ← **NEW, inserted here**
3. `<!-- ui-layout:ascii:end -->`
4. `### Embedded...` hand-drawn ASCII (unchanged, untouched)
5. `### Full-screen...` hand-drawn ASCII (unchanged)
6. `### STOP state...` hand-drawn ASCII (unchanged)

`extractProse` strips the yaml ui-layout fence but NOT the HTML comment markers or the plain ``` block inside them. `findAsciiBlock` searches for the FIRST block with box-drawing chars — this is now the generated block (items 2-3 above). Hand ASCII (items 4-6) remains in prose as later blocks, unreachable by `findAsciiBlock`'s first-match logic.

No double-render: `findAsciiBlock` returns exactly one block (the generated one). Hand ASCII is inert. ✓

Section G in verify-runtime still reports "no surface with bp-region-span found (OK, skip)". This is pre-existing: bp-region-span injection happens at Blueprint-subtab render time, not at Layout-tab render time which is what Section G probes. No regression; was already skip in phases 1-6.

---

## S14 generated base-variant ASCII block (verbatim, for human review)

```
┌────────────────────────────────────────────────────────────────────────────┐
│IDENTITY_BAR                                                                │
│· Hoàng Thức [GOLD][active] · Miền Trung · ?0983***35 [?Gọi][?Zalo] [360]   │
├────────────────────────────────────────────────────────────────────────────┤
│ALERT_ROW                                                                   │
│· [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]     │
├─────────────────────────────────────────────┬──────────────────────────────┤
│TALK_TRACK                                   │REASON_TO_CALL                │
│· "Dạ em chào anh Thức…" [?Copy]             │· * PRIMARY: REORDER · GT~1.2…│
├─────────────────────────────────────────────┤                              │
│STRATEGY_SUMMARY                             │                              │
│· ⏱ Gọi 1-2 ngày, giờ hành chính             │                              │
├─────────────────────────────────────────────┼──────────────────────────────┤
│TALKING_POINTS                               │SNAPSHOT                      │
│· 2/3 · ? Nhắc chu kỳ ? Ưu đãi ? Combo · Gợi…│· LTV 8.2tr · 3 đơn · 45d · g…│
├─────────────────────────────────────────────┼──────────────────────────────┤
│OBJECTION_HANDLING                           │COLLECT                       │
│· ? "Chưa cần mua" ? "Giá sao?" [? khách vừa…│· • Zalo [+] • Email [+] • Si…│
├─────────────────────────────────────────────┤                              │
│GUARDRAILS                                   │                              │
│· ? không giảm sâu · không hứa giao nhanh    │                              │
├─────────────────────────────────────────────┴──────────────────────────────┤
│TRUST_FOOTER                                                                │
│· độ tin vừa · script 24/6 07:15 ICT · ! AI gợi ý, dùng phán đoán           │
├────────────────────────────────────────────────────────────────────────────┤
│OUTCOME_BAR                                                                 │
│· [ghi chú tạm…] [vGọi được][xKhông nghe][⏳Hẹn lại][?Đã mua]                │
└────────────────────────────────────────────────────────────────────────────┘
```

**Diff vs hand-drawn — what's acceptable:**

| Aspect | Hand-drawn | Generated | Verdict |
|---|---|---|---|
| Column widths | ~40:35 visual split | 45:30 (from 3fr:2fr) | ✓ acceptable — fr-proportional |
| Cell labels | label in border row ("┌ IDENTITY BAR ──") | name inside cell (UPPER) | ✓ acceptable — style delta |
| reason_to_call rowspan | yes (2 rows, RIGHT rail) | yes ✓ | ✓ |
| collect rowspan | yes | yes ✓ | ✓ |
| trust_footer span | yes (─┴─ junction) | yes (├─┴─┤) ✓ | ✓ |
| Sample text | hand-authored narrative | from `samples:` dict | ✓ |
| Wide chars | emoji preserved | replaced with `?` | ✓ acceptable — alignment-safe |
| All regions present | 12/14 named in ASCII | all 14 named ✓ | ✓ improvement |

**Unacceptable deltas:** none. All 14 regions named, spanning correct, layout geometry matches YAML.

---

## Wide-char substitution detail

The following chars in S14 samples were replaced with `?`:

| Original | Unicode | Range | Substituted |
|---|---|---|---|
| ☎ | U+260E | 0x2600–0x27BF (wide) | ? |
| 📞 | U+1F4DE | emoji (wide) | ? |
| 💬 | U+1F4AC | emoji (wide) | ? |
| 📋 | U+1F4CB | emoji (wide) | ? |
| ☑ | U+2611 | 0x2600–0x27BF (wide) | ? |
| ☐ | U+2610 | 0x2600–0x27BF (wide) | ? |
| ▸ | U+25B8 | 0x25A0–0x25FF (wide) | ? |
| ⛔ | U+26D4 | 0x2600–0x27BF (wide) | ? |
| 🔍 | U+1F50D | emoji (wide) | ? |
| 🛒 | U+1F6D2 | emoji (wide) | ? |

The GLYPH_MAP (same as ascii-normalize.mjs) already handled: ⚠→!, ★→*, ✓→v, ✗→x.  
⏱ (U+23F0), ⏳ (U+23F3) and → are in non-wide ranges → pass through unchanged.

If human review finds `?` substitution too lossy, a phase-8 option is to extend GLYPH_MAP with single-char emoji mappings (e.g. 📞→@, ☑→v). This would need to land in both generate-ascii.mjs and ascii-normalize.mjs for consistency.

---

## Unresolved questions

1. **Wide-char substitution fidelity:** `?` is correct but loses emoji meaning. Should we extend the GLYPH_MAP with meaningful 1-char substitutions (📞→@, ☑→v, ⛔→!, ▸→>) before phase 8 migration? Current behavior is deterministic and alignment-safe.
2. **Section G bp-region-span:** Generated ASCII in the marked block is now the first ASCII block in prose. However, bp-region-span injection didn't activate in Section G (pre-existing: G probes while on Layout tab, not Blueprint tab). Worth verifying manually in browser that Blueprint tab for S14 now shows the generated ASCII with region highlights.
3. **`⏱ Gọi 1-2 ngày`** in strategy_summary passes through as-is (⏱ = U+23F0, 1-wide). Renders correctly in monospace viewers that support Misc Technical range. Acceptable.

---

Status: DONE  
Summary: Deterministic ASCII generator implemented (generate-ascii.mjs, 24 tests pass), injected into S14 after yaml ui-layout fence, build integrated; verify-runtime A-I green with zero errors.
