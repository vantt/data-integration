# Phase 07b — Glyph-Map & STOP Banner Fix Report

**Date:** 2026-07-02
**Branch:** feature/task-detail-cockpit-backend

---

## Summary of changes

### 1. Extended GLYPH_MAP (generate-ascii.mjs)

Added 18 new mappings; also switched regex flag from `"g"` to `"gu"` (required for supplementary-plane emoji above U+FFFF to match as full code points, not surrogate halves):

| Glyph | Mapping | Rationale |
|-------|---------|-----------|
| ▸ | `>` | S14 objection list triangles |
| ▾ | `v` | S14 secondary-reasons triangle |
| ☎ | `T:` | S14 identity_bar phone number |
| 📞 | `>` | S14 [Gọi] button |
| 💬 | `~` | S14 [Zalo] button |
| ✉ | `@` | hand-drawn ASCII block, future samples |
| ☑ | `[x]` | S14 talking_points checkboxes |
| ☐ | `[ ]` | S14 talking_points / reason_to_call |
| ✅ | `[x]` | future use |
| ❌ | `x` | future use |
| 🔍 | `(?)` | S14 objection search |
| ⛔ | `!!` | S14 guardrails, stop_banner |
| 🛒 | `$` | S14 outcome_bar |
| 📋 | `#` | S14 [Copy] button |
| 📊 | `#` | future analytics surfaces |
| 🔗 | `&` | future link icons |
| ⏱ | `(t)` | S14 strategy_summary, reason_to_call |
| ⏳ | `(t)` | S14 outcome_bar |

Glyphs already in map (kept): ▶ ◀ ▲ ▼ ■ ● ⚠ ☁ ✓ ✕ ✗ ★ ☆ ⓘ

**Scan scope:** all `samples:` values across 54 spec surfaces. Remaining non-ASCII chars are Vietnamese diacritics (Latin Extended, display-width-1, correctly pass through) plus `•`, `…`, `←`, `→` (all BMP, width-1, no change needed).

### 2. Floating-region block — `when:` caption inside box

Added a caption line inside the floating box after the region name. Previously the STOP block showed only the region name; now:

```
[STOP variant — when: recommended == false]
┌────────────────────────────────────────────────────────────────────────────┐
│STOP_BANNER                                                                 │
│when: recommended == false                                                  │
│· !! KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH · [Tạo task xác minh] [Xem hồ s…│
└────────────────────────────────────────────────────────────────────────────┘
```

No `when:` line is added when `when` is absent (tested).

### 3. S14 spec — added stop_banner sample

Added to `samples:` under `ui-layout` in `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`:
```
stop_banner: "⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH · [Tạo task xác minh] [Xem hồ sơ 360]"
```

### 4. Tests updated (generate-ascii.test.mjs)

Added 9 new tests (33 total, all pass):
- Floating box `when:` caption inside box
- Floating box without `when:` has no caption
- ⛔ → !!
- ☑/☐ → [x]/[ ]
- ▸/▾ → >/v
- emoji 📞/💬/📋/🔍/🛒 → ASCII
- ⏱/⏳ → (t)
- ✅/❌ → [x]/x
- ☎/✉ → T:/@

---

## Regenerated S14 base-block ASCII (for human review)

```
┌────────────────────────────────────────────────────────────────────────────┐
│IDENTITY_BAR                                                                │
│· Hoàng Thức [GOLD][active] · Miền Trung · T:0983***35 [>Gọi][~Zalo] [360]  │
├────────────────────────────────────────────────────────────────────────────┤
│ALERT_ROW                                                                   │
│· [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]     │
├─────────────────────────────────────────────┬──────────────────────────────┤
│TALK_TRACK                                   │REASON_TO_CALL                │
│· "Dạ em chào anh Thức…" [#Copy]             │· * PRIMARY: REORDER · GT~1.2…│
├─────────────────────────────────────────────┤                              │
│STRATEGY_SUMMARY                             │                              │
│· (t) Gọi 1-2 ngày, giờ hành chính           │                              │
├─────────────────────────────────────────────┼──────────────────────────────┤
│TALKING_POINTS                               │SNAPSHOT                      │
│· 2/3 · [x] Nhắc chu kỳ [x] Ưu đãi [ ] Combo…│· LTV 8.2tr · 3 đơn · 45d · g…│
├─────────────────────────────────────────────┼──────────────────────────────┤
│OBJECTION_HANDLING                           │COLLECT                       │
│· > "Chưa cần mua" > "Giá sao?" [(?) khách v…│· • Zalo [+] • Email [+] • Si…│
├─────────────────────────────────────────────┤                              │
│GUARDRAILS                                   │                              │
│· !! không giảm sâu · không hứa giao nhanh   │                              │
├─────────────────────────────────────────────┴──────────────────────────────┤
│TRUST_FOOTER                                                                │
│· độ tin vừa · script 24/6 07:15 ICT · ! AI gợi ý, dùng phán đoán           │
├────────────────────────────────────────────────────────────────────────────┤
│OUTCOME_BAR                                                                 │
│· [ghi chú tạm…] [vGọi được][xKhông nghe][(t)Hẹn lại][$Đã mua]              │
└────────────────────────────────────────────────────────────────────────────┘
```

**Glyph audit (base block):** 0 stray `?`. The 4 `?` chars in the full output (base + variant) are all `(?)` sequences representing 🔍 — intentional.

---

## Test results

| Suite | Pass | Fail |
|-------|------|------|
| generate-ascii.test.mjs | 33 | 0 |
| extract-layout.test.mjs | 9 | 0 |
| verify-runtime.mjs (A-I) | PASS | — |
| build.mjs | OK | — |
| ascii idempotency (2nd run) | 0 writes | — |

---

## Files changed

- `.agents/skills/ui-spec/tools/wireframe/generate-ascii.mjs` — GLYPH_MAP (+18 entries, `gu` flag), floating block `when:` caption
- `.agents/skills/ui-spec/tools/wireframe/generate-ascii.test.mjs` — 9 new tests
- `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` — added `stop_banner:` sample; ASCII block regenerated

---

Status: DONE
Summary: Extended GLYPH_MAP with 18 new ASCII-safe fallbacks (zero `?` litter in S14), added `when:` caption inside floating STOP box, injected `stop_banner` sample in S14; all 33 unit tests pass, verify-runtime A-I clean, idempotency confirmed.
