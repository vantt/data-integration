# ADR-004: 3-channel ingestion redundancy

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Sapo Data Sources](../../AGENTS.md), [`DATA_FLOW.md`](../DATA_FLOW.md)

## Bối cảnh

Sapo API cung cấp nhiều cách lấy dữ liệu. Không kênh nào đảm bảo 100% reliability.

## Quyết định

Sử dụng **3 kênh ingestion độc lập**, chấp nhận dữ liệu trùng lặp:

| Kênh | Tần suất | Đặc điểm | Vai trò |
|:---|:---|:---|:---|
| **Batch API** | Daily/hourly | Reliable, high latency | Baseline — đảm bảo tất cả data cuối cùng đều có |
| **Webhook** | Real-time | Fast, có thể miss events | Speed — data gần real-time |
| **History Log** | ~10 phút | Gap filling | Safety net — bắt những gì webhook miss |

## Lý do

1. **Không kênh nào 100% reliable:**
   - Webhook có thể miss do network issue, Cloudflare timeout
   - History Log có thể delay
   - Batch có latency cao nhất nhưng reliable nhất

2. **Redundancy tốt hơn single-point-of-failure:**
   - Cùng 1 order có thể đến qua cả 3 kênh → dedup xử lý ở src_ layer
   - Nếu webhook miss → history log bắt lại trong 10 phút
   - Nếu cả hai miss → batch daily đảm bảo data đầy đủ

3. **Priority hierarchy trong dedup:** webhook > history_log > batch
   - Ưu tiên source real-time nhất (freshest data)

## Hệ quả

- Storage tăng do trùng lặp raw data (chấp nhận được nhờ Parquet compression)
- Dedup logic phức tạp hơn (nhưng đã isolate trong src_ models)
- Cần monitor cả 3 kênh để phát hiện kênh nào bị lỗi

## Khi nào xem xét lại

- Nếu Sapo cung cấp guaranteed delivery API → có thể giảm xuống 1-2 kênh
- Nếu storage cost trở thành vấn đề → cân nhắc bỏ kênh ít giá trị nhất
