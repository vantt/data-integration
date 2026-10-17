---
title: "Hội đồng phản biện — góc nhìn Product Owner / Customer Success (SME TMĐT Việt Nam)"
reviewer: council-product
date: 2026-10-14
target: ../../report-product-design.md (draft v1)
inputs: [roadmap.md (Đợt 5, Đợt 7, Module sản phẩm, Thứ tự ưu tiên), references/reports/external-references.md, references/reports/handbook-inventory.md, docs/analytics-handbook/semantic/rules.md]
---

# Phản biện thiết kế "xưởng report" — góc nhìn sản phẩm và chăm sóc khách hàng

Vai trò: product owner kiêm customer success cho khách SME TMĐT Việt Nam (từ người bán một mình đến công ty 50 nhân sự), sản phẩm cài trên hạ tầng của khách, hỗ trợ từ xa qua Tailscale/TeamViewer. Tôi đánh giá thiết kế theo bốn câu hỏi: khách mới thấy giá trị sau bao lâu, chủ shop thật sự nhìn vào đâu, report riêng được yêu cầu, làm và bảo trì thế nào, và mỗi lựa chọn sinh ra bao nhiêu ticket hỗ trợ.

## Tóm tắt điều hành

1. Phần lõi kỹ thuật (một registry chỉ tiêu, catalog mở khoá theo khả năng dữ liệu, overlay không được sửa định nghĩa gốc, deployer idempotent không ghi cứng `field_id`) là đúng và nên giữ nguyên.
2. Thiết kế đang tối ưu cho người làm report, chưa tối ưu cho người xem report. Không có mục nào nói chủ shop mở cái gì vào sáng mai, trên điện thoại, khi Metabase nằm trong mạng LAN của cửa hàng.
3. Có ba chỗ thừa so với nhu cầu SME: ba renderer (Metabase, Evidence, Rill), phân quyền theo 21 ô, và bốn tham số ghi nhận doanh thu cho khách tự chỉnh. Có ba chỗ thiếu: bước đối chiếu số với Sapo khi bàn giao, phân quyền theo độ nhạy của chỉ tiêu (giá vốn, lãi), và kênh đẩy tin tóm tắt hằng ngày.
4. Trang chủ vai trò đang nằm ở phase 6 (cuối). Đó là thứ khách nhìn thấy đầu tiên, nên phải lên cùng đợt với thí điểm.
5. Câu hỏi khó nhất về sản phẩm: một shop chỉ dùng Sapo đã có sẵn báo cáo của Sapo, vậy họ trả tiền cho cái gì? Câu trả lời phải là xu hướng so kỳ, khách quay lại, tồn kho theo tốc độ bán, tin tóm tắt đẩy về điện thoại, và từ gói thứ hai trở đi là số xuyên nguồn (sàn, MISA, quảng cáo).

## (a) Những điểm thiết kế làm đúng

- **Mở khoá theo tập khả năng dữ liệu, không theo bậc.** Khớp thực tế: nhiều shop chạy quảng cáo Facebook mà chưa nhập giá vốn. Hiện "–" kèm "cần dữ liệu X" thay vì số 0 là chi tiết quan trọng nhất cho niềm tin; một số 0 sai sẽ sinh ticket "báo cáo bị lỗi".
- **Catalog gốc bất biến cộng overlay khai báo.** Đây là điều kiện để nâng cấp hàng loạt khách mà không phá tuỳ biến của từng người, đúng mẫu Daasity và Rill derived view.
- **Số tính sẵn trong mart.** Với hỗ trợ từ xa, khi khách hỏi "sao số này khác", mình chỉ cần tra một bảng, không phải đọc ba engine.
- **Gộp ~45 họ báo cáo về 14–18 report chuẩn và tách phần riêng Fine Japan ra overlay.** Bốn biến thể "bán hàng hôm nay" là dấu hiệu sản phẩm chưa có chủ; gộp là đúng.
- **Thí điểm Weekly Pulse chạy song song, so số rồi mới chuyển người dùng.** Đây cũng chính là quy trình bàn giao nên áp cho mọi khách mới (xem mục c).
- **Report sức khoẻ dữ liệu đi kèm mọi bản cài** (đề xuất trong `external-references.md`). Nên nâng lên thành thẻ bắt buộc trên mọi trang chủ, không chỉ là một report.

## (b) Thừa và thiếu so với nhu cầu SME

### Thừa (đề nghị cắt hoặc hoãn)

| Mục | Vì sao thừa | Đề nghị |
|---|---|---|
| Ba renderer (Metabase, Evidence, Rill) cho khách | Mỗi engine thêm một container, một cách đăng nhập, một loại ticket. SME không phân biệt được "trang Evidence" với "dashboard Metabase". Evidence bản legacy đang ở `latest`, bản mới không đọc DuckDB file. | Khách chỉ thấy Metabase. Rill giữ làm công cụ nội bộ của mình khi hỗ trợ (không cần renderer sinh tự động ở v1). Evidence bỏ khỏi sản phẩm (xem §9.2). |
| Phân quyền theo 21 ô (7 chức năng × 3 cấp) | 21 nhóm quyền và collection con là quá nhiều cho shop 5–15 người; người cấu hình là mình, không phải khách, nên mỗi ô là thêm việc hỗ trợ. Cấp quyết định là cách sắp xếp, không phải ranh giới bảo mật. | Giữ ô làm khung xếp catalog và trang chủ. Phân quyền chỉ theo **chức năng** (tối đa 7 collection) cộng một cờ **nhạy cảm** (xem phần thiếu). |
| Bốn tham số ghi nhận doanh thu cho từng khách | Mỗi tổ hợp tham số là một phiên bản số khác nhau mà mình phải hỗ trợ; chủ shop không tự chọn được giữa "trừ hoàn khi yêu cầu" và "khi hoàn tất". | Chỉ phát hành **hai preset**: "Như Sapo" (mặc định) và "Theo kế toán" (giao thành công, khớp MISA). Tham số rời giữ bên trong registry, không mở cho khách. |
| `custom_sql` không giới hạn trong spec v2 | Nếu không có rào, report riêng nào cũng sẽ đi đường này vì nhanh nhất, và mỗi bản là một quả mìn khi nâng cấp mart. | Cho phép, nhưng phải khai báo cột đầu ra, có test hợp đồng cột, và bị tính phí bảo trì (mục d). |

### Thiếu (đề nghị bổ sung vào thiết kế)

1. **Đối chiếu số với hệ thống nguồn lúc bàn giao.** Ticket hỗ trợ số một của mọi sản phẩm BI là "số không khớp Sapo". Cần một report chuẩn "Đối chiếu với Sapo" (đã có mầm: Order Listing Reconciliation #31) và một bước nghiệm thu có chữ ký của chủ shop: doanh thu và số đơn của 3 ngày, 1 tuần, 1 tháng khớp trong ngưỡng đã thoả thuận, phần lệch được giải thích bằng quy tắc ghi nhận.
2. **Phân quyền theo độ nhạy của chỉ tiêu, không theo ô.** Nhu cầu phân quyền thật của chủ SME Việt là "nhân viên không được thấy giá vốn và lãi", không phải "nhân viên marketing không được thấy giao vận". Registry cần cờ `sensitivity: cost_profit` trên chỉ tiêu; renderer không đưa thẻ/cột nhạy cảm vào report thuộc collection của nhóm không có quyền. Nếu chỉ phân quyền theo ô, report "Bán hàng theo kênh × sản phẩm" có cột biên lợi nhuận (khi có T2) sẽ làm lộ lãi cho cả nhóm bán hàng.
3. **Kênh đẩy tin tóm tắt hằng ngày (Zalo OA / Telegram / Lark / email).** Chủ shop nhỏ không mở BI; họ đọc tin nhắn. Metabase cài trong LAN của cửa hàng nên ngoài giờ hoặc trên điện thoại họ thường không vào được (trừ khi mở Tailscale cho cả chủ shop, thêm một việc hỗ trợ). `kpi_tiles` trong catalog đã đủ để sinh một tin nhắn văn bản: đây là một "renderer" rẻ nhất và giá trị cao nhất. Roadmap đang để notifier nhiều backend ở Đợt 8; tôi đề nghị đưa tin tóm tắt cuối ngày/đầu tuần lên cùng đợt report.
4. **Dữ liệu nhập tay có giao diện.** Mục tiêu doanh thu (`dim_channel_targets`), giá vốn nhập tay, chi phí cố định hằng tháng đang là "tham số trong tenant profile". Chủ shop không sửa YAML. Cần một đường nhập (Google Sheet theo mẫu hoặc một trang form) và ghi rõ ai cập nhật hằng tháng.
5. **Khu tự làm của khách trong Metabase.** Khách 20–50 người thường có một người biết Excel sẽ tự tạo question trong Metabase. Thiết kế chưa nói deployer đối xử thế nào với các question đó. Cần một collection "Tự làm" mà deployer không bao giờ chạm vào, và quy ước rõ: mình không bảo hành số ở đó.
6. **Nơi lưu overlay và report riêng phía mình.** Tenant profile "nằm ngoài image" trên máy khách. Nếu ổ khách hỏng hoặc khách đổi máy, mất toàn bộ report riêng. Cần một repo cấu hình riêng tư phía mình (mỗi khách một thư mục, không chứa dữ liệu, không chứa khoá) làm nguồn sự thật và để chạy kiểm tra trước nâng cấp.
7. **Chú giải thuật ngữ hiển thị trong report.** "Doanh số" và "Doanh thu" khác nhau ở Pancake; "lợi nhuận" mỗi hãng một nghĩa. Mỗi report cần chân trang một dòng: trục thời gian đang dùng, quy tắc ghi nhận, nguồn dữ liệu, giờ cập nhật cuối.

## (c) Ngày đầu tiên của một shop chỉ dùng Sapo

### Khả năng dữ liệu có ngay

Sapo cung cấp đơn, dòng hàng, khách, sản phẩm, nhân viên, chi nhánh, tồn kho, vận đơn và **giá vốn bình quân** (roadmap đã liệt kê là một nguồn giá vốn). Nghĩa là shop Sapo-only mở được cả lãi gộp ước tính ngay ngày đầu, nếu ghi rõ "theo giá vốn Sapo, phủ X% dòng hàng".

### Bảy report cài sẵn (cộng hai report hạ tầng)

| # | Report | Ô | Vì sao có mặt ngày đầu |
|---|---|---|---|
| 1 | Hôm nay của shop (R01) | Điều hành / ngày | Câu hỏi chủ shop hỏi nhiều nhất: hôm nay bán bao nhiêu, đơn nào đang chờ xử lý. |
| 2 | Nhịp tuần (R02) | Điều hành / tuần | So tuần trước và cùng kỳ năm trước: thứ Sapo admin không cho thấy gọn. Thiếu mục tiêu thì hiện "chưa đặt mục tiêu", không ẩn report. |
| 3 | Bán hàng theo kênh × sản phẩm (R04) | Bán hàng / tuần | Bán gì, ở kênh nào; nhóm theo kênh chuẩn `*_std`. |
| 4 | Nhân viên và chi nhánh (R05) | Bán hàng / ngày–tuần | Nhân viên là chiều hạng nhất ở thị trường Việt (Nhanh, Pancake, KiotViet đều có). Shop một người thì ẩn tự động. |
| 5 | Khách mới, khách quay lại (R07, bản gọn) | Khách hàng / tháng | Thứ Sapo không trả lời tốt và là cửa vào cho gói CRM/HUG sau này. |
| 6 | Tồn kho và tốc độ bán (R08) | Hàng hoá / tuần | Hàng sắp hết, hàng tồn lâu tính theo tốc độ bán, không chỉ số tồn. |
| 7 | Lãi gộp theo sản phẩm, ước tính (R12 bản Sapo) | Tài chính / tháng | Câu hỏi "bán cái gì có lãi" là lý do chủ shop trả tiền; gắn cờ nhạy cảm, chỉ chủ shop thấy. |
| H1 | Sức khoẻ dữ liệu | Hạ tầng | Lần cập nhật cuối, nguồn lỗi, nhãn chưa ánh xạ (`UNMAPPED`). |
| H2 | Đối chiếu với Sapo | Hạ tầng | Dùng khi nghiệm thu và khi khách hỏi "số sai". |

Giao vận và huỷ/hoàn (R09) nên là report thứ tám nếu shop giao COD nhiều; tôi không đưa vào bảy vì thời gian xử lý từ dữ liệu vận đơn Sapo cần xác minh độ đầy đủ trước khi hứa.

### Trang chủ "Chủ shop" (một màn, xem được trên điện thoại)

- Hàng thẻ 1 (hôm nay so cùng giờ hôm qua): Doanh thu thuần, Số đơn, Giá trị đơn trung bình, Đơn chờ xử lý, Đơn huỷ/hoàn.
- Hàng thẻ 2 (7 ngày so 7 ngày trước): Doanh thu thuần, Khách mới, Tỉ lệ khách quay lại, Lãi gộp ước tính (chỉ chủ shop).
- Hai danh sách ngắn: 5 sản phẩm sắp hết hàng theo tốc độ bán; 5 sản phẩm bán chạy nhất tuần.
- Dải trạng thái trên cùng: "Dữ liệu cập nhật lúc HH:MM, nguồn Sapo bình thường" hoặc cảnh báo đỏ.
- Mỗi thẻ bấm vào mở report tương ứng (trang chủ là bệ phóng, đúng mẫu Daasity).
- Cùng bộ thẻ này gửi qua tin nhắn lúc 21:00 hằng ngày và 08:00 thứ Hai.

### Mục tiêu thời gian tới giá trị

| Mốc | Nội dung | Mục tiêu |
|---|---|---|
| T+0 | Cài, nhập token Sapo, chạy `doctor` | Trong một buổi hỗ trợ từ xa (≤ 2 giờ) |
| T+1 ngày | Nạp lịch sử 12–24 tháng, trang chủ có số, tin nhắn đầu tiên | Tự động, không thao tác tay |
| T+3 ngày | Ánh xạ nhãn kênh/nguồn đơn sang mã chuẩn, xem trước tác động | Một cuộc gọi 30 phút với chủ shop |
| T+7 ngày | Nghiệm thu đối chiếu với Sapo, gán người vào persona | Biên bản nghiệm thu ký |

Thước đo thành công nên đo được: tỉ lệ khách mở trang chủ hoặc đọc tin nhắn ít nhất 4/7 ngày trong tháng đầu; số ticket "số không khớp" trong 30 ngày đầu ≤ 1 mỗi khách.

## (d) Luồng report riêng từ đầu đến cuối

### Ai hỏi, phân loại ở đâu

Yêu cầu đến từ chủ shop hoặc trưởng bộ phận, qua Zalo/nhóm hỗ trợ. Người tiếp nhận (customer success) phân vào một trong bốn loại trước khi ai viết gì:

| Loại | Ví dụ | Ai làm | Chi phí cho khách |
|---|---|---|---|
| L0 Đã có | "Muốn xem doanh thu theo nhân viên" khi R05 đã cài | CS chỉ đường, gán persona | Miễn phí |
| L1 Cấu hình overlay | Đổi nhãn, ẩn report, đổi ngưỡng, sắp lại trang chủ, thêm mục tiêu | CS sửa overlay, deployer `--dry-run` rồi cài | Miễn phí trong gói (giới hạn số lần/tháng) |
| L2 Report riêng trên chỉ tiêu chuẩn | Dashboard riêng cho trưởng kho ghép chỉ tiêu sẵn có theo chiều chuẩn | Agent (skill `analytics-design`) soạn spec v2, analyst của mình duyệt | Giá cố định theo report (đề xuất tương đương 0,5 ngày công) |
| L3 Cần chỉ tiêu mới hoặc `custom_sql` | Hoa hồng theo luật riêng của shop, đối soát với file ngân hàng | Analyst của mình viết, có test hợp đồng cột | Báo giá theo việc + phí bảo trì hằng năm |

Khách **không** tự sửa YAML. Khách tự làm được trong collection "Tự làm" của Metabase, không bảo hành.

### Các bước cho L2/L3

1. CS ghi yêu cầu thành câu hỏi nghiệp vụ, người dùng, nhịp xem, quyết định sẽ đưa ra (đúng Phase 0 của `analytics-design`).
2. Agent đọc tenant profile, registry và schema mart (chỉ cấu trúc, không lấy dữ liệu ra khỏi máy khách), soạn spec v2. Nếu agent cần chạy thử số, chạy trên máy khách qua kết nối hỗ trợ.
3. Analyst duyệt: chỉ dùng chỉ tiêu có sẵn khi có thể; chỉ tiêu mới phải có id tiền tố tenant; không nhóm theo nhãn riêng ngoài drill-down; cờ nhạy cảm được đặt đúng.
4. Deployer `--dry-run` lên collection nháp; khách xem thử và xác nhận số (so ít nhất một con số với nguồn họ tin).
5. Cài chính thức; spec lưu vào repo cấu hình phía mình; ghi vào sổ report riêng của khách (người yêu cầu, ngày, loại, chỉ tiêu dùng).

### Bảo trì khi nâng cấp

- Trước mỗi bản nâng cấp catalog/registry/mart, chạy kiểm tra toàn bộ overlay của mọi khách trong repo cấu hình: spec có biên dịch được không, chỉ tiêu còn tồn tại không, cột `custom_sql` còn đúng không. Khách nào hỏng thì sửa trước rồi mới nâng cấp khách đó.
- L1 và L2: mình chịu trách nhiệm giữ chạy qua mọi bản nâng cấp, trong phí gói.
- L3: giữ chạy trong thời hạn phí bảo trì; hết hạn thì report được đánh dấu "không bảo hành" chứ không xoá.
- Khu "Tự làm": không kiểm tra, không bảo hành; ghi chú trong release note khi đổi tên bảng/cột public.
- Report riêng không ai mở trong 90 ngày: hỏi khách rồi lưu trữ, để giảm số thứ phải giữ khi nâng cấp.

### Luật "đưa lên chuẩn" (promote)

Một report riêng được đưa lên catalog chuẩn khi đạt **tất cả** các điều kiện sau:

1. Ít nhất 3 khách độc lập yêu cầu cùng câu hỏi nghiệp vụ (không cần cùng giao diện), ghi nhận trong sổ report riêng.
2. Chỉ dùng chỉ tiêu chuẩn và chiều chuẩn `*_std`; chỉ tiêu tiền tố tenant phải được tổng quát hoá thành chỉ tiêu chuẩn trước, không còn nhãn riêng của khách.
3. Không có `custom_sql`, hoặc phần SQL đó đã chuyển xuống mart dbt.
4. Gán được vào một ô và có khai báo `requires`/`enhances`; chạy được với khách chỉ có tập khả năng tối thiểu ghi trong `requires`.
5. Qua golden query trên dữ liệu của ít nhất 2 khách.
6. Product owner duyệt theo đợt (đề xuất mỗi quý), để catalog không phình quá ~25 report.

Sau khi promote: bản riêng của các khách cũ được thay bằng report chuẩn cộng overlay (đổi nhãn/ngưỡng nếu cần), bản riêng được lưu trữ. Ngược lại, report chuẩn không ai mở ở phần lớn khách sau hai quý thì đưa xuống "tuỳ chọn" (không cài mặc định).

## (e) Persona mẫu theo cỡ doanh nghiệp

Ký hiệu ô: chức năng ĐH (Điều hành), BH (Bán hàng), MKT, TC (Tài chính), HH (Hàng hoá và tồn kho), GV (Giao vận), KH (Khách hàng); cấp C (chiến lược/tháng), Q (quản lý/tuần), T (tác nghiệp/ngày). "Nhạy cảm" là quyền xem giá vốn và lãi.

| Cỡ | Persona | Ô được gán | Nhạy cảm |
|---|---|---|---|
| Cá nhân (1–3 người) | Chủ shop | Tất cả ô có report đã cài; trang chủ "Chủ shop" | Có |
| Cá nhân | Người bán phụ (tuỳ chọn) | BH-T, GV-T | Không |
| Nhỏ (4–15) | Chủ shop | Tất cả | Có |
| Nhỏ | Quản lý cửa hàng / bán hàng | BH-T, BH-Q, KH-T, HH-T, GV-T | Không |
| Nhỏ | Kế toán | TC-C, TC-Q, TC-T, BH-C | Có |
| Nhỏ | Kho | HH-T, HH-Q, GV-T | Không |
| Vừa (15–50) | Giám đốc | ĐH-C, ĐH-Q, ĐH-T, cấp C của mọi chức năng | Có |
| Vừa | Trưởng kinh doanh | BH-C, BH-Q, BH-T, KH-Q, KH-T | Tuỳ chủ quyết định |
| Vừa | Marketing | MKT-C, MKT-Q, MKT-T, KH-C, KH-Q, BH-Q | Không (trừ khi có quảng cáo và cần CM3) |
| Vừa | Kế toán trưởng | TC-C, TC-Q, TC-T, BH-C, HH-C | Có |
| Vừa | Trưởng kho / vận hành | HH-Q, HH-T, GV-Q, GV-T | Không |
| Vừa | Chăm sóc khách hàng | KH-T, GV-T | Không |

Nguyên tắc: persona là mẫu để chọn nhanh lúc cài, không phải ràng buộc; một người được gán nhiều persona. Mỗi persona mẫu có trang chủ riêng ghép từ thẻ KPI của các report trong ô của nó. Ở cỡ cá nhân không tạo nhóm quyền nào: một tài khoản chủ shop là đủ.

## (f) Trả lời năm quyết định ở §9

1. **Ghi nhận doanh thu mặc định.** Mặc định phải là "giống Sapo", vì chủ shop sẽ so ngay với Sapo admin. Cụ thể: ghi nhận theo **ngày tạo đơn**, loại đơn huỷ (khớp quy ước `is_active_order` đang dùng trong `semantic/rules.md`); **trừ hoàn vào ngày hoàn tất trả hàng**, không sửa lại kỳ cũ (khớp quy tắc "Returns Not Restated" đang có); **sàn trợ giá là dòng riêng**, không cộng vào doanh thu thuần, nhưng cộng vào "thực nhận" trong report kinh tế sàn; **AOV = (doanh thu trước giảm giá − giảm giá) / số đơn không huỷ**, không trừ hoàn, để AOV của những ngày gần đây không tự đổi khi hàng hoàn về muộn (giống Shopify và Pancake; khác đề xuất `net_revenue/orders` trong `external-references.md`). Bổ sung một điểm chưa có trong §9: **VAT**. Fine Japan đang tách VAT; phần lớn hộ kinh doanh nhỏ xem giá đã gồm VAT như Sapo hiển thị. Mặc định nên là "như Sapo hiển thị", tách VAT nằm trong preset "Theo kế toán". Ghi rõ quy tắc ở chân trang mỗi report. Trước khi chốt, cần xác minh trên một shop Sapo thật rằng preset "Như Sapo" khớp báo cáo bán hàng của Sapo trong ngưỡng chấp nhận.
2. **Evidence.** Bỏ khỏi sản phẩm cho khách; chuyển 4 trang hiện có sang Metabase theo lịch, ghim phiên bản Evidence ngay cho Fine Japan trong lúc chuyển. Lý do sản phẩm: một engine hiển thị là một kiểu đăng nhập, một kiểu ticket, một thứ phải đào tạo. Hệ quả cần sửa ở roadmap Đợt 5: profile "lite = data-platform + Evidence" phải đổi thành "lite = data-platform + Metabase bản nhẹ" hoặc "lite = data-platform + tin nhắn tóm tắt, không có BI". Tôi nghiêng về phương án thứ hai cho người bán một mình nếu phần cứng của họ yếu.
3. **Catalog và registry.** Thành module code có schema kiểm tra, không nằm trong `docs/`. Lý do sản phẩm: overlay của từng khách phải được kiểm tra tự động trước mỗi lần nâng cấp; tài liệu văn xuôi không làm được việc đó. Tài liệu trong `docs/analytics-handbook/` sinh ra từ registry.
4. **Phân quyền theo dòng ở v1.** Không. Nhu cầu thật ở v1 là ẩn giá vốn/lãi (theo chỉ tiêu, giải bằng cờ nhạy cảm), không phải theo dòng. Nhu cầu theo chi nhánh chỉ xuất hiện ở chuỗi nhiều cửa hàng; ghi nhận khách nào hỏi, khi đủ ba khách thì làm bằng view theo nhóm. Trong lúc đó, bán hàng phải nói rõ với khách chuỗi rằng trưởng chi nhánh sẽ thấy số của mọi chi nhánh.
5. **Persona mẫu.** Bảy persona: Chủ shop, Giám đốc, Trưởng kinh doanh/quản lý cửa hàng, Marketing, Kế toán, Kho/vận hành, Chăm sóc khách hàng; đóng thành ba bộ theo cỡ như mục (e). "Trưởng kho" trong ví dụ §9 nên đổi thành "Kho/vận hành" vì ở shop nhỏ một người làm cả kho lẫn giao hàng. Persona "Trưởng nhóm sales" (LEAD trong tài liệu tham khảo) gộp vào Trưởng kinh doanh để không có hai mẫu gần trùng.

## Ba phương án tổng thể và phương án tối giản

| Tiêu chí | A. Xưởng đầy đủ như bản nháp | B. Xưởng một engine + tin nhắn (đề xuất) | C. Chỉ sửa blueprint hiện có |
|---|---|---|---|
| Nội dung | Registry, catalog, spec v2, 3 renderer, 21 nhóm quyền | Registry, catalog, spec v2, renderer Metabase, renderer tin nhắn từ `kpi_tiles`, quyền theo chức năng + cờ nhạy cảm | Bỏ ghi cứng `field_id`, deployer idempotent, giữ SQL viết tay trong blueprint |
| Công sức ước tính | Cao nhất (thêm 2 renderer và bộ test số giữa engine) | Trung bình | Thấp |
| Hỗ trợ khách | Ba loại ticket theo engine | Một loại | Một loại, nhưng sửa định nghĩa phải sửa từng blueprint |
| Nâng cấp hàng loạt | Tốt | Tốt | Kém: mỗi định nghĩa sửa ở nhiều chỗ, report riêng không kiểm tra được |
| Hệ quả bậc hai | Đội nhỏ bị kéo vào bảo trì generator thay vì làm connector Haravan/Shopee | Rill/Evidence của FJ cần lịch chuyển; notifier sớm hơn Đợt 8 | Ba nguồn định nghĩa tiếp tục lệch nhau; khách thứ ba trở đi sẽ đắt dần |

Phương án tối giản vẫn đáp ứng đủ mục tiêu "cài được cho bất kỳ khách nào và tạo được report riêng bằng cùng công cụ" là **B**. C rẻ hơn nhưng không đạt mục tiêu thứ hai một cách bảo trì được. Thứ tự đề nghị sửa lộ trình §8: đưa trang chủ "Chủ shop" và tin nhắn tóm tắt vào cùng phase thí điểm (phase 4), làm quyền theo chức năng + cờ nhạy cảm ở phase 5, bỏ phase 7 khỏi phạm vi sản phẩm.

## Gói giá ngụ ý

Bán theo tập khả năng, không theo số report: **Cơ bản** (POS/Sapo: 7 report ngày đầu, trang chủ, tin nhắn); **Đa kênh** (+ sàn: kinh tế sàn, đối soát tiền về); **Lợi nhuận** (+ pack finance, MISA hoặc giá vốn nhập tay: lãi theo SKU/đơn/kênh, P&L); **Tăng trưởng** (+ quảng cáo, CRM/HUG: hiệu quả quảng cáo, RFM và hàng đợi chăm sóc). Report riêng L2/L3 bán như dịch vụ kèm phí bảo trì. Rủi ro định giá: khách mua gói Lợi nhuận nhưng chưa có giá vốn thì report hiện "–"; hợp đồng phải ghi rõ khách chịu trách nhiệm dữ liệu đầu vào nào.

## (g) Rủi ro hàng đầu

1. **Số không khớp Sapo làm mất niềm tin ngay tuần đầu.** Giảm bằng preset "Như Sapo", report đối chiếu, nghiệm thu có ký.
2. **Giá trị mỏng với shop chỉ dùng Sapo** vì Sapo đã có báo cáo (cả báo cáo lợi nhuận từ 07/2026). Giảm bằng so kỳ, khách quay lại, tồn theo tốc độ bán, tin nhắn đẩy; không định vị sản phẩm bằng "có template theo vai trò" vì Haravan đã có.
3. **Chủ shop không truy cập được BI on-prem từ điện thoại.** Giảm bằng tin nhắn tóm tắt; quyết định rõ có mở truy cập từ xa cho người dùng cuối hay không (khác với truy cập hỗ trợ).
4. **Lộ giá vốn và lãi cho nhân viên** nếu chỉ phân quyền theo ô. Giảm bằng cờ nhạy cảm trên chỉ tiêu.
5. **Report riêng phình và chặn nâng cấp.** Giảm bằng phân loại L0–L3, phí bảo trì L3, kiểm tra overlay toàn khách trước nâng cấp, lưu trữ report không dùng.
6. **Catalog mang khuôn Fine Japan** (công ty 50 người, B2B, US, MISA). Cần thử catalog trên ít nhất một shop nhỏ thứ hai trước khi chốt; đây cũng là chặn đã ghi ở Đợt 4 (cần doanh nghiệp thứ hai).
7. **Gánh nặng hỗ trợ của nhiều engine và nhiều tham số.** Giảm bằng một engine hiển thị và hai preset.
8. **Agent soạn report sai số mà trông đúng.** Giảm bằng bước analyst duyệt bắt buộc và bước khách xác nhận một con số với nguồn.

Status: DONE_WITH_CONCERNS
Summary: Giữ lõi registry + catalog mở khoá theo khả năng + overlay + deployer; đề nghị một engine hiển thị (Metabase) cộng tin nhắn tóm tắt sinh từ `kpi_tiles`, phân quyền theo chức năng và cờ nhạy cảm giá vốn/lãi thay vì 21 ô, hai preset doanh thu ("Như Sapo" mặc định), bước nghiệm thu đối chiếu với Sapo, quy trình report riêng L0–L3 có luật promote và phí bảo trì.
Concerns: (1) Preset "Như Sapo" chưa được kiểm trên dữ liệu Sapo thật; định nghĩa AOV tôi đề xuất trái với `external-references.md` và cần user chốt. (2) Đề xuất tin nhắn tóm tắt và bỏ Evidence làm thay đổi roadmap Đợt 5 (profile lite) và Đợt 8 (notifier), cần user duyệt. (3) Độ đầy đủ dữ liệu vận đơn và giá vốn bình quân của Sapo cho shop nhỏ chưa xác minh. (4) Toàn bộ danh sách report và persona vẫn là suy luận, chưa phỏng vấn chủ shop nào ngoài Fine Japan.
