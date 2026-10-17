---
phase: 8
title: "Sửa tài liệu lỗi thời, restore.ps1, ADR, đóng plan"
status: pending
priority: P2
effort: "0.5d"
dependencies: [1, 2, 3, 4, 5, 6, 7]
---

# Phase 8: Dọn tài liệu và đóng plan

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/operations.md` mục "Backup & Recovery" (`:296-376`); `scripts/backup/README.md` (bỏ mục "Legacy: Windows" hoặc trỏ tới thư mục legacy theo quyết định); `docs/operations/deployment.md` mục "Docker Deployment (Windows Production)" (`:529`) và "Production Checklist › Reliability"; `docs/operations/backup-restore-completeness-runbook.md` (Reference index: plan mới thay plan 260624); `crm/docs/backup-restore-runbook.md` §"What is NOT protected" (bỏ câu "local checkpoint, not full DR"); `docs/decisions/019-offsite-backup-and-recovery.md` (Accepted); `docs/decisions/README.md` (thêm dòng 019); `docs/README.md` hoặc mục điều hướng docs hiện có (thêm `backup-and-recovery.md`).

## Mục tiêu

Không còn tài liệu nào chỉ dẫn sai về backup/khôi phục; quyết định được ghi thành ADR; plan đóng với bằng chứng nghiệm thu.

## Việc cụ thể

1. **`operations.md:296-376`:** bảng "What to Backup" (Raw Parquet giữ 2 năm, `.dlt/pipelines/`, `.dagster_home/`, DuckDB 7 ngày), script `rsync` mẫu và các mục "Recover from dlt State Loss"/"Recover from DuckDB Corruption" sai với hệ thống hiện tại (dlt state nằm ở destination filesystem, `ingestion/src/utils/pipeline_runner.py:116-118`; dagster_home là named volume). Thay cả mục bằng một đoạn ngắn trỏ tới `docs/operations/backup-and-recovery.md`; giữ lại các bước khôi phục DuckDB còn đúng nếu có, chuyển vào tài liệu mới.
2. **`scripts/backup/{backup,restore,setup-task-scheduler}.ps1`:** theo câu hỏi mở 6 (đề xuất xoá; git giữ lịch sử). Nếu giữ: chuyển vào `scripts/backup/legacy-windows/` kèm README một dòng "không dùng, không bảo trì".
3. `deployment.md` mục Windows Production: ghi rõ lỗi thời, trỏ runbook dựng lại từ con số 0; không viết lại cả mục (ngoài phạm vi).
4. ADR 019: trạng thái Accepted, ghi kết quả thật (RTO đo được, kích thước repo, kết quả spike OAuth, thời gian build lại image đo được ở phase 6 vì D12 chọn không lưu image).
5. Kiểm liên kết và claim trong mọi tài liệu đã sửa (đường dẫn file tồn tại, lệnh chạy được với `--help`).
6. Báo cáo nghiệm thu `plans/261015-1140-backup-restore-dr/reports/acceptance.md`: đối chiếu từng tiêu chí 1–10 của plan.md với bằng chứng.
7. Báo coordinator các việc ngoài thư mục plan: đánh dấu `plans/260624-2010-warehouse-pipeline-dr-verified-restore/plan.md` là `cancelled` (superseded by `261015-1140-backup-restore-dr`); cập nhật roadmap mục "Backup, khôi phục và tái dựng hệ thống" và hai dòng ở "Việc vận hành độc lập"; ghi chú vào plan 260705 phase 00 về service `backup`.

## Files

- Modify: các tài liệu ở khối đầu.
- Delete hoặc Move: `scripts/backup/*.ps1` theo quyết định.

## Verification

- `grep -rn "dlt/pipelines\|\.dagster_home\|restore.ps1" docs scripts/backup/README.md` chỉ còn tham chiếu có chủ đích (ghi rõ trong báo cáo).
- Mọi liên kết tương đối trong các file đã sửa trỏ tới file tồn tại.
- Báo cáo nghiệm thu có bằng chứng cho 10/10 tiêu chí.

**Đụng prod:** không (chỉ tài liệu và xoá script không chạy trên prod). **Cần giờ user duyệt:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Xoá `.ps1` khi vẫn còn máy Windows nào đó dùng | Hỏi user (câu hỏi mở 6) trước khi xoá |

## Rollback

`git revert`.
