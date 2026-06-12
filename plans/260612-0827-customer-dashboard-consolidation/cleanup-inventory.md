# Cleanup Inventory — old customer artifacts to retire (P4 ONLY)

> ⚠️ **KHÔNG xóa cho tới khi P3 validate xong** 4 board mới (A/B/C/D) chạy đúng + không thiếu insight.
> Ghi trước để không sót. `customer_support_social_commerce` KHÔNG nằm trong scope (domain khác — giữ nguyên).

## A. Metabase dashboards cần archive/xóa (sau validate)

| ID | Tên | Collection | Thay bằng |
|---|---|---|---|
| 99 | Customer Action Queue [Retail] | 52 | A (Daily Action Queue) |
| 48 | Customer Operational [Retail] | 52 | chia A/B/C |
| 14 | Customer Retention & Lifecycle [Retail] | 52 | B (Retention & Cohorts) |
| 15 | Customer Intelligence Monthly [Cross] | 93 Analytics | C (Customer Intelligence) |
| 102 | Retail Activation Cockpit [Retail] | 52 | D (Customer Profitability) |

Cách xóa: archive dashboard qua Metabase API (`PUT /api/dashboard/:id {archived:true}`) — reversible. Cards con archive theo. KHÔNG hard-delete ngay; archive trước, hard-delete sau 1-2 tuần nếu không ai cần.

## B. Blueprint files cần xóa (docs/analytics-handbook/blueprints/)
- [ ] `customer_action_queue.md`
- [ ] `customer_operational_dashboard.md`
- [ ] `customer_retention_dashboard.md`
- [ ] `customer_intelligence_monthly.md`
- [ ] `retail_activation_cockpit.md`

## C. Design specs cần xóa (docs/analytics-handbook/designs/)
- [ ] `customer_action_queue.md`
- [ ] `customer_operational_dashboard.md`
- [ ] `customer_retention_lifecycle.md`
- [ ] `customer_intelligence_monthly.md`
- [ ] `retail_activation_cockpit.md`

## D. Playbooks cần xóa (docs/analytics-handbook/playbooks/)
- [ ] `customer_action_queue.md`
- [ ] `customer_operational_dashboard.md`
- [ ] `customer_retention_dashboard.md`
- [ ] `customer_intelligence_monthly.md`
- (cockpit không có playbook)

## E. Registry / governance cần update (docs/analytics-handbook/)
- [ ] `collection_registry.yml` — dưới `Marketing & Customers`: bỏ 3 dòng customer cũ (Action Queue, Operational, Retention) + cockpit; thêm sub-collection `Customer` với 4 board mới (A/B/D + relocate C). Bỏ `Customer Intelligence Monthly` khỏi `Analytics` (nếu chốt chuyển hẳn).
- [ ] `collection_organization.md` — cập nhật sơ đồ + đếm board; thêm note sub-collection Customer.
- [ ] `AGENTS.md` (handbook) — Collection Governance lookup table nếu có nhắc tên board cũ.

## F. Tham chiếu chéo cần rà (grep trước khi xóa)
Trước khi xóa mỗi file, `grep -rl "<tên board/file cũ>" docs/` để sửa link gãy (README, các guide, plan retail-reactivation tham chiếu action_queue).
- [ ] grep `customer_action_queue` · `customer_operational` · `customer_retention_dashboard` · `customer_intelligence_monthly` · `retail_activation_cockpit`
- [ ] Đặc biệt: `plans/260604-1125-retail-reactivation/` + `domains/customer.md` tham chiếu các board này.

## G. Cards mồ côi đã biết
- card 303 (Churn Rate Trend cũ) — đã archive 2026-06-12. Hard-delete cùng đợt.

---
**Definition of done P4:** 5 board cũ archived · 14 file (B+C+D) xóa · registry+org+AGENTS updated · 0 link gãy (grep sạch) · git commit.
