# Phase A4 — One-shot Win-back + Suppress

> Stage A · Status: 🟢 thiết kế xong · Phụ thuộc: A1 (tier) · Context: [`discussion.md`](./discussion.md) §16 + economics report

## Mục tiêu

Đừng đốt tiền nghĩa địa. Win-back 2 nhóm contactable+giá trị, ưu tiên khác nhau: **DORMANT_VALUABLE (122, nguội gần 91–365)** = ưu tiên; **LAPSED_VALUABLE (1.144, nguội xa 365+)** = thử 1 phát → đo → suppress nếu kém. `GRAVEYARD` (4.183) + `NONBUYER` (1.598) → không action chủ động v1.

## Chốt

- **Target = DORMANT_VALUABLE (ưu tiên) + LAPSED_VALUABLE (thử)** — đều contactable + repeat/value≥SILVER; phân biệt nguội-gần (91–365) vs nguội-xa (365+). LAPSED đo tỉ lệ phản hồi rồi mới quyết duy trì/suppress (đừng cho cùng mức ưu tiên DORMANT).
- **Ưu đãi 1 phát theo value:** VIP/GOLD **~100K** · SILVER/repeat **~50K** (overall CM 592K → an toàn); min-order + loại SKU margin-âm (ride Sapo coupon).
- **Không phản hồi → suppress 90d** (giữ sender reputation). Bottom tier chỉ 1 lần.
- GRAVEYARD/NONBUYER → suppress; chờ organic / nuôi lead sau.

## Related code

- Rule tĩnh (KHÔNG cần engine): chọn DORMANT_VALUABLE → 1 ưu đãi → suppress flag. Suppress list để không lọt funnel/campaign khác.

## Success criteria

- Win-back gửi đúng DORMANT_VALUABLE; suppress sau 1 lần; nghĩa địa không bị đốt tiền.

## Open

- (sau) NONBUYER có nuôi không + cơ chế.
