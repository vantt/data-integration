---
phase: 7
title: "Đường Gmail OAuth (drive.file, app FG publish) + hướng dẫn cài cho khách"
status: pending
priority: P2
effort: "0.75d"
dependencies: [2]
---

# Phase 7: Đường Google Drive cho khách dùng Gmail cá nhân

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `scripts/backup/backends/gdrive-oauth.md` (chuẩn bị phía khách, cấp quyền trên laptop có trình duyệt bằng `rclone authorize`, dán token, cấp lại khi token bị thu hồi, giới hạn); `docs/operations/backup-and-recovery.md` mục **Off-site** (bảng backend, khi nào dùng đường nào: Gmail, Workspace, S3 trong nước/NAS theo D4); ADR 019 (kết quả spike `drive.file`).

## Mục tiêu

Đường mặc định cho khách điển hình (Gmail cá nhân) chạy được và đã chứng minh, kể cả khôi phục từ một máy khác. Rollout thật ở khách thứ hai (roadmap, user chốt 15/10); phase này **không đụng prod** của Fine Japan.

## Thiết kế

- **App OAuth của FG:** một GCP project "FG Backup" do FG sở hữu; OAuth client loại Desktop app; scope **chỉ** `https://www.googleapis.com/auth/drive.file` (non-sensitive, verification cơ bản); màn hình consent **publish** (ở Testing mode token hết hạn sau 7 ngày, nghiên cứu §3). `client_id` không phải bí mật với app Desktop; `client_secret` của Desktop app theo Google cũng không coi là bí mật, nhưng vẫn để trong `rclone.conf` của khách, không commit vào repo (đặt trong tài liệu nội bộ của FG). FG sở hữu app nhưng không có quyền truy cập dữ liệu: token nằm trên máy khách và repo được mã hoá bằng khoá khách (D5).
- **Remote rclone:** `type = drive`, `client_id`/`client_secret` của app FG, `scope = drive.file`, `root_folder_id` để trống (rclone tạo thư mục `fg-backup/<tenant>` do chính nó sở hữu), `token` từ `rclone authorize "drive" <client_id> <client_secret>` chạy trên laptop có trình duyệt rồi dán vào máy chủ.
- **Token được làm mới:** rclone ghi lại `rclone.conf`, vì vậy `/config` mount rw (design §6).
- `scripts/backup/sidecar/backend_gdrive_oauth.sh`: kiểm remote trước khi chạy (`rclone about`, `rclone lsd`), báo lỗi rõ khi token bị thu hồi ("khách cần cấp quyền lại, xem gdrive-oauth.md §Cấp lại").

## Spike bắt buộc (câu hỏi chưa chắc của nghiên cứu §3)

1. Với `drive.file`, trên **một máy khác** dùng cùng OAuth client và cùng tài khoản Gmail, cấp quyền mới (token mới) có thấy và đọc được các file restic đã tạo từ máy cũ không?
2. Đổi mật khẩu Gmail hoặc gỡ quyền app thì lần chạy kế tiếp lỗi thế nào, cảnh báo có tới không?
3. Upload ~3 GB và `check --read-data-subset` với tốc độ Drive cá nhân.

Nếu (1) **không** đạt: đường Gmail phải giữ token cũ trong Recovery Sheet (không an toàn) hoặc dùng scope `drive` (restricted, cần verification CASA). Khi đó dừng, trình user phương án; mặc định thay thế là S3 trong nước hoặc NAS cho khách không có Workspace.

## Files

- Create: `scripts/backup/backends/gdrive-oauth.md`, `scripts/backup/sidecar/backend_gdrive_oauth.sh`, báo cáo spike `plans/261015-1140-backup-restore-dr/reports/spike-gdrive-oauth.md`.
- Modify: tài liệu ở khối đầu.

## Verification

- Spike 1–3 có kết quả và bằng chứng (ảnh chụp màn hình không chứa token, log đã che).
- Tài khoản Gmail thử của FG: `init` → `offsite` (dữ liệu thử, không phải dữ liệu khách) → máy thứ hai `rclone authorize` mới → `restore.sh extract` + `verify` PASS.
- Thu hồi quyền app → lần `offsite` kế tiếp FAIL với thông báo "cấp quyền lại", Lark nhận tin (webhook test).

**Đụng prod:** không. **Cần giờ user duyệt:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Google đổi chính sách scope hoặc quota | Backend chỉ là cấu hình; S3/NAS đã chứng minh ở phase 2 |
| App chưa verify hiện cảnh báo "unverified app" làm khách lo | Làm verification cơ bản cho `drive.file`; hướng dẫn có ảnh màn hình |
| Lẫn dữ liệu khách trong tài khoản Gmail thử | Chỉ dùng dữ liệu tổng hợp/thử |

## Rollback

Không đụng prod. Gỡ backend bằng cách xoá file; app OAuth có thể vô hiệu hoá trong GCP.
