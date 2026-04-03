# Danh gia bo skill `analytics-design` va cac skill lien quan

Ngay danh gia: 2026-04-02
**Post-eval status review: 2026-04-03 — ARCHIVED**

---

## Ket qua sau khi thuc hien (so sanh voi 4 viec uu tien)

| # | Hang muc | Status | Evidence |
|---|----------|--------|----------|
| 1 | Text annotations + dashboard filters first-class trong deployer | **DONE** | `text-card-helpers.js` (idempotent marker), parser support `#### 📝 Text:` + `metabase-filter`, commit `3f9769d` |
| 2 | 2 pilot dashboards (CEO Weekly Pulse + Daily Sales) dong bo full artifact chain | **DONE** | 17 design specs upgraded (commit `634402a`), 17 blueprints synced (commit `00941cc`), 5 new dashboards deployed (commit `4f029ce`). Both CEO + Daily Sales co design + blueprint + designs dir |
| 3 | Action-design contract (Signal, Threshold, Owner, Action) | **DONE** | `design_spec_template.md` co Action Map table, 17 design specs upgraded voi imperative annotations + finish checklists |
| 4 | Visual Polish Spec | **DONE** | `VISUAL_LANGUAGE.md` sections 6-10: Visual Polish Checklist, Title & Copy Discipline, Spacing & Density Budget by archetype, Chart Labeling Rules, Dashboard Finish Checklist |

### Cac hang muc bo sung da hoan thanh

| Hang muc | Status | Evidence |
|----------|--------|----------|
| `.agents/*` dong bo voi 2-skill architecture | **DONE** | `create_metabase_blueprint.md` workflow rewritten theo 2-skill pipeline (commit `0937120`) |
| Text card idempotency (match existing, khong recreate) | **DONE** | `text-card-helpers.js` + commit `3f9769d` |
| Reverse-flow capture (live dashboard → design spec) | **DONE** | `generate-design-spec-from-dashboard.js` (commit `f2938ed`) |
| Analytics artifact validator | **DONE** | `validate-analytics-artifacts.js` (commit `90acab1`) |

### Van con mo (ongoing, khong phai blocker)

- CEO Weekly Pulse archetype discipline: van labeled `Executive Pulse` nhung co 3 views + tables → vi pham rule. La design decision, chua co commit fix.
- Premium visual polish / brand-level: semantic tokens da co, nhung chua co exemplar library hoac screenshot-based acceptance rubric.

---

## Pham vi danh gia

- `docs/ANALYTICS_2SKILL_SPEC.md`
- `.skills/analytics-design/*`
- `.skills/metabase-automation/*`
- `.claude/commands/*` lien quan
- `.agents/*` lien quan
- Mau artifact trong `docs/analytics-handbook/{domains,playbooks,designs,blueprints}/`

## Ket luan ngan

Bo `analytics-design` hien la mot khung **information design** tot, nhung chua phai mot **end-to-end dashboard design system** du chin.

No du manh de lam dashboard co thong diep, hierarchy va narrative tot hon mat bang chung; nhung o trang thai repo hien tai, no **chua du** de dam bao output cuoi cung luon that impactful, thoi thuc hanh dong, dep va chuyen nghiep.

Neu cham khat khe:

- Thiet ke tu duy: `8/10`
- Kha nang thuc day hanh dong: `6/10`
- Visual polish: `5/10`
- End-to-end fidelity khi deploy that: `4/10`

## Vi sao bo khung nay co tiem nang tot

### 1. Chan dung dung van de cot loi

Spec nhan dien dung benh goc cua dashboard cu:

- `Wall of Scalars`
- thieu visual hierarchy
- thieu comparative framing
- chon sai visualization
- khong co narrative structure

Dieu nay duoc neu ro trong [docs/ANALYTICS_2SKILL_SPEC.md](../../docs/ANALYTICS_2SKILL_SPEC.md).

### 2. Tach dung hai mindset

Kien truc `2 skills` tach:

- `analytics-design` = analyst brain, tool-agnostic
- `metabase-automation` = engineer brain, tool-specific

Day la huong dung vi no tao ra `Design Spec` lam contract trung gian giua y do thiet ke va implementation.

### 3. Co ngon ngu chung cho dashboard design

`analytics-design` da co nhung manh quan trong:

- `COMPOSITION_PATTERNS.md`: archetype, hero/supporting/trend/breakdown/detail, narrative flow, view grouping
- `VISUALIZATION_VOCABULARY.md`: standard viz vocabulary
- `VISUAL_LANGUAGE.md`: semantic tokens cho color/size
- `COMPARATIVE_FRAMING.md`: KPI phai co context, khong duoc dung so tran

Bo khung nay du tot de ep agent suy nghi theo kieu:

- dashboard nay phuc vu ai
- cau hoi chinh la gi
- hero la gi
- nguoi doc nhin vao dau truoc
- moi KPI dang so sanh voi cai gi
- card nay truyen dat thong diep gi

### 4. Mau redesign da cho thay gia tri that

`docs/analytics-handbook/designs/sales_daily_operation.md` la bang chung tot nhat:

- nhan ra dashboard cu thieu narrative flow
- dat lai hero ro rang
- thay scalar bang gauge va single-value-with-trend
- giam pie charts
- them annotation sections
- bien dashboard thanh mot cau chuyen co dau-cuoi

Day cho thay skill khong chi noi ly thuyet, ma da tao ra mot design intent tot hon dang ke.

## Tai sao no chua du de dam bao dashboard "impactful, action-driving, dep, chuyen nghiep"

### 1. Narrative la first-class trong design, nhung second-class trong deploy

Day la diem yeu lon nhat.

Trong `analytics-design`, `text-annotation` la thanh phan cot loi cua storytelling.
Nhung o tang `metabase-automation`, parser hien:

- khong ho tro text annotation headers
- khong xu ly dashboard-level filters trong markdown parser

Ket qua:

- design spec muon co section headings va narrative
- blueprint phai de comment "them text annotations thu cong sau deploy"

Dieu nay lam mat fidelity giua design intent va dashboard that. Mot dashboard impactful khong the phu thuoc vao thao tac thu cong cho phan narrative chinh cua no.

### 2. Executive flagship case chua chung minh duoc quality moi

Chinh spec mo ta `CEO Weekly Pulse` cu la mot dashboard bi "wall of scalars".
Va blueprint hien tai trong `docs/analytics-handbook/blueprints/ceo_weekly_pulse.md` van cho thay rat nhieu scalar/table.

Noi cach khac:

- framework moi da chan benh dung
- nhung artifact flagship chua duoc nang cap de chung minh framework moi ship ra output tot hon mot cach nhat quan

Neu dashboard cap CEO chua that su lot xac, rat khoi khang dinh bo skill da du suc tao dashboard "impactful".

### 3. Actionability chua duoc dac ta thanh contract bat buoc

Template playbook co muc `How to Read` va `Actions`.
Day la mot y tuong rat dung.

Nhung o artifact that, phan nay chua duoc implementation nghiem tuc va nhat quan.
Framework hien tai moi ep:

- audience
- goal
- archetype
- comparison
- composition

Nhung chua ep moi signal phai di kem:

- threshold / guardrail
- owner
- recommended action
- muc do uu tien
- hanh dong ngay / hanh dong dieu tra / hanh dong theo doi

Vi vay output de roi vao kieu:

- "dashboard giai thich tinh hinh rat tot"
- nhung "thoi thuc hanh dong" thi chua du luc

### 4. Visual polish chua duoc mo ta den muc design system

`VISUAL_LANGUAGE.md` moi cover:

- color semantics
- size semantics
- mot vai quy tac ve hierarchy va accessibility

No chua cover sau:

- title writing rules
- subtitle / annotation tone
- spacing rhythm
- density budget cho tung archetype
- typography hierarchy
- khi nao dung muted vs hide labels
- quy tac sap xep chart titles de tao cam giac premium
- dashboard QA checklist cho "looks finished"

No giup dashboard "do xau hon", nhung chua du de dashboard "dep, professional, polished".

### 5. Boundary "tool-agnostic" chua sach

Theo spec, `domains/` va `playbooks/` nen do `analytics-design` so huu va mang tinh tool-agnostic.

Nhung artifact hien tai van con nhieu dau vet Metabase:

- `domains/sales.md` van dung `Logic (Metabase SQL)` va `Metabase Mapping`
- mot so playbook van chua visualization configs kieu Metabase
- playbook CEO van nhac truc tiep toi `Metabase "compare to previous period"`

Nghia la analyst brain van chua tach sach khoi tool bias.
Dieu nay se lam giam chat luong reasoning, vi agent co the nghi theo display cua Metabase truoc khi nghi theo communication goal.

### 6. Orchestration chua dong bo giua `.claude` va `.agents`

`.claude/commands` da theo pipeline 2 buoc:

- Phase 0-6 = `analytics-design`
- Phase 7-10 = `metabase-automation`

Nhung `.agents/workflows` van mang logic cu:

- tool-first
- chon `line/bar/pie` truc tiep
- chua that su dua `Design Spec` thanh output bat buoc

Nghia la cung mot repo, nhung neu di vao entrypoint khac nhau thi agent co the sinh ra output khac chat luong. Day la dau hieu he thong chua on dinh.

### 7. Semantic layer strategy noi dung thi dung, artifact that thi chua theo

`metabase-automation/STRATEGY.md` noi rat dung:

- uu tien Model -> Metric -> Question
- dashboard questions khong nen day raw SQL

Nhung blueprint that, dac biet `sales_daily_operation.md`, van la rat nhieu `Question` dung native SQL truc tiep.

Dieu nay khong lam dashboard xau ngay lap tuc, nhung no lam giam:

- tinh nhat quan metric
- kha nang reuse
- do tin cay khi mo rong
- chat luong chuyen nghiep cua whole analytics system

## Danh gia theo tieu chi user dat ra

### 1. Co dap ung duoc "truyen tai thong diep" khong?

**Co, kha tot.**

Ly do:

- co narrative flow
- co hero/supporting roles
- co section headings
- co comparative framing
- co archetype theo audience va time budget

Neu agent thuc thi dung framework nay, dashboard se co thong diep ro hon rat nhieu so voi cach build bang metric list + chart list.

### 2. Co dap ung duoc "thoi thuc hanh dong" khong?

**Moi mot phan.**

Ly do:

- framework da dung huong khi nhac toi audience, decision enabled, actionability
- nhung chua co action contract du manh trong artifact schema

Dashboard se giup "thay van de" tot hon.
Nhung de "ep hanh dong" mot cach nhat quan, can them lop explicit:

- Neu X xau -> ai xu ly -> trong bao lau -> mo card nao tiep -> quyet dinh nao duoc phep dua ra

### 3. Co dap ung duoc "dep" khong?

**Chua du.**

No co kha nang tao dashboard hop ly va sach se hon.
Nhung "dep" o muc executive/professional can them mot visual system day du hon:

- style discipline
- copy discipline
- whitespace discipline
- polish QA
- implementation fidelity

Hien tai framework nghi nhieu ve "chon dung chart" hon la "tao mot san pham thi giac cao cap".

### 4. Co dap ung duoc "chuyen nghiep" khong?

**Mot nua.**

Ve mat tu duy analytics: kha chuyen nghiep.
Ve mat system delivery: chua du chuyen nghiep, vi con:

- parser limitations
- sync issue giua docs/artifacts
- stale playbooks
- entrypoint khong dong bo
- deploy phu thuoc thao tac thu cong cho annotation/filter

## Danh gia tung cum tai lieu / skill

### `docs/ANALYTICS_2SKILL_SPEC.md`

Rat manh ve:

- chan doan dung van de
- thiet ke architecture dung
- contract ro rang
- phase ownership ro

Day la file co chat luong tu duy cao nhat trong cum nay.

### `.skills/analytics-design/*`

Day la phan manh nhat cua he thong moi.

No du suc lam "analyst operating system" cho viec thiet ke dashboard.

Diem tot nhat:

- co abstraction dung
- co discipline dung
- giam nguy co chart-chasing

Diem thieu:

- chua formalize action design
- chua formalize visual polish
- chua co review rubric cuoi cho dashboard quality

### `.skills/metabase-automation/*`

Manh ve:

- implementation mapping
- size/color/viz translation
- semantic layer strategy
- awareness ve Metabase limitations

Yeu o cho:

- delivery fidelity thap hon design intent
- parser limitation va workaround thu cong
- artifact output that chua theo day du strategy de xuat

### `.claude/commands/*`

Da update kha dung voi 2-skill architecture.

Diem tot:

- `/design-dashboard` tach Phase 0-6
- `/create-metabase-blueprint` bat buoc di qua design truoc implementation

Day la huong dung.

### `.agents/*` lien quan

Dang lech so voi architecture moi.

Neu khong dong bo phan nay, se ton tai 2 he tu duy song song:

- mot he moi, design-first
- mot he cu, Metabase-first

Day la nguy co lon ve consistency.

## Phan doan cuoi cung

Neu cau hoi la:

> "Bo skill nay co du de nghi ra dashboard tot khong?"

Thi cau tra loi la:

**Co, kha tot.**

Neu cau hoi la:

> "Repo nay hien da du de ship ra dashboard that su impactful, action-driving, dep va professional mot cach nhat quan chua?"

Thi cau tra loi la:

**Chua.**

No dang o trang thai:

- tu duy da di dung huong
- framework da co cot song tot
- nhung implementation system va quality guardrails chua theo kip

## 4 viec uu tien cao nhat neu muon nang cap thanh he thong that su manh

### 1. Bien `text annotations` va `dashboard filters` thanh first-class trong deployer

Khong the de storytelling phu thuoc vao thao tac thu cong neu muon dashboard cuoi cung dat chat luong cao.

### 2. Chon 2 dashboard pilot de dong bo full artifact chain

De xuat:

- `CEO Weekly Pulse`
- `Daily Sales Dashboard`

Can dong bo:

- domain
- playbook
- design spec
- blueprint
- deployed dashboard

Muc tieu: chung minh framework moi khong chi noi dung, ma co the ship output tot hon that.

### 3. Them action-design contract

De xuat them vao playbook/design spec:

- Signal
- Threshold
- Why it matters
- Owner
- Immediate action
- Follow-up action

Luc do dashboard moi that su "thoi thuc hanh dong".

### 4. Tao them mot `Visual Polish Spec`

Nen co them mot tai lieu rieng cho:

- title/subtitle writing
- spacing rhythm
- density limits
- annotation tone
- chart labeling rules
- dashboard finish checklist

Neu khong co lop nay, output se dung nhung kho dep.

## Ket luan mot dong

`analytics-design` la bo nao phan tich rat co trien vong va da vuot xa kieu "chon vai chart roi ghep lai"; nhung de tao ra dashboard that su impactful, action-driving, dep va professional mot cach nhat quan, repo hien tai van can mot vong nang cap lon o tang orchestration, deploy fidelity, action contract va visual polish.
