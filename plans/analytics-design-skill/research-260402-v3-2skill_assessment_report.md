# Analytics 2-Skill Assessment Report

> Date: 2026-04-02
> Scope: `.skills/analytics-design/`, `.skills/metabase-automation/`, `.claude/commands/`, `docs/ANALYTICS_2SKILL_SPEC.md`, and current analytics-handbook artifacts
> Reviewer stance: dashboard design quality, actionability, narrative strength, and deployment realism

## Executive Summary

The 2-skill architecture is directionally correct and materially better than the prior "one skill does everything" setup. `analytics-design` already contains the right conceptual building blocks for impactful dashboards: domain-first metric thinking, archetypes, card roles, comparative framing, narrative structure, and visual hygiene.

However, the system is not yet reliably capable of producing dashboards that are consistently impactful, action-driving, beautiful, and professionally polished in production. The main gap is no longer "lack of design theory". The main gap is execution discipline across templates, commands, exemplars, and deployment tooling.

In short:

- Design intent: strong
- Artifact discipline: inconsistent
- Actionability: under-enforced
- Narrative deployment: partially supported but operationally broken
- Visual polish ceiling: good baseline, not yet premium/repeatable

## Scorecard

| Dimension | Assessment | Notes |
|---|---|---|
| Business storytelling | Strong in theory, uneven in practice | Good frameworks exist, but deployed exemplars do not consistently carry them through |
| Actionability | Weak to medium | Templates require action triggers, but current artifacts often omit them |
| Visual professionalism | Medium | Clean structure and semantics exist, but brand-level polish is not yet systematized |
| Technical deployability | Medium | Core deployment works for data cards; text/narrative layer is not round-trippable or idempotent |
| 2-skill separation | Medium | Spec is clear, but some docs/commands still leak old 1-skill thinking |

## What Is Already Strong

### 1. The design vocabulary is materially better than prompt-only dashboard generation

`analytics-design` has the core language needed for serious dashboard design:

- `DOMAIN_MODELING.md` separates metric meaning from charting
- `COMPOSITION_PATTERNS.md` defines archetypes, roles, narrative flow, grouping, and filters
- `VISUALIZATION_VOCABULARY.md` provides a stable tool-agnostic chart vocabulary
- `COMPARATIVE_FRAMING.md` enforces contextualization of KPIs
- `VISUAL_LANGUAGE.md` gives semantic tokens and design hygiene rules

This is enough to reason about message and communication, not just chart types.

### 2. The architecture correctly separates "intent" from "implementation"

The proposed Design Spec contract is the right abstraction:

- analyst skill defines purpose, roles, composition, comparison, and semantic tokens
- engineer skill translates those choices into Metabase-specific JSON and layout

This is the correct long-term architecture for portability and knowledge compounding.

### 3. Tooling support for text cards and tabs already exists

The system is not blocked by a total lack of support:

- `markdown_parser.js` parses `#### 📝 Text:` and `### 📑 Tab:`
- `deploy_from_markdown.js` builds text-card payloads and syncs tabs plus dashcards together
- `blueprint_template.md` documents text-card usage correctly

So the narrative/text problem is not "Metabase cannot do it" and not "the code cannot do it at all".

## Priority Findings

### P1. Action-driving behavior is specified, but not enforced in real artifacts

The templates require:

- `Action Triggers` in playbooks
- `Reading Flow` in playbooks
- `Key Insights`
- `Action Map` in design specs

But the current real artifacts do not consistently include them. This means the system often produces dashboards that describe performance instead of prescribing action.

Impact:

- dashboards stop at "interesting"
- owner, threshold, and next step are implicit
- the system does not consistently create decision-ready artifacts

### P1. Archetype discipline is being broken by canonical examples

The strongest example, `CEO Weekly Pulse`, is labeled `Executive Pulse` but behaves more like a multi-view review dashboard:

- 3 views
- detail table included
- about 26 visual elements across tabs

That directly conflicts with the skill's own rules for Executive Pulse:

- single view
- no tables
- at most about 10 cards

Impact:

- agents learn conflicting rules
- "pulse" dashboards can easily bloat back into cockpits
- visual hierarchy and decisiveness weaken over time

### P1. The narrative/text layer is not operationally reliable

This is the most important execution issue.

The codebase already supports text cards, but production blueprints still say things like "Text annotations to add manually after deploy". That means narrative has not been made part of the normal deployable artifact loop.

Impact:

- narrative is treated as optional polish instead of part of the dashboard contract
- dashboards lose section headings and message framing during implementation
- teams fall back to manual UI edits, which creates drift

### P2. The Metabase skill still leaks analyst decisions

Some Metabase skill docs and commands still instruct the agent to choose archetypes and visualization heuristics. That contradicts the 2-skill split, where those decisions should belong upstream in `analytics-design`.

Impact:

- agent can regress into tool-first design
- unclear ownership slows consistency
- spec says one thing, commands teach another

### P2. Visual polish is disciplined, but not yet elevated

The semantic token layer is strong for clarity and consistency. It is not yet enough to guarantee a premium or brand-consistent result:

- palette defaults are still close to Metabase defaults
- there is no explicit branded aesthetic system
- there is no screenshot-based acceptance rubric
- there is no exemplar library for "executive-grade" vs "operational-grade" dashboard quality

Impact:

- outcomes will usually be cleaner than before
- outcomes will not yet be reliably memorable, premium, or visually distinctive

## Why Automatic Deployment Of The Narrative/Text Layer Is Still Not Fixed

This issue persists because it is not one bug. It is a stack of workflow and architecture debts.

### Root Cause 1. Support exists in one place, but not in the working path most people use

There are two conflicting realities:

- `blueprint_template.md` clearly documents text-card support
- `create_blueprint.js` scaffolds only questions and tabs, not text cards
- existing blueprint exemplars still contain manual comments instead of `#### 📝 Text:` blocks

Result:

- the feature exists
- the normal authoring path does not reinforce it
- people keep generating or copying blueprints that preserve the old manual workflow

This is the first reason it "never gets fixed": the documented capability and the lived workflow diverged.

### Root Cause 2. Text cards are not idempotent on redeploy

`Dashboard.syncCards()` explicitly treats text cards as always-new:

- text cards are detected via `config.id === null`
- existing text dashcards are not matched
- they are always recreated on sync

Result:

- redeploying a blueprint with text cards can duplicate or churn text dashcards
- teams lose confidence in automated text deployment
- manual post-deploy edits feel "safer" than putting narrative in source

This is the core technical blocker. Until text cards can be matched and updated in place, narrative deployment will remain fragile.

### Root Cause 3. Capture/merge does not round-trip text cards

`capture_dashboard.js` currently renders only SQL-backed cards:

- it loops dashboard cards
- it resolves `cardCache[dc.card_id]`
- it skips non-SQL cards

Text cards do not survive capture/merge.

Result:

- narrative added in Metabase UI does not round-trip back into blueprints
- capture cannot produce a faithful deployable source-of-truth
- reverse flow for text/narrative is broken

This guarantees drift between live dashboards and repo artifacts.

### Root Cause 4. The capture command and spec are out of sync

The spec envisions:

- capture -> blueprint
- reverse translation -> design spec
- `status: draft-from-capture`

But the current capture command still frames itself as "save as deployable blueprint markdown" only.

Result:

- narrative is not part of the official capture contract
- reverse-generated design specs are not happening
- the migration path for legacy dashboards is stalled

### Root Cause 5. No validator forces narrative into required artifacts

There is no linter or CI gate checking:

- design spec has section annotations
- playbook has `Action Triggers`
- design spec has `Action Map`
- Executive Pulse respects density limits
- blueprint replaced manual comments with real text cards

Result:

- support can exist for months without becoming the standard
- artifact quality depends on author discipline
- the repo continues to accumulate stale examples that teach the wrong behavior

### Root Cause 6. The feature sits across both skills, so it falls between owners

Narrative/text is analytically owned by `analytics-design`, but implemented by `metabase-automation`.

Without a single explicit owner for the end-to-end text-card flow:

- analyst side assumes engineer can deploy it
- engineer side assumes artifacts will already contain it
- neither side closes the loop on idempotency, capture, migration, and enforcement

This is the organizational reason the issue keeps surviving.

## Bottom Line On The Text Layer

Automatic narrative deployment is not blocked by Metabase and not blocked by parser support.

It remains unfixed because:

1. the normal blueprint scaffolding path does not emit text cards
2. canonical blueprints still encode the old manual habit
3. redeploy is not idempotent for text cards
4. capture/merge drops non-SQL narrative cards
5. no validator or CI gate forces the new behavior
6. ownership is split across the analyst/engineer boundary

This is why the issue feels like it "never gets fixed": every layer is only half-finished, so the ecosystem keeps snapping back to manual edits.

## Recommended Roadmap

### P0. Stabilize narrative/text deployment as a first-class artifact loop

Target: 2-4 working days

Goal:

- make text cards safe to deploy
- make them safe to redeploy
- make them safe to capture

Concrete changes:

1. Add stable identity for text cards.
   - Recommended approach: inject a hidden marker into text markdown such as `<!-- codex:text-id:<slug> -->`
   - derive slug from `#### 📝 Text: <Name>` unless explicitly provided
   - on sync, match existing text dashcards by `dashboard_tab_id + text-id`

2. Update `Dashboard.syncCards()` to update existing text dashcards in place instead of always recreating them.
   - Current behavior should be replaced for text cards only
   - preserve dashcard IDs when matched

3. Extend `capture_dashboard.js` to capture text dashcards.
   - emit `#### 📝 Text:` blocks
   - preserve body markdown
   - preserve tab assignment and position
   - preserve hidden `text-id` marker

4. Replace manual text comments in canonical blueprints with real text blocks.
   - Start with:
     - `ceo_weekly_pulse.md`
     - `ceo_monthly_scorecard.md`
     - `sales_daily_operation.md`
     - `sales_ops_weekly_review.md`

5. Fix `create_blueprint.js` so it emits at least one text annotation per tab.
   - Better option: deprecate the inline scaffold and use `templates/blueprint_template.md` as the single source

Acceptance criteria:

- same blueprint can be deployed twice without duplicating text cards
- capture preserves text cards
- blueprint source contains actual `#### 📝 Text:` blocks, not manual comments

### P1. Enforce actionability and archetype discipline

Target: 3-5 working days

Goal:

- ensure dashboards are decision-driving, not just descriptive
- prevent archetype drift

Concrete changes:

1. Build a repo validator for analytics artifacts.
   - playbook must contain:
     - `Action Triggers`
     - `Reading Flow`
     - `How to Read`
   - design spec must contain:
     - frontmatter
     - `Views`
     - `Composition`
     - `Action Map`

2. Add archetype checks.
   - Executive Pulse:
     - max cards/view
     - single view by default
     - no detail table
   - Operational Cockpit:
     - tables allowed
     - multi-view allowed

3. Add blueprint checks.
   - fail if blueprint contains comments like "add manually after deploy"
   - warn if text annotations expected in design spec but absent in blueprint

4. Add pre-deploy validation hook.
   - run validator before `deploy_from_markdown.js`

Acceptance criteria:

- missing action sections are caught before merge/deploy
- pulse dashboards cannot silently become cockpits

### P1. Realign the 2-skill boundary in docs and commands

Target: 1-2 working days

Goal:

- make the 2-skill split true in practice, not just in spec

Concrete changes:

1. Remove or rewrite chart/archetype decision language in:
   - `.skills/metabase-automation/SKILL.md`
   - `.claude/commands/manage-metabase-resources.md`

2. Make these docs point back to `analytics-design` for:
   - archetype selection
   - viz selection
   - narrative structure

3. Keep Metabase docs focused on:
   - translation
   - JSON settings
   - API constraints
   - filter wiring
   - deploy behavior

Acceptance criteria:

- no Metabase command teaches the old 1-skill mindset
- analyst decisions happen upstream

### P2. Raise the aesthetic ceiling from "clean" to "executive-grade"

Target: 1-2 weeks

Goal:

- make outputs look intentionally designed, not merely tidy

Concrete changes:

1. Create a branded visual extension.
   - palette variants for executive, operations, marketing contexts
   - number-format conventions
   - title/copy examples in Vietnamese

2. Add a screenshot review rubric.
   - hierarchy clarity
   - glanceability
   - action clarity
   - annotation quality
   - clutter score

3. Create 3 canonical exemplars.
   - true Executive Pulse
   - true Operational Cockpit
   - true Exploratory Tool

4. Document anti-pattern examples.
   - wall of scalars
   - tab sprawl
   - generic section headings
   - tables inside pulse dashboards

Acceptance criteria:

- reviewers can reject "technically correct but visually mediocre" outputs
- design quality becomes teachable and repeatable

### P2. Complete the reverse-flow migration

Target: 1 week

Goal:

- make the repo recoverable from live dashboards
- support iterative redesign without drift

Concrete changes:

1. Implement `capture -> draft-from-capture design spec`
2. mark all reverse-generated specs with `status: draft-from-capture`
3. prioritize migration of high-value dashboards:
   - `ceo_weekly_pulse`
   - `ceo_monthly_scorecard`
   - `sales_daily_operation`
4. require analyst review before a captured spec becomes `final`

Acceptance criteria:

- live dashboards can be brought back into the 2-skill pipeline
- design intent can be reconstructed instead of manually re-authored each time

## Suggested Execution Order

Do not start with visual polish.

Recommended sequence:

1. P0 text-layer idempotency + capture
2. P1 artifact validator + deploy gate
3. P1 skill-boundary cleanup
4. P2 executive-grade visual system
5. P2 reverse-flow migration

## Final Recommendation

Treat the narrative/text layer as a release blocker, not a nice-to-have.

As long as headings, annotations, and message framing remain manual:

- the dashboard is not fully deployable from source
- reviewability is incomplete
- design intent drifts after every UI edit
- the 2-skill architecture never becomes truly closed-loop

The immediate win is not another new guideline. The immediate win is making text cards:

- source-controlled
- redeploy-safe
- capture-safe
- validator-enforced

Once that is done, the rest of the roadmap becomes much easier and far more credible.
