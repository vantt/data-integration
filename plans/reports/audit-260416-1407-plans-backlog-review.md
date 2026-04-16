# Plans & Backlog Audit — 2026-04-16

## Summary

Scanned 8 plan directories, 4 backlog files, 15 reports. Found **3 active plans with pending work**, **2 new pipelines blocked on user input**, **1 config plan ready to start**, and **several deferred items worth re-evaluating for actionable reports**.

---

## A. Active Plans — Status & Next Actions

### 1. Ingestion Trust Engineering (260415)
**Status:** Phases 0–4 DONE, Phase 5 DEFERRED
**Commits:** `bb5c965`..`5d171fe` (5 commits, all merged to main)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Health DB + writer | DONE | |
| 1 — Metadata contract | DONE | All assets call `_record_health` |
| 2 — Asset checks | DONE | Freshness + volume + trend |
| 3 — Reconciliation | DONE | Daily recon assets |
| 4 — Morning Lark digest | DONE | 08:00 card |
| 5 — KPI closure (revenue invariant) | DEFERRED | Blocked on Sapo revenue API validation |

**What can improve for actionable reports:**
- **Morning digest is operational** — but does it surface **actionable thresholds**? Current WARN/FAIL are based on row-trend. Could add:
  - **Zero-row consecutive ticks** count → explicit "Source X has not ingested in N runs" message
  - **Drift % in reconciliation** → if recon drift > threshold, digest should say "Recon drift 5.2% for orders — investigate"
  - **Link to Dagster run** in Lark card for failed/warn items → operator can click directly
- **Phase 5 (KPI closure)**: Still blocked on Sapo API validation. Pre-req: confirm `orders.json` can return `total_price` reliably for date range. Low priority per user.

### 2. Channel Taxonomy Rename (260415)
**Status:** COMPLETE ✅
- All 4 commits merged, Metabase cards updated (35 cards via API)
- Migration report written
- **No remaining work.** Can archive this plan.

### 3. Config Ecosystem Reorganization (260416)
**Status:** PENDING — all 6 phases not started
**Effort:** ~3h total

| Phase | Status | Effort |
|-------|--------|--------|
| 1 — Split .env files | Pending | 45m |
| 2 — Deduplicate config | Pending | 30m |
| 3 — Kill config loader | Pending | 45m |
| 4 — Clean compose env | Pending | 20m |
| 5 — Update templates | Pending | 20m |
| 6 — Validate | Pending | 30m |

**Action:** Ready to implement anytime. Clean P2 tech-debt cleanup. Fully planned, sequential dependencies clear.

### 4. Serving DB Hang Fix (260408)
**Status:** MOSTLY COMPLETE
- Phase 1 (subprocess fix + timeout) — DONE (verified in commit history)
- Phase 2 (Pattern C — bootstrap/refresh split) — DONE
- Phase 3 (synergy with Dagster stability) — DONE (stuck_run_alerter deployed)
- Metabase read-only JDBC — needs verification (was scheduled "Day 4")

**Remaining:** Verify Metabase JDBC `duckdb.read_only=true` is actually configured. If not, apply it.

---

## B. New Pipeline Plans — Blocked on User Input

### 5. Shopee Income Pipeline (260409)
**Status:** Design spec done, 6 implementation phases all PENDING
**Blocker:** 9 of 11 open questions unanswered (Q1–Q6, Q8, Q10, Q11 pending)

**Critical unanswered questions:**
| Q | Topic | Why it matters |
|---|-------|----------------|
| Q1 | Full fee coverage | Determines if `net_settlement` reconciles with Shopee totals |
| Q2 | Multi-SKU orders | Validates composite key design |
| Q3 | Shop identity | Single vs multi-shop partition strategy |
| Q8 | `piship_service_fee` type | INT vs DECIMAL column type |

**Action required from user:** Answer at least Q1, Q2, Q3 to unblock Phase 1 implementation.

### 6. MISA AMIS Pipeline (260409)
**Status:** Design spec done, 6 implementation phases all PENDING
**Blocker:** Depends on Shopee pipeline patterns (shared infrastructure). No independent blockers — can start implementation once Shopee pattern is established, or implement in parallel.

**Action:** Can start independently. Reuses same file-drop pattern as Shopee. Lower risk (single entity, simpler schema). Could be a good "first" to establish the pattern.

---

## C. Backlogs — What's Worth Picking Up

### Code Review Deferred Backlog

| Item | Priority | Actionability | Recommendation |
|------|----------|---------------|----------------|
| **Webhook ACK after load** (U7) | Medium | High — clear fix path | **Pick up.** Data loss risk if dlt load crashes after extraction. Clear implementation sketch exists. |
| **Cookie lock orphaned .tmp** | Low | Low — self-heals | Skip. Retry delay is 30s. |
| **`--limit` flag no-op** | Low | Low — CLI convenience | Skip. |
| **GSheet schema validation** | Low | Medium | Skip — dbt tests cover this. |
| **JSON malformed guard** | Low | Low — Sapo sends valid JSON | Skip unless errors observed. |
| **Hardcoded payment method** | Low | Medium | Worth revisiting if payment analytics needed. |
| **New status observability** | Low | Medium | `accepted_values` tests already exist. |
| **Parquet atomicity** | Low | Low — failure mode requires 3 simultaneous conditions | Skip. |
| **Webhook dedup merge** | Low | Optional | Skip unless storage concern. |

**Recommended pickup:** Only **Webhook ACK after load** is worth doing — it's the only item with real data-loss risk.

### Analytics Design Backlog

| Item | Priority | Actionability | Recommendation |
|------|----------|---------------|----------------|
| **Fix 1 — CEO Weekly Pulse archetype violation** | Medium | High — clear options | Quick win. Option A (re-label) is 15 min. |
| **Fix 2 — Blueprint→Design Spec references** | Low | High — mechanical | Quick win. Add header to 15 blueprints. |
| **P2 — Executive Visual System** | Low | Low — 1-2 week effort | Defer. No business pressure. |

---

## D. Improvement Opportunities for Actionable Reports

### 1. Morning Lark Digest — Make it actionable
**Current:** Shows per-source verdict (OK/WARN/FAIL) with volume + trend.
**Improvement:**
- Add **direct Dagster run link** for WARN/FAIL items
- Add **consecutive zero-row count** ("orders: 0 rows for 3 consecutive runs")
- Add **recommended action** per failure type ("Check API credentials" / "Check file drop folder" / "Run manual backfill")
- Add **recon drift %** inline (not just pass/fail)

### 2. Reconciliation — Surface drift details
**Current:** Daily recon assets compute drift metric.
**Improvement:**
- Add **weekly trend** — is drift improving or worsening?
- Add **per-entity breakdown** in digest when drift > threshold
- Consider a simple **Metabase dashboard card** showing recon drift over time (time-series)

### 3. Ingestion Health Dashboard — Already deployed, but can enhance
**Current:** Deployed as Metabase dashboard (commit `01191f1`).
**Improvement:**
- Add **SLA compliance rate** card (% of runs completing within 12h SLA)
- Add **data freshness heatmap** (entity × date, color = hours since last ingest)
- Add **alert history** card (count of WARN/FAIL per week, trending)

### 4. Stuck Run Alerter — Add resolution guidance
**Current:** Sends Lark card with "Operator kiểm tra thủ công".
**Improvement:**
- Include **likely cause** based on job type (serving → "check subprocess/DB lock", dbt → "check DuckDB contention", ingestion → "check API/auth")
- Include **runbook link** to `docs/operations/troubleshooting.md` relevant section
- Include **kill command** in card for quick resolution

---

## E. Priority Matrix

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P1** | Answer Shopee open questions → unblock pipeline | User time | Unlocks new data source |
| **P1** | MISA pipeline implementation (can start now) | 1-2 days | COGS data for margin analysis |
| **P1** | Lark digest improvements (actionable messages) | 2-3h | Reduces MTTR for ops issues |
| **P2** | Config ecosystem reorganization | 3h | Tech debt cleanup |
| **P2** | Webhook ACK after load fix | 2-3h | Eliminates data loss risk |
| **P2** | Verify Metabase read-only JDBC | 15min | Semantic correctness |
| **P3** | CEO Pulse archetype fix | 15min | Analytics skill hygiene |
| **P3** | Blueprint→design spec references | 30min | Documentation hygiene |
| **P3** | Stuck run alerter improvements | 1h | Better ops experience |
| **Defer** | KPI closure (Phase 5) | 4h | Blocked on Sapo API |
| **Defer** | P2 Executive Visual System | 1-2 weeks | No business pressure |
| **Defer** | Lock audit session | Half day | Good reference doc, not urgent |

---

## Unresolved Questions

1. **Metabase read-only JDBC** — Was this actually applied after the serving DB fix? Needs verification.
2. **Shopee open questions (9 pending)** — User needs to answer at least Q1-Q3 to unblock pipeline.
3. **MISA vs Shopee ordering** — Start MISA first (simpler) or wait for Shopee pattern?
4. **Morning digest effectiveness** — Has anyone acted on a digest alert yet? Real-world feedback would inform improvement priorities.
