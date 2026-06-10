---
title: "Product Journey × Customer Journey"
stage: 1
status: living
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

> ⚠️ **HIỆU CHỈNH 2026-06-10:** đây KHÔNG phải brand collagen làm đẹp — hero SKU là thực phẩm sức khỏe cho người lớn tuổi/bệnh nền (cordyceps/khớp/tim mạch/miễn dịch). Khung "da đẹp tuần 4–6" chỉ đúng cho dòng collagen tầm giữa. Bằng chứng kết quả phải theo công dụng (năng lượng/xét nghiệm/tái khám), không phải selfie da. Reorder 21–85 ngày TÙY sản phẩm, không phải 45–60 đồng loạt. Nguồn: [product-performance-assessment](../02-understand/product-performance-assessment.md).

## 0. Khung phân tích: Product Journey × Customer Journey

> **Cập nhật 2026-06-09.** Góc nhìn bổ sung để giải thích tại sao data-driven action queue chưa đủ.

### 0.1 Vấn đề tầng gốc

72% khách chỉ mua 1 lần — plan ban đầu giả định họ **quên** và cần nudge. Nhưng còn 3 nguyên nhân khác có trọng số cao hơn với supplement:

1. **Không thấy kết quả** → không có lý do reorder thật sự
2. **Dùng sai cách** → kết quả kém → bỏ
3. **Không có mối quan hệ với brand** → khi hết, mua chỗ khác (hoặc không mua tiếp)

Gọi điện / voucher không chữa được nguyên nhân 1 và 2.

### 0.2 Product Journey — Fine Japan (collagen/supplement)

```
Mua
 └→ Tuần 1–2: dùng nhưng chưa thấy gì      ← DANGER ZONE (hay bỏ ở đây)
 └→ Tuần 3–4: tín hiệu bắt đầu (da bớt khô, móng chắc hơn...)
 └→ Tuần 6–8: kết quả rõ ràng nhất
 └→ Hết hàng (ngày ~45–60)                  ← Điểm reorder tự nhiên
```

*Câu hỏi cần xác nhận với team sản phẩm: timeline kết quả thực tế theo từng dòng (Fine Japan Collagen vs FG Care)?*

### 0.3 Customer Journey hiện tại vs cần có

| Điểm thời gian | Hiện tại | Cần có |
|---|---|---|
| Mua | Xác nhận đơn | Xác nhận đơn |
| Day 3 | *(im lặng)* | "Nhận hàng chưa? Đây là cách dùng đúng nhất" |
| Day 7 | *(im lặng)* | *(tùy ngưỡng — có thể bỏ nếu Day 3 đã đủ)* |
| Day 21 | *(im lặng)* | "3 tuần rồi — cơ thể đang thay đổi từ bên trong..." + hỏi feedback |
| Day 45 | *(im lặng)* | "Sắp hết — đừng để đứt quãng lúc kết quả đỉnh nhất" + reorder link |
| Day 60+ | Vào action_queue (OVERDUE/WIN_BACK) | Đã có lý do reorder thật → tỷ lệ chuyển đổi cao hơn |

**Hệ quả:** action_queue (Luồng 1–4) vẫn cần, nhưng hiệu quả của nó phụ thuộc vào việc khách có trải qua đủ product journey không. Khách đã dùng đúng và thấy kết quả → conversion từ OVERDUE/WIN_BACK sẽ cao hơn nhiều.

### 0.4 Ưu tiên triển khai theo góc nhìn này

```
1. 3-touchpoint sequence (Day 3/21/45)   ← fix leak MỚI, không cần data work
2. Revamp script → product-experience first
3. Audit hộp CrossBorder (US gift recipient)
4. Action queue (call-list hiện tại)     ← vẫn làm, hiệu quả sẽ cao hơn sau #1
5. Data infra P1–P3                      ← scale sau khi biết message nào hoạt động
```

> **Lưu ý:** thứ tự trên tối ưu cho B2C retention. Nếu mục tiêu là **dòng tiền NGAY**, xem [first-principles-lenses.md](./first-principles-lenses.md)
> (nhóm A đề xuất đốt lửa B2B/supply trước). Hai thứ tự không loại trừ nhau — khác nhau ở **đốt gì trước**.

> Khung này dẫn tới điều tra ([02-understand](../02-understand/README.md)) và cơ hội action ([04-opportunities](../04-opportunities/README.md)).
