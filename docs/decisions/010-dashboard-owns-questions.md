# ADR-010: Dashboard sở hữu riêng questions, không share

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`deploy_from_markdown.js`](../../.skills/metabase-automation/scripts/deploy_from_markdown.js)

## Bối cảnh

Khi nhiều dashboard cùng hiển thị một metric (ví dụ: GMV, Total Orders, AOV), có 2 cách tiếp cận:

1. **Shared question:** Tạo 1 question, nhiều dashboard reference → dedup nhưng tạo coupling
2. **Owned question:** Mỗi dashboard tạo question riêng → trùng SQL nhưng độc lập

## Quyết định

**Mỗi dashboard sở hữu riêng tất cả questions.** Questions đặt trong cùng collection với dashboard cha.

- Deploy script tạo question mới cho mỗi dashboard, không tìm question có sẵn từ dashboard khác
- Không có collection "Shared Questions" hay "Question Library"
- Sự trùng lặp SQL giữa các dashboard là chấp nhận được

## Lý do

1. **Độc lập deployment** — deploy/undeploy dashboard A không ảnh hưởng dashboard B
2. **Tự do tùy biến** — cùng "GMV" nhưng CEO cần trend chart, Sales Ops cần breakdown table
3. **Đơn giản cho người dùng** — mở collection → thấy dashboard + tất cả questions liên quan
4. **dbt model là source of truth** — logic nằm ở dbt, question chỉ là presentation layer
5. **Metabase cache theo query** — 2 question cùng SQL vẫn được cache chung, không overhead

## Hệ quả

- SQL trùng lặp giữa dashboards (ví dụ: cùng query GMV ở 3 blueprint)
- Khi thay đổi metric logic → sửa dbt model, KHÔNG sửa từng question
- Deploy script check trùng question chỉ trong phạm vi dashboard hiện tại (`dashCardMap[q.name]`)

## Khi nào xem xét lại

- Có hàng trăm dashboard dùng chung cùng question → cân nhắc question library
- Question có custom SQL phức tạp cần maintain tập trung → chuyển logic xuống dbt model
