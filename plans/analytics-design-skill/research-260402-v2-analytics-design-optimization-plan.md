# Ke hoach toi uu bo skill analytics-design va cac skill lien quan

Ngay: 2026-04-02
Dua tren: `plans/analytics-design-skill/research-260402-v1-analytics-design-skill-evaluation.md`

---

## Tom tat

Bao cao danh gia da xac dinh **7 diem yeu** va **4 viec uu tien**. Sau khi doc toan bo ~3,200 dong code/docs trong `.skills/analytics-design/`, `.skills/metabase-automation/`, `.claude/commands/`, `.agents/`, va mau artifact, toi de xuat **12 hanh dong cu the** nhom thanh **4 tang** theo thu tu uu tien.

---

## Tang 1: Deploy Fidelity (Uu tien cao nhat)

> Muc tieu: Thu hep khoang cach giua design intent va dashboard that.

### 1.1 — Them `#### Text:` support vao markdown parser

**Van de**: `deploy_from_markdown.js` (327 dong) hien chi parse 3 loai heading: `#### ❓ Question:`, `#### 📏 Metric:`, `#### Filter:`. Khi gap `#### Text:`, parser gan `metabase-pos` block cho question truoc do → pha layout.

**Giai phap**: Sua `parseMarkdownConfig()` (file rieng, import boi deploy script) de nhan dien `#### Text:` hoac `#### 📝 Text:` heading. Tao text dashcard (card_id = null) voi:

```json
{
  "card_id": null,
  "visualization_settings": {
    "virtual_card": {
      "display": "text",
      "visualization_settings": {}
    },
    "text": "Noi dung text annotation"
  }
}
```

**Anh huong**:

- Sua 1 file: parser (parseMarkdownConfig source — can xac dinh vi tri chinh xac)
- Sua 1 file: `deploy_from_markdown.js` — them logic tao text dashcard trong vong lap question processing (line 230-315)
- Cap nhat: `templates/blueprint_template.md` — them vi du `#### Text:` syntax
- Cap nhat: `STRATEGY.md` Section 5.1 — xoa workaround "add text cards manually"

**Do phuc tap**: Trung binh. Parser can phan biet text heading khoi question heading, va text card can position nhung khong can SQL/viz.

### 1.2 — Cap nhat blueprint template voi text annotation syntax

**Van de**: `templates/blueprint_template.md` (197 dong) khong co vi du text annotation. Agent tao blueprint se khong biet cach viet.

**Giai phap**: Them section vi du:

````markdown
#### 📝 Text: Revenue Performance This Week

This section tracks week-over-week revenue trends.

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
`` `
```
````

**Anh huong**: Sua 1 file: `templates/blueprint_template.md`

### 1.3 — Xoa cac comment "them thu cong" trong blueprint hien tai

**Van de**: Cac blueprint hien tai (vd: `ceo_weekly_pulse.md`) co comment `<!-- Text annotations to add manually after deploy -->`. Sau khi parser ho tro text, cac comment nay tro nen sai.

**Giai phap**: Sau khi 1.1 xong, chuyen cac comment thanh `#### 📝 Text:` block that su trong tung blueprint.

**Anh huong**: Sua 5-7 file blueprint trong `docs/analytics-handbook/blueprints/`

---

## Tang 2: Action Contract & Playbook Upgrade

> Muc tieu: Dashboard khong chi "giai thich tinh hinh" ma "thoi thuc hanh dong".

### 2.1 — Them Action Design section vao playbook template

**Van de**: `templates/playbook_template.md` (75 dong) co muc `## Actions` nhung chi la placeholder chung chung. Khong co cau truc bat buoc cho: signal → threshold → owner → action.

**Giai phap**: Thay the muc `## Actions` bang:

```markdown
## Action Triggers

| Signal           | Threshold    | Severity | Owner            | Immediate Action        | Follow-up           |
| ---------------- | ------------ | -------- | ---------------- | ----------------------- | ------------------- |
| Revenue drop WoW | > -10%       | Warning  | Sales Lead       | Check channel breakdown | Review pricing      |
| Revenue drop WoW | > -25%       | Critical | CEO + Sales Lead | Emergency standup       | Root cause analysis |
| Churn spike      | > 5% monthly | Warning  | CS Lead          | Check recent cohorts    | Outreach campaign   |
```

**Them**: Muc `## Reading Flow` (da co nhung can formalize):

```markdown
## Reading Flow

1. Bat dau o [Hero Card] — tra loi cau hoi chinh
2. Neu [condition] → chuyen sang [Tab/Card] de dieu tra
3. Neu [condition] → escalate cho [Owner] voi context tu [Card]
```

**Anh huong**:

- Sua 1 file: `templates/playbook_template.md`
- Sua 1 file: `SKILL.md` — Phase 1 instructions can nhac "Action Triggers table is required"
- Cap nhat playbook hien tai: 7-8 file trong `docs/analytics-handbook/playbooks/`

### 2.2 — Them Action Context vao design spec template

**Van de**: `templates/design_spec_template.md` (64 dong) co Composition Table nhung khong co cot nao lien quan den hanh dong. Card chi co "Communication" nhung khong co "What to do when this signal fires".

**Giai phap**: Khong them cot vao Composition Table (da du 9 cot). Thay vao do, them section rieng:

```markdown
## Action Map

| Card        | Signal | Condition    | Recommended Action                      |
| ----------- | ------ | ------------ | --------------------------------------- |
| Net Revenue | Drop   | WoW < -10%   | Check breakdown by channel/product      |
| Order Count | Spike  | WoW > +30%   | Verify no duplicate orders, check promo |
| Churn Rate  | Rise   | > 5% monthly | Alert CS team, review recent cohort     |
```

**Anh huong**:

- Sua 1 file: `templates/design_spec_template.md`
- Cap nhat design spec hien tai: 5-7 file trong `docs/analytics-handbook/designs/`

### 2.3 — Formalize Phase 1 instruction trong SKILL.md

**Van de**: SKILL.md Phase 1 chi noi "Tao moi theo templates/playbook_template.md" nhung khong nhan manh Action Triggers la bat buoc.

**Giai phap**: Them bullet trong Phase 1:

```
- Action Triggers table la BAT BUOC. Moi metric chinh phai co it nhat 1 threshold + owner + action.
- Reading Flow la BAT BUOC. Mo ta duong di tu hero card → investigation → escalation.
```

**Anh huong**: Sua 1 file: `.skills/analytics-design/SKILL.md`

---

## Tang 3: Visual Polish & Design System

> Muc tieu: Dashboard khong chi "dung" ma "dep, professional, polished".

### 3.1 — Mo rong VISUAL_LANGUAGE.md thanh day du design system

**Van de**: `VISUAL_LANGUAGE.md` (312 dong) cover color semantics, size semantics, va mot vai quy tac hierarchy. Nhung thieu nhieu yeu to can thiet cho "looks professional":

- Title/subtitle writing rules
- Spacing rhythm
- Density budget per archetype
- Annotation tone & copy guidelines
- Chart labeling rules
- Dashboard finish checklist (hien chi co Visual Polish Checklist 6 muc trong Section 6)

**Giai phap**: Them 4 section moi vao VISUAL_LANGUAGE.md:

**Section 7 — Title & Copy Discipline**:

```markdown
## 7. Title & Copy Discipline

### Card Titles

- Pattern: `[Metric] [Comparison]` — vd: "Net Revenue vs Last Week"
- Khong dung "Chart of...", "Graph showing..."
- Khong dung viet tat tru khi la term chuan (KPI, WoW, MoM, YoY, ARPU)
- Max 50 ky tu

### Card Subtitles

- Chi dung khi can giai thich dieu kien loc hoac don vi
- Pattern: `[Filter context] · [Unit]` — vd: "Excluding US channel · VND"
- Max 80 ky tu

### Section Headings (Text Annotations)

- Dung imperative voice: "Monitor Revenue Trends" khong phai "Revenue Trends Section"
- Dung sentence case, khong dung Title Case
- Khong ket thuc bang dau cham

### Annotation Content

- 1-2 cau ngan. Moi cau < 15 tu.
- Giai thich WHY section nay quan trong, khong phai WHAT no chua.
- Tone: direct, professional, khong casual.
```

**Section 8 — Spacing & Density**:

```markdown
## 8. Spacing & Density Budget

### Row Spacing

- Giua cac row: 0 (Metabase tu them gap)
- Text annotation luon bat dau o col 0, width full-width

### Density Limits by Archetype

| Archetype           | Max cards/view | Max rows | Max tabs |
| ------------------- | -------------- | -------- | -------- |
| Executive Pulse     | 10             | 5        | 2        |
| Operational Cockpit | 16             | 8        | 4        |
| Exploratory Tool    | 20             | 10       | 5        |

### Whitespace Rules

- Hero row: max 3 cards
- Khong dat > 4 cards cung 1 row (tru data-table)
- Moi view phai co it nhat 1 text annotation lam section divider
```

**Section 9 — Chart Labeling**:

```markdown
## 9. Chart Labeling Rules

### Axes

- Y-axis: luon co label + unit (vd: "Revenue (VND)")
- X-axis: an label neu la thoi gian (thang/tuan/ngay hien thi tu dong)
- Luon bat dau y-axis tu 0 cho bar charts. Line charts co the khong.

### Legends

- An legend neu chi co 1 series
- Dat legend o bottom neu > 3 series
- Khong de legend che chart area

### Data Labels

- Bat cho: donut (%), horizontal-bar (value), progress (goal)
- Tat cho: line-chart, area-chart (dung tooltip thay the)
- Gauge: hien thi value + unit trong center
```

**Section 10 — Dashboard Finish Checklist** (mo rong tu Section 6 hien tai):

```markdown
## 10. Dashboard Finish Checklist

Truoc khi finalize design spec, kiem tra:

### Content

- [ ] Moi card co title theo Title Discipline (Section 7)
- [ ] Moi KPI co it nhat 1 comparison (COMPARATIVE_FRAMING.md)
- [ ] Text annotations dung imperative voice
- [ ] Khong co card orphan (khong thuoc narrative flow nao)

### Layout

- [ ] Hero card o row dau tien, noi bat nhat
- [ ] Row widths sum = full-width (18 cols)
- [ ] Density trong gioi han archetype (Section 8)
- [ ] Moi view co it nhat 1 section divider (text annotation)

### Visual

- [ ] Color tokens nhat quan trong toan dashboard
- [ ] Khong dung > 5 mau distinct trong 1 view
- [ ] Structural color cho elements phu (dividers, muted labels)
- [ ] Size hierarchy ro: hero > supporting > detail

### Action

- [ ] Action Triggers table trong playbook day du
- [ ] Action Map trong design spec day du
- [ ] Reading Flow mo ta duong di tu hero → investigation → escalation
```

**Anh huong**: Sua 1 file: `.skills/analytics-design/VISUAL_LANGUAGE.md` (them ~150 dong)

### 3.2 — Them density & labeling guidance vao COMPOSITION_PATTERNS.md

**Van de**: `COMPOSITION_PATTERNS.md` (310 dong) co Section 6 "Spatial Grouping" nhung chi noi ve relative sizing, khong co density budget.

**Giai phap**: Them cross-reference toi VISUAL_LANGUAGE.md Section 8 trong COMPOSITION_PATTERNS.md Section 6:

```markdown
> **Density Budget**: Xem VISUAL_LANGUAGE.md Section 8 cho gioi han so card/row/tab theo archetype.
```

**Anh huong**: Sua 1 file: `.skills/analytics-design/COMPOSITION_PATTERNS.md` (them 3-5 dong)

---

## Tang 4: System Hygiene & Consistency

> Muc tieu: Xoa tool bias, dong bo entrypoints, lam sach artifact.

### 4.1 — Lam sach tool-specific language trong domains va playbooks

**Van de**:

- `domains/sales.md` dung `Logic (Metabase SQL)` va `Metabase Mapping`
- Playbooks nhac `Metabase Collection`, `Metabase "compare to previous period"`
- Vi pham nguyen tac tool-agnostic cua analytics-design skill

**Giai phap**:

- Domains: Doi `Logic (Metabase SQL)` → `Logic (SQL)` hoac `Calculation`. Xoa `Metabase Mapping` section.
- Playbooks: Doi `Metabase Collection` → `Collection`. Xoa references cu the toi Metabase UI features.

**Anh huong**:

- Sua 2-3 domain files
- Sua 5-7 playbook files
- Khong anh huong deploy (blueprint van giu Metabase-specific content)

### 4.2 — Dong bo `.agents/workflows/` voi 2-skill architecture

**Van de**:

- `.agents/workflows/create_metabase_blueprint.md` tham chieu `docs/metabase-workspace/` (khong ton tai)
- `.agents/workflows/deploy_metabase_blueprint.md` dung emoji headers loi thoi
- Hai workflow nay tao ra "he tu duy cu" song song voi he moi

**Giai phap**: 2 lua chon:

**Option A (Recommended)**: Xoa 2 workflow cu, giu chi `.claude/commands/` lam entrypoint duy nhat.

- Ly do: `.claude/commands/` da day du va dong bo. Giu 2 he thong tao confusion.
- Risk: Neu co agent dung `.agents/workflows/` thi se mat entrypoint.

**Option B**: Cap nhat 2 workflow cho khop voi 2-skill architecture.

- Nhieu effort hon nhung giu backward compat.

**Anh huong**: Sua hoac xoa 2-3 file trong `.agents/workflows/`

### 4.3 — Them Design Spec reference bat buoc trong blueprint

**Van de**: Khong phai moi blueprint deu co link tro ve design spec. Khi design spec update, khong co cach biet blueprint da outdated.

**Giai phap**:

- Them field `design_spec:` vao blueprint frontmatter (neu co)
- Hoac them convention: dong dau tien cua moi blueprint phai la `> Design Spec: [name](../designs/name.md) | Last synced: YYYY-MM-DD`
- Deploy script co the warn neu design spec moi hon blueprint (da co logic trong STRATEGY.md Section 5 nhung chua enforce)

**Anh huong**:

- Sua template: `templates/blueprint_template.md`
- Cap nhat blueprint hien tai: them header line

---

## Thu tu thuc hien de xuat

```
Phase I  (Deploy Fidelity)     Phase II (Action & Polish)     Phase III (Hygiene)
─────────────────────────      ──────────────────────────     ───────────────────
1.1 Parser: Text support       2.1 Playbook template          4.1 Clean tool bias
1.2 Blueprint template         2.2 Design spec template       4.2 Sync workflows
1.3 Update blueprints          2.3 SKILL.md Phase 1           4.3 Blueprint refs
                               3.1 VISUAL_LANGUAGE.md
                               3.2 COMPOSITION_PATTERNS.md
```

**Phase I** nen lam truoc vi no la bottleneck lon nhat: moi design tot den may cung mat gia tri neu deploy script khong the hien duoc narrative/text annotations.

**Phase II** co the lam song song nhieu hanh dong, vi cac template va knowledge doc doc lap nhau.

**Phase III** la cleanup — quan trong nhung khong urgent. Co the lam bat ky luc nao.

---

## Danh gia tac dong du kien

| Tieu chi        | Truoc | Sau Phase I | Sau Phase II | Sau Phase III |
| --------------- | ----- | ----------- | ------------ | ------------- |
| Design thinking | 8/10  | 8/10        | 9/10         | 9/10          |
| Action-driving  | 6/10  | 6/10        | 8/10         | 8/10          |
| Visual polish   | 5/10  | 6/10        | 8/10         | 8/10          |
| Deploy fidelity | 4/10  | 7/10        | 7/10         | 8/10          |

---

## Nhung thu KHONG nen lam

1. **Khong tao file rieng cho Visual Polish Spec** — mo rong VISUAL_LANGUAGE.md da du. Them file moi tang cognitive load cho agent.
2. **Khong them schema validation tooling** — chua can automation, discipline qua template va checklist la du cho giai doan nay.
3. **Khong rewrite ANALYTICS_2SKILL_SPEC.md** — file nay da tot, chi can de nguyen lam reference.
4. **Khong them review rubric scoring system** — checklist binary (pass/fail) hieu qua hon scoring khi agent tu danh gia.
5. **Khong ep semantic layer (Model → Metric → Question) luc nay** — day la cai tien infrastructure lon, khong lien quan truc tiep den skill optimization. De cho sprint rieng.
