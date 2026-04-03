# Documentation System Audit Report

**Date:** 2026-03-30
**Scope:** All 125 Markdown files across the data-integration repository
**Total lines:** ~26,000 lines of documentation

---

## 1. File Map (Tree Structure)

```
data-integration/
├── README.md                          (89 lines)  - Project overview & quick start
├── CLAUDE.md                          (27 lines)  - Claude Code skill commands & env vars
├── AGENTS.md                         (444 lines)  - Global AI agent context (MASTER)
├── DEPLOYMENT.md                     (463 lines)  - Windows Docker deployment guide
├── MIGRATION.md                       (44 lines)  - Metabase H2 DB migration
│
├── .claude/commands/                  [AI AGENT - Claude Code slash commands]
│   ├── create-metabase-blueprint.md   (34 lines)
│   ├── deploy-metabase-blueprint.md   (30 lines)
│   ├── manage-metabase-resources.md   (52 lines)
│   ├── purge-dagster-runs.md          (19 lines)
│   └── setup-metabase-mcp.md         (42 lines)
│
├── .agents/                           [AI AGENT - Antigravity agent definitions]
│   ├── skills/
│   │   ├── metabase-automation/SKILL.md       (44 lines)  - Pointer to .skills/
│   │   ├── purge_dagster_runs/SKILL.md        (37 lines)
│   │   └── setup_metabase_mcp/SKILL.md       (153 lines)
│   └── workflows/
│       ├── create_metabase_blueprint.md        (40 lines)
│       ├── deploy_metabase_blueprint.md        (31 lines)
│       └── manage_metabase_resources.md        (93 lines)
│
├── .skills/metabase-automation/       [SHARED - Agent-agnostic tooling]
│   ├── SKILL.md                      (231 lines)  - Full Metabase API reference
│   ├── STRATEGY.md                    (48 lines)  - Dashboard archetypes & heuristics
│   └── templates/
│       └── blueprint_template.md               - Literate Config syntax reference
│
├── docs/                              [HUMAN - Core project documentation]
│   ├── README.md                     (135 lines)  - Doc index, progressive disclosure
│   ├── ARCHITECTURE.md               (508 lines)  - System architecture & design
│   ├── DATA_FLOW.md                  (503 lines)  - Pipeline data flow
│   ├── DATA_DICTIONARY.md            (562 lines)  - Schema & entity reference
│   ├── GLOSSARY.md                   (238 lines)  - Terms, abbreviations, naming
│   ├── CONTRIBUTING.md               (463 lines)  - Dev workflow & code standards
│   ├── DEPLOYMENT.md                 (463 lines)  - Deployment procedures
│   ├── OPERATIONS.md                 (413 lines)  - Daily ops & monitoring
│   ├── TROUBLESHOOTING.md            (531 lines)  - Diagnostics & recovery
│   │
│   ├── [Legacy/Vietnamese docs - unstructured]
│   │   ├── data_pipeline.md         (1812 lines)  - LARGEST file, pipeline arch
│   │   ├── data_context_overview.md   (673 lines)  - Sapo platform context (VN)
│   │   ├── dagster_dependencies.md    (175 lines)  - Dagster deps (VN)
│   │   ├── deployment_operation.md    (257 lines)  - Deployment ops (VN/EN mix)
│   │   ├── sapo_data_sources.md       (132 lines)  - Sapo sources (VN)
│   │   ├── incremental_strategy.md    (121 lines)  - Incremental sync (VN)
│   │   ├── pipeline_scheduling_strategy.md (65 lines)  - Scheduling (VN)
│   │   ├── transformation_architecture.md  (194 lines)  - Transformation arch
│   │   ├── setup_marketing_spend.md   (115 lines)  - Marketing spend setup (VN)
│   │   └── reports_and_metrics.md      (44 lines)  - Metrics index
│   │
│   ├── guides/
│   │   ├── dbt_vs_metabase_architecture.md   (66 lines)
│   │   └── targets_sheet_guide.md            (197 lines)
│   │
│   ├── plan/                          [OBSOLETE? - Implementation planning]
│   │   ├── implementation_plan.md     (96 lines)
│   │   ├── implementation-checklist.md (63 lines)
│   │   └── task.md                    (21 lines)
│   │
│   └── analytics-handbook/            [HUMAN + AI - BI knowledge base]
│       ├── README.md                 (175 lines)  - Handbook philosophy
│       ├── AGENTS.md                 (176 lines)  - AI agent rules for BI
│       ├── domains/                   [6 files - Business domain definitions]
│       │   ├── sales.md              (315 lines)
│       │   ├── customer.md           (205 lines)
│       │   ├── finance.md            (148 lines)
│       │   ├── product.md            (122 lines)
│       │   ├── logistics.md          (118 lines)
│       │   └── customer_support.md    (64 lines)
│       ├── playbooks/                 [15 files - Dashboard assembly specs]
│       │   ├── sales_*.md            (5 files, 32-87 lines each)
│       │   ├── customer_*.md         (3 files, 41-53 lines each)
│       │   ├── finance_*.md          (2 files, 32-49 lines each)
│       │   ├── logistics_*.md        (2 files, 33-47 lines each)
│       │   ├── product_*.md          (2 files, 32-48 lines each)
│       │   └── orders_*.md           (1 file, 79 lines)
│       ├── blueprints/                [7 files - Technical Metabase specs]
│       │   ├── sales_executive.md            (230 lines)
│       │   ├── sales_daily_operation.md      (347 lines)
│       │   ├── sales_yesterday_operation.md  (347 lines)
│       │   ├── customer_operational_dashboard.md (209 lines)
│       │   ├── customer_retention_dashboard.md   (175 lines)
│       │   ├── orders_today.md               (137 lines)
│       │   └── orders_yesterday.md           (137 lines)
│       └── guides/                    [6 files - Reference guides]
│           ├── channel_classification.md              (576 lines)
│           ├── channel_classification_implementation_prompt.md (49 lines)
│           ├── dashboard_design_patterns.md           (94 lines)
│           ├── metabase_concepts.md                   (121 lines)
│           ├── facebook_ads_integration.md            (119 lines)
│           └── facebook_messenger_integration.md      (75 lines)
│
├── ingestion/docs/                    [COMPONENT - Ingestion layer]
│   ├── README.md                     (149 lines)
│   ├── SOURCES.md                    (335 lines)
│   ├── CONFIGURATION.md             (218 lines)
│   ├── PIPELINES.md                  (340 lines)
│   ├── INCREMENTAL.md               (334 lines)
│   ├── DEPLOYMENT.md                (121 lines)
│   ├── cookie_management.md         (1733 lines)  - 2nd LARGEST
│   └── extract_sapo_orders.md       (1064 lines)  - 3rd LARGEST
│
├── transformation/                    [COMPONENT - Transformation layer]
│   ├── AGENTS.md                    (103 lines)  - dbt-specific AI rules
│   └── docs/
│       ├── README.md                (200 lines)
│       ├── MODELS.md                (382 lines)
│       ├── MATERIALIZATION.md       (403 lines)
│       ├── ARCHITECTURE_DETAIL.md   (190 lines)
│       ├── DEDUPLICATION.md         (295 lines)
│       ├── TESTING.md               (328 lines)
│       └── BUSINESS_LOGIC.md         (90 lines)
│
├── orchestration/docs/                [COMPONENT - Orchestration layer]
│   ├── README.md                    (214 lines)
│   ├── JOBS.md                      (305 lines)
│   ├── ASSETS.md                    (168 lines)
│   ├── SCHEDULES.md                 (336 lines)
│   └── RESOURCES.md                  (69 lines)
│
├── webhook_receiver/                  [COMPONENT - Webhook system]
│   ├── README.md                     (23 lines)
│   ├── docs/
│   │   ├── README.md               (211 lines)
│   │   ├── API.md                   (334 lines)
│   │   ├── SECURITY.md             (319 lines)
│   │   └── WEBHOOK_INGESTION_PRD.md  (59 lines)
│   ├── cloudflareD1/
│   │   ├── README.md                (92 lines)
│   │   └── docs/
│   │       ├── DEPLOYMENT.md        (213 lines)
│   │       └── PRD.md              (180 lines)
│   └── supabase_queue/
│       ├── README.md                 (88 lines)
│       └── docs/Supabase.md        (156 lines)
│
├── webhook_consumer/                  [COMPONENT - Webhook consumers]
│   ├── cloudflared1_consumer/README.md  (48 lines)
│   └── supabase_consumer/
│       ├── README.md                  (4 lines)
│       └── doc/
│           ├── PRD.md              (varies)
│           ├── ProjectSetup.md     (varies)
│           ├── PM2.md              (varies)
│           └── postgresql_setup_macos.md (varies)
│
└── plans/reports/                     [AUTO-GENERATED - AI review reports]
    ├── code-reviewer-260227-*.md      (7 files)
    └── research-260326-*.md           (2 files)
```

---

## 2. Content Classification

### 2.1 By Audience

| Audience | Files | Lines | % |
|----------|-------|-------|---|
| **Human (developers/ops)** | 50 | ~12,000 | 46% |
| **AI Agents** | 20 | ~2,500 | 10% |
| **Shared (human + AI)** | 46 | ~8,500 | 33% |
| **Auto-generated reports** | 9 | ~3,000 | 11% |

### 2.2 By Purpose

| Purpose | Count | Key files |
|---------|-------|-----------|
| **System Architecture** | 5 | ARCHITECTURE.md, DATA_FLOW.md, transformation_architecture.md, data_pipeline.md, ARCHITECTURE_DETAIL.md |
| **Component Reference** | 22 | ingestion/docs/*, transformation/docs/*, orchestration/docs/* |
| **Operations & Deployment** | 7 | DEPLOYMENT.md (x2), OPERATIONS.md, deployment_operation.md, TROUBLESHOOTING.md, MIGRATION.md |
| **BI / Analytics** | 35 | analytics-handbook/**, blueprints, STRATEGY.md |
| **AI Agent Instructions** | 14 | AGENTS.md (x3), CLAUDE.md, .claude/commands/*, .agents/** |
| **Domain Knowledge (Sapo)** | 8 | data_context_overview.md, sapo_data_sources.md, cookie_management.md, extract_sapo_orders.md |
| **Planning / Reports** | 12 | docs/plan/*, plans/reports/* |
| **Guides & How-To** | 8 | docs/guides/*, analytics-handbook/guides/* |
| **Project Entry Points** | 7 | README.md (x5), CONTRIBUTING.md, GLOSSARY.md |

### 2.3 By Language

| Language | Count | Notes |
|----------|-------|-------|
| English | ~80 | Structured docs, component references |
| Vietnamese | ~15 | Legacy design docs, Sapo context, some guides |
| Mixed EN/VN | ~5 | deployment_operation.md, some guides |
| N/A (code/template) | ~25 | Blueprints, templates, auto-generated |

---

## 3. Duplicate & Overlap Analysis

### 3.1 CRITICAL Duplicates (Same content, multiple locations)

#### A. Deployment Documentation (3 files, ~1,180 lines total)

| File | Lines | Content |
|------|-------|---------|
| `DEPLOYMENT.md` (root) | 463 | Windows Docker deployment |
| `docs/DEPLOYMENT.md` | 463 | DLT ops, Metabase deployment, serving layer |
| `docs/deployment_operation.md` | 257 | Overlaps heavily with docs/DEPLOYMENT.md (VN/EN) |

**Problem:** `docs/deployment_operation.md` duplicates content from `docs/DEPLOYMENT.md` in mixed Vietnamese/English. Root `DEPLOYMENT.md` covers Windows Docker setup specifically but overlaps with `docs/DEPLOYMENT.md` on Metabase deployment sections.

**Recommendation:** MERGE into a single `docs/DEPLOYMENT.md`. DELETE `docs/deployment_operation.md`. Keep root `DEPLOYMENT.md` only for Windows-specific quick start, or merge it into `docs/DEPLOYMENT.md` as a section.

#### B. Architecture Documentation (4 files, ~1,400 lines total)

| File | Lines | Overlapping Content |
|------|-------|-------------------|
| `docs/ARCHITECTURE.md` | 508 | 7-hop pipeline, all components, design principles |
| `docs/transformation_architecture.md` | 194 | OTP/OLAP pipelines, layer details, star schema ERD |
| `docs/data_pipeline.md` | 1812 | Lambda arch, OTP/OLAP, scheduling, transformation |
| `transformation/docs/ARCHITECTURE_DETAIL.md` | 190 | Entity definitions, dedup logic, layer details |

**Overlaps found:**
- **OTP vs OLAP pipeline** explained in 3 files (data_pipeline.md, transformation_architecture.md, ARCHITECTURE_DETAIL.md)
- **Star schema / Kimball ERD** diagrammed in 3 files
- **7-hop pipeline flow** described in 4 files
- **Design principles** repeated across ARCHITECTURE.md and data_pipeline.md

**Recommendation:**
- DELETE `docs/transformation_architecture.md` - content already in `transformation/docs/ARCHITECTURE_DETAIL.md`
- ARCHIVE `docs/data_pipeline.md` (1812 lines) - this is a legacy design doc superseded by the structured docs
- Let `docs/ARCHITECTURE.md` be the high-level overview, `transformation/docs/ARCHITECTURE_DETAIL.md` the deep-dive

#### C. Deduplication Strategy (4 files)

| File | Relevant Section |
|------|-----------------|
| `transformation/docs/DEDUPLICATION.md` | 295 lines - FULL reference |
| `transformation/docs/ARCHITECTURE_DETAIL.md` | ~50 lines - Repeated logic |
| `docs/ARCHITECTURE.md` | ~20 lines - Summary |
| `docs/data_pipeline.md` | ~80 lines - Detailed explanation |

**Recommendation:** Keep `transformation/docs/DEDUPLICATION.md` as the single source. Remove duplicate sections from other files, replace with cross-references.

#### D. Incremental Strategy (3 files)

| File | Lines | Focus |
|------|-------|-------|
| `docs/incremental_strategy.md` | 121 | Overall strategy (VN) |
| `ingestion/docs/INCREMENTAL.md` | 334 | Ingestion-specific |
| `transformation/docs/MATERIALIZATION.md` | 403 | Transformation-specific |

**Overlap:** Rolling snapshots concept explained 3 times. Zero-downtime serving architecture repeated.

**Recommendation:** MERGE `docs/incremental_strategy.md` into `AGENTS.md` (it's a design decision doc, not operational). Keep component-specific files for their respective details.

#### E. Sapo Data Sources (3 files)

| File | Lines | Focus |
|------|-------|-------|
| `docs/sapo_data_sources.md` | 132 | Source channel matrix (VN) |
| `docs/data_context_overview.md` | 673 | Full Sapo platform context (VN) |
| `ingestion/docs/SOURCES.md` | 335 | API endpoint reference |

**Overlap:** Channel matrix (Batch API, Webhooks, History Log) described in all 3 files.

**Recommendation:** MERGE `docs/sapo_data_sources.md` into `docs/data_context_overview.md` (both VN, same domain). Keep `ingestion/docs/SOURCES.md` as API-level reference.

### 3.2 Structural Duplicates (Same skill, different agent frameworks)

#### F. Metabase Automation Skill (3 parallel definitions)

| Location | Purpose | Agent Framework |
|----------|---------|----------------|
| `.skills/metabase-automation/SKILL.md` (231 lines) | Shared, agent-agnostic | Any |
| `.agents/skills/metabase-automation/SKILL.md` (44 lines) | Pointer to .skills/ | Antigravity |
| `.claude/commands/manage-metabase-resources.md` (52 lines) | Slash command | Claude Code |

**Plus workflow duplicates:**

| Location | Purpose | Agent Framework |
|----------|---------|----------------|
| `.agents/workflows/create_metabase_blueprint.md` | Workflow | Antigravity |
| `.claude/commands/create-metabase-blueprint.md` | Command | Claude Code |
| `.agents/workflows/deploy_metabase_blueprint.md` | Workflow | Antigravity |
| `.claude/commands/deploy-metabase-blueprint.md` | Command | Claude Code |

**Problem:** Each Metabase skill exists in 2-3 places with slightly different wording but identical intent. Changes must be synchronized manually.

**Recommendation:** Keep `.skills/` as the single source of truth. Make `.agents/` and `.claude/commands/` reference `.skills/` files (some already do this, like `.agents/skills/metabase-automation/SKILL.md`). Ensure all commands say "Read `.skills/.../SKILL.md` first."

#### G. Webhook System Documentation (Variant Confusion)

| Variant | Files | Status |
|---------|-------|--------|
| CloudflareD1 (receiver) | 3 files (README, DEPLOYMENT, PRD) | Active |
| Supabase Queue (receiver) | 2 files (README, Supabase.md) | Legacy? |
| CloudflareD1 Consumer | 1 file (README) | Active |
| Supabase Consumer | 4 files (README, PRD, ProjectSetup, PM2) | Legacy? |
| Shared webhook docs | 4 files (README, API, SECURITY, PRD) | Shared |

**Problem:** 14 files across 5 directories for the webhook system. No clear indicator of which variant is active vs deprecated. Supabase consumer has `postgresql_setup_macos.md` suggesting a different era of the project.

**Recommendation:** Add a `webhook_receiver/STATUS.md` that clearly states which variant is in production. Mark legacy files with `[DEPRECATED]` in their titles or move to an `archive/` folder.

---

## 4. Content Gap Analysis

### 4.1 Missing Documentation

| Gap | Impact | Suggestion |
|-----|--------|------------|
| No `docs/metabase-workspace/` blueprints | Blueprint deploy target dir empty | Either populate or update references |
| No top-level `ingestion/README.md` | Entry point missing | Symlink to `ingestion/docs/README.md` |
| No top-level `orchestration/README.md` | Entry point missing | Symlink to `orchestration/docs/README.md` |
| No top-level `webhook_consumer/README.md` | Entry point missing | Create overview of consumer variants |
| No `CHANGELOG.md` | No release history | Consider adding |
| No diagram/visual index | Hard to see big picture | Add to `docs/README.md` |

### 4.2 Stale/Obsolete Content

| File | Evidence | Action |
|------|----------|--------|
| `docs/plan/task.md` (21 lines) | One-time task checklist, likely completed | ARCHIVE or DELETE |
| `docs/plan/implementation_plan.md` | References "Phase 4" of dashboard impl | ARCHIVE if completed |
| `docs/plan/implementation-checklist.md` | Metabase chart checklist | ARCHIVE if completed |
| `docs/reports_and_metrics.md` (44 lines) | Thin index, no real content | MERGE into analytics-handbook or DELETE |
| `plans/reports/code-reviewer-*.md` (7 files) | Auto-generated one-time code reviews | ARCHIVE or set auto-cleanup |
| `webhook_consumer/supabase_consumer/doc/postgresql_setup_macos.md` | macOS Postgres setup for legacy variant | ARCHIVE if Supabase variant deprecated |

---

## 5. Discoverability Problems

### 5.1 For Humans

| Problem | Example | Impact |
|---------|---------|--------|
| **No topic index** | "Where is deduplication documented?" requires searching 4 files | Time wasted searching |
| **Mixed languages** | Vietnamese design docs alongside English references | Confusing for English-only readers |
| **Flat docs/ directory** | 18 files at `docs/` root with no grouping | Overwhelming to browse |
| **Naming inconsistency** | `ARCHITECTURE.md` (UPPER) vs `data_pipeline.md` (lower) vs `deployment_operation.md` (lower) | Hard to predict file names |
| **No "last updated" dates** | Can't tell which docs are current | Risk of following stale advice |

### 5.2 For AI Agents

| Problem | Example | Impact |
|---------|---------|--------|
| **AGENTS.md is 444 lines** | Agent loads entire file every time | Context window bloat |
| **No machine-readable metadata** | Files lack frontmatter (type, audience, status) | Can't filter by relevance |
| **Redundant reads required** | Same concept in 3+ files | Wasted tokens reading duplicates |
| **Blueprint target dir empty** | `docs/metabase-workspace/` referenced but doesn't exist | Deploy scripts may fail |
| **No explicit deprecation markers** | Legacy docs look identical to current | Agent may follow outdated guidance |

---

## 6. Reorganization Proposal

### 6.1 Principles

1. **Single Source of Truth** - Each concept lives in exactly one file
2. **Progressive Disclosure** - Entry point → Overview → Deep-dive
3. **Audience Separation** - Human docs vs AI instructions in clear locations
4. **Component Locality** - Component docs stay with their code
5. **Discoverability** - Consistent naming, topic index, status markers

### 6.2 Proposed Structure

```
data-integration/
│
├── README.md                          # Project overview (keep as-is)
├── CLAUDE.md                          # Claude Code config (keep as-is)
├── AGENTS.md                          # Global AI rules (SLIM DOWN - see 6.3)
│
├── docs/
│   ├── README.md                      # Documentation index with topic map
│   │
│   ├── architecture/                  # [NEW GROUP] System design
│   │   ├── overview.md                # ← from ARCHITECTURE.md (high-level only)
│   │   ├── data-flow.md              # ← from DATA_FLOW.md
│   │   └── data-dictionary.md        # ← from DATA_DICTIONARY.md
│   │
│   ├── operations/                    # [NEW GROUP] Running the system
│   │   ├── deployment.md             # ← MERGE root DEPLOYMENT.md + docs/DEPLOYMENT.md + deployment_operation.md
│   │   ├── operations.md             # ← from OPERATIONS.md
│   │   ├── troubleshooting.md        # ← from TROUBLESHOOTING.md
│   │   └── migration.md              # ← from root MIGRATION.md
│   │
│   ├── development/                   # [NEW GROUP] Contributing
│   │   ├── contributing.md           # ← from CONTRIBUTING.md
│   │   └── glossary.md              # ← from GLOSSARY.md
│   │
│   ├── context/                       # [NEW GROUP] Domain & platform knowledge
│   │   ├── sapo-platform.md          # ← MERGE data_context_overview.md + sapo_data_sources.md
│   │   ├── channel-classification.md # ← from analytics-handbook/guides/channel_classification.md
│   │   └── marketing-spend-setup.md  # ← from setup_marketing_spend.md
│   │
│   ├── guides/                        # [KEEP] How-to guides
│   │   ├── dbt-vs-metabase.md
│   │   ├── targets-sheet.md
│   │   ├── facebook-ads.md           # ← from analytics-handbook/guides/
│   │   └── facebook-messenger.md     # ← from analytics-handbook/guides/
│   │
│   ├── analytics-handbook/            # [KEEP] BI knowledge base
│   │   ├── README.md
│   │   ├── AGENTS.md
│   │   ├── domains/                   # [KEEP as-is - well structured]
│   │   ├── playbooks/                 # [KEEP as-is - well structured]
│   │   ├── blueprints/                # [KEEP as-is - well structured]
│   │   └── guides/
│   │       ├── dashboard-design-patterns.md
│   │       └── metabase-concepts.md
│   │
│   └── archive/                       # [NEW] Historical/completed docs
│       ├── data_pipeline.md           # ← Legacy 1812-line design doc
│       ├── incremental_strategy.md    # ← Superseded by component docs
│       ├── pipeline_scheduling_strategy.md
│       ├── transformation_architecture.md  # ← Superseded by transformation/docs/
│       └── plan/                      # ← Completed implementation plans
│           ├── implementation_plan.md
│           ├── implementation-checklist.md
│           └── task.md
│
├── ingestion/
│   ├── README.md                      # [NEW] Symlink → docs/README.md
│   └── docs/                          # [KEEP as-is - well structured]
│
├── transformation/
│   ├── AGENTS.md                      # [KEEP]
│   └── docs/                          # [KEEP as-is - well structured]
│
├── orchestration/
│   ├── README.md                      # [NEW] Symlink → docs/README.md
│   └── docs/                          # [KEEP as-is - well structured]
│
├── webhook_receiver/
│   ├── README.md                      # [UPDATE] Add variant status table
│   ├── docs/                          # [KEEP] Shared webhook docs
│   ├── cloudflareD1/                  # [KEEP] Mark as ACTIVE
│   └── supabase_queue/               # [MARK DEPRECATED]
│
├── webhook_consumer/
│   ├── README.md                      # [NEW] Overview of consumer variants
│   ├── cloudflared1_consumer/         # [KEEP] Mark as ACTIVE
│   └── supabase_consumer/            # [MARK DEPRECATED]
│
├── .skills/metabase-automation/       # [KEEP] Single source of truth for skills
│   ├── SKILL.md
│   ├── STRATEGY.md
│   └── templates/
│
├── .agents/                           # [SIMPLIFY] Point to .skills/
│   ├── skills/                        # Each SKILL.md just references .skills/
│   └── workflows/                     # Keep as Antigravity-specific
│
├── .claude/commands/                  # [KEEP] Each command references .skills/
│
└── plans/reports/                     # [ADD auto-cleanup policy]
```

### 6.3 AGENTS.md Refactoring

The root `AGENTS.md` (444 lines) tries to serve as both AI instructions AND architecture reference. Split into:

| Content | Move to | Rationale |
|---------|---------|-----------|
| Multi-project structure | Keep in AGENTS.md | AI needs this |
| Operation protocol | Keep in AGENTS.md | AI needs this |
| Sapo data sources detail | `docs/context/sapo-platform.md` | Reference, not instruction |
| 4-layer transformation detail | `transformation/docs/ARCHITECTURE_DETAIL.md` | Already exists there |
| Deduplication logic detail | `transformation/docs/DEDUPLICATION.md` | Already exists there |
| Dual DuckDB strategy | Keep in AGENTS.md (short) | Critical constraint |
| Dagster concurrency | Keep in AGENTS.md (short) | Critical constraint |
| Proven solutions | Keep in AGENTS.md | Lessons learned for AI |
| Analytics-as-Code | Keep in AGENTS.md (short) | Workflow reference |

**Target:** Reduce AGENTS.md from 444 → ~200 lines by moving detailed reference content out and keeping only rules, constraints, and pointers.

---

## 7. Specific Action Items

### Priority 1: Eliminate Duplicates (saves ~2,500 lines)

| # | Action | Files Affected | Lines Saved |
|---|--------|---------------|-------------|
| 1 | DELETE `docs/deployment_operation.md` | 1 file | ~257 |
| 2 | DELETE `docs/transformation_architecture.md` | 1 file | ~194 |
| 3 | MERGE `docs/sapo_data_sources.md` → `docs/data_context_overview.md` | 2→1 file | ~132 |
| 4 | ARCHIVE `docs/data_pipeline.md` → `docs/archive/` | 1 file | ~1812 (hidden) |
| 5 | ARCHIVE `docs/plan/*` → `docs/archive/plan/` | 3 files | ~180 (hidden) |
| 6 | MERGE root `DEPLOYMENT.md` + `docs/DEPLOYMENT.md` | 2→1 file | ~200 |

### Priority 2: Improve Discoverability

| # | Action | Benefit |
|---|--------|---------|
| 7 | Create `docs/README.md` topic index table | Find any topic in one lookup |
| 8 | Add frontmatter to all docs: `status: active|deprecated|archive` | AI can filter relevance |
| 9 | Rename inconsistent files to kebab-case | Predictable file names |
| 10 | Group `docs/` root files into subdirectories | Reduce cognitive load |
| 11 | Add variant status to `webhook_receiver/README.md` | Clear active vs legacy |

### Priority 3: Optimize for AI Agents

| # | Action | Benefit |
|---|--------|---------|
| 12 | Slim AGENTS.md to ~200 lines with pointers | Less context bloat |
| 13 | Ensure .claude/commands/ reference .skills/ (not duplicate content) | Single source of truth |
| 14 | Add `docs/metabase-workspace/.gitkeep` | Referenced dir exists |
| 15 | Set auto-cleanup for `plans/reports/` (>30 days) | Prevent report accumulation |

---

## 8. Summary

### Current State

| Metric | Value |
|--------|-------|
| Total .md files | 125 |
| Total lines | ~26,000 |
| Duplicate content | ~2,500 lines (10%) |
| Files with no clear owner/audience | ~15 |
| Mixed-language files | ~5 |
| Likely obsolete files | ~10 |
| Empty referenced directories | 1 (`docs/metabase-workspace/`) |

### Key Strengths
- **Component-local docs** (ingestion/docs/, transformation/docs/, orchestration/docs/) are well-structured
- **Analytics handbook** (domains/playbooks/blueprints) has a clear, scalable architecture
- **AI agent instructions** (AGENTS.md hierarchy) provide useful context
- **Skills system** (.skills/) provides reusable, agent-agnostic tooling

### Key Weaknesses
- **docs/ root is a dumping ground** - 18 files at root level, mixed naming, mixed languages
- **Deployment documented 3 times** in overlapping files
- **Architecture scattered** across 4+ files with repeated diagrams
- **Webhook system** has unclear variant status (active vs deprecated)
- **AGENTS.md too large** (444 lines) - mixes instructions with reference material
- **No topic index** - discoverability relies on knowing file names
- **No deprecation markers** - legacy docs indistinguishable from current

### After Proposed Changes

| Metric | Before | After |
|--------|--------|-------|
| Root docs/ files | 18 | 1 (README.md) |
| Duplicate lines | ~2,500 | ~0 |
| AGENTS.md lines | 444 | ~200 |
| Discoverable via index | No | Yes |
| Clear active/deprecated status | No | Yes |
| Empty referenced dirs | 1 | 0 |

---
---

# Part 2: Sub-Project Documentation Analysis & Linking Strategy

## 9. Sub-Project Inventory

The monorepo contains **6 sub-projects**, each with its own codebase and documentation:

| # | Sub-project | Path | Doc Location | Doc Files | Doc Lines | Has AGENTS.md? |
|---|-------------|------|-------------|-----------|-----------|----------------|
| 1 | **Ingestion** | `ingestion/` | `ingestion/docs/` | 8 | ~4,300 | No |
| 2 | **Transformation** | `transformation/` | `transformation/docs/` | 7 + AGENTS.md | ~2,090 | Yes (103 lines) |
| 3 | **Orchestration** | `orchestration/` | `orchestration/docs/` | 5 | ~1,090 | No |
| 4 | **Webhook Receiver** | `webhook_receiver/` | `webhook_receiver/docs/` + variants | 10 | ~1,750 | No |
| 5 | **Webhook Consumer** | `webhook_consumer/` | scattered across variants | 6 | ~500 | No |
| 6 | **Analytics Handbook** | `docs/analytics-handbook/` | self-contained | 35 | ~4,500 | Yes (176 lines) |

**Plus top-level docs:** `docs/` root contains 18 files (~6,200 lines) that SHOULD be the high-level layer but currently mix high-level overviews with detailed implementation content.

---

## 10. Topic-by-Topic: Where Content Lives (Top-Level vs Sub-Project)

### Legend
- **TOP** = `docs/` or root-level files
- **SUB** = sub-project `*/docs/` files
- **AGENTS** = `AGENTS.md` files
- Overlap = same content explained in multiple places

---

### 10.1 INGESTION

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Sapo API endpoints** | `docs/sapo_data_sources.md` (132L, VN) | `ingestion/docs/SOURCES.md` (335L, EN) | **HIGH** - same channel matrix, SUB is more complete |
| **Sapo platform context** | `docs/data_context_overview.md` (673L, VN) | `ingestion/docs/SOURCES.md` (335L) | **MEDIUM** - TOP has business context, SUB has API details |
| **Incremental loading** | `docs/incremental_strategy.md` (121L, VN) | `ingestion/docs/INCREMENTAL.md` (334L, EN) | **HIGH** - both explain cursors, watermarks; SUB is authoritative |
| **Pipeline definitions** | `docs/DATA_FLOW.md` Hop 1-2 (~100L) | `ingestion/docs/PIPELINES.md` (340L) | **MEDIUM** - TOP summarizes, SUB details each pipeline |
| **Pipeline architecture** | `docs/data_pipeline.md` (~300L relevant) | `ingestion/docs/README.md` (149L) | **MEDIUM** - TOP has legacy overview |
| **Configuration** | `docs/DEPLOYMENT.md` env vars section | `ingestion/docs/CONFIGURATION.md` (218L) | **LOW** - TOP mentions, SUB details |
| **Cookie management** | (none) | `ingestion/docs/cookie_management.md` (1733L) | None - unique to SUB |
| **Order extraction** | (none) | `ingestion/docs/extract_sapo_orders.md` (1064L) | None - unique to SUB |
| **Deployment** | `docs/DEPLOYMENT.md` section | `ingestion/docs/DEPLOYMENT.md` (121L) | **LOW** - different scope |

**Diagnosis:** The ingestion sub-project has excellent self-contained docs. The problem is that TOP-level docs (`sapo_data_sources.md`, `incremental_strategy.md`) duplicate what SUB already covers better, in a different language.

**Linking strategy:**
```
docs/ARCHITECTURE.md          → "See ingestion/docs/README.md for component details"
docs/DATA_FLOW.md (Hop 1-2)   → "See ingestion/docs/PIPELINES.md for pipeline specs"
docs/sapo_data_sources.md     → ABSORB into docs/data_context_overview.md (business context only)
docs/incremental_strategy.md  → DELETE (ingestion/docs/INCREMENTAL.md is authoritative)
AGENTS.md (Sapo sources)      → Keep summary, link to ingestion/docs/SOURCES.md
```

---

### 10.2 TRANSFORMATION

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Layer architecture** | `docs/transformation_architecture.md` (194L) | `transformation/docs/ARCHITECTURE_DETAIL.md` (190L) | **CRITICAL** - nearly identical content |
| **OTP/OLAP pipelines** | `docs/data_pipeline.md` (~200L) | `transformation/docs/ARCHITECTURE_DETAIL.md` | **HIGH** - same Lambda arch explanation |
| **Deduplication** | `docs/ARCHITECTURE.md` (~20L), `docs/data_pipeline.md` (~80L) | `transformation/docs/DEDUPLICATION.md` (295L) | **HIGH** - SUB is authoritative, TOP repeats |
| **Star schema / Kimball** | `docs/ARCHITECTURE.md` (~15L), `docs/transformation_architecture.md` (~40L) | `transformation/docs/ARCHITECTURE_DETAIL.md` (~30L), `transformation/docs/MODELS.md` | **HIGH** - ERD in 3 places |
| **Materialization** | `docs/incremental_strategy.md` (rolling snapshots) | `transformation/docs/MATERIALIZATION.md` (403L) | **MEDIUM** - SUB is authoritative |
| **Model catalog** | (none) | `transformation/docs/MODELS.md` (382L) | None - unique to SUB |
| **Testing** | (none) | `transformation/docs/TESTING.md` (328L) | None - unique to SUB |
| **Business logic** | (none) | `transformation/docs/BUSINESS_LOGIC.md` (90L) | None - unique to SUB |
| **dbt rules for AI** | `AGENTS.md` (~100L of transformation content) | `transformation/AGENTS.md` (103L) | **MEDIUM** - ROOT AGENTS has detailed transformation rules that should be in SUB |

**Diagnosis:** Worst overlap in the system. `docs/transformation_architecture.md` is a near-clone of `transformation/docs/ARCHITECTURE_DETAIL.md`. The legacy `docs/data_pipeline.md` (1812 lines) has huge sections that are now better covered by the sub-project's structured docs.

**Linking strategy:**
```
docs/ARCHITECTURE.md           → Keep 1-paragraph summary, "See transformation/docs/ for details"
docs/transformation_architecture.md → DELETE (content is in transformation/docs/ARCHITECTURE_DETAIL.md)
docs/data_pipeline.md          → ARCHIVE (legacy, superseded by structured sub-project docs)
AGENTS.md (4-layer arch)       → Reduce to rules only, "See transformation/docs/ARCHITECTURE_DETAIL.md"
AGENTS.md (dedup logic)        → Reduce to constraint, "See transformation/docs/DEDUPLICATION.md"
```

---

### 10.3 ORCHESTRATION

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Job definitions** | `docs/ARCHITECTURE.md` (~30L), `docs/OPERATIONS.md` (~50L), `docs/deployment_operation.md` (~40L) | `orchestration/docs/JOBS.md` (305L) | **HIGH** - job names/descriptions in 4 places |
| **Schedules** | `docs/pipeline_scheduling_strategy.md` (65L, VN), `docs/OPERATIONS.md` (~30L) | `orchestration/docs/SCHEDULES.md` (336L) | **HIGH** - SUB is authoritative |
| **Asset dependencies** | `docs/dagster_dependencies.md` (175L, VN) | `orchestration/docs/ASSETS.md` (168L) | **HIGH** - both explain DLT→dbt dependency resolution |
| **Dagster concurrency** | `AGENTS.md` (~30L) | (mentioned in orchestration/docs/README.md) | **MEDIUM** - AGENTS has critical constraint |
| **Resources/Config** | (none) | `orchestration/docs/RESOURCES.md` (69L) | None - unique to SUB |
| **Race condition fix** | `docs/dagster_dependencies.md` (VN) | `orchestration/docs/SCHEDULES.md` (architecture section) | **HIGH** - same problem/solution in both |

**Diagnosis:** TOP-level has 3 Vietnamese design docs (`dagster_dependencies.md`, `pipeline_scheduling_strategy.md`, plus sections in `deployment_operation.md`) that are now superseded by the well-structured English docs in `orchestration/docs/`.

**Linking strategy:**
```
docs/ARCHITECTURE.md           → Keep 1-paragraph summary, "See orchestration/docs/README.md"
docs/OPERATIONS.md             → Keep schedule table, "See orchestration/docs/JOBS.md for details"
docs/dagster_dependencies.md   → ARCHIVE (orchestration/docs/ASSETS.md covers this)
docs/pipeline_scheduling_strategy.md → ARCHIVE (orchestration/docs/SCHEDULES.md covers this)
docs/deployment_operation.md   → DELETE (content split across docs/OPERATIONS.md + sub-project docs)
AGENTS.md (Dagster concurrency) → Keep as constraint rule, link to orchestration/docs/
```

---

### 10.4 WEBHOOK RECEIVER + CONSUMER

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Webhook architecture** | `docs/ARCHITECTURE.md` (~40L), `docs/DATA_FLOW.md` (~50L) | `webhook_receiver/docs/README.md` (211L) | **MEDIUM** - TOP summarizes, SUB details |
| **API specification** | (none) | `webhook_receiver/docs/API.md` (334L) | None - unique to SUB |
| **Security** | (none) | `webhook_receiver/docs/SECURITY.md` (319L) | None - unique to SUB |
| **PRD / Requirements** | (none) | `webhook_receiver/docs/WEBHOOK_INGESTION_PRD.md` (59L) | None - but DUPLICATED within sub-project variants |
| **CloudflareD1 impl** | (none) | `webhook_receiver/cloudflareD1/` (3 files, ~485L) | None |
| **Supabase impl** | (none) | `webhook_receiver/supabase_queue/` (2 files, ~244L) | None |
| **Consumer workflow** | (none) | `webhook_consumer/cloudflared1_consumer/README.md` (48L) | None |
| **Supabase consumer** | (none) | `webhook_consumer/supabase_consumer/` (5 files, ~500L) | None |

**Internal sub-project overlap:**

| Overlap | File A | File B |
|---------|--------|--------|
| PRD requirements | `webhook_receiver/docs/WEBHOOK_INGESTION_PRD.md` | `webhook_receiver/cloudflareD1/docs/PRD.md` |
| Architecture overview | `webhook_receiver/docs/README.md` | `webhook_receiver/cloudflareD1/README.md` |
| Consumer PRD | `webhook_consumer/supabase_consumer/doc/PRD.md` | `webhook_receiver/docs/WEBHOOK_INGESTION_PRD.md` |

**Diagnosis:** Webhook docs have minimal overlap with TOP-level (good!). But internally they have variant confusion - two implementation paths (CloudflareD1 vs Supabase) each with their own README, PRD, and deployment guide, with no status indicator.

**Linking strategy:**
```
docs/ARCHITECTURE.md           → Keep 1-paragraph, "See webhook_receiver/docs/README.md"
docs/DATA_FLOW.md              → Keep webhook channel summary, link to sub-project
webhook_receiver/README.md     → UPDATE: Add status table (CloudflareD1=ACTIVE, Supabase=DEPRECATED)
webhook_receiver/docs/         → Shared docs (API, Security) stay here
webhook_receiver/supabase_queue/ → Mark [DEPRECATED] in README header
webhook_consumer/supabase_consumer/ → Mark [DEPRECATED] in README header
```

---

### 10.5 ANALYTICS HANDBOOK

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Metrics definitions** | `docs/reports_and_metrics.md` (44L) | `docs/analytics-handbook/domains/*.md` (6 files, ~970L) | **LOW** - TOP is thin index, SUB is authoritative |
| **Dashboard design** | (none) | `docs/analytics-handbook/guides/dashboard_design_patterns.md` (94L) | None |
| **Metabase concepts** | (none) | `docs/analytics-handbook/guides/metabase_concepts.md` (121L) | None |
| **Channel classification** | (none) | `docs/analytics-handbook/guides/channel_classification.md` (576L) | None |
| **Blueprints** | (none) | `docs/analytics-handbook/blueprints/` (7 files, ~1,580L) | None |
| **Playbooks** | (none) | `docs/analytics-handbook/playbooks/` (15 files, ~770L) | None |

**Diagnosis:** Analytics handbook is the best-organized sub-project. Clean separation (domains → playbooks → blueprints), own AGENTS.md, minimal overlap with TOP. The only issue is `docs/reports_and_metrics.md` which is a 44-line orphan index that should point here.

**Linking strategy:**
```
docs/reports_and_metrics.md    → DELETE (replace with link in docs/README.md → analytics-handbook)
docs/ARCHITECTURE.md           → "See docs/analytics-handbook/ for BI layer documentation"
```

---

### 10.6 METABASE AUTOMATION (Skills)

| Topic | TOP-level file(s) | SUB-project file(s) | Overlap? |
|-------|-------------------|---------------------|----------|
| **Skill definition** | `CLAUDE.md` (commands table) | `.skills/metabase-automation/SKILL.md` (231L) | **LOW** - CLAUDE.md is index |
| **Strategy** | (none) | `.skills/metabase-automation/STRATEGY.md` (48L) | None |
| **Agent wrappers** | `.agents/skills/metabase-automation/SKILL.md` (44L pointer) | `.skills/metabase-automation/SKILL.md` (231L) | **STRUCTURAL** - wrapper → source |
| **Claude commands** | `.claude/commands/*.md` (5 files) | `.agents/workflows/*.md` (3 files) | **STRUCTURAL** - parallel definitions |

**Diagnosis:** The `.skills/` → `.agents/` → `.claude/commands/` chain is intentional (shared source → framework adapters). But the `.agents/workflows/` and `.claude/commands/` files contain overlapping step-by-step instructions instead of referencing the shared source.

---

## 11. The Overlap Matrix (Heatmap)

Content duplication intensity between TOP-level `docs/` files and sub-project docs:

```
                    ┌─────────┬──────────┬──────────┬───────────┬──────────┬───────────┐
                    │Ingestion│Transform.│Orchestr. │Webhook Rx │Webhook Cx│Analytics  │
┌───────────────────┼─────────┼──────────┼──────────┼───────────┼──────────┼───────────┤
│ARCHITECTURE.md    │  ██░░   │  ███░    │  ██░░    │  ██░░     │  ░░░░    │  █░░░     │
│DATA_FLOW.md       │  ██░░   │  ██░░    │  █░░░    │  ██░░     │  ░░░░    │  ░░░░     │
│data_pipeline.md   │  ██░░   │  ████    │  ██░░    │  █░░░     │  ░░░░    │  ░░░░     │
│transform_arch.md  │  ░░░░   │  ████    │  ░░░░    │  ░░░░     │  ░░░░    │  ░░░░     │
│incremental_str.md │  ████   │  ███░    │  ░░░░    │  ░░░░     │  ░░░░    │  ░░░░     │
│sapo_data_src.md   │  ████   │  ░░░░    │  ░░░░    │  ░░░░     │  ░░░░    │  ░░░░     │
│data_context.md    │  ███░   │  ░░░░    │  ░░░░    │  ░░░░     │  ░░░░    │  ░░░░     │
│dagster_deps.md    │  ░░░░   │  ░░░░    │  ████    │  ░░░░     │  ░░░░    │  ░░░░     │
│pipeline_sched.md  │  ░░░░   │  ░░░░    │  ████    │  ░░░░     │  ░░░░    │  ░░░░     │
│deploy_oper.md     │  █░░░   │  █░░░    │  ██░░    │  ░░░░     │  ░░░░    │  ░░░░     │
│DEPLOYMENT.md      │  █░░░   │  █░░░    │  █░░░    │  █░░░     │  ░░░░    │  ░░░░     │
│OPERATIONS.md      │  █░░░   │  ░░░░    │  ███░    │  ░░░░     │  ░░░░    │  ░░░░     │
│reports_metrics.md │  ░░░░   │  ░░░░    │  ░░░░    │  ░░░░     │  ░░░░    │  ██░░     │
│AGENTS.md (root)   │  ██░░   │  ███░    │  ██░░    │  █░░░     │  ░░░░    │  █░░░     │
└───────────────────┴─────────┴──────────┴──────────┴───────────┴──────────┴───────────┘
Legend: ░ = no overlap, █ = low, ██ = medium, ███ = high, ████ = critical (near-duplicate)
```

---

## 12. Root Cause: Why Overlaps Exist

The documentation evolved in **3 phases**, each leaving artifacts:

### Phase 1: Design Documents (Vietnamese)
**Files:** `data_pipeline.md`, `data_context_overview.md`, `sapo_data_sources.md`, `incremental_strategy.md`, `pipeline_scheduling_strategy.md`, `dagster_dependencies.md`

These were **design-time documents** written before implementation. They describe the intended architecture in Vietnamese, often as narratives with rationale ("why we chose X over Y"). They were the **first and only documentation** at the time.

### Phase 2: Structured English Documentation
**Files:** `docs/ARCHITECTURE.md`, `docs/DATA_FLOW.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, plus all sub-project `*/docs/*.md`

As the system matured, comprehensive English documentation was written for each component. These are well-structured, follow conventions (README + topic files), and are the **current source of truth**. But the Phase 1 docs were never removed.

### Phase 3: AI Agent Layer
**Files:** `AGENTS.md`, `CLAUDE.md`, `transformation/AGENTS.md`, `analytics-handbook/AGENTS.md`, `.skills/`, `.agents/`, `.claude/commands/`

AI-agent instructions were added on top, often **re-summarizing** content from both Phase 1 and Phase 2 docs to provide context. This created a third copy of key concepts (e.g., deduplication logic, 4-layer architecture).

**Result:** The same concepts (deduplication, incremental loading, pipeline architecture, scheduling, etc.) exist in up to 3 forms:
1. Vietnamese design narrative (Phase 1)
2. English reference docs (Phase 2)
3. AI agent context summaries (Phase 3)

---

## 13. The Linking Architecture: High-Level Overview ↔ Sub-Project Details

### 13.1 Design Principle: "Zoom In / Zoom Out"

```
┌──────────────────────────────────────────────────────────────┐
│  LEVEL 0: Entry Points                                        │
│  README.md, CLAUDE.md                                         │
│  "What is this project? How do I start?"                      │
├──────────────────────────────────────────────────────────────┤
│  LEVEL 1: System Overview (docs/)                             │
│  ARCHITECTURE.md, DATA_FLOW.md, DATA_DICTIONARY.md            │
│  "How does the whole system work?"                            │
│  Contains: 1-paragraph per component + link to sub-project    │
├──────────────────────────────────────────────────────────────┤
│  LEVEL 2: Cross-Cutting Concerns (docs/)                      │
│  OPERATIONS.md, DEPLOYMENT.md, TROUBLESHOOTING.md,            │
│  CONTRIBUTING.md, GLOSSARY.md                                 │
│  "How do I operate/deploy/debug the WHOLE system?"            │
│  Contains: Component sections that LINK to sub-project detail │
├──────────────────────────────────────────────────────────────┤
│  LEVEL 3: Component Deep-Dives (sub-project/docs/)            │
│  ingestion/docs/, transformation/docs/, orchestration/docs/,  │
│  webhook_receiver/docs/, analytics-handbook/                  │
│  "How does THIS component work in detail?"                    │
│  Contains: Everything specific to the component               │
├──────────────────────────────────────────────────────────────┤
│  LEVEL 4: AI Agent Instructions                               │
│  AGENTS.md (root), transformation/AGENTS.md,                  │
│  analytics-handbook/AGENTS.md                                 │
│  "What rules and constraints must AI follow?"                 │
│  Contains: Rules, constraints, gotchas + LINKS to detail      │
└──────────────────────────────────────────────────────────────┘
```

### 13.2 The Rule

> **TOP-level docs contain WHAT and WHERE. Sub-project docs contain HOW and WHY.**

| Aspect | TOP-level (`docs/`) | Sub-project (`*/docs/`) |
|--------|--------------------|-----------------------|
| Scope | Entire system | Single component |
| Depth | 1-paragraph summaries | Full implementation detail |
| Links | Points DOWN to sub-projects | Points UP to system context |
| Audience | New developers, ops, AI agents | Component developers |
| Updates | Rarely (architecture changes) | Frequently (implementation changes) |
| Language | English only | Any (but prefer English) |

---

## 14. Concrete File Disposition Plan

### 14.1 Files to DELETE (content fully superseded by sub-project docs)

| File | Lines | Superseded by | Rationale |
|------|-------|---------------|-----------|
| `docs/transformation_architecture.md` | 194 | `transformation/docs/ARCHITECTURE_DETAIL.md` | Near-identical content |
| `docs/deployment_operation.md` | 257 | `docs/OPERATIONS.md` + sub-project deployment docs | Bilingual duplicate |
| `docs/reports_and_metrics.md` | 44 | `docs/analytics-handbook/domains/` | Thin index, domains are authoritative |

### 14.2 Files to ARCHIVE (legacy design docs, valuable history but no longer operational)

| File | Lines | Why archive (not delete) |
|------|-------|------------------------|
| `docs/data_pipeline.md` | 1812 | Original design narrative, has historical rationale |
| `docs/incremental_strategy.md` | 121 | Design decisions captured; `ingestion/docs/INCREMENTAL.md` is now authoritative |
| `docs/pipeline_scheduling_strategy.md` | 65 | Design decisions; `orchestration/docs/SCHEDULES.md` is authoritative |
| `docs/dagster_dependencies.md` | 175 | Race condition analysis; `orchestration/docs/ASSETS.md` + `SCHEDULES.md` cover this |
| `docs/plan/implementation_plan.md` | 96 | Completed one-time plan |
| `docs/plan/implementation-checklist.md` | 63 | Completed checklist |
| `docs/plan/task.md` | 21 | Completed task list |

### 14.3 Files to MERGE

| Source file | Merge into | Action |
|------------|-----------|--------|
| `docs/sapo_data_sources.md` (132L) | `docs/data_context_overview.md` | Absorb channel matrix, delete source |
| `DEPLOYMENT.md` (root, 122L) | `docs/DEPLOYMENT.md` | Add as "Quick Start (Docker)" section |

### 14.4 Files to REFACTOR (reduce to summary + links)

#### `docs/ARCHITECTURE.md` (508 lines → ~300 lines)

Current state: Contains full details for each component (ingestion, transformation, orchestration, webhook, serving).

Proposed change: Each component section becomes a **summary paragraph + link**:

```markdown
## 2. Transformation Layer
dbt + DuckDB transforms raw Parquet into a 4-layer model
(src_ → stg_ → std_ → marts) using Kimball star schema.
Key features: 2-level deduplication, rolling snapshots, zero-downtime serving.

→ **[Full documentation](../transformation/docs/README.md)** |
  [Architecture](../transformation/docs/ARCHITECTURE_DETAIL.md) |
  [Models](../transformation/docs/MODELS.md) |
  [Deduplication](../transformation/docs/DEDUPLICATION.md)
```

#### `docs/DATA_FLOW.md` (503 lines → ~300 lines)

Current state: Each hop has full implementation detail.

Proposed change: Each hop becomes a **flow description + link to owning sub-project**:

```markdown
### Hop 1-2: Ingestion
Three channels (Batch API, Webhooks, History Log) extract data from Sapo
and write to partitioned Parquet files.

→ **[Ingestion docs](../ingestion/docs/README.md)** |
  [Pipelines](../ingestion/docs/PIPELINES.md) |
  [Incremental Strategy](../ingestion/docs/INCREMENTAL.md)
```

#### `docs/OPERATIONS.md` (413 lines → ~250 lines)

Current state: Contains Dagster job tables, schedule details, manual commands.

Proposed change: Keep daily health checks and monitoring. Replace job/schedule tables with links:

```markdown
### Job Schedules
→ **[Full schedule reference](../orchestration/docs/SCHEDULES.md)**
→ **[Job definitions](../orchestration/docs/JOBS.md)**
```

#### `AGENTS.md` (root, 444 lines → ~200 lines)

Current state: Mixes AI rules with architecture reference content.

Proposed change: Keep rules/constraints, replace detailed explanations with pointers:

```markdown
## Transformation Architecture
4-layer model: src_ → stg_ → std_ → marts.
→ See transformation/docs/ARCHITECTURE_DETAIL.md for layer details
→ See transformation/docs/DEDUPLICATION.md for 2-level dedup logic

**CRITICAL CONSTRAINTS (keep inline):**
- ALWAYS use `location="{{ get_rolling_location() }}"` for marts
- Never `SELECT *` from Parquet (OOM risk)
- src_ and stg_ must be VIEWS, not tables
```

### 14.5 Sub-Project Files to ADD/UPDATE

| Sub-project | Action | Detail |
|------------|--------|--------|
| `ingestion/` | ADD `README.md` at root | Symlink or 10-line pointer to `ingestion/docs/README.md` |
| `orchestration/` | ADD `README.md` at root | Symlink or 10-line pointer to `orchestration/docs/README.md` |
| `webhook_consumer/` | ADD `README.md` at root | Overview with variant status table |
| `webhook_receiver/README.md` | UPDATE | Add clear status: CloudflareD1=ACTIVE, Supabase=DEPRECATED |
| `webhook_receiver/supabase_queue/README.md` | UPDATE | Add `> **[DEPRECATED]**` banner |
| `webhook_consumer/supabase_consumer/README.md` | UPDATE | Add `> **[DEPRECATED]**` banner |
| `docs/data_context_overview.md` | UPDATE | Absorb `sapo_data_sources.md` content, add link to `ingestion/docs/SOURCES.md` for API details |

---

## 15. Proposed Cross-Reference Map

After cleanup, this is how documents should reference each other:

```
README.md ─────────────────────────┐
  │                                │
  ├→ docs/ARCHITECTURE.md ─────────┤
  │    ├→ ingestion/docs/README.md │
  │    ├→ transformation/docs/README.md
  │    ├→ orchestration/docs/README.md
  │    ├→ webhook_receiver/docs/README.md
  │    └→ docs/analytics-handbook/README.md
  │                                │
  ├→ docs/DATA_FLOW.md ───────────┤
  │    ├→ (same sub-project links) │
  │    └→ docs/DATA_DICTIONARY.md  │
  │                                │
  ├→ docs/OPERATIONS.md ──────────┤
  │    ├→ orchestration/docs/JOBS.md
  │    ├→ orchestration/docs/SCHEDULES.md
  │    └→ docs/TROUBLESHOOTING.md  │
  │                                │
  ├→ docs/DEPLOYMENT.md ──────────┤
  │    ├→ ingestion/docs/DEPLOYMENT.md
  │    ├→ webhook_receiver/cloudflareD1/docs/DEPLOYMENT.md
  │    └→ MIGRATION.md            │
  │                                │
  └→ docs/CONTRIBUTING.md         │
       └→ docs/GLOSSARY.md        │
                                   │
AGENTS.md ─────────────────────────┘
  ├→ transformation/AGENTS.md
  ├→ docs/analytics-handbook/AGENTS.md
  ├→ (all sub-project docs for reference)
  └→ .skills/ (for automation skills)

CLAUDE.md
  └→ .skills/metabase-automation/SKILL.md
       ├→ .agents/skills/ (framework adapters)
       └→ .claude/commands/ (slash commands)
```

### Sub-project internal linking (each sub-project follows same pattern):

```
{sub-project}/
  ├── README.md (or docs/README.md)     ← Entry point
  │     ├→ Links UP to docs/ARCHITECTURE.md (system context)
  │     └→ Links DOWN to sibling docs (details)
  ├── docs/TOPIC_A.md
  ├── docs/TOPIC_B.md
  └── [AGENTS.md]                        ← AI rules (if applicable)
        └→ Links to sibling docs for detail
```

---

## 16. docs/README.md: The Master Index (Proposed)

The heart of the linking system. This should be the single place anyone (human or AI) goes to find documentation:

```markdown
# Documentation Index

## System Overview
| Document | What it covers |
|----------|---------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, components, principles |
| [DATA_FLOW.md](DATA_FLOW.md) | Pipeline flow from source to serving |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Entity schemas, field definitions |
| [GLOSSARY.md](GLOSSARY.md) | Terms, naming conventions |

## Component Documentation
| Component | Entry Point | Key Topics |
|-----------|------------|------------|
| **Ingestion** (dlt) | [ingestion/docs/README.md](../ingestion/docs/README.md) | Sources, Pipelines, Incremental, Config |
| **Transformation** (dbt) | [transformation/docs/README.md](../transformation/docs/README.md) | Models, Materialization, Dedup, Testing |
| **Orchestration** (Dagster) | [orchestration/docs/README.md](../orchestration/docs/README.md) | Jobs, Assets, Schedules, Resources |
| **Webhook System** | [webhook_receiver/docs/README.md](../webhook_receiver/docs/README.md) | API, Security, CloudflareD1 |
| **Analytics** (Metabase) | [analytics-handbook/README.md](analytics-handbook/README.md) | Domains, Playbooks, Blueprints |

## Operations
| Document | What it covers |
|----------|---------------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Setup, install, deploy all components |
| [OPERATIONS.md](OPERATIONS.md) | Daily ops, monitoring, health checks |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Diagnostics, recovery procedures |

## Domain Knowledge
| Document | What it covers |
|----------|---------------|
| [data_context_overview.md](data_context_overview.md) | Sapo platform, API limitations |
| [analytics-handbook/domains/](analytics-handbook/domains/) | Business metrics by domain |

## AI Agent Instructions
| Document | Scope |
|----------|-------|
| [AGENTS.md](../AGENTS.md) | Global rules & constraints |
| [transformation/AGENTS.md](../transformation/AGENTS.md) | dbt-specific rules |
| [analytics-handbook/AGENTS.md](analytics-handbook/AGENTS.md) | BI/dashboard rules |
```

---

## 17. Summary: Before vs After

### Content Flow (Before)
```
                    ┌─ docs/data_pipeline.md (1812L) ──── DEAD END
                    ├─ docs/transformation_architecture.md ── DUPLICATES sub-project
TOP-LEVEL ──────────├─ docs/incremental_strategy.md ──── DUPLICATES sub-project
(18 flat files,     ├─ docs/dagster_dependencies.md ──── DUPLICATES sub-project
 mixed lang,        ├─ docs/sapo_data_sources.md ──── DUPLICATES sub-project
 no links)          ├─ docs/ARCHITECTURE.md ──── REPEATS sub-project content
                    └─ AGENTS.md ──── REPEATS sub-project content

SUB-PROJECTS ──── (well-structured but ORPHANED - no links from TOP)
```

### Content Flow (After)
```
README.md
  │
  └→ docs/README.md (MASTER INDEX)
       │
       ├→ docs/ARCHITECTURE.md ──summary──→ ingestion/docs/README.md
       │                        ──summary──→ transformation/docs/README.md
       │                        ──summary──→ orchestration/docs/README.md
       │                        ──summary──→ webhook_receiver/docs/README.md
       │
       ├→ docs/DATA_FLOW.md ───hop-links──→ (same sub-projects)
       │
       ├→ docs/OPERATIONS.md ──job-links──→ orchestration/docs/JOBS.md
       │                      ──sched-link→ orchestration/docs/SCHEDULES.md
       │
       └→ docs/DEPLOYMENT.md ──comp-links─→ ingestion/docs/DEPLOYMENT.md
                               ──comp-links→ webhook_receiver/.../DEPLOYMENT.md

AGENTS.md ──constraints + pointers──→ (sub-project docs for detail)

docs/archive/ ──── Phase 1 design docs (preserved but out of active path)
```

### Impact Metrics

| Metric | Before | After |
|--------|--------|-------|
| Active docs at `docs/` root | 18 files | 9 files |
| Duplicate content lines | ~3,500 | ~0 |
| Orphaned sub-project docs (no inbound links) | 30+ files | 0 |
| Files to read to understand "deduplication" | 4 | 1 (`transformation/docs/DEDUPLICATION.md`) |
| Files to read to understand "scheduling" | 3 | 1 (`orchestration/docs/SCHEDULES.md`) |
| Files to read to understand "incremental" | 3 | 1 per layer (`ingestion/docs/INCREMENTAL.md` or `transformation/docs/MATERIALIZATION.md`) |
| AGENTS.md context load | 444 lines | ~200 lines |
| Average hops to find any topic | 3-5 (search) | 2 (index → detail) |
| Legacy VN docs in active path | 8 files | 1 (`data_context_overview.md`, updated) |
