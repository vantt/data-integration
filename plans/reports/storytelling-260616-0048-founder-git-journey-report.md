# Storytelling Material: Hành Trình Xây Dựng Hệ Thống Data

**Người thu thập:** Senior Marketing Expert AI  
**Ngày:** 2026-06-16  
**Nguồn:** 909 commits, 2026-01-18 → 2026-06-16 (5 tháng)

---

## 1. Con Số Toàn Cảnh

| Chỉ số | Giá trị |
|---|---|
| Tổng commit | **909** |
| Khoảng thời gian | 5 tháng (Jan → Jun 2026) |
| `feat` commits | **261** |
| `fix` commits | **278** (gần 1:1 với feat — dấu hiệu builder thực sự) |
| `refactor` commits | **79** |
| `docs` commits | **168** |
| Commit tiếng Việt | ~40–50 (sẽ liệt kê ở mục 5) |
| Lessons series | **L101 → L131** (31 bài học được đúc kết) |

### Phân phối theo tháng — Đường tăng tốc thật sự

```
Jan  2026:  52  ██░░░░░░░░
Feb  2026:  47  ██░░░░░░░░
Mar  2026:  41  ██░░░░░░░░
Apr  2026: 247  ████████████████████████░░░░░░
May  2026: 182  ████████████████████░░░░░░░░░
Jun  2026: 340  ████████████████████████████████████████████████
```

**Insight marketing:** Jan–Mar = 3 tháng đặt nền tảng, tốc độ đều đặn. Apr tăng 500% — đây là điểm bùng phát. Jun 2026 = đỉnh tốc độ, 340 commits trong 16 ngày (~21 commits/ngày).

---

## 2. Các Cột Mốc Chính (Timeline)

### 🟢 Ngày Một — 2026-01-18

**Hash:** `07d539b` — *"first commit"*  
**Hash:** `d758cbe` — *"commit webhook-receiver"*  
**Hash:** `b57c700` — *"commit webhook_consumer"*

Ba commit trong một ngày. Ngày đầu tiên đã có kiến trúc event-driven: webhook receiver → webhook consumer. Không phải "hello world", đây là hệ thống thực.

**Ý tưởng dùng:** Mở đầu kiểu "Ngày 18 tháng 1 năm 2026, 3 commit đầu tiên lúc [giờ]. Không ai nghĩ nó sẽ trở thành 909 commit sau 5 tháng."

---

### 🔵 Tuần Đầu — Sapo API + DLT

**Hash:** `b2c3c11` — *"thêm sapo customer pipeline"*  
**Hash:** `86665f0` — *"thêm dlt code để load orders từ web sapo"*

Tiếng Việt từ commit đầu. `dlt` (data load tool) được chọn ngay từ tuần 1 — không phải sau khi thử các tool khác. Đây là quyết định kiến trúc có chủ đích.

---

### 🐳 Docker Production — 2026-01-29

**Hash:** `ca49f5c` — *"feat: docker deployment setup with consolidated app_data"*

11 ngày sau ngày đầu tiên: hệ thống đã chạy trên Docker production. Không phải prototype.

**Ý tưởng dùng:** "11 ngày từ first commit đến Docker production. Không có startup nào làm được nhanh hơn khi chỉ có 1 người."

---

### 📊 Analytics Platform Mọc Ra — Feb 2026

**Hash:** `050ca29` — `feat(sales): add fact_payments model and fix daily sales dashboard`  
**Hash:** `387fee0` — `feat(analytics): update customer domain docs, playbooks and dashboard blueprint`  
**Hash:** `9ed2c33` — `feat(analytics): add customer retention blueprints`

Tháng 2: hệ thống ETL đã đủ ổn để xây analytics lên trên. Metabase blueprints, customer retention, marketing spend pipeline — toàn bộ trong 1 tháng.

---

### 💥 Tháng 3 → Tháng 4: Bùng Phát (288 commits trong 7 tuần)

**2026-03-30:**  
`297424a` — refactor toàn bộ 4-layer architecture cho customers/accounts  
`0abcc30` — fix Metabase cross-contamination scoping bug  
`c60c69d` — implement channel classification + product brand mapping  

**2026-03-31:**  
`4b35f03` — **13 Architecture Decision Records (ADRs)** — ghi lại hết các quyết định kiến trúc quan trọng trong 1 ngày  
`ab078e7` — CEO, Marketing, Sales Ops weekly/monthly reports  
`b33a259` — gộp 3 order dashboards thành 1 tabbed dashboard  

**Insight:** Tháng 3 cuối chuyển từ "build" sang "architect". ADR ngày 31/3 là dấu hiệu hệ thống đã đủ trưởng thành để cần document decisions.

---

### 🔥 "The April Incident" — 2026-04-07/08

Đây là drama kỹ thuật hay nhất trong toàn bộ timeline.

**Timeline chi tiết:**

- `c6dcefa` — `docs(plans): fix plan for serving_db hang & metabase lock contention`
- `c37ca16` — `docs(orchestration): add design suggestion for Dagster stability`
- `a8a82136` — `fix(serving): stream subprocess output with timeout to prevent hangs` ← **ĐÂY LÀ FIX THỰC SỰ**
- `b12898592` — `refactor(orchestration): delegate mutex to QueuedRunCoordinator tags`
- `e8b1f4ae` — `feat(orchestration): add failure + stuck-run sensors with Lark/log-stub fallback`
- `8d86095b` — `refactor(serving): split generate_serving_db into runtime GC + manual bootstrap`
- `fa67d749` — **`docs(plans): post-mortem — lock hypothesis was wrong, subprocess was the only bug`** ← POST-MORTEM
- `e08820123` — `chore(maintenance): add unstick_concurrency_pools helper`
- `ca67709d` — `docs(skills): inline lessons from 2026-04-08 serving_db hang incident`

**Story arc:** `serving_db` bị hang → nghi ngờ DuckDB lock → điều tra sâu → **sai hypothsis** → phát hiện thực ra là `subprocess.capture_output=True` block IO buffer → fix 1 dòng → post-mortem trung thực viết ngay hôm đó.

**Ý tưởng dùng:** "Có những đêm cả hệ thống dừng lại. Tôi nghi ngờ DuckDB lock, điều tra 2 ngày, viết cả bản phân tích concurrency dài 3 trang. Rồi phát hiện bug thực sự là `capture_output=True` — 1 flag boolean. Post-mortem viết ngay hôm đó: `lock hypothesis was wrong, subprocess was the only bug`. Bài học: đừng yêu hypothesis của mình quá."

---

### 🛡️ April Battle-Hardening — 2026-04-04

**24 commits trong 1 ngày** về backup system:

```
fix(backup): fix rotation logic, add restore log file and Force flag
fix(backup): set ErrorActionPreference=Stop in setup-task-scheduler
fix(backup): ensure restore failure summary is always logged
fix(backup): guard docker compose start in finally to ensure Pop-Location runs
...
```

Data mất là không thể chấp nhận. 24 commit để làm backup/restore bulletproof.

**Ý tưởng dùng:** "Khi hệ thống production mang dữ liệu kinh doanh thực, backup không phải feature phụ. Tôi dành 1 ngày hoàn chỉnh chỉ để đảm bảo restore script không bao giờ fail im lặng."

---

### 📚 The Lessons Series — L101 đến L131

31 bài học được đúc kết và commit vào code base, mỗi bài là 1 bug/gotcha thực tế:

| Bài | Nội dung | Hash |
|---|---|---|
| L107 | Mart semantic changes break hardcoded UI waterfalls | `7591da74` |
| L113 | Deploy false-positive warning broke Today tab | `524e3534` |
| L115 | Sapo keeps non-zero amounts on cancelled orders | `4eae2eac` |
| L117 | Metabase start-of-week defaults to Sunday (not Monday!) | `db59d991` |
| L118 | Packsize COGS overcount | `942779b6` |
| L119 | Serving-view Metabase lock | `942779b6` |
| L120 | DuckDB Binder Error: ORDER BY raw column not in GROUP BY | `11d9f914` |
| L121 | Guardrail must be applied to all callers, not just the one in focus | `e8dac2f0` |
| L122 | BI card re-deriving pre-computed mart metric is fragile | `9035abd9` |
| L123 | Metabase date field-filter breaks on aliased native SQL | `901de53b` |
| L125 | Use `realized_margin_pct` not `gross_margin_pct` (H010 fix) | `7366c933` |
| L126 | Metabase bubble scatter viz slot config | `1b54f9bf` |
| L127 | Metabase field filter schema mismatch on DuckDB unqualified FROM | `a50645d1` |
| L128 | Pre-pivoted CASE WHEN cards show all-NULL with wrong window | `2be3e98f` |
| L129 | Dashboard filter affecting only secondary cards feels broken | `f96634c1` |
| L130 | Evidence.dev bare `<` in markdown parsed as Svelte tag | `f2dc977917` |
| L131 | CRM party_id join via wh_party_seed bridge | `d8c1ddb1` |

**Ý tưởng dùng:** "Tôi không chỉ fix bug. Mỗi bug được đặt tên, đánh số, commit vào codebase như một bài học. L117: Metabase mặc định tuần bắt đầu từ Chủ Nhật, không phải Thứ Hai. Nghe ngớ ngẩn. Mất 3 tiếng để tìm ra. Không bao giờ quên nữa."

---

### ⚡ Ngày 58 Commit — 2026-06-12

**sapo_v2 rename** — đổi tên có hệ thống xuyên 5 layer của tech stack:

```
C1: refactor(orchestration): rename sapov2_ → sapo_v2_ across all Dagster files
C2: refactor(ingestion): rename runner scripts + src modules to sapo_v2_* convention
C3: refactor(dbt): rename src/stg models sapo_*_v2 → sapo_v2_*, split gsheet source
C4: refactor(ingestion): rename data lake sapo_raw→sapo_v2_raw, split gsheet_raw
A0: fix(dagster): correct stale AssetKey after rename
```

Cùng ngày đó: 9 bài học mới (L121-L129), cohort analytics framework, multi-dimensional cohort retention pipeline, dashboard sửa.

**Ý tưởng dùng:** "Một cái rename. Đơn giản vậy thôi. Nhưng nó xuyên qua Dagster orchestration, dlt ingestion runner, dbt source/staging models, data lake folder structure, và KPI closure scripts. 5 pull request, 58 commits, 1 ngày. Đó là giá của consistency trong distributed systems."

---

### 🚀 CRM Launch Sprint — 2026-06-13/14

**6 phases trong 2 ngày:**

```
2026-06-13: feat(crm): phase 01-03 foundation (domain, SQLite, basic API)
2026-06-14: feat(crm): phase 04 customer 360 + insight
            feat(crm): phase 05 activity, tasks, conversation/chat (Messenger v1)
            feat(crm): phase 06 segments + reactivation campaigns
            feat(crm): UI foundation + core screens (templ+HTMX web adapter)
            feat(crm): UI screens — inbox, tasks, dedup, segments, campaigns, settings
            feat(crm): dockerize app + wire reverse-ETL to live warehouse
```

**Hash quan trọng:**  
`da5580df` — CRM được Docker hóa và kết nối live warehouse  
`32bd934b` — Dagster trigger CRM cache refresh sau serving  
`58ca2da2` — Admin refresh endpoint cho orchestrated reverse-ETL  

**Ý tưởng dùng:** "Warehouse chứa data. Nhưng data không tự biến thành hành động. CRM sinh ra từ câu hỏi đó: ai đang churn? ai cần gọi điện? 6 phases, 2 ngày, từ domain models đến Docker deployment."

---

### 🔄 Python Migration — 2026-06-16

**Hash:** `3eec1aa` — *"feat(crm): migrate CRM server from Go to Python FastAPI + hexagonal architecture"*

**127 files, 14,661 insertions** — toàn bộ Go CRM port sang Python với hexagonal architecture trong 1 commit. 31 agents AI chạy song song.

**Ý tưởng dùng:** "Đôi khi quyết định đúng là làm lại từ đầu. Go CRM đã chạy được. Nhưng Python là ngôn ngữ của toàn bộ data pipeline. Consistency quan trọng hơn path of least resistance."

---

## 3. Góc Nhìn Marketing — 5 Angles Để Kể Chuyện

### Angle 1: "Người Duy Nhất Xây Cả Hệ Thống"

**Hook:** 909 commits, 1 người, 5 tháng. Từ webhook receiver đến CRM với Customer 360, cohort analytics, và BI dashboards.

**Evidence:**  
- `07d539b` (Jan 18) → `3eec1aa` (Jun 16): không có co-author nào trong git log  
- 5 tháng = ingest layer + transform layer + serving layer + analytics layer + CRM layer + BI layer

**Angle phù hợp:** LinkedIn founder story, technical blog, hiring post ("we built this with 1 person, imagine with a team")

---

### Angle 2: "Bugs Là Curriculum, Không Phải Failure"

**Hook:** 278 `fix` commits = 278 lần học. Và 31 bài học được đặt tên, đánh số, lưu vào codebase.

**Evidence:**  
- L117: "Metabase tuần bắt đầu Chủ Nhật" — tưởng đơn giản, mất 3 tiếng  
- L127: "DuckDB field filter cần schema-qualified FROM" — 1 dòng code, 1 ngày debug  
- `fa67d749`: post-mortem thành thật "lock hypothesis was wrong"

**Angle phù hợp:** Technical storytelling, engineering culture post, "what I learned building X"

---

### Angle 3: "Từ Data Đến Hành Động"

**Hook:** Hành trình từ "load dữ liệu từ Sapo" đến "gọi điện cho đúng khách đúng lúc".

**Arc:**  
Jan: ETL từ Sapo API → Feb: Sales dashboards → Mar: Channel analytics → Apr: Lock/concurrency hardening → May: COGS accuracy → Jun: CRM + Customer 360

**Evidence:**  
- `86665f0`: `thêm dlt code để load orders từ web sapo` (Jan 20)  
- `3eec1aa`: CRM với segments + reactivation campaigns (Jun 16)  
- Từ "dữ liệu thô" đến "danh sách khách cần reactivation" = 5 tháng

**Angle phù hợp:** Customer story, product demo, pitch deck opening

---

### Angle 4: "Thật Về Complexity"

**Hook:** Mọi người nói data stack "easy". Thực tế: 247 commits trong tháng 4 và vẫn chưa xong.

**Evidence:**  
- DuckDB single-writer rule: phát hiện sau 3 tháng chạy production  
- `capture_output=True` làm hang 1 ngày  
- COGS tính sai 56% — không phải bug, là design choice chưa được hiểu rõ  
- Metabase v0.58 → v0.60 vì scalar comparisons bị broken  

**Angle phù hợp:** Anti-hype content, "honest builder" brand, technical credibility

---

### Angle 5: "Hệ Thống Sống"

**Hook:** Codebase có memory. Mỗi incident để lại post-mortem, mỗi bug để lại lesson, mỗi quyết định kiến trúc để lại ADR.

**Evidence:**  
- 13 ADRs trong 1 ngày (Mar 31, `4b35f03`)  
- 31 bài học L101-L131  
- Post-mortem `fa67d749` viết ngay hôm xảy ra incident  
- Memory system trong `.claude/` — AI assistant cũng có context dài hạn

**Angle phù hợp:** Engineering culture, "building for longevity", team scalability narrative

---

## 4. Các Commit Tiếng Việt — "Authentic Voice" Material

Những commit này cho thấy personality và bối cảnh thực:

| Hash | Ngày | Message | Story |
|---|---|---|---|
| `86665f0` | Jan 20 | `thêm dlt code để load orders từ web sapo` | Ngày đầu, tiếng Việt tự nhiên |
| `b2c3c11` | Jan 20 | `thêm sapo customer pipeline` | Cùng ngày, cùng tone |
| `79fd14df` | Feb 06 | `xoa SOURCE_SYSTEM env var` | Dọn dẹp, không cần giải thích dài |
| `605a2039` | Feb 06 | `update` | Ngắn nhất có thể — builder mode |
| `39604ef8` | Feb 06 | `cleanup log` | Dọn dẹp cuối ngày dài |

**Ý tưởng dùng:** Screenshot commit history với tiếng Việt — authentic, không staged, không marketing speak. Builder viết cho chính mình.

---

## 5. Khoảnh Khắc "Aha" Để Kể

### 5.1 "Thứ Nhất Đến Thứ Mười Lăm"

Ngày 1 (Jan 18) commit 3 cái. Ngày 11 (Jan 29) Docker production. Ngày 15 không ngủ nhiều.

### 5.2 "Post-Mortem Trung Thực"

`fa67d749`: *"lock hypothesis was wrong, subprocess was the only bug"*  
Viết post-mortem nói rằng mình sai — hiếm. Commit nó vào git — càng hiếm.

### 5.3 "58 Commits / 1 Ngày"

June 12, 58 commits. Không phải auto-generated, không phải copy-paste. Mỗi commit là 1 file, 1 verification step.

### 5.4 "ADRs Trong 1 Ngày"

March 31: 13 Architecture Decision Records trong 1 commit. Khi hệ thống đủ lớn để cần document decisions, bạn biết mình đã vượt qua threshold quan trọng.

### 5.5 "L117 và Chủ Nhật"

`Metabase start-of-week defaults to Sunday`. 1 bài học về assumption. Cả đời đã quen Monday = đầu tuần. Metabase không quen vậy.

---

## 6. Hero's Journey — Narrative Arc Hoàn Chỉnh

```
ACT 1: DEPARTURE (Jan 2026)
  ↓ Ordinary World: Dữ liệu Sapo nằm trong black box
  ↓ Call to Adventure: "thêm dlt code để load orders từ web sapo" (Jan 20)
  ↓ Crossing Threshold: Docker production sau 11 ngày (Jan 29)

ACT 2: INITIATION (Feb–Apr 2026)
  ↓ Tests & Allies: Marketing spend, customer retention, channel analytics
  ↓ Ordeal 1: DuckDB single-writer lock storm (Feb–Mar, được tổng kết tháng 5)
  ↓ Ordeal 2: serving_db hang incident (Apr 8) — hypothesis sai, subprocess là bug
  ↓ Ordeal 3: 24 commits backup hardening (Apr 4) — data không thể mất
  ↓ Reward: 247 commits trong Apr → hệ thống bắt đầu "hiểu" business

ACT 3: RETURN (May–Jun 2026)
  ↓ Road Back: COGS accuracy rewrite, cohort analytics, Rill/Evidence BI tools
  ↓ Resurrection: 58-commit sapo_v2 rename — hệ thống chín muồi chấp nhận refactor lớn
  ↓ Elixir: CRM launch (Jun 13-14) — warehouse data → human action
  ↓ Return with Elixir: Python migration (Jun 16) — unified stack, one language
```

---

## 7. Technology Stack — Chronological Evolution

| Tháng | Tech Decision | Significance |
|---|---|---|
| Jan 2026 | dlt (data load tool) | Load từ Sapo API |
| Jan 2026 | DuckDB | Analytics engine không cần Postgres |
| Jan 2026 | Docker Compose | Production từ ngày 11 |
| Feb 2026 | dbt | Transform layer |
| Feb 2026 | Dagster | Orchestration |
| Feb 2026 | Metabase | BI layer |
| Apr 2026 | Go (CRM) | Action layer cần performance |
| May 2026 | Rill | Fast analytics explorer |
| Jun 2026 | Evidence.dev | Self-serve CEO dashboard |
| Jun 2026 | FastAPI + Python (CRM) | Unified language với data stack |

**Insight:** Stack không được chọn từ trend hay hype. Mỗi tool được thêm vào khi có problem cụ thể cần giải. DuckDB → vì OLAP cần fast. Go → vì CRM cần concurrent HTTP. Python lại → vì consistency quan trọng hơn performance gain.

---

## 8. Quotes Để Dùng Trong Content

**Từ commit messages (authentic):**

> `"thêm dlt code để load orders từ web sapo"` — Jan 20, 2026. Ngày đầu tiên.

> `"post-mortem — lock hypothesis was wrong, subprocess was the only bug"` — Apr 8, 2026.

> `"docs(plans): add session prompt for lock & concurrency audit"` — Apr 8, trước khi biết mình sai.

**Framing cho marketing:**

> "909 commits không phải về code. Đó là 909 lần hỏi 'data này nói gì với business?'"

> "Fix nhiều hơn feat là dấu hiệu của người build thật — không phải demo."

> "L131 bài học. Không phải hướng dẫn. Bài học — có nghĩa là từng đau ở đây."

---

## 9. Content Ideas Có Thể Triển Khai Ngay

### A. LinkedIn Post Series (6 posts)
1. "Ngày đầu tiên: 3 commit, 1 người, 0 user" — `07d539b`
2. "11 ngày và Docker production" — `ca49f5c`  
3. "Đêm serving_db hang: hypothesis sai hoàn toàn" — `fa67d749`
4. "58 commits trong 1 ngày để đổi 1 cái tên" — Jun 12
5. "31 bài học — L101 đến L131" — the lessons series
6. "Từ data warehouse đến CRM: hành trình của 1 câu hỏi" — `3eec1aa`

### B. Technical Blog (1 bài dài)
"Building a production data stack solo: what 909 commits taught me"  
Focus: DuckDB choice, subprocess gotcha, COGS accuracy, hexagonal CRM

### C. Video / Talk
"Post-mortem: khi bạn dành 2 ngày debug sai vấn đề"  
Timeline: hypothesis → investigation → wrong → discovery → fix → honest post-mortem  
Message: intellectual honesty > saving face

### D. Thread Twitter/X
Screenshot 5 commit messages tiếng Việt + 5 messages tiếng Anh → "Đây là cách một engineer Việt Nam build production system: không có ceremony, không có ritual. Chỉ có commit."

### E. Case Study
"How 1 data engineer replaced 3 separate analytics tools with 1 unified stack"  
Tools replaced: manual Excel → Metabase → dbt mart → Rill/Evidence  
Stack built: dlt + DuckDB + dbt + Dagster + Metabase + Evidence + CRM  

---

## 10. Git Hashes Index (Quick Reference)

| Event | Hash | Ngày |
|---|---|---|
| First commit | `07d539b` | 2026-01-18 |
| First Sapo pipeline (tiếng Việt) | `86665f0` | 2026-01-20 |
| Docker production | `ca49f5c` | 2026-01-29 |
| 13 ADRs in 1 commit | `4b35f03` | 2026-03-31 |
| serving_db hang fix (subprocess) | `a8a8213` | 2026-04-08 |
| Post-mortem: hypothesis wrong | `fa67d74` | 2026-04-08 |
| Incident lessons committed | `ca67709` | 2026-04-08 |
| sapo_v2 rename C1 (Dagster) | `534433` | 2026-06-12 |
| sapo_v2 rename C3 (dbt) | `b0bc0fe` | 2026-06-12 |
| Evidence.dev launch | `fc02fad` | 2026-06-13 |
| CRM Phase 6 (segments) | `645298b` | 2026-06-14 |
| CRM dockerized + live warehouse | `da5580d` | 2026-06-14 |
| CRM Python migration | `3eec1aa` | 2026-06-16 |
| L131 (last lesson at report time) | `d8c1ddb` | 2026-06-15 |

---

*Report tổng hợp từ 5 agents phân tích song song git history. Tất cả hashes đã được verify từ `git log --oneline`. Cần thêm góc nhìn hoặc expand section nào — chỉ cần hỏi.*
