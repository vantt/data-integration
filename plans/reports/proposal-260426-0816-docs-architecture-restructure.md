# Đề xuất tái cấu trúc tài liệu — Narrative arc + per-context library

> **Date:** 2026-04-26
> **Author:** Claude (analysis)
> **Status:** Đề xuất, chờ thảo luận
> **Inputs:** Quét toàn bộ `docs/`, `plans/reports/`, `plans/`, codebase; audit `documentation-system-audit-2026-03-30.md`

---

## TL;DR

Hiện tại tài liệu **đầy đủ về thông tin nhưng nghèo về luồng đọc**, và **chưa được thiết kế cho AI agent đồng-phát triển**. Người mới (analyst, business viewer, engineer, hay AI agent) không có "đường dẫn" để tự hiểu được: bắt đầu ở đâu, đi tiếp đến đâu, và khi cần update thì làm theo quy tắc nào.

Đề xuất:

1. **Áp một "narrative arc" 9 bước lên `docs/`**, đánh số rõ ràng từ vấn đề → thiết kế → sử dụng → nguồn → đích → chiến thuật → triển khai → vận hành → phát triển.
2. **Tạo lớp `contexts/`** — mỗi analytic context là một folder kể trọn câu chuyện theo cùng arc đó.
3. **Đối xử AI agent như co-developer**: tạo `docs/_meta/` chứa charter + conventions + decision trees + templates + schemas + validation, với 3 lớp discovery (root AGENTS.md → docs/AGENTS.md → _meta/) đảm bảo bất kỳ agent nào có ý định sửa docs đều **tự động** gặp rule. Chi tiết §13.
4. **Giữ nguyên** `analytics-handbook/` (đang tốt) và sub-component docs (`ingestion/docs/`, `transformation/docs/`, `orchestration/docs/`) — chúng trở thành "thư viện implementation" mà narrative trỏ đến.
5. **Archive** legacy & spec lớn (`ANALYTICS_2SKILL_SPEC.md`, `dlt-ingestion-skill-design.md`, `archive/`), đưa Phase-1 VN docs về `archive/`.
6. **Slim** root `AGENTS.md` (444 dòng) → ~120 dòng; thêm `docs/AGENTS.md` (NEW, ~80 dòng) làm discovery anchor cho doc system.

Kết quả mong đợi: business viewer mở `docs/01-perspective/` đọc 15 phút hiểu mình ở đâu; analyst mở `contexts/ceo-pulse/` đọc 30 phút biết toàn bộ "chuyện CEO pulse"; engineer mở `docs/06-strategy/` đọc 1h hiểu vì sao mọi quyết định kỹ thuật được chọn; **AI agent mở bất kỳ file `docs/**` nào để edit đều tự động được dẫn đến charter + template + checklist trong `docs/_meta/`, không phỏng đoán format**.

---

## 1. Chẩn đoán hiện trạng

### 1.1 Số liệu

| Chỉ số | Giá trị |
| --- | --- |
| Tổng MD files | ~125 |
| Tổng dòng tài liệu | ~26.000 |
| Files VN / EN / mixed | ~15 / ~80 / ~5 |
| Duplicate lines (audit ước tính) | ~2.500 |
| Folders top-level trong `docs/` | 14 (architecture, operations, decisions, context, guides, development, analytics-handbook, misa-amis, shopee-integration, archive, reports, + 6 file MD lẻ) |

### 1.2 Sáu vấn đề đọng lại sau khi quét

**(1) Không có luồng đọc.** `docs/README.md` có "progressive disclosure" Level 1-4 nhưng đó là phân *loại độ sâu*, không phải *chuỗi câu chuyện*. Người đọc không biết "sau khi đọc Architecture xong thì đọc gì để nối tiếp tư duy?".

**(2) Ba audience cùng tranh chỗ trong cùng cây folder:**
- Business viewer (đọc dashboard) → cần: ý nghĩa metric, cách đọc, ai đáp ứng
- Analyst (thiết kế dashboard) → cần: domain, design pattern, mart catalog
- Data engineer (xây/sửa pipeline) → cần: source nature, transformation logic, ADR

Hiện tại tất cả đều bị đẩy vào cùng `docs/architecture/` hoặc `docs/context/` mà không tách audience.

**(3) Per-context fragmentation.** Để hiểu "Shopee Channel Economics" cần đọc 7 nơi:
- `docs/shopee-integration/data-source-description.md` (raw source)
- `docs/architecture/source-entities/external-sources.md` (entity)
- `docs/analytics-handbook/blueprints/shopee_channel_economics.md` (Metabase deploy)
- `docs/analytics-handbook/playbooks/shopee_channel_economics.md` (story)
- `docs/analytics-handbook/designs/shopee_channel_economics.md` (design spec)
- `transformation/models/intermediate/shopee/*.sql` (transform)
- `transformation/models/marts/sales/fact_order_economics.sql` (mart)

Không nơi nào tổng hợp lại thành một câu chuyện duy nhất.

**(4) Duplicate & legacy đè lên current docs.** Audit chỉ rõ: `docs/transformation_architecture.md` ≈ `transformation/docs/ARCHITECTURE_DETAIL.md`; `docs/data_pipeline.md` (1.812 dòng) là Phase-1 design VN giờ đã lỗi thời nhưng vẫn nằm cạnh ARCHITECTURE.md hiện hành.

**(5) Sub-component docs orphaned.** `ingestion/docs/`, `transformation/docs/`, `orchestration/docs/` viết tốt, English, đầy đủ — nhưng không có inbound link từ `docs/architecture/overview.md` ngoài 1 dòng "Detailed docs →". Người đọc không biết phải xuống thăm.

**(6) AGENTS.md = mega-file.** 444 dòng trộn: AI agent rules + multi-project structure + operation interface + troubleshooting + Sapo domain context + Metabase config + concurrency rules + analytics-as-code workflow. Mỗi mục đều xứng đáng có 1 file riêng (hoặc đã có rồi nhưng AGENTS.md vẫn duplicate).

### 1.3 Cái đang LÀM TỐT (giữ nguyên)

- `analytics-handbook/` 4 lớp (domains/playbooks/designs/blueprints) — kiến trúc rõ ràng, được skills `.skills/analytics-design/` và `.skills/metabase-automation/` tham chiếu trực tiếp.
- Sub-component docs trong từng folder nguồn (`ingestion/docs/*.md`, `transformation/docs/*.md`, `orchestration/docs/*.md`).
- `docs/decisions/` — 13 ADRs có hệ thống, đánh số.
- `docs/architecture/source-entities/` — chia entity theo nhóm logic.
- Skills đã chuẩn (`.skills/analytics-design/SKILL.md`, `.skills/metabase-automation/STRATEGY.md`).

---

## 2. Triết lý đề xuất — "Narrative arc"

### 2.1 Arc 9 bước

Áp đúng dãy bạn mô tả, từ "consumer-first" sang "engineering":

```
┌─ FRONT-OF-HOUSE (consumer perspective) ──────────────────┐
│  01  PERSPECTIVE   ← vấn đề + ai + tiếp cận làm việc      │
│  02  DESIGN        ← chọn thiết kế gì + chi tiết           │
│  03  USAGE         ← hướng dẫn sử dụng                     │
└──────────────────────────────────────────────────────────┘
            ↓ (chuyển từ "what users see" sang "how it's made")
┌─ BACK-OF-HOUSE (engineering perspective) ────────────────┐
│  04  SOURCE        ← bản chất + khó khăn của nguồn         │
│  05  TARGET        ← dữ liệu đích cần                       │
│  06  STRATEGY      ← chiến thuật + ADRs                     │
│  07  IMPLEMENTATION ← cách biến đổi (code-level pointers)   │
└──────────────────────────────────────────────────────────┘
            ↓ (operational concerns, dev workflow)
┌─ OPS & DEV ──────────────────────────────────────────────┐
│  08  OPERATIONS    ← deploy, run, troubleshoot, monitor    │
│  09  DEVELOPMENT   ← contribute, standards, testing        │
└──────────────────────────────────────────────────────────┘
            ↓ (per-context library — same arc, scoped)
┌─ ANALYTIC CONTEXTS (per-domain narratives) ──────────────┐
│  contexts/{context-name}/  ← mỗi cái lặp lại arc 1-7      │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Vì sao thứ tự này

- Đặt **PERSPECTIVE trước SOURCE** vì người đọc cần biết "tại sao tôi cần biết Sapo có giới hạn API" — câu trả lời là "vì dashboard CEO cần dữ liệu nhất quán hằng ngày, mà API không filter theo modified_on".
- **DESIGN đứng trước SOURCE** để analyst hiểu "đây là cái CEO sẽ thấy" trước khi đào vào "đây là chỗ Shopee data khó parse". Engineer skim qua phần 02-03 cũng OK.
- **STRATEGY tách rời IMPLEMENTATION**: strategy = quyết định kiến trúc (cite ADR), implementation = "code ở đâu, đọc tiếp ở `transformation/docs/`".
- **OPERATIONS & DEVELOPMENT cuối cùng** vì chúng presupposes mọi thứ trên.

### 2.3 Hai tầng (macro + micro)

| Tầng | Áp dụng | Ví dụ |
| --- | --- | --- |
| **Macro** (`docs/01-09/`) | Toàn hệ thống | "Pipeline 7-hop chung" |
| **Micro** (`docs/contexts/{name}/`) | Một analytic context (= một dashboard family hoặc một domain analytics) | "Shopee channel economics" — kể trọn từ vấn đề CEO đến SQL cuối cùng |

Micro tier KHÔNG duplicate macro — nó **trỏ vào** macro + handbook + code, đóng vai **tour guide** cho 1 chủ đề.

---

## 3. Cấu trúc đề xuất — Macro tier

### 3.1 Cây thư mục mục tiêu

```
docs/
├── README.md                          ← Front door, audience routing 4 lối
├── AGENTS.md                          ← (NEW) Doc-level discovery anchor (~80 dòng)
│                                          → trỏ vào _meta/ cho full charter
│                                          → kích hoạt khi agent edit docs/**
│
├── _meta/                             ← (NEW) META SYSTEM (sorts đầu, agent-first)
│   ├── README.md                      ← "Bạn là editor/agent? Đọc đây trước"
│   ├── doc-system-charter.md          ← THE CONSTITUTION (the WHY, ~200 dòng)
│   ├── conventions.md                 ← Frontmatter spec, naming, length, language
│   ├── decision-trees.md              ← SOP cookbook ("muốn X thì làm Y, Z")
│   ├── glossary-of-doc-terms.md       ← "narrative file", "context", "pointer", v.v.
│   ├── templates/
│   │   ├── README.md                  ← "Template nào dùng khi nào"
│   │   ├── narrative-file.template.md         ← Cho 01-09/*.md
│   │   ├── folder-readme.template.md          ← Cho mọi README.md folder
│   │   ├── context-readme.template.md
│   │   ├── context-perspective.template.md
│   │   ├── context-design.template.md
│   │   ├── context-usage.template.md
│   │   ├── context-source.template.md
│   │   ├── context-target.template.md
│   │   ├── context-strategy.template.md
│   │   ├── source-overview.template.md        ← Cho 04-source-landscape/X/what-it-is.md
│   │   ├── pointer.template.md                ← Cho 07-implementation/*.md
│   │   ├── adr.template.md
│   │   └── orientation.template.md
│   ├── schemas/
│   │   ├── frontmatter.schema.json    ← JSON Schema cho YAML frontmatter
│   │   ├── audience.enum.yaml
│   │   └── status.enum.yaml
│   └── validation/
│       ├── checklist.md               ← Manual pre-commit checklist
│       └── how-to-run-validator.md    ← Pointer → scripts/testing/validate_docs.py
│
├── orientation/                       ← Onboarding & navigation aids
│   ├── for-business-viewers.md
│   ├── for-analysts.md
│   ├── for-data-engineers.md
│   ├── for-ai-agents.md               ← Đường vào nhanh (USE perspective)
│   │                                      Khác với docs/AGENTS.md (MAINTAIN perspective)
│   └── glossary.md                    ← (chuyển từ docs/development/glossary.md)
│
├── 01-perspective/                    ← VẤN ĐỀ + GÓC NHÌN
│   ├── README.md                      ← Tóm lược cả phần
│   ├── business-questions.md          ← Câu hỏi cốt lõi mà hệ thống trả lời
│   ├── audience-and-roles.md          ← CEO/Sales/Marketing/Ops/CS — họ cần gì
│   ├── analyst-workflow.md            ← Quy trình một analyst làm việc
│   ├── viewer-workflow.md             ← Cách business viewer tiếp nhận info
│   └── design-philosophy.md           ← Audience-first, dashboard-owns-questions
│
├── 02-design/                         ← LÝ DO + CHI TIẾT THIẾT KẾ
│   ├── README.md
│   ├── dashboard-catalog.md           ← Index dashboards (link → handbook playbooks)
│   ├── mart-catalog.md                ← Index marts (link → data-dictionary)
│   ├── design-archetypes.md           ← Pulse / Cockpit / Exploratory (cite ADR-011)
│   ├── collection-architecture.md     ← Audience-based collections (cite ADR-009)
│   └── visual-language.md             ← Color tokens, sizing, comparative framing
│
├── 03-usage/                          ← HƯỚNG DẪN SỬ DỤNG
│   ├── README.md
│   ├── reading-dashboards.md          ← Cách đọc card, filter, comparison frame
│   ├── self-service-querying.md       ← Metabase native, DuckDB CLI, Rill explore
│   ├── common-questions.md            ← FAQ "where do I find X"
│   └── decision-workflow.md           ← Từ insight → action
│
├── 04-source-landscape/               ← NGUỒN: BẢN CHẤT + KHÓ KHĂN
│   ├── README.md                      ← Source matrix (Sapo/Shopee/MISA/FB/Sheets)
│   ├── sapo/
│   │   ├── what-it-is.md              ← Sapo là gì
│   │   ├── api-nature-and-limits.md   ← (rút từ docs/context/sapo-platform.md)
│   │   ├── 3-channel-strategy.md      ← Vì sao webhook + history-log + batch
│   │   ├── entity-model.md            ← (gộp source-entities/core + reference)
│   │   └── channel-taxonomy.md        ← (rút từ docs/context/channel-grouping-analysis.md)
│   ├── shopee/
│   │   ├── what-it-is.md
│   │   ├── file-drop-nature.md        ← Excel multi-row header, dual-grain
│   │   ├── parsing-hazards.md
│   │   └── released-payout-grain.md
│   ├── misa-amis/
│   │   ├── what-it-is.md
│   │   ├── ledger-grain.md
│   │   ├── cogs-as-only-cost-source.md
│   │   └── voucher-no-as-bridge-key.md
│   ├── facebook-ads/
│   │   └── what-it-is.md
│   ├── facebook-messenger/
│   │   └── what-it-is.md
│   └── sheets/
│       ├── targets-sheet.md           ← (chuyển từ docs/guides/targets-sheet.md)
│       └── marketing-spend.md         ← (chuyển từ docs/context/marketing-spend-setup.md)
│
├── 05-target-shape/                   ← DỮ LIỆU ĐÍCH CẦN
│   ├── README.md
│   ├── dimensional-model.md           ← Star schema overview (rút từ context/data-model)
│   ├── grain-conventions.md           ← "1 row = ..." mỗi fact
│   ├── data-dictionary.md             ← (chuyển từ architecture/data-dictionary.md)
│   ├── naming-conventions.md
│   └── envelope-schema.md             ← (chuyển từ architecture/source-entities/)
│
├── 06-strategy/                       ← CHIẾN THUẬT + ADRs
│   ├── README.md
│   ├── pipeline-architecture.md       ← 7-hop với rationale (gộp overview+data-flow)
│   ├── deduplication-strategy.md      ← Câu chuyện 2-level dedup
│   ├── concurrency-and-locking.md     ← (chuyển từ architecture/locking-and-concurrency.md)
│   ├── rolling-snapshots.md           ← Zero-downtime serving
│   ├── orchestration-patterns.md      ← Job priority, schedule offsets
│   ├── analytics-as-code.md           ← (rút từ ADR-008)
│   └── decisions/                     ← ADRs (chuyển từ docs/decisions/)
│       ├── README.md
│       └── 001-013-*.md               ← Giữ nguyên đánh số
│
├── 07-implementation/                 ← CÁCH BIẾN ĐỔI (code pointers)
│   ├── README.md                      ← Bản đồ "ở component nào làm gì"
│   ├── ingestion.md                   ← 1-2 trang summary + link → ingestion/docs/
│   ├── transformation.md              ← 1-2 trang summary + link → transformation/docs/
│   ├── orchestration.md               ← idem
│   ├── webhook-system.md              ← idem (nói rõ active vs deprecated variant)
│   ├── serving-layer.md               ← bootstrap_serving_views.py + refresh_rolling.py
│   └── scripts.md                     ← provisioning/, maintenance/, testing/
│
├── 08-operations/                     ← VẬN HÀNH (giữ docs/operations/ rename)
│   ├── deployment.md
│   ├── daily-operations.md            ← (rename từ operations.md)
│   ├── troubleshooting.md
│   ├── monitoring.md                  ← MỚI (gom Dagster digest, ingestion health)
│   ├── migration.md
│   └── config-guide.md                ← (chuyển từ docs/config-guide.md)
│
├── 09-development/                    ← CONTRIBUTE
│   ├── contributing.md
│   ├── code-standards.md              ← (mới hoặc rút từ AGENTS.md)
│   ├── testing-strategy.md            ← (mới)
│   └── release-and-changelog.md       ← (chuyển docs/project-changelog.md)
│
├── contexts/                          ← MICRO TIER — per-analytic-context
│   ├── README.md                      ← Index of contexts với 1-line description
│   ├── ceo-pulse/
│   ├── ceo-monthly-scorecard/
│   ├── shopee-channel-economics/
│   ├── customer-retention/
│   ├── marketing-roi/
│   ├── finance-pl/
│   ├── ingestion-health/
│   ├── order-economics/
│   └── ...
│
├── analytics-handbook/                ← KHÔNG ĐỘNG — implementation library
│   ├── domains/
│   ├── playbooks/
│   ├── designs/
│   ├── blueprints/
│   ├── guides/                        ← guides giữ nguyên
│   └── README.md
│
└── archive/                           ← Legacy + Phase-1 VN docs
    ├── README.md                      ← Giải thích vì sao archive
    ├── phase-1-vietnamese/
    │   ├── data_pipeline.md           ← (chuyển từ archive hiện tại + bổ sung)
    │   ├── data_context_overview.md
    │   └── ...
    ├── deprecated-skills/
    │   ├── ANALYTICS_2SKILL_SPEC.md   ← 82KB, thay thế bởi .skills/
    │   └── dlt-ingestion-skill-design.md
    └── superseded-architecture/
        ├── transformation_architecture.md
        └── deployment_operation.md
```

### 3.2 README.md — Front door

`docs/README.md` viết lại theo 3 lối vào:

```markdown
# Data Integration — Documentation

## Bạn là ai?

| Vai trò | Bắt đầu ở | Mục tiêu |
| --- | --- | --- |
| **Business viewer** (đọc dashboard) | [orientation/for-business-viewers.md](./orientation/for-business-viewers.md) | Hiểu metric, biết khi nào dùng |
| **Analyst / dashboard designer** | [orientation/for-analysts.md](./orientation/for-analysts.md) | Thiết kế / sửa dashboard |
| **Data engineer** | [orientation/for-data-engineers.md](./orientation/for-data-engineers.md) | Xây / vận hành pipeline |
| **AI agent** | [orientation/for-ai-agents.md](./orientation/for-ai-agents.md) | Hiểu rule khi tự động hóa |

## Bạn quan tâm chủ đề cụ thể?

- Một dashboard / domain → xem **[contexts/](./contexts/)** (per-context narratives)
- Một component code → xem **[07-implementation/](./07-implementation/)** (pointers)
- Một quyết định kiến trúc → xem **[06-strategy/decisions/](./06-strategy/decisions/)**

## Đọc theo luồng câu chuyện?

01-Perspective → 02-Design → 03-Usage → 04-Source → 05-Target → 06-Strategy → 07-Implementation → 08-Operations → 09-Development
```

### 3.3 Quy ước viết cho mỗi file

Mỗi file MD trong `docs/01-09/` và `docs/contexts/` có **YAML frontmatter** chuẩn:

```yaml
---
title: "Pipeline Architecture"
audience: [engineer]            # viewer | analyst | engineer | ai-agent | all
status: active                  # active | draft | deprecated | archive
language: en                    # en | vi | mixed
last_modified: 2026-04-26
upstream_refs:                  # links đến file khác cần đọc trước (optional)
  - 04-source-landscape/README.md
related:                        # links song song (optional)
  - 06-strategy/decisions/001-pipeline-7-hop-elt.md
---
```

Lợi ích:
- AI agent filter theo `audience` để load context tối thiểu.
- Audit dễ tìm `status: deprecated` để dọn.
- Người đọc thấy ngay "ai cần đọc cái này".

---

## 4. Cấu trúc per-context — Micro tier

### 4.1 Triết lý

Một "analytic context" = **một câu chuyện trọn vẹn xung quanh một dashboard family hoặc một analytics domain**. Ví dụ:

- `ceo-pulse` = câu chuyện CEO Weekly Pulse (1 dashboard cụ thể)
- `shopee-channel-economics` = câu chuyện toàn bộ phân tích kinh tế kênh Shopee (kéo theo nhiều mart, dashboard, MISA bridge)
- `customer-retention` = câu chuyện retention analytics (mart fact_customer_retention + dashboard + lifecycle)

Mỗi context **lặp lại arc** từ 01 đến 07 (bỏ 08-09 vì là operational chung).

### 4.2 Cấu trúc một context folder

```
contexts/shopee-channel-economics/
├── README.md                  ← TLDR + navigation map (1 trang)
├── 01-perspective.md          ← Vấn đề: vì sao CEO cần biết kênh Shopee đang lỗ/lãi?
├── 02-design.md               ← Thiết kế dashboard + rationale (link → handbook playbook + design)
├── 03-usage.md                ← Cách đọc, ai dùng, ngưỡng cảnh báo
├── 04-source.md               ← Shopee Income export + MISA COGS + Sapo orders
│                                  - Bản chất: Shopee dual-grain, fee signed
│                                  - Khó khăn: filename-driven window, multi-row header
│                                  - Bridge keys: voucher_no (MISA ↔ Sapo/Shopee)
├── 05-target.md               ← Mart cần: fact_order_economics, dim_channels
│                                  - Grain: 1 row = 1 order × 1 channel
│                                  - Columns chính + ý nghĩa
├── 06-strategy.md             ← Cách biến đổi:
│                                  - intermediate/shopee/* deduplicate income
│                                  - intermediate/misa/* extract COGS theo voucher
│                                  - join trong fact_order_economics
│                                  - cách handle MISA late-arriving COGS
└── visuals/                   ← (optional) screenshots, lineage diagrams
    └── lineage.mmd
```

### 4.3 README.md của một context (template)

```markdown
---
title: "Shopee Channel Economics"
audience: [analyst, engineer, viewer]
status: active
language: vi
last_modified: 2026-04-26
related_artifacts:
  playbook: ../../analytics-handbook/playbooks/shopee_channel_economics.md
  design:   ../../analytics-handbook/designs/shopee_channel_economics.md
  blueprint: ../../analytics-handbook/blueprints/shopee_channel_economics.md
  dbt_models:
    - transformation/models/intermediate/shopee/
    - transformation/models/marts/sales/fact_order_economics.sql
  source_docs:
    - ../../04-source-landscape/shopee/
    - ../../04-source-landscape/misa-amis/
---

# Shopee Channel Economics

## TLDR (30 giây)

Dashboard này trả lời câu hỏi: **"Mỗi đơn Shopee thực chất lãi/lỗ bao nhiêu sau khi trừ phí sàn, phí vận chuyển, và COGS?"**

CEO + Sales Director dùng hằng tháng để quyết định có push sale Shopee hay không.

## Câu chuyện 1 phút

1. **Vấn đề** (xem [01-perspective](./01-perspective.md)): Doanh thu Shopee tăng nhưng margin không rõ vì phí sàn ẩn nhiều khoản.
2. **Thiết kế** (xem [02-design](./02-design.md)): Bento grid 4 KPI + 1 trend + 1 breakdown by SKU.
3. **Sử dụng** (xem [03-usage](./03-usage.md)): Đọc waterfall trước, drilldown SKU sau.
4. **Nguồn** (xem [04-source](./04-source.md)): Shopee Income export (Excel) + MISA AMIS (COGS) + Sapo (order metadata).
5. **Đích** (xem [05-target](./05-target.md)): `fact_order_economics`, grain = order × channel.
6. **Chiến thuật** (xem [06-strategy](./06-strategy.md)): Bridge bằng `voucher_no` từ MISA, dedupe Shopee theo `payout_released_at`.

## Bạn cần làm gì?

| Mục đích | Đi đến |
| --- | --- |
| Đọc dashboard | [03-usage.md](./03-usage.md) → Metabase link |
| Sửa metric | [02-design.md](./02-design.md) → playbook ↑ |
| Sửa transform | [06-strategy.md](./06-strategy.md) → dbt model ↑ |
| Hiểu vì sao chọn `voucher_no` | [04-source.md → MISA](./04-source.md#misa-bridge) |
```

### 4.4 Mỗi file con (01-06) trong context

- **Ngắn**: 50-200 dòng, là *narrative*, không phải reference.
- **Trỏ liên tục**: mỗi đoạn nên link ra handbook hoặc code, không tự lặp lại logic.
- **Viết bằng VN** (vì audience hỗn hợp business + dev VN), giữ tên kỹ thuật bằng EN.
- **Không có SQL dài**: SQL nằm trong dbt; context file kể "vì sao SQL như vậy".

### 4.5 Danh sách context ưu tiên seed (8 context cho lần đầu)

| # | Context | Vì sao ưu tiên |
| --- | --- | --- |
| 1 | `ceo-pulse` | Khán giả cấp cao nhất, mẫu chuẩn cho Pulse archetype |
| 2 | `shopee-channel-economics` | Multi-source phức tạp nhất, mẫu cho cross-source bridge |
| 3 | `customer-retention` | Customer-domain, mẫu cho lifecycle analytics |
| 4 | `marketing-roi` | Marketing-domain, link FB Ads + Sales |
| 5 | `finance-pl` | Finance-domain, mẫu cho MISA-driven |
| 6 | `ingestion-health` | Self-monitoring, mẫu cho operational dashboard |
| 7 | `sales-daily-operation` | Operational cockpit, mẫu cho daily archetype |
| 8 | `order-economics` | Mart-driven (không gắn 1 dashboard cụ thể), mẫu cho domain context không phải dashboard |

Sau 8 cái này, các context khác có thể được template hóa nhanh.

---

## 5. Migration mapping — Cũ → Mới

### 5.1 Files chuyển vị trí

| Hiện tại | Mới | Lý do |
| --- | --- | --- |
| `docs/architecture/overview.md` | `docs/06-strategy/pipeline-architecture.md` (gộp với data-flow) | Architecture overview = strategy + how |
| `docs/architecture/data-flow.md` | (gộp vào pipeline-architecture.md trên) | Nội dung trùng lắp với overview |
| `docs/architecture/data-dictionary.md` | `docs/05-target-shape/data-dictionary.md` | Dictionary = target shape |
| `docs/architecture/raw-data-sources.md` | `docs/04-source-landscape/README.md` | Đúng layer |
| `docs/architecture/source-entities/*.md` | `docs/04-source-landscape/sapo/entity-model.md` (consolidate) + `05-target-shape/envelope-schema.md` | Tách entity (source) khỏi envelope (target) |
| `docs/architecture/locking-and-concurrency.md` | `docs/06-strategy/concurrency-and-locking.md` | Strategy decision |
| `docs/context/sapo-platform.md` | `docs/04-source-landscape/sapo/api-nature-and-limits.md` | Source nature |
| `docs/context/channel-grouping-analysis.md` | `docs/04-source-landscape/sapo/channel-taxonomy.md` | Source-domain |
| `docs/context/sales-segmentation-guide.md` | `docs/01-perspective/audience-and-roles.md` (rút phần segmentation) + `analytics-handbook/domains/sales.md` (logic) | Tách perspective khỏi logic |
| `docs/context/customer-segmentation.md` | `analytics-handbook/domains/customer.md` (đã có) — merge | Logic nằm ở handbook |
| `docs/context/marketing-spend-setup.md` | `docs/04-source-landscape/sheets/marketing-spend.md` | Sheet = source |
| `docs/context/team-management.md` | `docs/01-perspective/audience-and-roles.md` | Audience |
| `docs/context/data-model-overview.md` | `docs/05-target-shape/dimensional-model.md` | Target shape |
| `docs/decisions/*.md` | `docs/06-strategy/decisions/*.md` | ADR là strategy |
| `docs/operations/*.md` | `docs/08-operations/*.md` | Rename folder để vào số thứ tự |
| `docs/development/*.md` | `docs/09-development/*.md` + `docs/orientation/glossary.md` | Tách glossary làm orientation |
| `docs/guides/dbt-vs-metabase.md` | `docs/06-strategy/dbt-vs-metabase.md` | Architecture decision |
| `docs/guides/rill-with-metabase.md` | `docs/02-design/rill-with-metabase.md` | Design choice |
| `docs/guides/targets-sheet.md` | `docs/04-source-landscape/sheets/targets-sheet.md` | Source |
| `docs/guides/facebook-ads.md` | `docs/04-source-landscape/facebook-ads/integration-guide.md` | Source |
| `docs/guides/facebook-messenger.md` | `docs/04-source-landscape/facebook-messenger/integration-guide.md` | Source |
| `docs/shopee-integration/*.md` | `docs/04-source-landscape/shopee/*.md` | Source |
| `docs/misa-amis/*.md` | `docs/04-source-landscape/misa-amis/*.md` | Source |
| `docs/config-guide.md` | `docs/08-operations/config-guide.md` | Operational |
| `docs/project-changelog.md` | `docs/09-development/release-and-changelog.md` | Dev concern |
| `docs/reports/*.md` | `plans/reports/*.md` | Trùng mục đích, gom 1 chỗ |

### 5.2 Files archive

| File | Đến | Lý do |
| --- | --- | --- |
| `docs/ANALYTICS_2SKILL_SPEC.md` (82KB) | `docs/archive/deprecated-skills/` | Đã thay thế bởi `.skills/analytics-design/` + `.skills/metabase-automation/` |
| `docs/dlt-ingestion-skill-design.md` | `docs/archive/deprecated-skills/` | Đã có `.skills/data-pipeline/` |
| `docs/archive/*` | giữ nguyên `docs/archive/` | OK |

### 5.3 Files KHÔNG ĐỘNG

| Path | Lý do |
| --- | --- |
| `docs/analytics-handbook/**` | Skills tham chiếu trực tiếp; cấu trúc đã tốt |
| `ingestion/docs/**` | Component-local, gắn với code |
| `transformation/docs/**` | idem |
| `transformation/AGENTS.md` | dbt-specific rules |
| `orchestration/docs/**` | idem |
| `webhook_receiver/docs/**` | idem (nhưng cần thêm "ACTIVE/DEPRECATED" status — xem §6.3) |
| `webhook_consumer/**/README.md` | idem |
| `.skills/**` | Skills directory |

### 5.4 Files MỚI cần viết

(Không có gì quá nhiều — chủ yếu là REWRITE / CONSOLIDATE từ nội dung hiện có.)

| File mới | Nguồn |
| --- | --- |
| `docs/README.md` (rewrite) | Hiện tại + 3-audience routing |
| `docs/orientation/for-{viewer,analyst,engineer,ai-agent}.md` | Mới — viết từ đầu, ngắn (50-100 dòng/file) |
| `docs/01-perspective/business-questions.md` | Mới — gom từ blueprints + scope notes |
| `docs/01-perspective/{audience-and-roles,analyst-workflow,viewer-workflow,design-philosophy}.md` | Mới — viết từ đầu |
| `docs/02-design/dashboard-catalog.md` | Mới — bảng index links → handbook |
| `docs/02-design/mart-catalog.md` | Mới — bảng index links → data-dictionary |
| `docs/03-usage/*.md` | Mới |
| `docs/04-source-landscape/README.md` | Mới — source matrix |
| `docs/04-source-landscape/{sapo,shopee,misa-amis,facebook-*,sheets}/what-it-is.md` | Mới — 1-2 trang/file |
| `docs/05-target-shape/grain-conventions.md` | Mới |
| `docs/05-target-shape/naming-conventions.md` | Mới (có thể rút từ AGENTS.md + transformation docs) |
| `docs/06-strategy/{deduplication-strategy,rolling-snapshots,orchestration-patterns,analytics-as-code}.md` | Mới — gom từ AGENTS.md + sub-docs |
| `docs/07-implementation/README.md` + 6 pointer files | Mới — pointer pattern |
| `docs/08-operations/monitoring.md` | Mới |
| `docs/09-development/{code-standards,testing-strategy}.md` | Mới |
| `docs/contexts/README.md` + 8 context folders × 7 files | Mới (template-driven) |

Tổng MD mới: ~50 files, đa số nhỏ (100-200 dòng).

---

## 6. Slim các file "mega"

### 6.1 `AGENTS.md` (444 → ~150 dòng)

**Giữ:**
- AI Agent Operation Protocol (machine-readable)
- Multi-Project Repository Structure (concise version)
- Quick Reference (paths, commands)
- Hook response protocol (`@@PRIVACY_PROMPT@@`)

**Tách ra:**
- "Documentation Map" → `docs/README.md` (đã có 1 phần)
- "Multi-Project Repository Structure" detail → `docs/07-implementation/README.md`
- "AI Context - Data Engineering & Sapo Domain" → `docs/04-source-landscape/sapo/README.md`
- "Architecture & Deployment Criticals" → `docs/06-strategy/concurrency-and-locking.md` + `docs/08-operations/deployment.md`
- "Analytics-as-Code (Literate Configuration)" → `docs/06-strategy/analytics-as-code.md`
- "Proven Solutions & Common Pitfalls" → `docs/08-operations/troubleshooting.md`
- Metabase MCP config → `docs/08-operations/config-guide.md`

### 6.2 `docs/analytics-handbook/AGENTS.md` (giữ nguyên — đã focus đúng)

### 6.3 `webhook_receiver/README.md` — thêm STATUS BANNER

```markdown
> **Active variant:** `cloudflareD1/` (production)
> **Deprecated variant:** `supabase_queue/` (kept for reference, do not deploy)
```

Tương tự cho `webhook_consumer/README.md`.

---

## 7. Lộ trình thực hiện (phases)

Đề xuất chia 6 phase, làm tuần tự để tránh broken links giữa chừng. Mỗi phase tự đứng được.

### Phase 1 — Skeleton + Front-of-house (3-4 ngày)
- Tạo cây folder rỗng + README placeholders
- Viết `docs/README.md` rewrite
- Viết `docs/orientation/*` (4 file)
- Viết `docs/01-perspective/*` (5 file)
- Viết `docs/02-design/*` (5 file, dashboard-catalog tự động sinh từ handbook)
- Viết `docs/03-usage/*` (4 file)
- **Output**: business viewer + analyst đã có lối vào.

### Phase 2 — Source landscape (2-3 ngày)
- Tạo `04-source-landscape/` skeleton
- Move `docs/context/sapo-platform.md`, `docs/shopee-integration/`, `docs/misa-amis/`
- Move guides `facebook-*`, `targets-sheet`, `marketing-spend-setup`
- Tách `architecture/source-entities/` thành per-source `entity-model.md`
- Viết `04-source-landscape/README.md` (source matrix)

### Phase 3 — Target & Strategy (2-3 ngày)
- Move `architecture/data-dictionary.md` → `05-target-shape/`
- Viết `05-target-shape/dimensional-model.md`, `grain-conventions.md`, `naming-conventions.md`
- Move `decisions/` → `06-strategy/decisions/`
- Move `architecture/locking-and-concurrency.md` → `06-strategy/`
- Gộp `architecture/overview.md` + `architecture/data-flow.md` → `06-strategy/pipeline-architecture.md`
- Viết các strategy file mới (deduplication, rolling-snapshots, orchestration-patterns, analytics-as-code)

### Phase 4 — Implementation pointers + ops & dev (1-2 ngày)
- Viết `07-implementation/` 7 pointer files
- Move `operations/` → `08-operations/`
- Move `development/` → `09-development/`
- Move `config-guide.md`, `project-changelog.md`

### Phase 5 — Per-context narratives (4-5 ngày, parallelizable)
- Viết template + 1 mẫu (ceo-pulse) đầy đủ → review
- Sinh 7 context còn lại theo template
- Cross-link với handbook artifacts
- **Optional**: chia phase này thành sub-phases theo ưu tiên

### Phase 6 — Cleanup + slim AGENTS + archive (1-2 ngày)
- Slim `AGENTS.md` xuống ~150 dòng
- Add status banner cho webhook variants
- Move legacy files sang `archive/`
- Update tất cả internal links (script Python tự động)
- Update `README.md` (root), `CLAUDE.md`, sub-component AGENTS.md
- Cập nhật `.claude/commands/` nếu có path-based command

**Tổng:** ~13-19 ngày, có thể song song hóa Phase 5.

---

## 8. Nguyên tắc viết — Áp dụng cho tất cả file mới

### 8.1 Format

- **YAML frontmatter** (schema tại `_meta/schemas/frontmatter.schema.json`, xem §13.6) bắt buộc cho file trong `01-09/` và `contexts/`. Required fields: `title`, `audience`, `status`, `language`, `last_modified`, `summary`, `maintainer_doc`. Optional: `upstream_refs`, `related`, `template_used`.
- **Heading H1** trùng với `title` trong frontmatter.
- **Đoạn TLDR** ngay sau H1, ≤3 câu, in nghiêng hoặc blockquote (cũng nên trùng nội dung `summary:` field).
- **Cross-references** dùng đường dẫn relative (`../05-target-shape/...`), không absolute.
- **Validate** trước commit qua checklist `_meta/validation/checklist.md` + script `validate_docs_structure.py`.

### 8.2 Audience-first writing

- Mỗi file biết audience của mình (`audience: [viewer]` hay `[engineer]` v.v.).
- Khi audience là `viewer` hoặc `analyst`: tránh thuật ngữ kỹ thuật chưa định nghĩa trong glossary.
- Khi audience là `engineer`: được phép sâu vào code path nhưng phải link ra source code.

### 8.3 Ngôn ngữ

- **Macro tier (`01-09/`)**: chủ yếu English (vì AI agent đọc), phần audience=viewer có thể song ngữ.
- **Micro tier (`contexts/`)**: Vietnamese-first (vì user là VN business), thuật ngữ kỹ thuật giữ EN.
- **Sub-component docs**: English (như hiện tại).
- **Handbook**: bilingual (như hiện tại).

### 8.4 Anti-duplication

- **Không** lặp lại nội dung đã có ở nơi khác. Luôn link.
- Nếu cần "context bridging" (ví dụ giải thích một concept để dẫn vào), làm 2-3 câu rồi link.
- Khi định viết một section dài, hỏi: "Cái này có nên ở handbook/sub-component thay vì ở đây?"

### 8.5 Length budget

| Loại file | Target |
| --- | --- |
| README hub (folder index) | 50-100 dòng |
| Narrative file (`01-09/`) | 100-300 dòng |
| Per-context file (`contexts/X/0Y-*.md`) | 50-200 dòng |
| Pointer file (`07-implementation/*`) | 30-80 dòng |
| ADR | 100-200 dòng (giữ chuẩn hiện tại) |

Không file MD nào nên vượt 800 dòng (giới hạn mềm bạn đã đặt trong hook config).

---

## 9. Câu hỏi mở (cần bạn quyết)

1. **Đánh số folder**: dùng `01-perspective/` hay `perspective/` (rely on README index)? Số giúp giữ thứ tự đọc trên file explorer, nhưng làm path dài hơn và tạo "bias" rằng đây là tutorial. Đề xuất: dùng số.

2. **Vietnamese vs English consistency**: standardize sang một ngôn ngữ, hay giữ hybrid (macro=EN, micro=VN, handbook=mixed)? Đề xuất: hybrid như §8.3.

3. **`analytics-handbook/domains/`** hiện đang **empty**. AGENTS.md handbook nói "Logic goes into `domains/*.md`" nhưng thực tế logic đang nằm trực tiếp trong dbt SQL. Có nên backfill domains/ ngay hay để sau? Đề xuất: backfill song song Phase 5 (mỗi context tạo ra domain entry tương ứng).

4. **`contexts/{X}/` chứa logic hay chỉ link?** Đề xuất nghiêm ngặt: chỉ là "tour guide" — không định nghĩa metric / SQL lần đầu. Nếu một context có metric mới, viết vào `analytics-handbook/domains/` rồi context link đến.

5. **Move ADRs vào `06-strategy/decisions/`** — sẽ phá vỡ inbound link từ blogposts/PR/external. Có cần redirect (`docs/decisions/README.md` → "moved to ...") không? Đề xuất: có, tạo 1 file pointer trong `docs/decisions/README.md` cũ (nếu xóa cả folder) trỏ sang vị trí mới.

6. **`AGENTS.md` slim down**: cắt từ 444 → ~150 dòng có làm AI agent confused vì mất một số "in-line context"? Hay dùng `for-ai-agents.md` orientation thay thế? Đề xuất: dùng `orientation/for-ai-agents.md` làm entry point chính cho agent, AGENTS.md chỉ giữ machine-readable protocol.

7. **Per-context folder format** — 7 file là đúng độ chi tiết, hay nên giảm xuống 1 file `README.md` tổng hợp (cho context đơn giản)? Đề xuất: cho phép cả 2: format đầy đủ (folder 7 file) cho context phức tạp, format gọn (1 MD) cho context đơn giản. Quy ước trong `contexts/README.md`.

8. **Reports vs plans/reports** — `docs/reports/` (1 file) gộp về `plans/reports/`? Đề xuất: có, vì chúng cùng kiểu (audit/research outputs).

9. **Frontmatter `last_modified`** — manual update hay hook script? Đề xuất: manual cho lần đầu, sau đó nếu thấy giá trị thì viết hook auto.

10. **README chuyển từ link "Architecture" sang "01-perspective"** — sẽ làm các bookmark/link cũ vỡ. Có chấp nhận trade-off không, hay cần redirect? Đề xuất: chấp nhận (đây là internal docs, không có external traffic).

11. **(Meta) Discovery hook (Lớp C, §13.7)** — bật mặc định trong `settings.json` (project-level) để mọi máy dev đều có, hay chỉ document trong `_meta/` để mỗi người opt-in qua `settings.local.json`? Đề xuất: bật mặc định project-level (Lớp C nhẹ — chỉ inject text reminder, không block).

12. **(Meta) Validation script — gating mode** — chạy ở severity `warn` (advisory) hay `error` (block commit qua pre-commit hook)? Đề xuất: ship ở `warn` 2 tuần đầu để team quen, sau đó upgrade `error` cho schema violations + broken links; giữ `warn` cho length budget.

13. **(Meta) Charter ownership** — ai có quyền sửa `_meta/doc-system-charter.md`? Đề xuất: PR + label `charter-update` + reviewer là người maintain doc system (1-2 người named owner). Sửa templates/decision-trees không cần label đặc biệt — như normal docs.

14. **(Meta) Khi agent thấy charter sai/lỗi thời** — agent nên (a) follow blindly, (b) flag và đợi user, hay (c) propose update charter trong cùng PR? Đề xuất: (b) flag, không tự động sửa charter; charter chỉ sửa qua human-initiated PR.

---

## 10. Trade-offs đã xem xét

| Trade-off | Đã chọn | Lý do |
| --- | --- | --- |
| Cấu trúc số (`01-...`) vs flat | Số | Thể hiện luồng đọc, đúng vision của user |
| Per-context folder vs per-context file | Folder | User nói "một bộ tài liệu" (số nhiều); folder cho phép visual như screenshots |
| Move ADRs vs giữ tại `docs/decisions/` | Move | ADR = strategy decision, hợp lý ở `06-strategy/decisions/` |
| Touch handbook vs giữ nguyên | Giữ | Skills tham chiếu paths; format đã tốt |
| Slim AGENTS.md vs giữ | Slim | Audit khuyến nghị; AI agent có `orientation/for-ai-agents.md` |
| English-only vs hybrid | Hybrid | User base VN; engineer reference EN |
| 1 audience-routing README vs 4 entry files | 4 entry | Mỗi audience có nhu cầu khác hẳn nhau |

---

## 11. Cái KHÔNG đề xuất (để tránh hiểu lầm)

- **Không** đổi `analytics-handbook/` (domains/playbooks/designs/blueprints) format hay vị trí.
- **Không** đổi sub-component `*/docs/` cấu trúc nội bộ.
- **Không** đổi `.skills/` hay `.claude/commands/` (chỉ update path nếu cần).
- **Không** xóa file ngay — tất cả "deprecated" chuyển vào `archive/`.
- **Không** thay đổi naming convention dbt models, file naming Python, v.v. (chỉ docs).
- **Không** thay đổi process deploy (Metabase deploy script tham chiếu blueprints).

---

## 12. Lợi ích mong đợi (sau migration)

| Persona | Trước | Sau |
| --- | --- | --- |
| Business viewer mới | Mở `docs/README.md` → bị lạc giữa "Architecture / Data Flow / Operations" → bỏ cuộc | Mở `docs/README.md` → chọn "viewer" → 5 phút biết mình đọc cái gì, ở đâu |
| Analyst thiết kế dashboard mới | Đọc handbook AGENTS, không hiểu vì sao có archetype Pulse/Cockpit | Đọc `01-perspective` → `02-design/design-archetypes.md` → cite ADR → áp dụng |
| Engineer onboard | Đọc 444 dòng AGENTS.md + 4 ARCHITECTURE.md trùng nhau → mất 2 ngày | Đọc `orientation/for-data-engineers.md` → đi theo `04-05-06-07` → 1 ngày |
| AI agent (READER) task mới | Nuốt 444 dòng AGENTS + tải sub-docs → bloated context | Đọc `orientation/for-ai-agents.md` → filter `audience: ai-agent` files → 3-5k tokens |
| AI agent (MAINTAINER) sửa/tạo doc | Phỏng đoán format, dễ phá frontmatter, không biết file đặt đâu, dễ duplicate content | Lớp A: gặp `docs/AGENTS.md` qua convention → Lớp B: thấy `maintainer_doc:` field → đọc charter + decision tree → copy template → fill → validator check → commit. Không phỏng đoán, không drift. |
| Maintain context "Shopee" | Đào 7 nơi rời rạc | Mở `contexts/shopee-channel-economics/README.md` → có map đầy đủ |

---

---

## 13. AI Agent là *first-class doc maintainer* — `_meta/` system

> Yêu cầu mới (thêm vào lần review 2026-04-26): tài liệu phải **đáp ứng cho AI agent đồng-phát triển**, không chỉ là reader. Phải có **tài liệu quy định cách thiết kế hệ thống doc** đặt đúng chỗ để bất kỳ agent nào có ý định cập nhật đều **tự động nhận ra** quy tắc.

### 13.1 Vai trò AI agent — định nghĩa lại

| Cấp độ | Tác vụ điển hình | Yêu cầu hệ thống |
| --- | --- | --- |
| **Reader** (đọc để trả lời) | "Dashboard CEO Pulse có những metric gì?" | Index files, navigation, frontmatter `summary` |
| **Reasoner** (đọc để quyết) | "Source nào cung cấp COGS?" | Cross-reference graph, `related:` field |
| **Maintainer** (sửa hoặc tạo file) | "Thêm dashboard inventory turnover" | Templates, decision trees, validation, schema |
| **System updater** (sửa cấu trúc doc) | "Thêm field `risk:` vào frontmatter" | Charter (immutable principles + meta-process) |

Đề xuất hiện tại đáp ứng tốt 2 cấp đầu, **chưa đủ** cho 2 cấp sau. `_meta/` system đóng vai đó.

### 13.2 Phân lớp meta-system

Tách **5 thành phần riêng biệt** (đừng trộn lẫn — mỗi loại có vòng đời khác nhau):

| Thành phần | File | Trả lời câu hỏi | Tần suất sửa |
| --- | --- | --- | --- |
| **Charter** | `_meta/doc-system-charter.md` | WHY — triết lý, principles | Hiếm (như ADR) |
| **Conventions** | `_meta/conventions.md` | WHAT — frontmatter spec, naming, length | Hiếm-trung bình |
| **Decision trees** | `_meta/decision-trees.md` | HOW — SOP cho tác vụ thường gặp | Trung bình (mỗi khi pattern mới) |
| **Templates** | `_meta/templates/*.template.md` | COPY-PASTE — frontmatter pre-filled | Cao (theo tệp loại mới) |
| **Schemas** | `_meta/schemas/*.{json,yaml}` | MACHINE RULES — validate được | Hiếm |

Lý do tách: sửa template là chuyện thường xuyên (thêm field hint), nhưng charter là chuyện hiếm cần consensus. Trộn lẫn = mỗi sửa nhỏ cũng rủi ro.

### 13.3 Charter — nội dung tối thiểu

`_meta/doc-system-charter.md` phải trả lời:

1. **Mục đích doc system** — phục vụ ai, để làm gì
2. **The narrative arc 9 bước** — vì sao thứ tự này (cite §2 đề xuất)
3. **Two-tier (macro/micro)** — ranh giới giữa `01-09/` và `contexts/`
4. **3 audience tiers + AI agent** — ai đọc gì
5. **Immutable rules** (5-7 rule cốt lõi):
   - Mỗi narrative file có YAML frontmatter chuẩn schema
   - Không định nghĩa metric/SQL ngoài `analytics-handbook/domains/`
   - Không duplicate nội dung — luôn link
   - Length budget (xem §8.5)
   - VN/EN policy theo §8.3
   - Cross-references dùng relative path
   - Mỗi folder có README.md làm index
6. **Boundary rules** — gì thuộc `_meta/`, gì thuộc `analytics-handbook/`, gì thuộc sub-component docs
7. **Meta-process** — cách sửa charter (PR + label + reviewer)

Charter dài ~200 dòng. **Không** chứa template hay SOP cụ thể.

### 13.4 Decision trees — SOP cookbook

`_meta/decision-trees.md` chứa các SOP — mỗi cái là **quy trình từng bước**, agent đọc xong biết chính xác phải động vào file nào theo thứ tự nào.

Top 10 SOPs cần ship trong v1:

| # | SOP | Áp dụng khi |
| --- | --- | --- |
| 1 | Add new dashboard | Tạo dashboard mới |
| 2 | Add new metric vào domain hiện có | Sửa logic metric |
| 3 | Add new domain | Mở rộng business area |
| 4 | Add new data source | Tích hợp source mới |
| 5 | Add new ADR | Quyết định kiến trúc mới |
| 6 | Add new context (per-context narrative) | Tạo `contexts/{X}/` mới |
| 7 | Deprecate dashboard / domain / source | Xử lý retire |
| 8 | Move / rename file | Tránh broken link |
| 9 | Update charter / conventions | Meta-process |
| 10 | Onboard new AI agent / new contributor | Discovery flow |

Mỗi SOP có dạng:

```markdown
## SOP-1: Add new dashboard

**Inputs:** dashboard name (slug), domain, audience, archetype
**Outputs:** 4-7 files created/updated, deployed Metabase resource

### Steps

1. **Identify domain** → check `analytics-handbook/domains/` xem đã có entry chưa.
   - Nếu chưa → SOP-3 (add new domain) trước.
2. **Decide collection** → đọc `analytics-handbook/collection_registry.yml`.
   - Quy tắc: `Executive | Marketing & Customers | Operations`.
3. **Tạo artifacts theo thứ tự**:
   - a. Domain entry (nếu cần): copy `_meta/templates/...` → `domains/{domain}.md`
   - b. Playbook: copy `_meta/templates/playbook.template.md` → `playbooks/{slug}.md`
   - c. Design spec: copy `_meta/templates/design-spec.template.md` → `designs/{slug}.md`
   - d. Blueprint: copy `_meta/templates/blueprint.template.md` → `blueprints/{slug}.md`
4. **Tạo context narrative** at `contexts/{slug}/`:
   - copy `_meta/templates/context-readme.template.md` + 6 child templates
5. **Update indexes**:
   - `02-design/dashboard-catalog.md` (thêm 1 row)
   - `contexts/README.md` (thêm 1 entry)
6. **Validate**:
   - Run: `python scripts/testing/validate_docs_structure.py`
   - Manual: `_meta/validation/checklist.md`
7. **Deploy** (nếu cần):
   - `node .skills/metabase-automation/scripts/deploy_from_markdown.js {blueprint}`
8. **Commit** với message: `docs(analytics): add {dashboard-name}`
```

Agent đọc SOP-1 xong **biết chính xác** phải làm gì — không phỏng đoán.

### 13.5 Templates — copy-paste-ready

Mỗi template có cấu trúc:
- YAML frontmatter pre-filled với placeholder `{TITLE}`, `{AUDIENCE}`, v.v.
- Tất cả section heading required
- Inline `<!-- HINT: ... -->` comments giải thích choices
- Reference example link đến file thực đang dùng template này

Ví dụ `_meta/templates/context-readme.template.md`:

```markdown
---
title: "{CONTEXT_TITLE}"
audience: [analyst, engineer, viewer]    <!-- HINT: chọn 1-3 từ enum -->
status: draft                             <!-- HINT: draft → active sau review -->
language: vi                              <!-- HINT: micro tier mặc định vi -->
last_modified: {YYYY-MM-DD}
summary: "{1 câu, max 200 ký tự}"
maintainer_doc: docs/_meta/doc-system-charter.md
template_used: docs/_meta/templates/context-readme.template.md
related_artifacts:
  playbook: ../../analytics-handbook/playbooks/{SLUG}.md
  design:   ../../analytics-handbook/designs/{SLUG}.md
  blueprint: ../../analytics-handbook/blueprints/{SLUG}.md
  dbt_models:
    - transformation/models/{PATH}
  source_docs:
    - ../../04-source-landscape/{SOURCE}/
---

# {CONTEXT_TITLE}

## TLDR (30 giây)

<!-- HINT: 1-2 câu trả lời câu hỏi cốt lõi mà context này giải quyết -->
{TLDR}

## Câu chuyện 1 phút

<!-- HINT: liệt kê 6 bước theo arc, mỗi bước 1 câu + link tới file con -->

1. **Vấn đề** (xem [01-perspective](./01-perspective.md)): {...}
2. **Thiết kế** (xem [02-design](./02-design.md)): {...}
3. **Sử dụng** (xem [03-usage](./03-usage.md)): {...}
4. **Nguồn** (xem [04-source](./04-source.md)): {...}
5. **Đích** (xem [05-target](./05-target.md)): {...}
6. **Chiến thuật** (xem [06-strategy](./06-strategy.md)): {...}

## Bạn cần làm gì?

| Mục đích | Đi đến |
| --- | --- |
| Đọc dashboard | [03-usage.md](./03-usage.md) → Metabase link |
| Sửa metric | [02-design.md](./02-design.md) → playbook ↑ |
| Sửa transform | [06-strategy.md](./06-strategy.md) → dbt model ↑ |

<!-- Reference example: docs/contexts/ceo-pulse/README.md -->
```

13 templates trong v1 (xem cây thư mục §3.1).

### 13.6 Schemas — machine validation

`_meta/schemas/frontmatter.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Doc Frontmatter",
  "type": "object",
  "required": ["title", "audience", "status", "language", "last_modified", "summary", "maintainer_doc"],
  "properties": {
    "title": {"type": "string", "minLength": 1},
    "audience": {
      "type": "array",
      "items": {"enum": ["viewer", "analyst", "engineer", "ai-agent", "all"]},
      "minItems": 1
    },
    "status": {"enum": ["active", "draft", "deprecated", "archive"]},
    "language": {"enum": ["en", "vi", "mixed"]},
    "last_modified": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "summary": {"type": "string", "maxLength": 200},
    "upstream_refs": {"type": "array", "items": {"type": "string"}},
    "related": {"type": "array", "items": {"type": "string"}},
    "maintainer_doc": {"const": "docs/_meta/doc-system-charter.md"},
    "template_used": {"type": "string"}
  }
}
```

Lợi ích: `validate_docs_structure.py` check schema mechanical — agent không thể commit file thiếu field hay sai enum.

### 13.7 Discovery mechanism — 3 lớp đảm bảo agent gặp charter

Agent có thể bắt đầu task bằng nhiều cách. Đảm bảo MỌI lối vào đều dẫn tới charter.

**Lớp A — AGENTS.md hierarchy (passive, by convention)**

```
Root AGENTS.md (~120 dòng)
├── Nói: "Editing docs/**? Read docs/AGENTS.md trước."
└── Slim: chỉ giữ multi-project rules + AI operation protocol

docs/AGENTS.md (NEW, ~80 dòng) ← discovery anchor
├── Top: "Bạn là agent đang edit docs? Quy trình:"
│       1. Đọc docs/_meta/doc-system-charter.md
│       2. Tìm SOP phù hợp ở docs/_meta/decision-trees.md
│       3. Copy template từ docs/_meta/templates/
│       4. Validate: scripts/testing/validate_docs_structure.py
├── 5 immutable rules ngắn gọn (đủ để skim)
└── Pointer chi tiết tới _meta/

docs/analytics-handbook/AGENTS.md (existing, slight slim)
└── "Domain-specific rules. Vẫn áp dụng docs/_meta/ charter."

(Tùy chọn) docs/contexts/AGENTS.md
└── "Per-context narratives. Theo template context-*.template.md."
```

Convention này **đã có sẵn** trong repo (transformation/AGENTS.md, analytics-handbook/AGENTS.md). Agent quen pattern.

**Lớp B — Frontmatter pointer (active, in every file)**

Mỗi narrative file có:
```yaml
maintainer_doc: docs/_meta/doc-system-charter.md
template_used: docs/_meta/templates/{X}.template.md
```

Agent Read file (nó nên Read trước khi Edit) → thấy ngay 2 field này → biết tham chiếu charter + template gốc.

**Lớp C — PreToolUse hook (optional, opt-in)**

`.claude/settings.local.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "...",
        "condition": "tool_input.file_path matches 'docs/.+\\.md$'",
        "inject": "REMINDER: Editing docs/. Charter: docs/_meta/doc-system-charter.md. Templates: docs/_meta/templates/. Validate: scripts/testing/validate_docs_structure.py"
      }
    ]
  }
}
```

Lớp C là **belt-and-suspenders** — bắn reminder bất kể agent có discover được Lớp A/B hay không. Khuyến nghị bật mặc định trong `settings.json` (project-level), agent có thể tắt qua `settings.local.json`.

**Tổng hợp**: Lớp A+B là *passive* (dựa vào agent đọc đúng); Lớp C là *active* (force inject). Default ship A+B+C; nếu C gây phiền, tắt C, vẫn còn A+B.

### 13.8 Validation tooling

Hai cấp:

**Manual checklist** (`_meta/validation/checklist.md`)

```markdown
Trước khi commit doc thay đổi:

- [ ] YAML frontmatter present, valid against schema
- [ ] `last_modified` updated to today
- [ ] `audience` field matches actual content
- [ ] All internal links resolve (no `[X](broken/path.md)`)
- [ ] Không trùng nội dung với file đã có (link thay vì duplicate)
- [ ] Length within budget (xem `_meta/conventions.md` §length-budget)
- [ ] `related:` field bidirectional (nếu A.related → B, thì B.related → A)
- [ ] Nếu thêm folder mới: có README.md làm index
- [ ] Nếu rename/move file: tất cả inbound link đã update
- [ ] Run: `python scripts/testing/validate_docs_structure.py` → pass
```

**Automated script** (`scripts/testing/validate_docs_structure.py`)

Check tự động:
1. Frontmatter present + valid against `_meta/schemas/frontmatter.schema.json`
2. All internal `[link](path)` resolve
3. Required folders exist (`_meta/`, `01-perspective/`, ..., `contexts/`)
4. `_meta/templates/` có đủ templates trong inventory
5. Cross-reference bidirectionality (A.related includes B ⟺ B.related includes A)
6. No file > length budget (warn, not error)
7. No duplicate `summary:` strings (early signal of content drift)

Output: report + exit code (0=pass, 1=warn, 2=error). CI có thể gate trên exit code.

**Optional pre-commit hook**: chạy validator tự động trên file `docs/**/*.md` đã staged.

### 13.9 Cross-reference graph (optional, advanced)

Auto-generate `_meta/generated/cross-ref-graph.json` từ `related:`/`upstream_refs:` của tất cả file. Agent có thể query: "Sửa file X ảnh hưởng những đâu?"

Generator: `scripts/maintenance/generate_doc_graph.py` chạy hằng ngày qua Dagster (asset `doc_graph_snapshot`). Phase này ship trong Phase 6 (cleanup) — không phải MVP.

### 13.10 Phase 0 — Build meta system FIRST

Đề xuất chèn **Phase 0** vào trước Phase 1:

**Phase 0 — Meta system (2-3 ngày)**
- Tạo `docs/_meta/` skeleton + README
- Viết `doc-system-charter.md` (~200 dòng — the constitution)
- Viết `conventions.md` (~150 dòng — frontmatter spec, naming, length, language)
- Viết `decision-trees.md` (~200 dòng — 5 SOP đầu: dashboard, source, domain, ADR, deprecate)
- Viết 13 templates trong `_meta/templates/`
- Viết schemas JSON + enum YAML
- Viết `_meta/validation/checklist.md`
- Viết `scripts/testing/validate_docs_structure.py` (basic version)
- Viết `docs/AGENTS.md` (~80 dòng — discovery anchor)
- Update root `AGENTS.md`: thêm "When editing docs/**, read docs/AGENTS.md first"
- (Optional) Setup PreToolUse hook trong `settings.json`

**Output Phase 0**: Hệ thống meta hoàn chỉnh. Mọi phase sau dùng templates + decision trees từ Phase 0. Không retrofit.

### 13.11 Cập nhật lộ trình tổng

| Phase | Tên | Ngày | Phụ thuộc |
| --- | --- | --- | --- |
| **0** | **Meta system (NEW)** | **2-3** | **None** |
| 1 | Skeleton + Front-of-house | 3-4 | Phase 0 |
| 2 | Source landscape | 2-3 | Phase 0 |
| 3 | Target & Strategy | 2-3 | Phase 0 |
| 4 | Implementation pointers + ops & dev | 1-2 | Phase 0 |
| 5 | Per-context narratives | 4-5 | Phase 0, 4 |
| 6 | Cleanup + slim AGENTS + archive + cross-ref graph | 1-2 | Tất cả |

**Tổng mới**: 15-22 ngày (cộng 2-3 ngày so với bản v1).

### 13.12 Lợi ích đo đếm được

| Metric | Trước | Sau |
| --- | --- | --- |
| Token agent burn để hiểu doc structure khi nhận task mới | 15-25k tokens (load AGENTS.md + Glob + Read mò) | 3-5k tokens (read docs/AGENTS.md + relevant template) |
| Tỉ lệ agent commit broken frontmatter | ~30% (no schema) | <5% (schema-validated) |
| Thời gian agent quyết "file này đặt ở đâu" | 5-15 min mò | <1 min (decision-trees.md) |
| Drift sau 6 tháng (số file lệch convention) | Có thể >20% | <5% (validator + checklist) |
| Onboard agent mới (đọc trước khi làm) | Không xác định, dễ miss rule | 1 file 80 dòng + charter 200 dòng |

### 13.13 Trả lời 2 yêu cầu mới (mapping)

| Yêu cầu | Giải pháp trong §13 |
| --- | --- |
| Tài liệu phải đáp ứng cho AI agent đồng-phát triển, nhanh chóng hiểu được và biết phải làm gì | §13.1 định nghĩa lại 4 cấp; §13.2-§13.6 cung cấp charter + conventions + SOP + templates + schemas; §13.8 validation; §13.10 Phase 0 build trước |
| Tài liệu quy định cách thiết kế hệ thống doc, đặt đúng chỗ, agent tự nhận ra | `_meta/doc-system-charter.md` (đặt ở `_meta/` sort đầu trong `docs/`); discovery 3 lớp ở §13.7 đảm bảo agent gặp charter qua Lớp A (AGENTS.md hierarchy), Lớp B (frontmatter pointer), Lớp C (optional hook) |

---

## Kết luận

Đề xuất này **không tạo content mới** quá nhiều — chủ yếu **tái cấu trúc + viết lại các "narrative bridge"** giữa các artifact đã có sẵn, cộng thêm **meta-system `_meta/`** để biến doc system thành self-maintainable bởi cả human + AI agent.

Lao động chính:
- **Phase 0** (NEW, 2-3 ngày): meta system — charter + templates + decision trees + validation
- **Phase 1** (3-4 ngày): front-of-house narrative
- **Phase 5** (4-5 ngày): 8 context narratives đầu tiên

Tổng ước tính: **15-22 ngày** làm việc tập trung.

Trước khi triển khai, đề xuất bạn:
1. Phản hồi 14 câu hỏi mở ở §9 (10 câu cũ + 4 câu mới về meta-system)
2. Confirm cấu trúc folder ở §3.1 (đặc biệt việc đánh số `01-09/` + `_meta/` + `docs/AGENTS.md` mới)
3. Confirm danh sách 8 context ưu tiên ở §4.5
4. Quyết định fate của `ANALYTICS_2SKILL_SPEC.md` (82KB) và `dlt-ingestion-skill-design.md`
5. **Confirm 3-lớp discovery (§13.7)**: Lớp A+B+C bật mặc định, hay chỉ A+B (C opt-in)?
6. **Confirm Phase 0 trước Phase 1**: build meta system trước, hay parallel?

Sau khi confirm, tôi sẽ tạo plan chi tiết per-phase ở `plans/260426-XXXX-docs-architecture-restructure/` với phase files (bao gồm `phase-00-meta-system.md` mới) để track progress.

---

## Unresolved questions

1. Có cần preserve git history khi `git mv` các file (dùng `git mv` đúng cách) — hay chấp nhận mất history?
2. `.claude/commands/` có command nào hard-code path docs không? Cần grep trước khi move.
3. Trong codebase, có file Python nào tham chiếu đường dẫn docs không (ví dụ `metabase_provisioner.py` đọc blueprint paths)? Cần audit trước Phase 5.
4. Bilingual policy — VN docs cũ có cần dịch sang EN trước khi archive, hay archive nguyên trạng?
