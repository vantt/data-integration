---
title: "Rà soát thiết kế bộ máy phân loại: góc nhìn product owner cho SME TMĐT Việt Nam"
reviewer: product-sme (1/4)
date: 2026-10-14
reviewed: ../../taxonomy-engine-design.md
---

# Rà soát từ góc nhìn product owner cho SME

Góc nhìn của tôi: người mua là chủ shop 5–50 nhân viên bán trên Sapo/Haravan và sàn. Người duy trì phân loại là chủ shop hoặc kế toán, không phải data engineer. Mình cài trên hạ tầng của khách và hỗ trợ từ xa qua Tailscale/TeamViewer. Câu hỏi tôi dùng để chấm mọi điểm trong thiết kế là: điểm này có làm giảm số giờ onboarding khách thứ hai, hoặc số cuộc gọi hỗ trợ mỗi tháng, hay không.

## Tóm tắt

Hướng đi (nhãn riêng + mã chuẩn, luật là dữ liệu, `UNMAPPED` có giám sát) là đúng và tôi đồng ý. Phần tôi không đồng ý là **quy mô**. Thiết kế mô tả một rule engine tổng quát với 8 thuộc tính mỗi domain, 5 dạng luật và khoảng 20 domain, trong khi bằng chứng ngay trong repo cho thấy nhân viên SME chỉ điều khiển **hai ô**: "Nguồn đơn hàng" và "Nhóm khách hàng" (staff guide, TL;DR). Phần lớn giá trị cho khách nằm ở hai bảng ánh xạ cộng một danh sách gán tay. Mọi thứ khác nên là SQL của sản phẩm với ngưỡng mặc định, không phải luật do khách cấu hình.

Đề xuất của tôi: giữ nguyên **mô hình dữ liệu** của thiết kế (mã chuẩn, nhãn, override có lý do, 4 mã dành riêng), nhưng cắt **bề mặt cấu hình cho khách** xuống còn bảng ánh xạ và danh sách gán tay, và lấy dữ liệu thật của một shop thứ hai **trước** khi chốt bộ mã chuẩn.

## (a) Những gì thiết kế làm đúng

1. **Hai cột nhãn riêng + mã chuẩn.** Đây là điều kiện để bán một bộ report chuẩn cho nhiều shop. Không có nó, mỗi khách mới là một dự án dashboard riêng, và mình không có sản phẩm.
2. **`UNMAPPED` tách khỏi `UNKNOWN`, `NOT_APPLICABLE`, `OTHER`.** Với SME, đây là tính năng bán hàng chứ không chỉ là kỹ thuật: chủ shop thấy ngay "12% doanh thu tháng này chưa phân loại" và biết phải làm gì.
3. **`rule_id` trên mỗi nhãn để giải thích được.** Câu hỏi hỗ trợ phổ biến nhất sẽ là "vì sao khách này là sỉ" hoặc "vì sao đơn này không có trong doanh thu". Trả lời bằng một truy vấn thay vì đọc SQL là giảm thời gian hỗ trợ thật.
4. **Gán tay thắng luật, có lý do và người tạo.** Khớp đúng cách chủ shop làm việc: "khách này tôi biết là đại lý".
5. **Tách `order_purpose` khỏi nguồn đơn.** Đây là lỗi tốn tiền nhất mà Fine Japan đã gặp (quà, test, ưu đãi nhân viên, US lẫn vào doanh thu; `channel-grouping-analysis.md`). Shop thứ hai gần như chắc chắn có cùng vấn đề.
6. **Không có SQL tự do trong luật; luật chéo bảng thành đặc trưng do sản phẩm viết.** Đúng, và đây là ranh giới giữ cho hỗ trợ từ xa còn khả thi.
7. **Thí điểm `customer_type` với 0 khác biệt trên Fine Japan.** Chứng minh được mà không đụng số của khách đang trả tiền.

## (b) Phần thừa và phần thiếu cho SME

### Thừa (hoặc quá sớm)

1. **Coi mọi phân loại là "domain có luật do khách cấu hình".** `geo_region`, `payment_behavior`, `acquisition_source`, `channel_preference`, `product_affinity`, `lifecycle_stage`, `channel_category` là các chiều **tính ra** từ dữ liệu. Shopify cũng làm vậy: `rfmGroup`, `is_b2b_order`, `new_or_returning_customer` do nền tảng tính, merchant không sửa (`shopify.md` TL;DR 2). Đưa chúng vào bộ máy làm phình phạm vi engine mà không khách nào cấu hình chúng. Tôi đề nghị chia hai loại: **domain cấu hình được** (khoảng 4–5) và **chiều tính sẵn** (SQL sản phẩm, chỉ có tham số như số ngày 30/90/180).
2. **8 thuộc tính mỗi domain (`hit_policy`, `stickiness`, `time_semantics`, `versioning`, `depends_on`...).** Mỗi thuộc tính đúng về lý thuyết, nhưng khách không bao giờ thấy chúng. Nếu một thuộc tính chỉ có một giá trị trong MVP thì đừng tạo cột; thêm cột khi có domain cần giá trị thứ hai.
3. **Toán tử `regex` cho người nghiệp vụ.** Kế toán không viết regex. `regex` trong Google Sheet là một nguồn cuộc gọi hỗ trợ. Giới hạn bề mặt cho khách ở `eq` (ánh xạ) và `contains`; `regex` chỉ dùng trong gói luật do mình viết.
4. **Cả `value_tier` lẫn `rfm_segment` 8 nhóm.** Hai cách xếp hạng giá trị khách làm chủ shop rối ("VIP" và "Champions" khác nhau chỗ nào?). Chọn một làm mặc định trên dashboard (tôi chọn `value_tier` 4 mức vì Fine Japan đã dùng và dễ giải thích); RFM là report chuyên sâu, làm sau.
5. **`seller_role`, `content_carrier`.** API Sapo và các OMS Việt Nam không có dữ liệu này (`vietnam-sources.md` §10). Domain toàn `UNKNOWN` chỉ làm report khó đọc. Để tới khi có connector TikTok Shop trực tiếp.
6. **Phân vị chốt theo kỳ + `taxonomy_param` có phiên bản.** Có cách đơn giản hơn nhiều: lúc onboarding, tính phân vị **một lần** rồi đổi thành **số tuyệt đối** ("từ 20 triệu/năm là VIP"). Chủ shop hiểu số tiền, không hiểu phân vị; nhãn không trôi; không cần bảng tham số có phiên bản. Khách muốn đổi thì đổi con số.
7. **`ruleset_version` dạng hash.** Có ích cho tái lập, nhưng với mặc định restate và luật có lịch sử thay đổi (sheet hoặc kho mã), hash là thứ thêm sau được mà không đổi schema.

### Thiếu (quan trọng hơn phần thừa)

1. **Bước "khảo sát dữ liệu thô" (bước ② của Đợt 4) không có trong MVP.** Đây là công cụ onboarding giá trị nhất: một truy vấn liệt kê mọi nguồn đơn, nhóm khách, lý do giảm giá chưa ánh xạ, kèm số đơn và doanh thu, sắp theo doanh thu. Không có nó, mình ngồi đoán cùng khách. Nó rẻ (một model SQL) và phải nằm trong MVP.
2. **Gợi ý điền sẵn.** `vietnam-sources.md` §11.1 đã có sẵn: nguồn mặc định của Sapo không đổi được tên (Shopee, Lazada, POS, Web, Facebook, Zalo...) nên map chắc chắn; tên nguồn/nhóm khớp `đại lý|sỉ|buôn`, `quà|tặng`, `test`, `nhân viên` cho gợi ý. Thiết kế dời "gói connector" tới khi làm connector thứ hai. Nhưng tenant #2 khả năng cao là **Sapo**, cùng connector, nên gói Sapo chính là thứ tiết kiệm giờ onboarding nhiều nhất. Phải có trong MVP.
3. **Ngữ nghĩa mặc định của `UNMAPPED` trong doanh thu.** Ở Fine Japan, "Other" bị **loại khỏi mọi báo cáo doanh thu** (staff guide §1A). Nếu bê nguyên quy ước này cho khách mới, ngày đầu tiên dashboard sẽ báo doanh thu thấp hơn số trên Sapo, và chủ shop mất niềm tin ngay. Đề xuất mặc định cho tenant mới: đơn `UNMAPPED` **vẫn tính** vào tổng doanh thu, hiện thành dòng "Chưa phân loại" riêng; chỉ đơn đã được gán `order_purpose` khác SALE mới bị loại. Đây là quyết định sản phẩm, cần ghi rõ.
4. **Cách cập nhật luật trên bản cài của khách.** Thiết kế chọn "seed CSV trong thư mục tenant, qua gate". Roadmap Đợt 2 đưa prod về chạy từ image, không bind-mount code. Hai điều này mâu thuẫn: nếu luật là seed nằm trong code, mỗi lần khách tạo nguồn đơn mới trên Sapo thì mình phải deploy qua Tailscale. Luật phải nằm ở **thư mục cấu hình tenant mount riêng** hoặc Google Sheet đồng bộ có kiểm tra, nạp như dữ liệu mà không phải đóng image mới. Thiết kế cần nói rõ điểm này.
5. **"Quy ước thay cho cấu hình" chưa được xét.** Staff guide cho thấy cách sửa tốt nhất là sửa ở khâu nhập Sapo. Với khách mới (chưa có lịch sử rối như Fine Japan), checklist onboarding có thể yêu cầu: "tạo nhóm khách theo mã `TYPE_WHOLESALE`, `TYPE_PARTNER`, `TYPE_STAFF`, `TYPE_KOL`" và "tạo nguồn Quà tặng / Test / Nội bộ với danh mục 'Nhân viên tự tạo'". Gói Sapo map các mã này tự động, gần như không cần luật riêng. Đây là phương án C bên dưới.
6. **Tài liệu một trang cho nhân viên của khách.** Phần A của staff guide Fine Japan chính là sản phẩm. Nó nên trở thành mẫu chuẩn sinh từ bảng mã chuẩn và nhãn của tenant, không viết tay lại cho mỗi khách.

## Ba phương án thật sự khác nhau

| | A. Engine như thiết kế (MVP đã cắt) | B. Bảng ánh xạ trước | C. Quy ước Sapo + gói connector |
|---|---|---|---|
| Khách cấu hình gì | Luật nhiều dạng, hit policy, ngưỡng | 3 bảng: nguồn đơn → (`channel_format`, `order_purpose`); nhóm khách → `customer_type`; danh sách gán tay. Ngưỡng là vài con số | Gần như không gì nếu đặt tên đúng quy ước; phần lệch quy ước dùng bảng của B |
| Công sản phẩm trước tenant #2 | Cao (macro chung, 3 hit policy, lớp, test): ước 8–12 ngày | Thấp: 3–5 ngày (join `ref()`, test nhãn → mã, model khảo sát, gói Sapo) | Thấp nhất phía mình, nhưng đòi khách đổi thói quen nhập liệu |
| Giờ onboarding tenant #2 | Cao: cần người hiểu engine | 2–4 giờ cùng khách, có điền sẵn | 1–2 giờ nếu shop mới mở; không áp dụng được cho shop có lịch sử dài |
| Khách tự bảo trì | Khó: lỗi thứ tự luật, regex | Dễ: thêm một dòng ánh xạ khi có nguồn mới | Dễ nhất nhưng phụ thuộc kỷ luật nhân viên |
| Hệ quả bậc hai | Dễ xây đủ engine trước khi biết tenant #2 cần gì; mỗi khách thành dịch vụ cấu hình | Fine Japan vẫn cần luật dò mẫu (đã có `ref_tag_categories`) và đặc trưng CROSSBORDER; vẫn biểu diễn được | Dữ liệu cũ trước khi đổi quy ước vẫn cần ánh xạ theo B |
| Lãng phí khi đổi hướng | Không, nhưng tốn trước | Không: B là tập con của A, cùng schema | Không: C là quy ước đặt trên B |

**Phương án đơn giản nhất vẫn đủ yêu cầu: B, kèm C làm checklist onboarding.** B dùng đúng schema của thiết kế (`taxonomy_canonical`, `taxonomy_label`, `taxonomy_rule` với `eq`/`contains`/`starts_with`, `taxonomy_override`), chỉ là chưa làm phần tổng quát chưa có khách nào cần. Mọi tính năng còn lại của A được thêm khi một domain cụ thể đòi.

## (c) Trả lời 6 quyết định ở §8

**1. Nhãn riêng + mã chuẩn bắt buộc: Đồng ý, có giới hạn.** Bắt buộc mã chuẩn chỉ cho các domain mà report chuẩn thật sự group theo: `channel_format`, `order_purpose`, `customer_type`, `value_tier`, `discount_purpose`. Mỗi bộ mã giữ ≤ 8 giá trị, có tên tiếng Việt dễ hiểu, vì chủ shop sẽ đọc chúng trên dashboard. Không chốt bộ mã chỉ từ Fine Japan; `standards-and-patterns.md` §8.5 rủi ro 3 đã nói đúng, và tôi coi đây là điều kiện cứng. Về CROSSBORDER: đó không phải loại khách mà là một **mục đích đơn** (giao hộ, 0đ doanh thu, đã xác nhận 13/04). Neo nhãn khách CROSSBORDER vào `OTHER`, còn việc loại khỏi doanh thu do `order_purpose = FULFILLMENT_SERVICE` đảm nhận. Không thêm mã chuẩn riêng cho một trường hợp của một tenant.

**2. Thời điểm: Trước phase 6, nhưng chỉ phương án B và có hộp thời gian.** Lập luận "tách SQL custom rồi phải tách lần nữa" là đúng, nên tôi không giữ ở Đợt 4. Nhưng tôi không đồng ý đặt toàn bộ MVP engine trước phase 6, vì nó kéo dài Đợt 1 mà không đưa mình gần tenant #2 hơn (tenant #2 còn chờ phần cài đặt ở Đợt 5). Đề xuất: phase mới tối đa 4 ngày, chỉ `customer_type` và ánh xạ nguồn đơn, FIRST + override, 0 khác biệt trên Fine Japan. Quá 4 ngày thì dừng: phase 6 tách các literal của Fine Japan thành seed ánh xạ của tenant (vẫn là dữ liệu, không phải SQL), và engine quay về Đợt 4. Song song, việc rẻ nhất và đáng giá nhất là **xin ngay một shop Sapo thứ hai danh sách nguồn đơn, nhóm khách và lý do giảm giá** (xuất Excel hoặc chụp màn hình cấu hình, 30 phút). Một danh sách thật đáng giá hơn bốn tài liệu tham chiếu khi chốt bộ mã.

**3. Phase 4 bỏ bước tách macro nguyên văn: Đồng ý.** Macro nguyên văn không mang giá trị gì cho khách và sẽ bị thay. Giữ kiểm kê `TAXONOMY.md` (đây là bản yêu cầu của engine) và dời seed. Rủi ro "engine bị hoãn lâu" có cách phòng rẻ hơn macro: cột "giá trị tenant" trong `TAXONOMY.md` đã chỉ đúng chỗ cần tách ở phase 6.

**4. Kênh nhiều trục, tách `order_purpose`: Đồng ý một phần.** Tách `order_purpose` là ưu tiên số một, vì đây là lỗi số liệu tốn tiền nhất cho SME. `channel_category` nên là cây cha (`parent_code`) của `channel_format`, không phải domain riêng. `platform` là chiều tính sẵn từ gói connector, không phải thứ khách cấu hình. `seller_role` và `content_carrier`: không làm bây giờ (YAGNI, không có dữ liệu). Cần chốt thêm một điểm cho khách: ở Sapo, một nguồn đơn tuỳ chỉnh vừa quyết định `channel_format` vừa quyết định `order_purpose` (vd. nguồn "Quà Tặng"), nên bảng ánh xạ nguồn đơn phải có **hai cột kết quả trên cùng một dòng**. Với khách, đó là một bảng, không phải hai domain phải hiểu.

**5. Restate làm mặc định, chỉ khoá kỳ cho kế toán: Đồng ý.** Chủ shop sửa "khách này là sỉ" thì mong số các tháng trước cũng đổi; restate khớp kỳ vọng đó. Điều kiện đi kèm: dashboard có ghi chú "phân loại cập nhật ngày X" ở chân trang, nếu không chủ shop sẽ gọi hỗ trợ vì "số tháng trước tự đổi". `freeze_after_close` không làm cho tới khi có domain kế toán hoặc thưởng nhân viên đã chốt.

**6. Ai nhập luật: Kết hợp, nhưng phân vai rõ.** Mình cấu hình luật lúc onboarding (gói setup có tính phí, 2–4 giờ). Khách chỉ tự bảo trì đúng hai thứ: (a) thêm dòng ánh xạ khi xuất hiện nguồn đơn hoặc nhóm khách mới (cảnh báo `UNMAPPED` dẫn thẳng tới dòng cần điền), (b) danh sách gán tay khách. Giao diện là Google Sheet với dropdown chỉ cho chọn mã chuẩn và nhãn đã khai báo, có bước kiểm tra trước khi nạp. Ngưỡng, luật dò mẫu, luật dẫn xuất do mình sửa theo yêu cầu hỗ trợ. Lý do: kế toán SME bảo trì được một bảng hai cột có dropdown; họ không bảo trì được thứ tự ưu tiên luật. Lưu ý: không phải khách nào cũng chấp nhận để dữ liệu cấu hình trên Google; cần phương án dự phòng là file CSV trong thư mục cấu hình tenant trên máy của khách, dùng chung bộ kiểm tra.

## (d) Bản tối thiểu sẽ ship và cách onboard tenant #2

### Bản tối thiểu (phương án B)

- Bộ mã chuẩn cho 5 domain cấu hình được: `channel_format`, `order_purpose`, `customer_type`, `value_tier`, `discount_purpose`; cộng 4 mã dành riêng.
- Ba bảng tenant: ánh xạ nguồn đơn (nguồn → `channel_format`, `order_purpose`, nhãn riêng); ánh xạ nhóm khách (mã/tên nhóm → `customer_type`, nhãn riêng, toán tử `eq` hoặc `contains`); danh sách gán tay (khách → `customer_type`, lý do, người gán).
- Gói Sapo: nguồn mặc định của Sapo, trạng thái đơn, luật "giá sỉ không phải KM" (`reason=''`, `rate=100`), gợi ý theo tên (chỉ điền sẵn, không tự áp dụng).
- Chiều tính sẵn bằng SQL sản phẩm với tham số mặc định: vòng đời 30/90/180, `value_tier` theo ngưỡng tuyệt đối tính một lần từ phân vị lúc onboarding, vùng địa lý.
- Model khảo sát `UNMAPPED` (giá trị thô, số đơn, doanh thu) và một trang dashboard "Chất lượng phân loại".
- Test: kết quả nằm trong bộ mã chuẩn, một nhãn mỗi đối tượng, nhãn → mã là hàm, override mồ côi.

### Onboard một shop Sapo trong 3–5 ngày

| Ngày | Việc | Ai |
|---|---|---|
| Trước khi ký | Xin danh sách nguồn đơn, nhóm khách, lý do giảm giá; đánh giá độ "rối" để báo giá setup | Mình + chủ shop, 30 phút |
| 1 | Cài đặt, kết nối Sapo, nạp lịch sử | Mình qua Tailscale |
| 2 | Chạy model khảo sát; sinh sheet ánh xạ đã điền sẵn từ gói Sapo và gợi ý tên; mình đoán trước phần còn lại | Mình, phần lớn tự động |
| 2–3 | Một cuộc gọi 1–2 giờ: chủ shop xác nhận từng dòng theo thứ tự doanh thu giảm dần; chốt ngưỡng VIP bằng số tiền | Chủ shop/kế toán + mình |
| 3 | Nạp, chạy, mở dashboard; dòng "Chưa phân loại" phải < 5% doanh thu | Mình |
| 4–5 | Giao checklist quy ước Sapo và tài liệu một trang cho nhân viên; hướng dẫn sửa sheet khi có nguồn mới | Mình |
| Tuần 2–4 | Theo dõi cảnh báo `UNMAPPED`, nhận danh sách gán tay khách sỉ ẩn | Khách tự làm, mình hỗ trợ |

### Shop Haravan

Thẳng thắn: chưa onboard được trong vài ngày, và nguyên nhân **không phải** bộ máy phân loại. Connector Haravan là Đợt 6, phần cài đặt cho khách là Đợt 5. Khi có connector, phân loại Haravan nhẹ hơn Sapo (kênh `web`/`pos`/`iphone`/`android` được bảo vệ), nhưng nhóm khách của Haravan chưa xác nhận lấy được qua API (`vietnam-sources.md` §3.2), nên `customer_type` có thể phải dựa vào tag và danh sách gán tay. Nếu muốn bán cho shop Haravan sớm, ưu tiên connector chứ không phải engine.

## (e) Ba rủi ro lớn nhất

1. **Xây engine và chốt bộ mã từ dữ liệu của một khách.** Fine Japan có lịch sử rất riêng (CROSSBORDER, ký gửi, US). Nếu bộ mã và engine đóng băng trước khi thấy dữ liệu shop thứ hai, khả năng cao phải đổi mã đã phát hành, tức là đổi số của cả hai khách. Giảm thiểu: lấy danh sách cấu hình của 1–2 shop Sapo khác ngay tuần này; chỉ đánh dấu bộ mã là "ổn định" sau khi neo được ≥ 95% doanh thu của shop thứ hai vào mã khác `OTHER`.
2. **Phân loại biến thành dịch vụ tư vấn không co giãn.** Nếu bề mặt cấu hình quá rộng (dò mẫu, ngưỡng, bảng quyết định, regex), mỗi khách cần người của mình để bảo trì, và chi phí hỗ trợ tăng tuyến tính theo số khách trong khi giá bán cho SME thấp. Giảm thiểu: khách chỉ chạm vào bảng ánh xạ và danh sách gán tay; theo dõi số giờ hỗ trợ phân loại mỗi khách mỗi tháng như một chỉ số sản phẩm (mục tiêu < 1 giờ sau tháng đầu).
3. **Niềm tin số liệu ở ngày đầu.** Hai điểm có thể làm chủ shop thấy "số không khớp Sapo": quy ước loại `UNMAPPED`/"Other" khỏi doanh thu, và restate làm số tháng trước tự đổi. Giảm thiểu: mặc định tính `UNMAPPED` vào tổng và hiển thị riêng; có ô đối chiếu "tổng doanh thu Sapo so với dashboard" ở trang đầu; ghi ngày cập nhật phân loại ở chân trang.

Rủi ro phụ cần ghi lại: luật nằm ở seed trong code xung đột với hướng chạy prod từ image (Đợt 2, Đợt 5), dẫn tới mỗi thay đổi ánh xạ là một lần deploy từ xa. Phải chốt nơi lưu luật ngoài image trước khi viết engine.

## Tiêu chí đo thành công đề xuất

- Onboard shop Sapo thứ hai: ≤ 5 ngày làm việc, ≤ 4 giờ công cùng khách cho phần phân loại.
- Sau cuộc gọi ánh xạ: "Chưa phân loại" < 5% doanh thu 90 ngày gần nhất.
- Sau tháng đầu: khách tự xử lý ≥ 80% cảnh báo `UNMAPPED` mà không cần mình.
- Fine Japan: 0 khác biệt trên gate S sau khi chuyển `customer_type` và nguồn đơn.

## Câu hỏi chưa giải

1. Có shop Sapo nào sẵn sàng cho xem danh sách nguồn đơn và nhóm khách ngay bây giờ không? Đây là đầu vào chặn việc chốt bộ mã.
2. Quy ước "Other loại khỏi doanh thu" là quyết định riêng của Fine Japan hay mặc định của sản phẩm?
3. Luật của tenant sẽ nằm ở đâu trên bản cài của khách khi prod chạy từ image?
4. Giá setup onboarding có bao gồm cấu hình phân loại không, và có giới hạn số giờ không?

---

Status: DONE
Summary: Đồng ý hướng nhãn riêng + mã chuẩn, restate và tách `order_purpose`, nhưng khuyên cắt bộ máy xuống "bảng ánh xạ + gán tay + gói Sapo + model khảo sát" (phương án B, cùng schema với thiết kế) và lấy dữ liệu của một shop Sapo thứ hai trước khi chốt bộ mã chuẩn. Quyết định 2 trả lời "trước phase 6 nhưng tối đa 4 ngày, có điểm dừng".
Concerns/Blockers: Bộ mã chuẩn hiện chỉ dựa trên Fine Japan. Nơi lưu luật (seed trong code) mâu thuẫn với hướng chạy prod từ image. Quy ước loại "Other" khỏi doanh thu sẽ làm mất niềm tin của khách mới nếu dùng làm mặc định.
