# Phase 07: Validation Script & Deploy Aliases

> **Status:** DONE
> **Owner:** Data Team
> **Depends:** Phase 02, 03, 04, 06 done
> **Blocks:** None (final phase)

---

## Context Links

- Drift discovered: `plans/reports/audit-260527-1202-metabase-collection-tree.md` §3, §4
- Deploy script: `.skills/metabase-automation/scripts/deploy_from_markdown.js`
- Existing validator: `.skills/metabase-automation/scripts/validate-analytics-artifacts.js`

## Overview

Sau khi cleanup xong, cần **chống tái phát**. Phase này build:
1. Validation script on-demand chống drift spec↔live
2. Archive policy — aliases support trong deploy script

> **Removed from scope:**
> - D2 pre-commit hook — overhead không cần thiết
> - D4 Dagster daily job — làm rối, user tự phát hiện drift
> - D5 Rollout communication — defer thành plan riêng

## Deliverables

### D1 — `validate-collections.js`

**Location:** `.skills/metabase-automation/scripts/validate-collections.js`

**6 checks:**
1. Blueprint collection paths đều có trong `collection_registry.yml`
2. Registry khớp với live Metabase collection tree
3. Không có duplicate dashboard name trong cùng collection
4. Sub-collection có ≤1 dashboard → warn
5. Mọi dashboard có scope suffix `[All|Retail|B2B|Cross|US|Internal]`
6. Mọi dashboard có description ≥10 ký tự

**Output modes:**
- `--mode=report` (default): in kết quả ra console
- `--mode=ci`: exit 1 nếu có errors (dùng trong pipeline nếu cần)

### D3 — `aliases:` support trong deploy script

**File:** `.skills/metabase-automation/scripts/deploy_from_markdown.js`

**Behavior:** Khi blueprint có `aliases:` frontmatter, deploy script tìm dashboard cũ theo tên alias và archive trước khi tạo mới.

**Blueprint frontmatter example:**
```yaml
---
title: CEO Weekly Pulse [All]
aliases:
  - CEO Weekly Pulse
---
```

## Todo List

- [x] D1: Write `validate-collections.js` (6 checks, --mode=report/ci)
- [x] D3: Add aliases auto-archive to `deploy_from_markdown.js`

## Run Result (2026-06-11)

```
Live state: 12 collections, 37 dashboards | Registry: 12 paths | Blueprints: 38 files
0 errors — 4 known warnings (2× C4 single-board subs, 2× C5 intentional no-suffix)
```

## Success Criteria

- [ ] `validate-collections.js` chạy clean (0 errors) trên current live state
- [ ] Deploy với `aliases:` tự archive bản cũ, verified manually
