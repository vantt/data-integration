# CRM Health Profile + Tag Governance Admin

**Ngày:** 2026-07-06
**Mục tiêu:** (1) Thu thập health profile (domain chips + free text) trong call cockpit. (2) Xây admin screen tổng quát để quản lý taxonomy tags, xử lý provisional tags (2 levels), và chipify free text → structured tags — áp dụng cho mọi category, không chỉ health.

**Depends on:** `260619-0830-crm-tag-acl-sync` Phase 01 (adds `crm_party_tag.source` + `ext_ref`, tạo `crm_ext_tag`/`crm_ext_tag_map` trong cùng migration — nên ACL tables LUÔN tồn tại khi plan này chạy, không cần feature-guard)

> **Cập nhật 2026-07-06 (khớp thiết kế với 260619 revised):** Merge/Archive trong phase 03 phải xử lý `crm_ext_tag_map` (repoint khi merge, deactivate inbound mapping khi archive) — nếu không, merge gãy FK/mồ côi mapping, archive tạo zombie sync. Chi tiết đã vá trong [phase-03](phase-03-tag-governance-admin.md). Reassign party_tag khi merge dùng INSERT OR IGNORE + DELETE (PK collision khi party có cả 2 tag).

---

## Vấn đề

| Vấn đề | Hiện trạng |
|--------|-----------|
| Health data siloed | `skin_type` là custom field cứng, không scale khi SP đa dạng |
| Tags phình không kiểm soát | Không có merge/archive/governance — duplicates tăng dần |
| Rep không thể nhập tag mới | Phải dùng M14 (require category), không có fast path |
| Free text không queryable | Rep ghi chú sức khỏe nhưng không thể segment/filter |
| Không có bulk admin view | M03 chỉ per-party; không thấy pattern across customers |

## Giải pháp

**Provisional tag pattern — 2 levels:**

| Level | category | is_provisional | Ý nghĩa | Admin action |
|-------|----------|---------------|---------|-------------|
| Canonical | set | 0 | Hiện trong chips/pickers | — |
| **L1** provisional | set | 1 | Domain đã biết, tag chưa validate | Confirm/rename/merge trong tab đúng domain |
| **L2** provisional | NULL | 1 | Domain chưa biết, chỉ có text | Gán domain trước → rồi confirm/merge |

Rep nhập tag tự do trong S14/M03 → tạo provisional (L1 hoặc L2) → admin chuẩn hóa trong Governance Admin.

`health_context_raw` trong `party.custom` là scratchpad song song — ops chipify text này thành structured tags.

---

## Data structure

```
crm_tag                                 (0003 + Phase 01)
  tag_id          TEXT PK
  name            TEXT NOT NULL
  category        TEXT                   -- NULL = L2 provisional
  color           TEXT
  is_provisional  INTEGER DEFAULT 0      -- 0=canonical / 1=chờ admin  ← NEW
  is_archived     INTEGER DEFAULT 0      -- 0=active / 1=retired        ← NEW
  UNIQUE (category, name)

crm_party_tag                           (0003 + 260619 Phase 01)
  party_id, tag_id  PK
  tagged_by, tagged_at
  source      TEXT DEFAULT 'crm_user'   -- 'crm_user'|'ops_normalized'  ← 260619
                                        -- |'sapo_v2_sync'|'merged'
  ext_ref     TEXT                                                       ← 260619

crm_ext_tag + crm_ext_tag_map          (260619 Phase 01 — ACL Sapo sync)

crm_customer_profile.custom (JSON)
  health_context_raw          string    -- free text rep nhập
  health_context_raw_reviewed bool      -- ops đã chipify/skip
```

---

## Phases

| # | Phase | Trạng thái | Output chính |
|---|-------|-----------|-------------|
| 01 | [Schema — is_provisional + is_archived + seed health tags](phase-01-schema.md) | ✅ | Migration: 2 columns mới trên crm_tag; seed 8 health domain tags |
| 02 | [S14 collect — health chips + context text + provisional inline](phase-02-s14-health-collect.md) | ✅ | collect region: domain multi-chip + free text row + POST inline tạo provisional tag |
| 03 | [Tag Governance Admin — S13 extension](phase-03-tag-governance-admin.md) | ✅ | `/settings/tags`: taxonomy + L1 queue + L2 queue + chipify |
| 04 | Script generator integration | ➡️ Moved | Moved sang [`260707-2343-crm-tag-deferred-followups`](../../260707-2343-crm-tag-deferred-followups/phase-02-approach-script-health-integration.md) phase 02 — `wh_approach_script` reads health_tags → `data_gaps[]`, `talking_points[]` |

**v1 scope:** Phase 01 + 02 + 03. Phase 04 moved sang backlog plan `260707-2343-crm-tag-deferred-followups`.

> **Status:** ✅ Plan hoàn tất (Phase 01+02+03 done). Phase 04 moved sang `260707-2343-crm-tag-deferred-followups`.

---

## Dependencies

- Phase 01 → 02 → 03 (strict sequential)
- Phase 01 depends on `260619` Phase 01 (crm_party_tag.source column)
- Phase 04 (moved to `260707-2343-crm-tag-deferred-followups`) depends on script generator refactor (track riêng)

---

## Conflict rules

| Tình huống | Xử lý |
|-----------|-------|
| Rep assign tag (canonical) từ S14 | `source='crm_user'` |
| Rep tạo provisional tag từ S14/M03 | `source='crm_user'`, `is_provisional=1` |
| Ops chipify health_context_raw | `source='ops_normalized'`, `is_provisional=0` |
| Sapo sync gán tag có source=crm_user | ON CONFLICT DO NOTHING — crm_user wins |
| Admin promote L1 provisional | `SET is_provisional=0` — không đổi source/assignment |
| Admin merge provisional → canonical | reassign party_tag, `source='merged'` trên rows được move |

---

## Non-goals (v1)

- Không LLM auto-suggest tags
- Không outbound sync health tags về Sapo
- Không per-customer health history timeline
- Không NLP fuzzy grouping — chipify dùng exact text group v1

> Backlog ý tưởng (LLM auto-suggest, outbound health sync, history timeline, NLP fuzzy grouping) đã gom vào [`260707-2343-crm-tag-deferred-followups`](../../260707-2343-crm-tag-deferred-followups/plan.md).
