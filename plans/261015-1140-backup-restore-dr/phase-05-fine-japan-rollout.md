---
phase: 5
title: "Triển khai Fine Japan: SA + Shared Drive, nghi thức khoá, cài timer, backup đầu, T2 chứng kiến, 14 ngày quan sát"
status: pending
priority: P1
effort: "0.75d + 14 ngày quan sát"
dependencies: [4]
---

# Phase 5: Triển khai cho Fine Japan

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Triển khai cho một khách** (chuẩn bị phía khách cho đường SA + Shared Drive, thứ tự cài, nghi thức khoá, biên bản mẫu, nhật ký triển khai Fine Japan) và **Lịch** (giờ thật đã cài); `scripts/backup/backends/gdrive-sa.md` (bổ sung những gì gặp thật khi làm với Workspace của FJ); `plan.md` (nhật ký deploy D2, ngày bắt đầu và kết thúc 14 ngày).

## Mục tiêu

Backup ngoài máy của Fine Japan chạy hằng ngày lên Shared Drive của FJ, khoá do FJ giữ, có một lần khôi phục thử có người FJ chứng kiến bằng khoá của FJ, và 14 ngày liên tiếp xanh.

## Chuẩn bị phía Fine Japan (trước ngày deploy)

1. Admin Workspace FJ tạo Shared Drive `FG Backup – fine_japan`.
2. Tạo service account riêng cho backup (không dùng lại SA của Google Sheet trong `app_data/secrets`), bật Drive API; thêm email SA vào Shared Drive với quyền **Content manager**; tải khoá JSON và giao cho kỹ thuật viên cài đặt qua kênh an toàn (không qua chat). Nếu FJ muốn tự tạo SA thì FG gửi hướng dẫn `gdrive-sa.md`.
3. FJ chỉ định người giữ `key-customer` và `key-customer-2`, người ký biên bản, và người/tài khoản đứng tên healthchecks.io (câu hỏi mở 2 và 4).
4. Xác nhận dung lượng Shared Drive (dự kiến 3–10 GB, design §10).

## Các bước (giờ do user duyệt; tránh 02:30–04:00 cho bước 4–6)

1. **Deploy D2** theo runbook "Refactor deploys": merge nhánh có phase 2–4 (service `backup` profile `ops`, check `backup_freshness`). `docker compose build backup` (không đụng image khác). Kiểm instigator trước/sau như runbook.
2. Tạo `${FG_BACKUP_CONFIG_DIR}` với `env`, `rclone.conf` (remote `gdrive` dạng SA + `team_drive`), `sa.json` (0600).
3. **Nghi thức khoá** (có người FJ): `docker compose --profile ops run --rm backup init` → in hai khoá khách ngay trên giấy, niêm phong trước mặt người giữ; ký nhận vào biên bản; `key-host` ở `restic.pass`. Không chụp ảnh, không lưu file khoá khách.
4. Backup đầu tiên chạy tay `scripts/backup/offsite.sh` (upload ~2–3 GB, ghi thời gian), rồi `check-full` (đọc lại toàn bộ một lần).
5. **T2 chứng kiến:** `restore-drill.sh weekly --customer-key`, người FJ nhập `key-customer`. PASS → ghi snapshot id, thời gian, kết quả từng gate vào biên bản; FJ ký.
6. Cài timer: `install-units.sh --enable fg-offsite-backup,fg-restore-drill-weekly,fg-restore-drill-monthly`; tạo 3 check healthchecks; ping thử.
7. Quan sát 14 ngày: mỗi ngày kiểm `status/offsite.json`, `status/check.json`; hai lần T2 tự động Chủ nhật; T3 tháng đầu tiên. Lỗi nào thì sửa trên worktree, deploy lại theo runbook, **đếm lại 14 ngày từ đầu**.
8. Thử cảnh báo có chủ đích trong giờ duyệt: đổi tạm `RESTIC_REPOSITORY` sang một đường sai trong một lần chạy tay → có tin Lark; tạm disable timer một ngày trên một check healthchecks thử (không phải check thật) → healthchecks báo down.

## Files

Không có code mới. Biên bản bàn giao lưu ở chỗ FJ chọn (giấy và bản scan của FJ); repo chỉ ghi "đã ký ngày …, người ký …" trong nhật ký triển khai, không lưu khoá hay chữ ký.

## Verification

- Tiêu chí 1, 2, 3 (phần chứng kiến và hai T2), 6, 7 của plan.md đạt.
- Không có dòng nào trong log chứa giá trị khoá hay secret (`grep` theo độ dài/khuôn của khoá trong log sidecar và journal).
- Dashboard và nightly không bị ảnh hưởng: nightly 14 đêm xanh như trước, không asset check mới đỏ trừ `backup_freshness` khi có lỗi thật.

**Đụng prod:** có (deploy D2, cài timer, chạy backup và diễn tập trên máy prod). **Cần giờ user duyệt:** có, cho deploy D2 và buổi nghi thức khoá + T2 chứng kiến.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| SA tạo sau 04/2025 có quota 0 (nghiên cứu §3) | Chỉ ghi vào Shared Drive (quota tính cho Shared Drive, không cho SA); kiểm upload ở bước 4 |
| Upload lần đầu làm chậm mạng văn phòng FJ | Chạy ngoài giờ làm việc; `--limit-upload` của restic nếu cần |
| T2 tốn RAM khi đang có nhiều người dùng dashboard | Lần chứng kiến chạy trong giờ duyệt, theo dõi `free`; T2 tự động chạy sáng Chủ nhật |
| Người FJ làm mất bản in khoá ngay sau bàn giao | Hai khoá, hai người; `key-host` vẫn chạy; có thể `key add` khoá mới và `key remove` khoá mất (cần một khoá còn lại) |

## Rollback

`systemctl --user disable --now` ba timer; revert D2 theo runbook (service `backup` không chạy thường trực; check `backup_freshness` biến mất). Repo trên Shared Drive giữ nguyên, thuộc FJ.
