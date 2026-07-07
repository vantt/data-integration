# Phase 02 — Approach-script Health Integration (Blocked)

**Context:** [plan.md](plan.md) · Moved from `plans/archive/260706-0833-crm-health-profile-tag-governance/phase-04-script-integration-deferred.md`
**Blocked bởi:** `wh_approach_script` batch job architecture chưa rõ ràng (script generator batch pipeline refactor)

## What this phase will do

`wh_approach_script` hiện generate kịch bản static. Sau phase này, script generator đọc health tags của khách để:

### 1. data_gaps[] driven by health tags

```python
# Trong script generator
if not customer_health_domain_tags:
    data_gaps.append("health_domain")  # → S14 collect row xuất hiện
if not customer.custom.get("health_context_raw"):
    data_gaps.append("health_context")
```

### 2. Personalized talking_points[]

| Health domain tag | Talking point gợi ý |
|---|---|
| `tim-mach` | Natto K2: cải thiện đàn hồi thành mạch, giảm fibrinogen |
| `ho-hap` | Cordyceps: tăng VO2 max, hỗ trợ phục hồi hô hấp |
| `mien-dich` | Cordyceps + Vitamin C combo |
| `xuong-khop` | Collagen Type II + Glucosamine |

### 3. cross_sell[] aware of health profile

Khách có tag `tim-mach` + chưa mua Natto → Natto nằm trong `cross_sell[]` với rationale liên kết domain.

## Non-goal cho tới khi unblock

Không implement cho đến khi script generator được refactor sang batch pipeline có input schema rõ ràng.
