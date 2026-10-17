---
title: Plan module hoá suite data platform
date: 2026-10-13
summary: "Research + plan 8 phase module hoá suite Fine Japan, red-team 15 phát hiện, roadmap dài hạn"
---

# Plan module hoá suite data platform

## What happened
- Research report `plans/reports/research-261013-1610-sme-commerce-data-platform-modularization.md`: kiến trúc đích 7 module (kernel, connectors, CDM, core, packs, tenant overlay, report templates), taxonomy là nơi chứa độ phức tạp thật của Fine Japan.
- Scout: 13/14 `std_*` chỉ đọc Sapo; ~25 model core/pack đọc thẳng `stg_*`/`src_*`; `definitions.py` 835 dòng import cứng; luật phân loại lặp và lệch nhau giữa `dim_customers`, `fact_orders`, `int_customer_benchmarks`.
- Plan `plans/261013-1751-modularize-data-platform-suite/` (8 phase, 15d) + `roadmap.md` (Đợt 1–8).
- Red team 4 góc nhìn: 37 phát hiện thô → 15; quan trọng nhất: ba chỗ tạo thư mục rolling theo tên thư mục `marts/intermediate`; không có khung giờ yên tĩnh để deploy (lịch */3); seed bị job prod ghi theo đường dẫn phẳng; shadow không chạy được offline nếu không chuẩn bị `dbt_packages`/extensions; golden có thể sạch giả do parquet thừa kế.

## Decision
- Taxonomy chỉ gom về module (macro theo biến thể, SQL giữ nguyên); luật thành dữ liệu để đợt bàn đầu ra.
- Contract `std_*` chưa enforce, dùng test warn.
- Đóng gói: tách thư mục trong một dbt project trước; image/GHCR theo plan 260705 sau.
- Hệ thống đang chạy vận hành hằng ngày như cũ: làm trên worktree + shadow, deploy bằng runbook dừng-ff-start, đóng băng khi nightly đỏ.
- Phát hiện phụ: lỗi alert trong `crm/ops/backup_crm.py` chỉ ảnh hưởng đường CLI; prod đã được Dagster failure sensor cảnh báo.

## Next steps
- User duyệt plan (AGENTS.md yêu cầu duyệt rõ trước khi thực thi).
- Bắt đầu phase 0 (safety harness) bằng `/ak:cook`.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
