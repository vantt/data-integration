# PRD — Hệ tri thức dự án `pkf`

Tài liệu yêu cầu thiết kế cho `pkf`. Đây là căn cứ để đánh giá mọi đề xuất thêm hoặc thay đổi
tính năng của hệ thống — không phải bài giải thích sau khi đã làm xong. Bản kỹ thuật đầy đủ, có
trích dẫn tới từng thành phần cụ thể của skill, nằm ở `references/philosophy.md`.

## 1. Vấn đề

Tri thức phát sinh trong quá trình làm việc với AI trên một dự án thường không tồn tại lâu dài.
Nó mất đi theo một trong hai cách: hoặc biến mất hoàn toàn giữa các phiên làm việc (mỗi phiên bắt
đầu lại từ số 0, không kế thừa gì từ phiên trước), hoặc tích luỹ một chiều (AI ghi nhận và tự đọc
lại, con người chỉ đóng vai trò phê duyệt thụ động, không thực sự đồng tác giả). Cả hai cách đều
không tạo ra một hệ tri thức mà cả người và AI cùng ngày càng hiểu rõ dự án hơn.

## 2. Mục tiêu

- Tri thức dự án phải **tích luỹ** qua thời gian và qua nhiều công cụ khác nhau, không mất đi
  giữa các phiên làm việc.
- Việc tạo tri thức phải mang tính **hai chiều** — con người đọc, sửa, và trực tiếp đóng góp,
  không chỉ phê duyệt những gì AI viết ra.
- Hệ thống phải **phối hợp** với các công cụ và quy trình hiện có, không đòi hỏi mọi việc phải đi
  qua nó.
- Mức độ giám sát của con người phải **tương xứng với rủi ro** của từng việc, không đồng nhất.
- Mọi thông tin ghi nhận phải **trung thực và có thể truy vết ngược** — không bịa đặt, không xoá
  bỏ lịch sử.

## 3. Ngoài phạm vi

- Không thay thế các công cụ, quy trình, hay tài liệu khác đang dùng trong dự án.
- Không phải cổng bắt buộc mà mọi công việc đều phải đi qua.
- Không phải hệ thống tra cứu kiểu tái tạo câu trả lời từ đầu mỗi lần hỏi.
- Không áp đặt một khuôn mẫu tài liệu cố định cho mọi loại công việc.
- Không phải một tác nhân tự động hoạt động không giới hạn — mọi hoạt động thu thập thông tin bổ
  sung đều có điểm dừng rõ ràng.

## 4. Yêu cầu thiết kế

1. **Tích luỹ, không tái tạo.** Tri thức đã ghi nhận phải tồn tại lâu dài và được tái sử dụng ở
   các lần làm việc sau, không bị suy luận lại từ đầu mỗi lần.
2. **Phối hợp, không chiếm quyền.** Hệ thống phải hoạt động song song với các công cụ khác, có
   đúng hai điểm chạm bắt buộc bất kể việc được thực hiện bằng công cụ nào: tra cứu tri thức đã có
   trước khi bắt đầu việc lớn, và ghi nhận lại những gì học được sau khi hoàn thành.
3. **Hai chiều, không đơn phương.** Nội dung do con người cung cấp phải được ghi nhận đúng như đã
   nói, không bị diễn giải lại thành sự thật mới. Kết quả công việc phải được trình bày lại bằng
   ngôn ngữ dễ hiểu để con người xác nhận hoặc sửa lại trước khi coi là hoàn tất.
4. **Giám sát theo mức độ rủi ro.** Công việc có rủi ro thực sự (liên quan tới tiền, dữ liệu,
   hành vi người dùng, hoặc thay đổi cấu trúc lớn) bắt buộc phải có sự đồng ý của con người trước
   khi thực hiện và trước khi coi là hoàn tất. Công việc rủi ro thấp có thể tiến hành ngay nhưng
   vẫn phải minh bạch, không được thực hiện âm thầm.
5. **Cấu trúc linh hoạt theo bản chất công việc.** Mức độ chi tiết của tài liệu phải phù hợp với
   quy mô và loại công việc thực tế, không bắt buộc điền đủ mọi mục cho mọi trường hợp.
6. **Ghi nhận bản chất, không lặp lại chi tiết kỹ thuật.** Tài liệu tri thức mô tả cái gì và vì
   sao, kèm đường dẫn tới nơi hiện thực hoá — không sao chép lại nội dung đã có trong mã nguồn.
7. **Trung thực tuyệt đối.** Không được tạo ra thông tin không có căn cứ — ngày tháng, nguồn tham
   chiếu, hay lý do của một quyết định. Thiếu thông tin thì để trống hoặc hỏi lại.
8. **Có giới hạn rõ ràng cho mọi việc thu thập thông tin bổ sung.** Không được để một hoạt động
   tìm kiếm/tra cứu tiếp diễn không giới hạn — phải có ngưỡng dừng xác định trước.
9. **Định dạng độc lập nền tảng.** Toàn bộ dữ liệu phải là văn bản thuần, không phụ thuộc phần
   mềm hay cơ sở dữ liệu riêng, đảm bảo có thể đọc và di chuyển được về sau.
10. **Công bố thông tin theo nhu cầu sử dụng.** Tài liệu hướng dẫn cho AI phải được tổ chức theo
    lớp — thông tin chi tiết chỉ được tải khi thực sự cần đến, không dồn hết vào một chỗ.
11. **Lịch sử bất biến.** Không được xoá hoặc ghi đè âm thầm các bản ghi đã có — mọi thay đổi
    trạng thái phải được bổ sung thêm, không thay thế. Các phương án từng bị loại bỏ trong một
    quyết định phải được ghi lại cùng với lý do, không chỉ ghi phương án được chọn.

## 5. Quy trình áp dụng

Trước khi thêm hoặc thay đổi bất kỳ phần nào của hệ thống, phải đối chiếu với Mục tiêu, Ngoài
phạm vi, và các Yêu cầu thiết kế liên quan ở trên. Nếu phát sinh xung đột: hoặc đề xuất đó không
phù hợp và cần điều chỉnh, hoặc yêu cầu trong tài liệu này đã lỗi thời và cần được cập nhật công
khai kèm lý do. Không được để hệ thống vận hành khác với những gì tài liệu này quy định mà không
ai ghi nhận lại sự khác biệt đó.
