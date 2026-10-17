---
phase: 9
title: "ADR, rà tài liệu, allowlist cuối, dọn shadow"
status: pending
priority: P2
effort: "0.25d"
dependencies: [1, 2, 3, 4, 5, 6, 7, 8]
---

# Phase 9: Đóng plan

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** ADR mới trong `docs/decisions/` (số kế tiếp sau các ADR của Đợt 1; kiểm `docs/decisions/README.md` lúc làm, dự kiến 018) và `docs/decisions/README.md`; rà lần cuối `docs/architecture/modules.md`, `transformation/AGENTS.md`, `orchestration/packs/README.md`, `orchestration/connectors/README.md`, README các pack; `docs/operations/deployment.md` mục "Refactor deploys" (tên nhánh là tham số, không cố định `refactor/modularize-suite`); `roadmap.md` của plan cha (đánh dấu việc ưu tiên #1 đã xong, ghi việc còn lại).

## Việc làm

1. Viết ADR "Bật/tắt pack và điểm cắm lõi ↔ pack/tenant": `modules.yaml` là nguồn, `dbt_project.yml` là bản sao có kiểm; `pack_ref` + hợp đồng cột trong `pack_contracts()` + test; NULL khi pack tắt; `tenant_ref` + seed mặc định rỗng; `AFTER_SERVING_ASSETS`; khai báo khả năng bằng seed; lớp nhãn xem trước; phương án đã loại (truyền `--vars` ở mọi lời gọi dbt, hai bản model bật/tắt, `graph` lúc parse) và lý do.
2. Kiểm `scripts/checks/boundary_allowlist.yaml` không còn dòng `core -> pack:*`, không còn `dbt-seed` lõi → seed tenant, không còn `orch-import` connector → pack. Các dòng còn lại (pack → pack, pack → connector, `dbt-source` của crm, tenant hook `mart_data_quality`) có lý do và lối ra cập nhật.
3. Kiểm mọi link trong tài liệu mới trỏ tới file tồn tại.
4. Đối chiếu Acceptance Criteria trong `plan.md`, ghi kết quả từng mục.
5. Dọn: `scripts/shadow/cleanup.sh --all`, `git worktree remove` các worktree của plan (`refactor-safety-harness.md` §9.3). Dừng mọi tiến trình nền đã mở cho shadow.

## Verification

- `scripts/checks/run-all.sh` pass trên `main` sau D3.
- `git worktree list` chỉ còn checkout prod; thư mục shadow không còn.
- Ba lần deploy D1–D3 đều có nightly kế tiếp xanh (ghi ngày giờ vào `plan.md`).

**Đổi số:** không. Nếu ADR hay README đổi mà không đổi code thì không cần gate; commit tài liệu đi qua runbook như mọi thay đổi khác của checkout prod.

## Rollback

Revert commit tài liệu.
