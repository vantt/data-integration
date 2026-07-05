# Phase 2 — Cắt import crm → orchestration (inline Lark alert)

**Depends on:** không (độc lập, có thể làm trước Phase 1)
**Mục tiêu:** Xóa cross-import duy nhất giữa crm và pipeline. Đồng thời fix bug: import này **chưa bao giờ chạy được trong container crm** (orchestration không được mount/copy vào image crm) — alert backup hiện silently no-op.

## Context

- `crm/ops/backup_crm.py:249-256` — hàm `_alert()` import `orchestration.notifications.lark_client.send_lark_alert` trong try/except, nuốt ImportError → trong container luôn fail im lặng.
- `orchestration/notifications/lark_client.py` (110 dòng) — đọc env `LARK_ALERT_WEBHOOK` + `LARK_ALERT_SECRET`, degrade về logging khi unset.

## Files

- **Create** `crm/ops/lark_alert.py` (~60-80 dòng): copy phần tối thiểu từ `orchestration/notifications/lark_client.py` — hàm `send_lark_alert(message)` (webhook POST + HMAC signature nếu có secret + stub-log khi env unset). Không copy phần card formatting nếu backup chỉ cần plain alert. stdlib only (`urllib.request`, `hashlib`, `hmac`) — không thêm dependency vào crm image. Lưu ý: set User-Agent header tường minh (Cloudflare Bot Fight chặn `Python-urllib` UA).
- **Modify** `crm/ops/backup_crm.py` — `_alert()` import `from lark_alert import send_lark_alert` (hoặc relative theo cách crm/ops được invoke; kiểm tra sys.path khi chạy trong container trước khi chọn dạng import).
- **Modify** `docker-compose.yml` — nếu service crm chưa có env `LARK_ALERT_WEBHOOK`/`LARK_ALERT_SECRET`, thêm passthrough để alert thực sự hoạt động.

## Steps

1. Đọc `orchestration/notifications/lark_client.py` đầy đủ, xác định subset `send_lark_alert` cần.
2. Viết `crm/ops/lark_alert.py`, docstring ghi rõ: bản inline độc lập, KHÔNG import từ orchestration (boundary contract), nguồn tham khảo.
3. Sửa `_alert()` trong backup_crm.py, giữ nguyên semantics best-effort never-raise.
4. Thêm env passthrough vào compose (cả base lẫn tính trước cho phase 5).
5. Test trong container crm (theo memory: CRM tests chạy trong container `crm`).

## Validation

- `docker compose exec crm python -c "from crm.ops.lark_alert import send_lark_alert; send_lark_alert('test boundary phase-02')"` (điều chỉnh import path theo thực tế) — khi env unset: log stub, không raise; khi có webhook thật: nhận message trên Lark.
- Chạy `backup_crm.py` một lần trong container — exit code không đổi, alert path không raise.
- `grep -rn "orchestration" crm/` → 0 kết quả import (chuẩn bị cho contract Phase 3).

## Risks & Rollback

- DRY trade-off có chủ đích: chấp nhận ~60 dòng duplicate để đổi lấy boundary sạch — nếu sau này ≥3 components cần Lark alert thì mới cân nhắc shared lib/package riêng (YAGNI).
- Rollback: revert commit; hành vi cũ (silent no-op) vô hại.
