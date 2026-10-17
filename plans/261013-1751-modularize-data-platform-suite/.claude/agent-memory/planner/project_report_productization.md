---
name: report-productization-plan-conventions
description: Conventions and constraints for plans in fg-dataware-house (Vietnamese plans, mandatory doc header, prod-safety rules, report productization decisions)
metadata:
  type: project
---

Plans in this repo are written in Vietnamese (complete sentences, code identifiers in English). Every phase file starts with the user's mandatory header "làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó" plus a "Tài liệu phải cập nhật" list; style template is plans/261013-1751-modularize-data-platform-suite/phase-06-fine-japan-tenant-overlay.md.

**Why:** user requirement since 13/10/2026; dashboards (Metabase, Evidence) are used daily by Fine Japan.

**How to apply:** prod changes only via docs/operations/deployment.md runbooks, executing session deploys after the user approves the time; avoid 02:30–04:00; never write prod Metabase without cold H2 copy (scripts/backup/metabase_cold_backup.sh pre-deploy) + reviewed plan; no plan/phase IDs in code or commits. Report productization plan (2026-10-14) lives at plans/261014-2225-report-productization/ and implements report-product-design.md v2 §8 with all §11 decisions approved. See [[report-productization-plan]].
