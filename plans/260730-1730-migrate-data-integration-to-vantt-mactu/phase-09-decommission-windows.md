# Phase 9 — Pre-wipe checklist (Windows sẽ bị uninstall + cài lại)

**Bối cảnh (chốt 2026-08-04)**: khác draft ban đầu ("giữ Windows dừng làm rollback vô thời hạn, quyết định sau ≥7 ngày"), user đã xác nhận Windows **sẽ bị uninstall và cài lại** sau khi migrate thành công — đây là mốc cứng, có điểm-không-thể-quay-lại (point of no return). Phase này là **checklist xác nhận AN TOÀN ĐỂ WIPE**, không phải "decommission rồi chờ xem sao".

**GATE — TUYỆT ĐỐI không cho phép wipe Windows nếu chưa tick hết checklist dưới đây.** Sau khi wipe, KHÔNG còn cách khôi phục bất kỳ dữ liệu/config nào còn sót trên Windows.

## Checklist trước khi cho phép wipe

- [ ] Phase 7 acceptance criteria đã PASS toàn bộ (6 service healthy, data parity khớp, Dagster history sạch).
- [ ] Phase 8 acceptance criteria đã PASS toàn bộ (CRM + Cloudflare Tunnel hoạt động qua `crm.fwg.vn`/`bi.fwg.vn`, integrity check CRM SQLite ok, nhân viên đăng nhập thử được).
- [ ] `vnflow.fwg.vn` — user đã xác nhận chấp nhận bỏ (2026-08-04), không phải chờ fix.
- [ ] `hermes.fwg.vn`/`fgos.fwg.vn` — verify vẫn hoạt động bình thường sau khi tunnel connector chuyển sang vantt-mactu (không phụ thuộc Windows).
- [ ] Đã chạy thử ít nhất 1 chu kỳ Dagster schedule/sensor đầy đủ trên vantt-mactu (không chỉ container "healthy" lúc mới lên) — xác nhận không có lỗi ẩn chỉ lộ ra khi chạy job thật theo lịch.
- [ ] Đã kiểm tra không còn secret/credential nào CHỈ tồn tại trên Windows chưa transfer (`.env`, `.env.local`, `.env.docker`, `app_data/secrets/`, `~/.cloudflared/` — đã transfer ở phase 5 + 8, nhưng re-verify lần cuối trước khi wipe vì đây là điểm không thể lấy lại).
- [ ] User tự xác nhận bằng lời đồng ý wipe — KHÔNG suy luận từ việc các bước trên đã pass.

## Bước (sau khi checklist trên đã tick hết)

1. Dừng toàn bộ container Windows (không bắt buộc phải làm trước khi wipe, nhưng làm cho sạch nếu còn chạy):
   ```powershell
   docker compose stop
   cd caddy-global; docker compose stop
   Stop-Service Cloudflared
   ```
2. Update tài liệu TRƯỚC khi Windows biến mất (path cũ trong docs sẽ không còn ý nghĩa tham chiếu sau wipe):
   - `AGENTS.md` — sửa path cũ `d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2` (đã sai từ trước, càng sai hơn sau migrate) thành path thật trên vantt-mactu.
   - `docs/operations/deployment.md`, `scripts/backup/README.md` — path Windows cũ, defaults trong `backup.ps1`/`restore.ps1` (PowerShell/robocopy) không chạy được trên Linux — cần viết lại bằng bash/rsync nếu muốn tiếp tục tự động hoá backup trên vantt-mactu (việc riêng, có thể làm sau, không blocking wipe).
3. Xác nhận lần cuối với user, sau đó **user tự thực hiện wipe** (KHÔNG phải bước tôi thực thi — cài lại OS là hành động ngoài phạm vi công cụ tôi có).

## Rollback
**KHÔNG CÓ** sau khi wipe xảy ra — đây là lý do checklist ở trên bắt buộc phải tick hết trước, không phải sau. Trước khi wipe: Windows containers vẫn nguyên (stopped), `docker compose start` khôi phục ngay được nếu phát hiện vấn đề ở phút chót.

## Acceptance
- Checklist 100% tick.
- Docs đã cập nhật path mới.
- User xác nhận bằng lời đồng ý wipe.
