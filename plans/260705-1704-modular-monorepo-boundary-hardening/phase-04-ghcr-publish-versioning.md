# Phase 4 — GHCR publish + per-component versioning

**Depends on:** Phase 1 (build contexts đã chuẩn), Prereq B (PAT + docker login)
**Mục tiêu:** Mỗi component build → tag version riêng → push GHCR. Máy prod chỉ pull. Đây là forcing function chính của kỷ luật release: mỗi lần push phải trả lời "cái này đổi gì, phá contract nào không".

## Context

- Repo hiện tag global `v2.x.x` — giữ nguyên cho lịch sử; từ giờ thêm tag per-component.
- 6 images publish: `data-platform`, `crm`, `crm-drill-runner`, `metabase`, `rill`, `evidence`. (detailView retired — skip. fileserver dùng `caddy:alpine` gốc — không cần publish.)
- GHCR: private mặc định khi push lần đầu; giữ private. Máy dev cần PAT `write:packages`, máy prod `read:packages`.

## Design

- **Image name:** `ghcr.io/<OWNER>/<component>` — `<OWNER>` chốt theo Unresolved Q1 của plan.md.
- **Git tag scheme:** `<component>-vX.Y.Z` (vd `crm-v1.0.0`, `data-platform-v1.0.0`). Bắt đầu mọi component từ `v1.0.0`.
- **Image tags:** mỗi lần release push 2 tags: `X.Y.Z` + `latest`. Prod pin `X.Y.Z`, KHÔNG bao giờ dùng `latest` trên prod.
- **SemVer nghĩa gì ở đây:** MAJOR = phá data/API contract với component khác (đổi schema serving view, đổi webhook payload); MINOR = feature nội bộ; PATCH = fix. Quy ước này ghi vào boundary doc (Phase 6).

## Files

- **Create** `tools/release-component.ps1`:
  ```
  .\tools\release-component.ps1 -Component crm -Version 1.0.0 [-DryRun]
  ```
  Logic: (1) validate working tree sạch + component hợp lệ (bảng component→context/dockerfile hardcode trong script); (2) `docker build` đúng context; (3) tag `ghcr.io/<owner>/<component>:{X.Y.Z,latest}`; (4) `docker push` cả 2; (5) `git tag <component>-vX.Y.Z` + push tag. `-DryRun` dừng trước push.
- **Modify** `.env.example` (tạo nếu chưa có) — thêm `GHCR_OWNER=<owner>`, `TAG_CRM=`, `TAG_DATA_PLATFORM=`, … (dùng ở Phase 5).

## Steps

1. Chốt `<OWNER>` + tạo PAT, `docker login ghcr.io` trên máy dev.
2. Viết script (PowerShell — máy dev Windows; script phải chạy được từ repo root).
3. Release lần đầu cả 6 components ở `1.0.0` (sau khi Phase 1 merge — image nội dung y hệt bản đang chạy).
4. Verify trên GitHub Packages UI: 6 packages, visibility private, link về repo.
5. Test pull từ máy khác (hoặc `docker logout` + login bằng PAT read-only rồi pull) — xác nhận prod-path hoạt động.

## Validation

- `docker pull ghcr.io/<owner>/crm:1.0.0` bằng PAT read-only thành công.
- `docker run --rm ghcr.io/<owner>/crm:1.0.0 sh -c "ls /app/crm/src | head"` — layout đúng.
- Git tags `*-v1.0.0` × 6 tồn tại trên remote.
- Chạy script lần 2 cùng version → phải từ chối (tag đã tồn tại) — idempotency guard.

## Risks & Rollback

- KHÔNG dùng GitHub Actions build image ở phase này (image cần data mounts để test thật, build local kiểm soát tốt hơn; CI build là nâng cấp tương lai nếu thấy cần — YAGNI).
- PAT lộ trong shell history: script đọc token từ `docker login` đã có sẵn (credential store), không nhận token qua tham số.
- Rollback: images trên GHCR xóa được qua UI; git tag xóa bằng `git push --delete origin <tag>`.
