# Tham chiếu Trung Quốc: chuẩn hoá phân loại (taxonomy) cho nền tảng dữ liệu thương mại điện tử

- Ngày nghiên cứu: 2026-10-14 (Asia/Saigon)
- Phạm vi: phương pháp OneData/DataWorks/Dataphin; hệ thống tag (标签体系); SaaS cho người bán (Youzan, Weimob, Jushuitan); taxonomy sản phẩm của Taobao/JD; mô hình giá trị khách hàng; phân loại kênh của Douyin; bài học về quản trị (governance).
- Mục đích: làm đầu vào cho Đợt 4 (rules-as-data) của [taxonomy-engine.md](../../architecture/taxonomy-engine.md). Tài liệu này chỉ để tham khảo, không phải quyết định thiết kế.
- Quy ước độ tin cậy: **[A]** tài liệu chính thức của nhà cung cấp (help.aliyun.com, help.youzan.com, help.weimob.com, erp321.com wiki, volcengine/byteplus docs). **[B]** sách hoặc blog kỹ thuật uy tín, báo chí lớn. **[C]** bài tổng hợp của bên thứ ba (woshipm, bookdown, blog SEO), chỉ dùng để tham khảo. **[?]** chưa xác minh được.

---

## TL;DR

1. **Trung Quốc tách rõ "định nghĩa chỉ số" khỏi "phân loại".** Theo OneData/DataWorks, một chỉ số dẫn xuất (派生指标) bằng chỉ số nguyên tử (原子指标) cộng với từ bổ nghĩa (修饰词) và kỳ thời gian (时间周期) [A]. Từ bổ nghĩa chính là chỗ đặt phân loại. DataWorks có loại "维度枚举修饰词", trong đó **giá trị buộc phải lấy từ một bảng mã chuẩn (标准代码)** [A]. Cách này tương ứng đúng với mô hình của chúng ta: domain → tập giá trị canonical (bảng mã chuẩn) → nhãn tenant.
2. **Mọi CDP lớn của Trung Quốc đều để người dùng nghiệp vụ định nghĩa tag luật (规则标签) qua UI, không cần code.** Các hình thức định nghĩa gần như trùng nhau giữa các nhà cung cấp: giá trị tự định nghĩa theo điều kiện, tag thống kê theo chỉ số, hành vi đầu/cuối, sở thích (top-N), mô hình (RFM/AIPL/vòng đời), tag SQL, import, nhập tay [A: Quick Tracking, BytePlus/VeCDP, ThinkingData, Dataphin]. **Ba điểm thiết kế quyết định chất lượng** là (a) nhiều giá trị khớp cùng lúc thì xử lý ra sao (khớp đầu tiên theo thứ tự, ưu tiên một giá trị, hay giữ tất cả), (b) xử lý khách không khớp luật nào, (c) khi không còn khớp thì giữ nhãn cũ hay xoá [A].
3. **SaaS cho người bán (Youzan/Weimob) chỉ cho một luật trên mỗi nhóm tag, chạy hằng ngày, có cờ "tự xoá khi không còn khớp". Tag gắn tay không bao giờ bị luật ghi đè** [A]. Đây là tiền lệ cho manual override.
4. **Có hai trục bị gộp nhầm thành "kênh".** Jushuitan tách 订单来源 (nguồn đơn: platform, import, nhập tay, đơn đẩy từ phân phối, offline) khỏi 订单类型 (loại đơn: thường, gửi bù, đổi hàng, phân phối) [A]. Douyin tách hình thức nội dung (直播/短视频/商品卡: live, video ngắn, thẻ sản phẩm) khỏi chủ thể bán (店播 người bán tự live, 达播 KOL live) và khỏi bối cảnh mua (内容场 kênh nội dung, 货架场 kênh kệ hàng) [B/C]. Chúng ta nên tách ít nhất `sales_channel` (nền tảng), `content_carrier` và `seller_role`, và tách `order_purpose` ra khỏi kênh.
5. **Giá trị khách hàng: Quick Audience dùng kết hợp ngưỡng tuyệt đối và tương đối.** Mỗi chiều R/F/M chấm 3 hoặc 5 mức theo khoảng tuyệt đối. Sau đó so điểm với **trung bình toàn bộ khách hàng hoặc một ngưỡng tự đặt** để xếp Cao/Thấp, ra 8 nhóm khách cố định [A]. Tám nhóm RFM, AIPL (A<I<P<L, khớp nhiều giai đoạn thì lấy giai đoạn cao nhất) và O-5A là các **tập giá trị canonical** có sẵn để dùng lại.
6. **Hàng hoá: danh mục chuẩn của nền tảng (cây danh mục, hàng hoá phải gắn ở danh mục lá) và danh mục tự định nghĩa của shop cùng tồn tại song song** [C]. Không thay thế nhau. Thuộc tính chia ba loại: thuộc tính khoá (xác định SPU), thuộc tính bán (xác định SKU), thuộc tính mô tả [C]. Bài học: lưu cả danh mục của shop (nhãn tenant) lẫn ánh xạ sang danh mục canonical.
7. **Quản trị (governance) ở Trung Quốc khá mỏng ở tầng tag.** Phần có tài liệu là version cùng so sánh version trước khi publish (Dataphin), trạng thái vòng đời tag (上线/下线/生效/失效: chạy/ngừng cập nhật, dùng được/không dùng được), lưu lịch sử kết quả theo ngày (ThinkingData), và tự sinh quy tắc chất lượng "số dòng có giá trị enum không khớp = 0" khi một cột gắn với bảng mã chuẩn (DataWorks) [A]. Không tìm thấy quy trình duyệt (审批) chi tiết công khai [?].

**Khuyến nghị xếp hạng (chi tiết ở mục 9):** (1) dùng mô hình "domain → bảng mã canonical bắt buộc → nhãn tenant" theo kiểu 维度枚举修饰词; (2) mỗi domain khai báo rõ ba thuộc tính đơn trị/đa trị, chính sách khớp nhiều, chính sách giữ hay xoá nhãn; (3) tách kênh thành nhiều trục; (4) ngưỡng mặc định tương đối, cho phép chuyển sang tuyệt đối; (5) tag gắn tay là lớp override có ưu tiên cao nhất; (6) quản trị tối thiểu gồm version, xem trước khác biệt, monitor UNMAPPED.

---

## 1. OneData, DataWorks, Dataphin: chuẩn hoá chỉ số và chiều (dimension)

### 1.1 OneData (阿里 OneData 体系)

| Thành phần | Pinyin / nghĩa | Nội dung | Nguồn |
|---|---|---|---|
| OneData | — | Phương pháp luận Alibaba đúc kết từ khoảng năm 2012. Trước OneData có hơn 30.000 chỉ số, nhiều chỉ số trùng tên nhưng khác cách tính (口径 kǒujìng: định nghĩa cách tính) | [C] woshipm; [B] developer.aliyun.com |
| OneModel | 统一建模 tǒngyī jiànmó: mô hình hoá thống nhất | Mô hình hoá chiều (维度建模) theo "mảng nghiệp vụ + chiều phân tích". Nhiều nghiệp vụ độc lập dùng chung **chiều công cộng (公共维度 gōnggòng wéidù)** | [C] |
| OneID / OneEntity | 统一实体: thực thể thống nhất | ID-mapping nối các nguồn rời rạc thành một thực thể, sau đó tạo tag | [C], tên gọi không thống nhất giữa các nguồn [?] |
| OneService | 统一服务: dịch vụ thống nhất | Dữ liệu cung cấp qua API, không cho truy cập bảng trực tiếp | [C] |

Nguồn chính thức công khai về OneData còn ít. Tài liệu gốc là sách 《大数据之路：阿里巴巴大数据实践》. Các khái niệm của OneData hiện được hiện thực hoá trong Dataphin và DataWorks (phần dưới), nên dùng tài liệu sản phẩm làm nguồn chuẩn.

### 1.2 Kiến trúc khái niệm (DataWorks/Dataphin)

| Khái niệm | Pinyin / nghĩa | Định nghĩa | Ví dụ | Nguồn |
|---|---|---|---|---|
| 数据域 | shùjù yù: miền dữ liệu | Nhóm các quy trình nghiệp vụ đã trừu tượng hoá | Miền giao dịch | [A] DataWorks data planning |
| 业务过程 | yèwù guòchéng: quy trình nghiệp vụ | Hoạt động nghiệp vụ cụ thể trong miền | Đặt đơn, thanh toán, giao hàng, xác nhận nhận hàng | [A] bus matrix |
| 一致性维度 | yízhìxìng wéidù: chiều nhất quán | Mỗi chiều chỉ được định nghĩa **một lần duy nhất** trong toàn kho dữ liệu | Mã tỉnh có cùng nghĩa ở mọi quy trình | [A] |
| 总线矩阵 | zǒngxiàn jǔzhèn: ma trận bus | Ma trận quy trình × chiều, đánh dấu Y/N | Tỉnh, thành phố, danh mục, thương hiệu, sản phẩm áp dụng cho cả 4 quy trình | [A] |
| 原子指标 | yuánzǐ zhǐbiāo: chỉ số nguyên tử | Định nghĩa cách tính (SUM/COUNT...) trên một quy trình nghiệp vụ, **không kèm điều kiện thời gian hay kênh**. Chỉ được tạo ở tầng công cộng | Số tiền thanh toán, số người thanh toán | [A] |
| 修饰词 / 业务限定 | xiūshìcí / yèwù xiàndìng: từ bổ nghĩa / giới hạn nghiệp vụ | Thu hẹp phạm vi thống kê, tương tự mệnh đề WHERE **nhưng không gồm thời gian**. Dataphin gọi là 业务限定 | "Kênh online", "cửa hàng tươi sống" | [A] |
| 时间周期 / 统计周期 | shíjiān zhōuqī: kỳ thời gian | Phạm vi thời gian. DataWorks có sẵn 9 mức cơ bản và cho tạo thêm | 7 ngày gần nhất, tháng hiện tại | [A] |
| 派生指标 | pàishēng zhǐbiāo: chỉ số dẫn xuất | Nguyên tử + từ bổ nghĩa + kỳ (+ độ chi tiết thống kê 统计粒度 ở Dataphin) | Số tiền thanh toán trên PC trong 30 ngày gần nhất | [A] |
| 复合/衍生指标 | fùhé / yǎnshēng: chỉ số phức hợp | Phép cộng/trừ/nhân/chia trên các chỉ số dẫn xuất | Tỷ lệ chuyển đổi 30 ngày | [A] |

Dataphin 3.3 đổi tên một số thuật ngữ: chiều thành 业务对象 (đối tượng nghiệp vụ), quy trình nghiệp vụ thành 业务活动 (hoạt động nghiệp vụ), miền dữ liệu thành 主题域 (miền chủ đề) [A]. Mỗi bảng tổng hợp logic chỉ có **một độ chi tiết thống kê**, và khoá chính của bảng là tổ hợp các chiều [A].

### 1.3 Hai loại 修饰词 trong DataWorks: điểm quan trọng nhất cho thiết kế của chúng ta

| Loại | Giá trị | Ràng buộc | Nguồn |
|---|---|---|---|
| 普通业务修饰词 (từ bổ nghĩa nghiệp vụ thường) | Nhãn/văn bản tự do | Không gắn với bảng chiều | [A] DataWorks modifier |
| 维度枚举修饰词 (từ bổ nghĩa liệt kê theo chiều) | Phải là thành viên của một bảng chiều | **Bắt buộc gắn với một 标准代码 (bảng mã chuẩn)**, giá trị liệt kê lấy từ bảng mã đó | [A] |

Hệ quả: Alibaba đã cài sẵn trong công cụ việc phân biệt "nhãn tự do" với "nhãn bị ràng buộc bởi tập giá trị chuẩn". Mô hình "nhãn tenant + giá trị canonical bắt buộc" của chúng ta đi cùng hướng này.

### 1.4 Chuẩn dữ liệu (数据标准) của DataWorks

| Loại chuẩn | Nội dung | Cách áp chuẩn vào mô hình (落标 luòbiāo) | Nguồn |
|---|---|---|---|
| 字段标准 (chuẩn trường) | Tên tiếng Anh, tên tiếng Trung, kiểu dữ liệu, có cho phép null, giá trị mặc định. Có chuẩn cha (vd. buyer_id, seller_id kế thừa member_id). Có thể tham chiếu bảng mã | Gắn vào trường của mô hình logic, trường đó kế thừa tên, kiểu và ràng buộc null | [A] |
| 标准代码 / 码表 (bảng mã) | Mỗi giá trị gồm mã, tên mã, tên tiếng Anh, ý nghĩa. Có thể phát hành thành bảng vật lý hoặc materialized view | Khi bảng phát hành thành bảng vật lý, **hệ thống tự sinh quy tắc chất lượng "số dòng có giá trị enum không khớp = 0"** | [A] |
| 度量单位 (đơn vị đo) | Tiền tệ, lượng từ, tỷ lệ, xếp hạng, thời gian | Gắn vào trường và chỉ số nguyên tử | [A] |
| 命名词典 (từ điển đặt tên) | Từ gốc, hình vị, bản dịch chuẩn | Bộ kiểm tra phân tầng kho kiểm tra tên bảng | [A] |

Import/export dùng .xlsx, tối đa 30.000 dòng mỗi lần, khi trùng tên thì chọn bỏ qua hoặc ghi đè [A]. Trang tài liệu không mô tả version hay quy trình duyệt cho chuẩn dữ liệu [A, ghi nhận do thiếu thông tin]. Về quyền: chỉ admin, vận hành và người thiết kế mô hình được sửa mô hình; chỉ admin và vận hành được publish [A].

---

## 2. Hệ thống tag (标签体系 biāoqiān tǐxì)

### 2.1 Phân loại tag theo cách sinh ra

| Cách chia | Loại | Định nghĩa | Ví dụ | Nguồn |
|---|---|---|---|---|
| Phổ biến trong ngành | 事实标签 (tag sự kiện, shìshí) | Làm sạch rồi phân loại dữ liệu gốc, mô tả sự thật khách quan | Hạng hội viên, số lần mua, số tiền mua | [C] woshipm |
| | 规则标签 (tag luật, guīzé) | Sinh ra từ luật nghiệp vụ, **luật do dữ liệu và nghiệp vụ cùng đặt** | "Hoạt động" = 30 ngày có X lần hành vi a và b. Chu kỳ rời bỏ lấy theo điểm gãy (vd. 5 tuần). Chia cao/trung/thấp theo tứ phân vị | [C] |
| | 预测/模型标签 (tag dự báo/mô hình) | Dùng thuật toán (cây quyết định, Bayes...). Đắt, ít | Xác suất rời bỏ | [C] |
| Dataphin | 属性 / 统计 / 预测 / 组合 | Thuộc tính, thống kê (vd. tiền mua 7 ngày), dự báo, **tổ hợp (kết hợp tag khác theo luật, vd. phân tầng khách hàng)** | | [A] |
| Theo tính thời gian | 静态 / 动态 (tĩnh / động) | Tag tĩnh hiếm khi đổi. Tag động phải làm mới định kỳ | Giới tính / số đơn 7 ngày | [A] Dataphin |

### 2.2 Các hình thức định nghĩa tag luật trên UI (so sánh nhà cung cấp)

| Hình thức | Quick Tracking (Alibaba) | BytePlus/VeCDP (ByteDance) | ThinkingData | Dataphin | Tương ứng của chúng ta |
|---|---|---|---|---|---|
| Giá trị theo điều kiện | 自定义标签值 | Rule | Custom Conditions | 组合标签 (rule combination) | Dò mẫu có ưu tiên / bảng quyết định |
| Thống kê chỉ số rồi chia nhóm | 指标统计 | Statistical (tổng số lần, số ngày, số ngày liên tiếp, sum, avg, max, min) | Indicator Value | 指标映射 / 行为统计 | Feature + chia ngưỡng |
| Hành vi đầu/cuối | 首/末次行为 | First and Last | First and Last Features | — | Feature (ngày mua đầu/cuối) |
| Sở thích (top-N) | 用户偏好 (Top 5/10/30) | Preference | — | 行为偏好 | Feature (danh mục mua nhiều nhất) |
| Phân bố hành vi | 行为分布 | — | — | — | Feature |
| Mô hình sẵn có | — (Quick Audience có RFM/AIPL) | Lifecycle, RFM | — | 预测 | Decision table có sẵn |
| SQL | — | SQL tags | — | — | Luật đặc thù (escape hatch) |
| Import file | Import CSV/Excel | Import | ID Upload | — | Manual override hàng loạt |
| Nhập tay | — | Manual entry | — | — | Manual override |

Nguồn: [A] Quick Tracking tag system; [A] BytePlus CDP overview và Statistical Tags; [A] ThinkingData User Tags v3.8; [A] Dataphin.

Giới hạn đáng chú ý: Quick Tracking cho tối đa 25 giá trị mỗi tag; ThinkingData tối đa 20 giá trị; Dataphin cho rule combination lồng tối đa 5 tầng, 10 điều kiện [A]. Các giới hạn này cho thấy **tag luật được thiết kế cho tập giá trị nhỏ, đóng**. Tập giá trị lớn (danh mục, thương hiệu) không đi theo đường tag luật mà đi theo bảng mã hoặc bảng ánh xạ.

### 2.3 Ba điểm thiết kế quyết định ngữ nghĩa

| Vấn đề | Lựa chọn của nhà cung cấp | Nguồn |
|---|---|---|
| **Khớp nhiều giá trị cùng lúc** | ThinkingData: xét điều kiện theo thứ tự giá trị, **khớp giá trị trên thì không xét giá trị dưới** (first-match). VeCDP: cấu hình "标签值保存类型" (kiểu lưu giá trị tag), chọn **giữ một giá trị theo độ ưu tiên** hoặc **giữ tất cả giá trị khớp**. AIPL: lấy giai đoạn cao nhất | [A] ThinkingData; [A] snippet từ trang tài liệu VeCDP (không tải được toàn trang) [?]; [A] Quick Audience AIPL |
| **Không khớp giá trị nào** | ThinkingData: khách không khớp **không có tag**, không có giá trị "khác" mặc định. Các nhà cung cấp khác không ghi rõ | [A] |
| **Không còn khớp sau một thời gian** | Youzan: cờ "自动删除" (tự xoá) cho tag gắn bằng luật; **tag gắn tay không bị xoá**. VeCDP: chọn "计算为空时保留空缺" (lần tính mới rỗng thì để trống) hoặc "保留历史值" (giữ giá trị cũ); kết quả lưu mặc định 32 ngày | [A] Youzan; [A] VeCDP private docs (snippet) [?] |
| **Đơn trị hay đa trị** | Youzan: nhóm tag chọn "仅可添加一个标签" (chỉ một tag, loại trừ lẫn nhau) hoặc "可添加多个" (nhiều tag). Weimob: kiểu giá trị 单选项 / 多选项 / 日期 / 文本 / 数值 (một lựa chọn / nhiều lựa chọn / ngày / văn bản / số) | [A] |

### 2.4 Vòng đời và vận hành tag

| Khía cạnh | Thực hành | Nguồn |
|---|---|---|
| Lịch cập nhật | Hằng ngày lúc 0h (Weimob, ThinkingData; có thể đặt độ trễ chờ dữ liệu đến muộn); "tính một lần" hoặc "tính mỗi ngày" (Quick Tracking); thủ công / định kỳ / thời gian thực (BytePlus). Offline cập nhật theo ngày, real-time trễ ở mức giây (Sensors) | [A]; [B] Sensors |
| Lịch sử | ThinkingData: mỗi lần cập nhật ghi kết quả thành version lịch sử theo ngày. Có thể tính lại một ngày hoặc một khoảng (backfill). Trạng thái version: Normal / Missing / **Outdated (điều kiện hoặc kiểu đã đổi)** / Failed | [A] |
| Version luật | Dataphin real-time tag: mỗi tag có số version; khi publish **chọn version và có màn hình so sánh version** | [A] |
| Trạng thái | Analysys: 上线/下线 (chạy hoặc ngừng cập nhật định kỳ), 生效/失效 (dùng được hoặc không trong phân nhóm/phân tích), 删除 (xoá vật lý cả lịch sử) | [A] |
| Cây danh mục tag | Mỗi tag thuộc một 标签类目 (danh mục tag). BytePlus: người không có quyền sửa cây tag thì tag mới vào "未分类" (chưa phân loại) | [A] |
| Duyệt | VeCDP có API `approvalUpdate` (cập nhật trạng thái duyệt tag) nhưng không có tài liệu quy trình công khai | [A] API list [?] |

---

## 3. SaaS cho người bán (tương tự Sapo): Youzan, Weimob, Jushuitan

### 3.1 Hạng hội viên (会员等级 huìyuán děngjí) của Youzan

| Chế độ | Căn cứ xếp hạng | Ngưỡng | Kỳ tính | Hạ hạng | Nguồn |
|---|---|---|---|---|---|
| 消费模式 (theo chi tiêu) | Chi tiêu thực tế | Mỗi hạng đặt một trong ba: tổng chi tiêu, giá trị một đơn, tổng số đơn; **đạt một điều kiện là lên hạng** | 1–12 tháng | Mỗi hạng đặt riêng điều kiện giữ hạng; hoàn tiền có thể làm hạ hạng | [A] |
| 成长值模式 (theo điểm tăng trưởng) | Điểm từ mua hàng, điểm danh, hoàn thiện hồ sơ | Điểm tối thiểu cho mỗi hạng | 1/3/12 tháng | Toàn cục: không hạ, hoặc hạ **mỗi lần một hạng** | [A] |
| 储值模式 (theo nạp tiền) | Số tiền một lần nạp | Một lần nạp ≥ mức của hạng | Mỗi lần nạp | Về hạng thấp nhất khi số dư < 0 | [A] |

Các chế độ chỉ chuyển được một chiều (theo điểm sang theo chi tiêu, không chuyển ngược lại). Khi admin chỉnh hạng bằng tay, điểm tăng trưởng tự điều chỉnh về ngưỡng của hạng mới [A]. **Bài học:** hạng hội viên là phép chia ngưỡng tuyệt đối do người bán đặt, có cửa sổ thời gian và có quy tắc giữ hạng (hysteresis). Đây không phải phân vị.

### 3.2 Tag khách hàng của Youzan và Weimob

| Thuộc tính | Youzan | Weimob | Nguồn |
|---|---|---|---|
| Nhóm tag | Đơn trị (loại trừ) hoặc đa trị | 单选/多选/日期/文本/数值 (một lựa chọn / nhiều lựa chọn / ngày / văn bản / số) | [A] |
| Điều kiện tự gắn | Thời điểm mua gần nhất, tổng số lần mua, tổng tiền, giá trị đơn trung bình, tổng điểm, đã mua sản phẩm X | Theo chiều đơn hàng / chi tiêu / sản phẩm / khách hàng / chuyển đổi quảng cáo Tencent | [A] |
| Logic | Khớp bất kỳ hoặc khớp tất cả | "统一打标" (cùng một điều kiện gắn một tag), "**多规则打标**" (nhiều khoảng số → nhiều tag, vd. cao/trung/thấp), "引用结果打标" (ghi trực tiếp giá trị số, vd. tiền 7 ngày, làm tag) | [A] |
| Số luật | — | **Một luật cho mỗi nhóm tag** | [A] |
| Lịch | Khách mới gắn tức thì; khách cũ gắn vào sáng sớm hôm sau | Hằng ngày lúc 0h | [A] |
| Tag gắn tay | Không bị tự xoá | Gắn hàng loạt theo tệp khách; chỉ tag số/ngày có tuỳ chọn ghi đè giá trị cũ | [A] |
| Kênh nguồn khách | — | Hồ sơ khách có "来源渠道" (kênh nguồn). Tài liệu gợi ý phân tầng tag theo kênh: quảng cáo, tài khoản công chúng (公众号), shop online, cửa hàng offline | [A] |

Weimob "多规则打标" về bản chất là **chia ngưỡng có tên** (luật dạng ngưỡng của chúng ta). "引用结果打标" là **feature lưu thành tag** (lớp feature của chúng ta).

### 3.3 Phân phối và CTV: 分销员 (fēnxiāo yuán) của Youzan

| Khái niệm | Nội dung | Nguồn |
|---|---|---|
| 分销员 / 销售员 (người phân phối / nhân viên bán) | Người giới thiệu (tương đương CTV hoặc affiliate), hưởng hoa hồng theo link | [A] |
| 客户关系绑定 (gắn quan hệ khách) | Khách được gắn với người phân phối qua link | [A] |
| 保护期 (thời hạn bảo vệ) | Trong thời hạn này, người phân phối khác không "giành" được khách. Tính từ lần click link cuối và **tự gia hạn khi khách click lại** (vd. 15 ngày, click lại ngày thứ 14 thì cộng thêm 15 ngày). Không nên dài hơn thời hạn hiệu lực của link | [A] |
| Tự mua | Đơn người phân phối tự đặt gắn với chính họ, không chịu thời hạn bảo vệ | [A] |

**Bài học:** "khách của CTV" không phải là tag cố định của khách. Đó là **quan hệ có hiệu lực theo thời gian** (khách → CTV, từ ngày, đến ngày). Phân loại đơn "qua CTV" nên dựa trên quan hệ còn hiệu lực tại thời điểm đặt đơn, không dựa trên tag hiện tại của khách.

### 3.4 Jushuitan (聚水潭, ERP quản lý đơn đa kênh): nguồn đơn và loại đơn là hai trục riêng

| Trục | Giá trị | Nguồn |
|---|---|---|
| **订单来源 (nguồn đơn)** | Shop nền tảng (嗨淘, TOP平台, 普通淘宝, 聚划算), 导入 (import), 手工下单 (tạo tay), 供销推送 (đơn nhà phân phối đẩy sang, mình là nhà cung cấp), 分销推送 (đẩy cho nhà cung cấp, mình là nhà phân phối), 分销商采购单推送 (đơn mua phối hợp của nhà phân phối), 线下直接拿货出库 (lấy hàng tại quầy) | [A] erp321 wiki (bản lịch sử) |
| **订单类型 (loại đơn)** | 普通订单 (đơn thường), **补发订单 (gửi bù, sinh từ hậu mãi)**, **换货订单 (đổi hàng)**, 天猫分销 (phân phối Tmall), 协同订单 (đơn phối hợp) | [A] |
| Hậu tố vai trò | 分销+ / 供销+ / cả hai, tuỳ khách là nhà phân phối hay nhà cung cấp | [A] |
| Luật xác định nhà cung cấp | Mã hàng dạng `[mã của nhà cung cấp]$$[mã nhà cung cấp]` có **ưu tiên cao nhất**, đứng trên chiến lược tự động theo shop/sản phẩm/mã kiểu | [A] snippet từ wiki |
| Tag/cờ đơn | ERP có 标签 (tag) và 旗帜 (cờ màu) để lọc đơn | [A] |
| Đơn offline | Module import dùng cho nền tảng chưa kết nối hoặc cửa hàng offline | [A] |

**Bài học:** (1) Đơn gửi bù và đơn đổi hàng là **mục đích đơn** (order purpose). Không gộp vào kênh, và không nên cộng vào doanh thu như đơn bán mới. (2) Luật phân loại có thứ tự ưu tiên: **khai báo tường minh (mã hàng) thắng suy luận (theo shop)**. Đây là tiền lệ cho "manual override > pattern > default".

### 3.5 Nhà phân phối/đại lý (经销商 jīngxiāoshāng)

Không tìm được tài liệu chính thức công khai đủ chi tiết về cấp đại lý hay bảng giá theo cấp của các nền tảng 订货 (B2B đặt hàng) Trung Quốc như 易订货 hoặc 聚经销 (trang 聚经销 trả lỗi 504) [?]. Thực hành phổ biến (không xác minh): cấp đại lý (一级/二级经销商: đại lý cấp 1/cấp 2) gắn với **bảng giá theo cấp (价格等级)**. Vì vậy cấp đại lý thường suy ra được từ **bảng giá áp cho khách** chứ không cần luật hành vi.

---

## 4. Taxonomy hàng hoá: Taobao/Tmall/JD

| Khái niệm | Pinyin / nghĩa | Nội dung | Nguồn |
|---|---|---|---|
| 后台类目 | hòutái lèimù: danh mục hậu đài | Cây danh mục chuẩn của nền tảng. **Hàng hoá chỉ được gắn ở danh mục lá (叶子类目)** | [C] woshipm, cnblogs |
| 前台类目 | qiántái: danh mục hiển thị | Cây danh mục cho người mua, ánh xạ sang danh mục hậu đài. Taobao tách hai cây từ khoảng năm 2008 | [C] |
| 属性模板 | shǔxìng múbǎn: mẫu thuộc tính | Gắn vào danh mục lá. Thuộc tính = tên + giá trị (CPV: category–property–value) | [C] |
| 关键属性 | guānjiàn: thuộc tính khoá | Danh mục + thuộc tính khoá xác định duy nhất SPU (vd. thương hiệu + model) | [C] |
| 销售属性 | xiāoshòu: thuộc tính bán | Tổ hợp tạo SKU (màu, dung lượng) | [C] |
| 非关键属性 | thuộc tính mô tả | Nạp tự động khi chọn danh mục lá | [C] |
| CSPU | — | Danh mục + thuộc tính khoá + thuộc tính bán | [C] |
| Nguồn giá trị thuộc tính | — | Một phần từ ủy ban chuẩn ngành, phần lớn do người bán và nền tảng cùng xây, có kiểm duyệt | [C] |
| 品牌 / 授权 | Thương hiệu / ủy quyền | API `taobao.itemcats.authorize.get` trả danh mục và thương hiệu người bán được ủy quyền. JD yêu cầu giấy chứng nhận hoặc ủy quyền nhãn hiệu | [C], cần đối chiếu open.taobao.com (không tải được) |
| 店铺自定义分类 | diànpù zìdìngyì fēnlèi: danh mục tự định nghĩa của shop | Danh mục riêng của shop, độc lập với cây của nền tảng (API `sellercats`). Một sản phẩm có thể thuộc nhiều danh mục shop | [?] không lấy được tài liệu chính thức |

**Bài học:** nền tảng giữ **danh mục canonical (lá) bắt buộc, đơn trị, có thuộc tính chuẩn**. Shop giữ **danh mục tự do, đa trị, chỉ dùng cho hiển thị và bán hàng**. Hai lớp này cùng tồn tại, không lớp nào thay lớp nào. Thương hiệu là một thư viện có kiểm soát, không phải chuỗi tự do.

---

## 5. Mô hình giá trị khách hàng

### 5.1 RFM 8 nhóm (Quick Audience: định nghĩa chính thức)

Cách tính: mỗi chiều R/F/M chấm **3 hoặc 5 mức** theo khoảng tuyệt đối do người dùng đặt. Ví dụ R: 0–30 ngày = 3 điểm, 31–90 = 2, >90 = 1. So điểm với **giá trị so sánh**: mặc định là **trung bình có trọng số của toàn bộ khách hàng**, hoặc giá trị tự đặt. Điểm ≥ giá trị so sánh là Cao, ngược lại là Thấp [A].

| Nhóm (中文) | Pinyin / tiếng Việt | R | F | M |
|---|---|---|---|---|
| 高价值用户 (cũng gọi 重要价值客户) | gāo jiàzhí: giá trị cao | Cao | Cao | Cao |
| 重点保持用户 | zhòngdiǎn bǎochí: cần giữ chân | Thấp | Cao | Cao |
| 重点发展用户 | zhòngdiǎn fāzhǎn: cần phát triển | Cao | Thấp | Cao |
| 重点挽留用户 | zhòngdiǎn wǎnliú: cần cứu vãn | Thấp | Thấp | Cao |
| 一般价值用户 | yìbān jiàzhí: giá trị thường | Cao | Cao | Thấp |
| 一般保持用户 | yìbān bǎochí: giữ chân thường | Thấp | Cao | Thấp |
| 一般发展用户 | yìbān fāzhǎn: phát triển thường | Cao | Thấp | Thấp |
| 潜在用户 | qiánzài: tiềm năng | Thấp | Thấp | Thấp |

Nguồn: [A] Quick Audience RFM model. Tên gọi "重要价值客户" (khách giá trị quan trọng) là cách gọi phổ biến trong ngành; tài liệu Alibaba gọi là "高价值用户".

**Đây là mẫu tham khảo tốt nhất cho dạng luật "bảng quyết định".** Feature (R/F/M) → ngưỡng (khoảng điểm) → Cao/Thấp (so với trung bình hoặc giá trị tự đặt) → bảng 2×2×2 → 8 giá trị canonical cố định. Người bán chỉ chỉnh ngưỡng; tập giá trị đầu ra giữ nguyên.

### 5.2 AIPL, FAST, GROW (Alibaba / Tmall)

| Mô hình | Giá trị / chỉ số | Định nghĩa | Nguồn |
|---|---|---|---|
| AIPL | A Awareness (认知: nhận biết) | Tiếp xúc thụ động: thấy quảng cáo, tìm từ khoá danh mục | [A] Quick Audience |
| | I Interest (兴趣: quan tâm) | Tiếp xúc chủ động: click quảng cáo, xem trang thương hiệu/sản phẩm, tìm từ khoá thương hiệu, nhận dùng thử, theo dõi/vào hội viên, thêm giỏ/yêu thích | [A] |
| | P Purchase (购买: mua) | Đã mua | [A] |
| | L Loyalty (忠诚: trung thành) | Mua lại, đánh giá tốt, chia sẻ | [A] |
| | Thứ tự | **A<I<P<L; khớp nhiều giai đoạn thì lấy giai đoạn cao nhất** | [A] |
| | Cấu hình | Mỗi nhóm cấu hình kênh nguồn, kênh hành vi, loại hành vi + khoảng thời gian, tối đa 2 chỉ số thống kê + 5 điều kiện thuộc tính (AND). Giữa các luật dùng AND/OR/hiệu | [A] |
| FAST | Fertility, Advancing, Superiority, Thriving | Đánh giá sức khoẻ tài sản tập khách hàng theo lượng và chất. F = tổng số khách AIPL. "Khách hàng hoạt động" tính theo cửa sổ: nhận biết 15 ngày, quan tâm 15 ngày, mua 2,5 năm, trung thành 1 năm | [C] bookdown; tên tiếng Trung từng chữ cái chưa thống nhất [?] |
| GROW | Gain 渗透力 (độ thâm nhập), Retain 复购力 (mua lại), bOOst 价格力 (sức giá), Widen 新品力 (sản phẩm mới) | Tách tăng trưởng GMV của thương hiệu ngành FMCG thành các nhân tố. Do Tmall FMCG cùng Bain đưa ra | [B] digitaling (báo ngành) |

Cửa sổ thời gian của AIPL/FAST cho thấy **các giai đoạn dùng cửa sổ khác nhau** (giai đoạn nhận biết ngắn, giai đoạn mua dài). Ngưỡng ngày của vòng đời không nên là một tham số chung cho mọi giai đoạn.

### 5.3 O-5A (Ocean Engine / Douyin 巨量云图)

| Mức | Tên | Hành vi điển hình trên Douyin | Nguồn |
|---|---|---|---|
| O | 机会人群 (nhóm cơ hội) | Hoạt động trong các lĩnh vực quan tâm liên quan, chưa tiếp xúc thương hiệu | [C] woshipm, digitaling |
| A1 | 了解 (biết đến) | Thấy thụ động | [C] |
| A2 | 吸引 (bị thu hút) | Tương tác nhẹ: vào trang chủ, thích, bình luận | [C] |
| A3 | 种草 (zhòngcǎo: "gieo cỏ", nảy ý muốn mua; mô hình 5A của Kotler gọi là 问询 hỏi thăm) | Tìm kiếm, thêm giỏ, chuyển trang | [C] |
| A4 | 购买 (mua) | Mua | [C] |
| A5 | 复购 / 拥护 (mua lại / ủng hộ) | Mua lại, theo dõi, đánh giá tốt, chia sẻ | [C] |

Ocean Engine còn có "商品 5A" (5A cấp sản phẩm). Chưa lấy được whitepaper chính thức (Roland Berger × 巨量引擎); định nghĩa cửa sổ ngày của từng mức chưa xác minh [?]. Có báo cáo cho biết tài sản nhóm 5A đóng góp 77% GMV (năm 2023) [B, Sina].

### 5.4 Vòng đời hội viên (会员生命周期)

Không có định nghĩa chuẩn duy nhất. Thực hành phổ biến: 新客 (khách mới), 活跃 (hoạt động), 沉睡/预警 (ngủ đông/cảnh báo), 流失 (rời bỏ), 召回 (khách quay lại). **Ngưỡng lấy theo chu kỳ mua của ngành hàng** (điểm gãy, tứ phân vị), không dùng số cố định [C]. BytePlus CDP coi vòng đời là một loại tag mô hình có sẵn, đứng cạnh RFM [A].

**Tuyệt đối hay tương đối (tổng hợp):**

| Kiểu ngưỡng | Ví dụ ở Trung Quốc | Ưu điểm | Nhược điểm |
|---|---|---|---|
| Tuyệt đối | Hạng hội viên Youzan (tổng chi tiêu ≥ X); khoảng điểm R/F/M | Ổn định, dễ giải thích với khách hàng, đem đi giao kèo quyền lợi được | Phải hiệu chỉnh theo từng doanh nghiệp; sai lệch khi giá cả hoặc quy mô thay đổi |
| Tương đối | So với trung bình trong RFM; tứ phân vị; quy tắc 80/20 | Chạy ngay không cần cấu hình | Nhãn của một khách thay đổi khi tập khách thay đổi, khó so sánh qua thời gian |
| Lai (Quick Audience) | Chấm điểm tuyệt đối, xếp Cao/Thấp tương đối | Cân bằng hai bên | Phức tạp hơn khi giải thích |

---

## 6. Douyin: phân loại kênh và nguồn traffic (tương tự TikTok Shop Việt Nam)

| Trục | Giá trị | Định nghĩa | Nguồn |
|---|---|---|---|
| **场 (bối cảnh mua)** | 内容场 (nội dung) / 货架场 (kệ hàng) | Nội dung: video/live, "hàng tìm người", phù hợp sản phẩm hot và khách mới. Kệ hàng: trung tâm mua sắm (商城), tìm kiếm, shop, "người tìm hàng", phù hợp mua lại | [B] pedaily, tmtpost; năm 2022 Douyin chuyển định vị sang "全域兴趣电商" |
| **载体 (hình thức nội dung)** | 直播 (live) / 短视频 (video ngắn) / 商品卡 (thẻ sản phẩm) / 图文 (ảnh + chữ) | Thẻ sản phẩm là "hình thức hiển thị thông tin sản phẩm trong bối cảnh kệ hàng", đứng ngang với live và video | [B] lời PCT Douyin (木青) trích trên báo; 图文 [?] |
| **主体 (chủ thể bán)** | 店播/自播 (người bán tự live) / 达播/达人带货 (KOL live/bán hộ) | Live của KOL: người live là cá nhân. Live của shop: người live là thương hiệu hoặc shop | [B] báo chí; có tỷ lệ tham khảo "kệ hàng 40%, live shop 30%, live KOL 30%", **không rõ năm và nguồn** [?] |
| **流量来源 (nguồn traffic)** | 自然流量 (tự nhiên) / 广告流量 (quảng cáo) / 社交分享 (chia sẻ); live: 推荐Feed (feed đề xuất), 直播广场 (quảng trường live), 关注 (người theo dõi), 同城 (cùng thành phố), 短视频引流 (dẫn từ video) | Trục traffic tách khỏi trục kênh | [C] fanruan, woshipm |

Cùng trên một đơn, các trục này **trực giao** với nhau. Một đơn có thể đồng thời là "live", "KOL" và "traffic quảng cáo". TikTok Shop (bản quốc tế) cũng chia GMV theo LIVE / Video / Product card và theo tài khoản của người bán / affiliate. GMV Max quy cả đơn tự nhiên lẫn đơn trả phí cho chiến dịch [A ads.tiktok.com cho GMV Max; C cho cách chia Data Compass].

**Bài học:** nếu gộp các trục thành một enum `channel` (vd. `TIKTOK_LIVE_KOL`) thì sẽ bùng nổ tổ hợp và mất khả năng phân tích theo từng trục. Nên giữ từng trục là một domain riêng, mỗi domain có tập canonical nhỏ.

---

## 7. Bài học thiết kế: phần nào canonical, phần nào do người bán định nghĩa

### 7.1 Ranh giới canonical / người bán trong thực tiễn Trung Quốc

| Đối tượng | Canonical (nền tảng hoặc sản phẩm sở hữu) | Người bán định nghĩa | Nguồn |
|---|---|---|---|
| Chỉ số | Chỉ số nguyên tử (cách tính) ở tầng công cộng | Kết hợp từ bổ nghĩa và kỳ thời gian để ra chỉ số dẫn xuất | [A] DataWorks |
| Tập giá trị phân loại | 标准代码 (bảng mã) | Từ bổ nghĩa thường (nhãn tự do) | [A] |
| Danh mục sản phẩm | Cây hậu đài, danh mục lá, thuộc tính khoá/bán | Danh mục của shop | [C] |
| Thương hiệu | Thư viện thương hiệu và ủy quyền | — | [C] |
| Hạng hội viên | Khung 3 chế độ và cơ chế giữ hạng | Số hạng, tên hạng, ngưỡng | [A] Youzan |
| Tag khách hàng | Kiểu nhóm tag (đơn/đa trị, kiểu giá trị), loại điều kiện, lịch chạy | Tên tag, giá trị, điều kiện | [A] Youzan/Weimob |
| Giá trị khách hàng | 8 nhóm RFM, AIPL, O-5A (tập giá trị cố định) | Khoảng điểm, giá trị so sánh, cửa sổ | [A] Quick Audience |
| Kênh/đơn | Enum nguồn đơn và loại đơn của ERP | Tag và cờ đơn | [A] Jushuitan |

### 7.2 Người dùng nghiệp vụ định nghĩa luật mà không cần code

1. **Chọn feature từ danh mục có sẵn.** Không viết biểu thức; feature (tổng tiền, số lần, lần mua cuối, đã mua SP X) do sản phẩm định nghĩa [A Youzan, Weimob, Quick Tracking].
2. **Mỗi giá trị = một nhóm điều kiện AND/OR; có giới hạn độ sâu và số giá trị** (20–25 giá trị, 5 tầng) [A].
3. **Xem trước phân bố trước khi lưu.** Quick Audience hiện số khách mỗi khoảng điểm và trung bình để người dùng chọn ngưỡng. Analysys cho xem trước phân bố rồi mới chạy [A].
4. **SQL là đường thoát dành cho người có kỹ năng** (BytePlus SQL tags), không phải đường mặc định [A].
5. **Import tệp hoặc gắn tay là lớp override** [A].

### 7.3 Quản trị (版本 version, 审批 duyệt, 血缘 lineage)

| Cơ chế | Có trong tài liệu công khai | Nguồn |
|---|---|---|
| Version và so sánh trước khi publish | Có (Dataphin real-time tag) | [A] |
| Lịch sử kết quả theo ngày, backfill, trạng thái Outdated khi luật đổi | Có (ThinkingData) | [A] |
| Kiểm tra giá trị enum tự động | Có (DataWorks, theo bảng mã) | [A] |
| Vòng đời tag (chạy/ngừng/dùng được/không dùng được/xoá) | Có (Analysys) | [A] |
| Phân quyền sửa/publish mô hình; phân quyền cây tag | Có (DataWorks, BytePlus) | [A] |
| Quy trình duyệt tag | Chỉ có tên API, không có tài liệu quy trình | [A]/[?] |
| Lineage tag → nguồn | Không tìm thấy tài liệu cụ thể trong lần nghiên cứu này | [?] |

---

## 8. Ánh xạ sang mô hình của chúng ta

Mô hình đích: **feature do sản phẩm định nghĩa → luật dạng dữ liệu (ánh xạ trực tiếp, dò mẫu có ưu tiên, chia ngưỡng, bảng quyết định, manual override) → nhãn tenant + giá trị canonical bắt buộc.**

### 8.1 Đối chiếu khái niệm

| Khái niệm của chúng ta | Tương đương ở Trung Quốc | Ghi chú |
|---|---|---|
| Domain | Nhóm tag (标签组) / chiều | Khai báo kiểu đơn/đa trị như Youzan và Weimob |
| Giá trị canonical | 标准代码 (bảng mã) / tập giá trị mô hình cố định (8 nhóm RFM, AIPL) | Bắt buộc, giống 维度枚举修饰词 |
| Nhãn tenant | 修饰词 thường / tên tag của người bán | Tự do, nhưng phải ánh xạ sang một giá trị canonical |
| Feature | 指标统计, 首末次, 偏好, 引用结果打标 | Do sản phẩm tính sẵn; người bán không viết |
| Ánh xạ trực tiếp | 码表 mapping; ERP nhận diện shop theo ID | |
| Dò mẫu có ưu tiên | ThinkingData first-match; VeCDP chế độ một giá trị theo ưu tiên | |
| Chia ngưỡng | Weimob 多规则打标; Youzan 消费模式; khoảng điểm RFM | |
| Bảng quyết định | RFM 2×2×2; AIPL lấy giai đoạn cao nhất | |
| Manual override | Tag gắn tay của Youzan (không tự xoá); Jushuitan mã `$$` ưu tiên cao nhất; import | |
| UNMAPPED + monitor | Quy tắc DataWorks "enum không khớp = 0" | Trung Quốc **bỏ qua** khách không khớp (ThinkingData); chúng ta nên **giữ tường minh** |

### 8.2 Bảng ánh xạ theo domain

| Domain | Feature (sản phẩm) | Dạng luật chính | Ví dụ nhãn tenant | Đề xuất giá trị canonical | Tham chiếu Trung Quốc |
|---|---|---|---|---|---|
| `sales_channel` (nền tảng) | `source_name`, `shop_id`, `location_id` | Ánh xạ trực tiếp, dò mẫu có ưu tiên | "Shopee Mall HCM", "Live Fanpage" | `MARKETPLACE`, `SOCIAL_COMMERCE`, `OWN_WEB`, `CHAT_SOCIAL` (FB/Zalo), `POS_OFFLINE`, `B2B_DIRECT`, `OTHER`, `UNMAPPED` | 订单来源 của Jushuitan |
| `platform` | connector + shop | Ánh xạ trực tiếp | "Shopee", "TikTok Shop" | `SHOPEE`, `TIKTOK_SHOP`, `LAZADA`, `SAPO_WEB`, `HARAVAN`, ... | Shop/nền tảng của ERP |
| `content_carrier` | nguồn đơn TikTok/Shopee (nếu API có) | Ánh xạ trực tiếp | "LIVE", "VIDEO" | `LIVE`, `SHORT_VIDEO`, `PRODUCT_CARD`, `NONE`, `UNKNOWN` | 载体 của Douyin |
| `seller_role` | affiliate/creator id trên đơn | Ánh xạ trực tiếp + override | "KOL A", "Live nhà" | `SELF`, `AFFILIATE_KOL`, `CTV_RESELLER`, `UNKNOWN` | 店播/达播 |
| `order_purpose` | tag đơn, giá = 0, ghi chú, liên kết đơn đổi trả | Dò mẫu có ưu tiên + override | "Đơn tặng KOL", "Gửi bù" | `SALE`, `REPLACEMENT`, `EXCHANGE`, `GIFT_SAMPLE`, `INTERNAL_USE`, `UNMAPPED` | 订单类型 của Jushuitan (普通/补发/换货) |
| `customer_type` | nhóm khách nguồn, bảng giá áp dụng, tag | Ánh xạ trực tiếp, dò mẫu + override (sticky) | "ĐẠI LÝ CẤP 1", "CTV", "LẺ" | `B2C_RETAIL`, `B2B_WHOLESALE`, `DEALER`, `RESELLER_CTV`, `KOL_AFFILIATE`, `STAFF`, `UNMAPPED` | 分销/供销 role; 价格等级 [?] |
| `dealer_tier` | bảng giá / nhóm khách | Ánh xạ trực tiếp | "Cấp 1", "Cấp 2" | `TIER_1`, `TIER_2`, `TIER_3`, `NONE` | 一级/二级经销商 [?] |
| `ctv_attribution` (quan hệ) | link, mã giới thiệu, nhân viên phụ trách | Quan hệ theo thời gian + override | — | (khách → CTV, valid_from, valid_to) | 分销员保护期 của Youzan |
| `rfm_segment` | R (ngày), F (số đơn trong N ngày), M (tiền trong N ngày) | Chia ngưỡng + bảng quyết định | Tên tiếng Việt do tenant đặt | 8 giá trị theo Quick Audience | Quick Audience RFM |
| `value_tier` (hạng) | tổng chi tiêu / giá trị đơn / số đơn trong cửa sổ | Chia ngưỡng (tuyệt đối hoặc phân vị) + giữ hạng | "VIP", "Kim cương" | `TIER_TOP`, `TIER_HIGH`, `TIER_MID`, `TIER_BASE` (theo thứ tự, tên do tenant) | 会员等级 của Youzan |
| `lifecycle` | ngày mua đầu/cuối, số đơn | Chia ngưỡng (cửa sổ theo ngành hàng) | "Ngủ đông" | `NEW`, `ACTIVE`, `AT_RISK`, `CHURNED`, `REACTIVATED`, `PROSPECT` | 会员生命周期; cửa sổ của AIPL/FAST |
| `engagement_stage` (tuỳ chọn) | hành vi (nếu có dữ liệu sự kiện) | Bảng quyết định (lấy giai đoạn cao nhất) | — | `AWARE`, `INTEREST`, `PURCHASE`, `LOYAL` | AIPL / O-5A |
| `product_category` | danh mục nguồn, danh mục shop, tên SP | Ánh xạ trực tiếp + dò mẫu | Danh mục Sapo của shop | Cây canonical L1–L2 (đề xuất ánh xạ từ danh mục lá của Shopee/TikTok) | 后台类目 vs 店铺自定义分类 |
| `brand` | trường vendor/brand, tên SP | Ánh xạ trực tiếp (thư viện) | "FJ", "Fine Japan" | ID thương hiệu chuẩn hoá | 品牌库 |
| `discount_type` | tên CTKM, mã giảm giá, nguồn tài trợ | Dò mẫu có ưu tiên | "Flash sale 9.9" | `PLATFORM_VOUCHER`, `SELLER_VOUCHER`, `PRICE_MARKDOWN`, `BUNDLE`, `LOYALTY`, `SHIPPING`, `UNMAPPED` | (không có nguồn Trung Quốc chính thức trong lần này [?]) |

### 8.3 Thuộc tính mỗi domain phải khai báo (rút từ mục 2.3)

| Thuộc tính | Giá trị | Lấy cảm hứng từ |
|---|---|---|
| `cardinality` | `single` / `multi` | Youzan "仅可添加一个标签"; Weimob 单选/多选 |
| `multi_match_policy` | `first_match` (theo `priority`) / `keep_all` | ThinkingData; VeCDP 标签值保存类型 |
| `unmatched_value` | luôn là `UNMAPPED` (không bỏ qua) | Khác ThinkingData; khớp DataWorks enum check |
| `stickiness` | `recompute` / `keep_last` / `manual_wins` | Youzan 自动删除; VeCDP 保留历史值 |
| `as_of` | đánh giá tại thời điểm đơn hay thời điểm hiện tại | Thời hạn bảo vệ của Youzan; version lịch sử của ThinkingData |
| `refresh` | hằng ngày (mặc định) | Weimob/ThinkingData 0h |

---

## 9. Gợi ý cho thị trường Việt Nam (xếp theo mức ưu tiên)

| # | Khuyến nghị | Lý do | Rủi ro / đánh đổi | Mức tin cậy |
|---|---|---|---|---|
| 1 | **Mỗi domain có một bảng mã canonical đóng, có `UNMAPPED`. Nhãn tenant là văn bản tự do nhưng bắt buộc ánh xạ sang mã canonical.** Kiểm tra tự động: số dòng có giá trị ngoài bảng mã = 0 | Đúng mô hình 维度枚举修饰词 + 标准代码 của DataWorks; report chạy được cho mọi tenant | Tập canonical quá thô sẽ làm mất thông tin. Giảm bằng cách giữ song song nhãn tenant cho drill-down | Cao (nguồn [A]) |
| 2 | **Tách "kênh" thành các trục trực giao:** `platform`, `sales_channel`, `content_carrier`, `seller_role`, và tách `order_purpose` khỏi kênh | Jushuitan tách nguồn đơn/loại đơn; Douyin tách bối cảnh/hình thức/chủ thể. TikTok Shop VN có cùng cấu trúc LIVE/Video/Product card + affiliate | Nhiều cột hơn. API Sapo/Shopee có thể không có `content_carrier`, khi đó để `UNKNOWN` | Cao về nguyên tắc; trung bình về giá trị cụ thể (nguồn Douyin [B/C]) |
| 3 | **Khai báo `cardinality`, `multi_match_policy`, `stickiness` cho từng domain.** Mặc định: đơn trị + first-match theo priority + recompute; riêng `customer_type` dùng `manual_wins` | Ba điểm này là nơi các nhà cung cấp khác nhau nhiều nhất, và cũng là nguồn lệch hiện tại (vd. CROSSBORDER có 3 định nghĩa) | Nếu đổi policy thì số liệu đổi; phải đi qua gate | Cao |
| 4 | **Ngưỡng mặc định dạng lai cho tenant mới:** chia ngưỡng tuyệt đối có giá trị mặc định theo ngành hàng; RFM Cao/Thấp so với trung bình. Tenant chuyển sang ngưỡng tuyệt đối riêng sau khi xem phân bố | Theo Quick Audience. SME Việt Nam thường không biết đặt ngưỡng ngay từ đầu | Nhãn tương đối trôi theo thời gian, nên snapshot theo tháng | Cao (nguồn [A]) |
| 5 | **Dùng tập canonical có sẵn cho giá trị khách hàng:** 8 nhóm RFM (đổi tên tiếng Việt, giữ mã) và vòng đời 5–6 trạng thái. Chỉ dùng AIPL/5A khi có dữ liệu hành vi | Không phải phát minh lại; người dùng đã quen qua các bài học thương mại điện tử Trung Quốc | AIPL/5A cần dữ liệu sự kiện mà Sapo/MISA không có, nên để sau | Cao |
| 6 | **Manual override là một lớp riêng có ưu tiên cao nhất, có người tạo, thời gian và lý do.** Luật không bao giờ ghi đè override | Tag gắn tay của Youzan không bị tự xoá; mã `$$` của Jushuitan thắng chiến lược; Weimob bắt nhập lý do khi đổi hạng | Override bị lãng quên. Cần monitor override đã cũ | Cao |
| 7 | **Phân loại CTV/affiliate là quan hệ theo thời gian, không phải tag hiện tại của khách.** Phân loại đơn theo quan hệ còn hiệu lực tại thời điểm đặt | Thời hạn bảo vệ của Youzan. Mô hình CTV ở Việt Nam rất giống | Cần dữ liệu link/mã giới thiệu; Sapo có thể chỉ có "nhân viên phụ trách" | Trung bình |
| 8 | **Danh mục sản phẩm hai lớp:** giữ danh mục của shop (đa trị, nhãn tenant) và ánh xạ sang cây canonical 2 cấp. Gợi ý lấy từ danh mục lá của Shopee/TikTok khi sản phẩm có bán trên sàn | Mô hình hậu đài/shop của Taobao | Ánh xạ thủ công tốn công. Tự gợi ý từ danh mục sàn khi có | Trung bình (nguồn [C]) |
| 9 | **Quản trị tối thiểu:** luật có version; xem trước khác biệt (phân bố trước/sau, % UNMAPPED, danh sách khoá bị đổi nhãn) trước khi áp dụng; lưu snapshot nhãn theo ngày; trạng thái `active/inactive` | Dataphin so sánh version; ThinkingData lưu lịch sử và trạng thái Outdated; Analysys trạng thái vòng đời. Khớp với gate phase 0 | Quy trình duyệt nhiều cấp là thừa với SME; chỉ cần một người duyệt | Cao |
| 10 | **Giới hạn độ phức tạp luật trên UI hoặc Sheet** (≤ 25 giá trị mỗi domain, điều kiện lồng nông). Luật chéo bảng thì dùng SQL do mình viết | Tất cả CDP lớn đều đặt giới hạn tương tự | Một số tenant cần nhiều hơn; xử lý qua escape hatch | Trung bình |

---

## 10. Hạn chế của nghiên cứu này

- **Không đọc được nguồn gốc** sách 《大数据之路》, whitepaper O-5A, tài liệu open.taobao.com (bị chặn), trang 聚经销 (504), và trang quy tắc tag VeCDP (trang rỗng, chỉ có snippet từ kết quả tìm kiếm). Các mục liên quan đã đánh dấu [?] hoặc [C].
- **Sensors Data (神策) và GrowingIO:** không lấy được tài liệu chính thức về loại tag (PDF của Sensors bị lỗi kết nối). Nội dung về tag dựa chủ yếu vào Alibaba (Quick Tracking/Quick Audience/Dataphin), ByteDance (BytePlus/VeCDP), ThinkingData, Youzan, Weimob. Các nhà cung cấp này đủ đại diện, nhưng thiếu góc nhìn của Sensors.
- **Phân loại kênh Douyin** không có định nghĩa chỉ số chính thức (罗盘 Compass); đang dựa vào báo chí. Tỷ lệ GMV kệ hàng/live shop/live KOL không rõ nguồn.
- **Loại giảm giá (discount type) và cấp đại lý** không tìm được nguồn Trung Quốc chính thức. Phần đề xuất canonical cho hai domain này là suy luận của người nghiên cứu.
- Tài liệu SaaS (Youzan/Weimob/Jushuitan wiki) có thể là bản cũ; giao diện có thể đã đổi. Chỉ dùng làm tiền lệ thiết kế, không dùng làm đặc tả.

## 11. Câu hỏi còn mở (cần quyết định trước Đợt 4)

1. Tập canonical của `customer_type` có tách `DEALER` khỏi `B2B_WHOLESALE` không, hay `dealer_tier` là domain con?
2. `order_purpose` (gửi bù, đổi hàng, quà tặng) có loại khỏi doanh thu mặc định không? Nếu có thì số liệu sẽ đổi so với hiện tại.
3. API Sapo/Shopee/TikTok Shop VN có trả `content_carrier` và affiliate trên đơn không? Cần khảo sát connector.
4. Mặc định `lifecycle` theo ngày cố định (30/90/180) hay theo chu kỳ mua của ngành hàng?
5. Nhãn tương đối (RFM so với trung bình) có cần snapshot theo tháng để so sánh qua thời gian không?

---

## Nguồn (truy cập 2026-10-14)

**Alibaba Cloud: DataWorks / Dataphin / Quick Audience / Quick Tracking [A]**
- DataWorks 数据指标: https://help.aliyun.com/zh/dataworks/user-guide/data-metric
- DataWorks 原子指标: https://www.alibabacloud.com/help/zh/dataworks/user-guide/atomic-metric
- DataWorks 派生指标: https://help.aliyun.com/zh/dataworks/user-guide/derived-metric
- DataWorks 修饰词: https://help.aliyun.com/zh/dataworks/user-guide/modifier
- DataWorks 时间周期: https://help.aliyun.com/zh/dataworks/user-guide/period
- DataWorks 数据标准: https://help.aliyun.com/zh/dataworks/user-guide/data-standards
- DataWorks 数据建模概述: https://help.aliyun.com/zh/dataworks/user-guide/data-modeling-overview/
- DataWorks 维度与总线矩阵: https://help.aliyun.com/zh/dataworks/define-dimensions-and-build-a-bus-matrix
- DataWorks 数据规划: https://help.aliyun.com/zh/dataworks/user-guide/data-planning-overview
- Dataphin 派生指标: https://help.aliyun.com/zh/dataphin/fullmanaged/user-guide/create-derived-metrics
- Dataphin 核心概念: https://help.aliyun.com/zh/dataphin/product-overview/core-concepts
- Dataphin 规则组合实时标签: https://help.aliyun.com/zh/dataphin/semimanaged-v4/user-guide/create-real-time-labels-through-rule-combinations
- Dataphin 指标映射标签: https://help.aliyun.com/en/dataphin/fullmanaged/user-guide/create-indicator-mapping-tags
- Quick Audience 是什么: https://help.aliyun.com/zh/document_detail/136924.html
- Quick Audience RFM 模型: https://www.alibabacloud.com/help/zh/quick-audience/latest/rfm-model
- Quick Audience AIPL 模型: https://www.alibabacloud.com/help/zh/quick-audience/latest/aipl-model
- Quick Tracking 标签体系: https://help.aliyun.com/zh/document_detail/471998.html

**ByteDance / Volcengine / BytePlus [A]**
- BytePlus CDP overview: https://docs.byteplus.com/de/docs/cdp/Overview___
- BytePlus CDP Statistical Tags: https://docs.byteplus.com/id/docs/cdp/Statistical_Tags
- BytePlus CDP Life Cycle Tags: https://docs.byteplus.com/en/docs/cdp/Life_Cycle_Tags
- VeCDP 规则标签 (chỉ có snippet từ tìm kiếm, không tải được trang): https://docs.volcengine.com/docs/6356/81266
- VeCDP 私有化 API 列表: https://docs.volcengine.com/docs/7139/1302030?lang=zh
- TikTok Ads, About attribution for GMV Max: https://ads.tiktok.com/help/article/about-attribution-for-gmv-max

**CDP/phân tích khác [A]**
- ThinkingData User Tags v3.8: https://docs.thinkingdata.cn/ta-manual/v3.8/en/user_guide/user_analysis/tag.html
- Analysys 标签生命周期管理: https://arkdocs.analysys.cn/features/user/user-profile/taglifecycle
- Analysys 自定义标签: https://arkdocs.analysys.cn/features/user/user-profile/tag-customize

**SaaS cho người bán [A]**
- Youzan 标签组管理: https://help.youzan.com/displaylist/detail_4_4-2-81977
- Youzan 消费/成长值/储值模式: https://help.youzan.com/displaylist/detail_44_44-2-79695
- Youzan 会员等级使用教程: https://help.youzan.com/displaylist/detail_4_4-2-21541
- Youzan 分销员保护期: https://help.youzan.com/displaylist/detail_13_13-1-36368
- Youzan 分销员绑定关系说明: https://help.youzan.com/displaylist/detail_5_5-2-32061
- Weimob 客户标签: https://help.weimob.com/os/article/4387
- Weimob 客户标签 (bài 2): https://help.weimob.com/os/article/6402
- Jushuitan SaaS 百科, 订单模块: https://www.erp321.com/app/wiki/historydetail.aspx?id=5&logid=764
- Jushuitan SaaS 百科, 导入订单: https://www.erp321.com/app/wiki/historydetail.aspx?id=76&logid=643
- Jushuitan 全渠道分销: https://www.jushuitan.com/solution/fenxiao.html

**Phương pháp luận, báo chí, bên thứ ba [B]/[C]**
- OneData tổng quan (woshipm) [C]: https://www.woshipm.com/share/6034772.html
- OneData chỉ số (woshipm) [C]: https://www.woshipm.com/pd/3605275.html
- Aliyun developer, OneData [B]: https://developer.aliyun.com/article/785122
- Phân loại tag sự kiện/luật/dự báo (woshipm) [C]: https://www.woshipm.com/it/5132049.html
- Hệ thống danh mục và thuộc tính Taobao [C]: https://www.woshipm.com/pd/4369061.html ; https://www.cnblogs.com/Jelena1028/p/20813610
- Mô hình FAST (bookdown, tài liệu cá nhân) [C]: https://bookdown.org/hellosunny2016/bookdown/customeranalysis.html
- GROW 2.0, Tmall × Bain [B]: https://www.digitaling.com/articles/277619.html
- O-5A, Douyin và Xiaohongshu [C]: https://www.woshipm.com/marketing/6065234.html
- Whitepaper O-5A (Roland Berger × 巨量引擎, chưa tải được toàn văn): https://www.rolandberger.com/zh/Insights/Publications/%E5%B7%A8%E9%87%8F%E5%BC%95%E6%93%8EO-5A%E4%BA%BA%E7%BE%A4%E8%B5%84%E4%BA%A7%E7%BB%8F%E8%90%A5%E6%96%B9%E6%B3%95%E8%AE%BA.html
- Ocean Engine 5A, số liệu năm 2023 [B]: https://news.sina.com.cn/sx/2022-07-22/detail-imizmscv3073900.shtml
- Douyin kênh nội dung và kệ hàng [B]: https://news.pedaily.cn/20230601/59488.shtml ; https://www.tmtpost.com/7298197.html
- Douyin, nguồn traffic live [C]: https://www.woshipm.com/operate/4548189.html ; https://www.fanruan.com/blog/article/1573387/
