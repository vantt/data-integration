---
title: "Rà soát thiết kế taxonomy engine — góc nhìn vận hành và red team"
reviewer: delivery & operations lead / red team
date: 2026-10-14
target: taxonomy-engine-design.md (§6, §7, §8), plan.md, roadmap.md, phase-04/06/07, standards-and-patterns.md §8.5
---

# Rà soát rủi ro vận hành: taxonomy engine

## Tóm tắt một đoạn

Mô hình nhãn riêng + mã chuẩn là đúng hướng, nhưng **cách đưa nó vào plan đang chạy là sai chỗ**. Lý do chính để chèn engine trước phase 6 ("phase 6 tách phần riêng của Fine Japan, mà phần đó phần lớn là luật") không khớp với phạm vi thật của phase 6: phase 6 dời HUG, US shipment, CRM, cashflow budget, overhead, seed FJ và URL cấu hình, không dời khối `CASE` phân loại nào. Chèn engine vào giữa Đợt 1 sẽ biến một plan "không đổi số" thành plan có thay đổi hợp đồng public, kéo dài vòng đời shadow lake chứa PII và để prod ở trạng thái nửa module hoá. Đề xuất của tôi: đóng Đợt 1 trước (phase 4 rút gọn → 6 → 7), rồi làm engine thành plan riêng với thí điểm `customer_type` chạy **song song tối (dark launch) trên prod** trước khi đổi cột mart, có tiêu chí huỷ rõ ràng.

## (a) Rủi ro thứ tự

### a1. Tiền đề "làm hai lần" không đứng vững

`phase-06-fine-japan-tenant-overlay.md` liệt kê phạm vi dbt gồm HUG, US shipment, CRM, cashflow budget, overhead và seed `seed_*` của FJ, cộng URL/domain cứng trong orchestration. Không có dòng nào nói dời luật phân loại. Thứ duy nhất phase 6 chạm tới taxonomy là **tenant hook** của `dim_customers` (CROSSBORDER đọc đơn US), và hook đó chỉ là một dòng trong `boundary_allowlist.yaml`. Nếu engine đến sau, việc phải làm lại chỉ là xoá một dòng allowlist. Như vậy chi phí "làm hai lần" gần bằng không, trong khi chi phí chèn engine là vài tuần.

Điểm 4 của phase 4 ("đánh dấu giá trị tenant làm đầu vào cho phase 6") cũng chỉ là ghi chú; phase 6 hiện không tiêu thụ nó. Nên sửa câu đó để không ai hiểu nhầm rằng phase 6 phụ thuộc vào engine.

### a2. Chèn engine làm Đợt 1 mất tính chất "không đổi số"

Toàn bộ an toàn của Đợt 1 dựa trên bất biến "không đổi một con số, không đổi tên bảng public" và gate trả PASS khi 0 khác biệt. Engine MVP theo §3.7 **thêm cột** `customer_type_std` vào `dim_customers` và thêm model `lbl_*`, `entity_labels`. Gate S hiện chỉ PASS khi 83 bảng giống hệt; thêm cột nghĩa là phải chạy chế độ `--allow-new` và đọc khác biệt bằng mắt, tức là đổi kiểu gate giữa chừng một plan đã cam kết "PASS hoặc không deploy". Đây là thay đổi bản chất của acceptance criteria trong `plan.md`, không phải thêm một phase.

### a3. Prod ở trạng thái nửa vời lâu hơn

Hiện tại phase 0–3 đã lên prod, phase 5 đã có trên `main` (`b718befc`), phase 4 hoãn, 6–7 chưa làm. Trạng thái này chấp nhận được trong vài ngày, nhưng nếu kéo dài theo engine thì:

- `docs/architecture/modules.md`, `check_boundaries.py` và allowlist mô tả một kiến trúc chưa hoàn tất; mọi thay đổi nóng của analyst trên `main` (sửa `dim_customers`, thêm seed) phải đoán đang theo quy ước cũ hay mới.
- Seed vẫn ở thư mục phẳng, trong khi `seed_paths.py` chưa có; rủi ro Critical #5 trong red-team (job 02:30 ghi lại seed vào đường dẫn cũ) vẫn treo cho tới khi phase 4 làm xong.
- Shadow lake (`/home/vantt/app/fg-dw-shadow`) chứa PII khách hàng sống lâu hơn; red-team #13 và phase 7 đều yêu cầu xoá khi đóng plan. Mỗi tuần kéo dài là thêm một tuần bản sao PII tồn tại.
- Baseline của gate phải là "commit được chấp nhận gần nhất" (harness §9.2); plan càng dài càng nhiều lần phải dựng lại baseline, và đã có một lần gate fail giả vì baseline cũ (báo cáo phase 5).

### a4. Xung đột merge và xung đột bố cục

- Engine đặt seed luật "trong thư mục tenant" (§4), nhưng thư mục `seeds/tenants/fine_japan/` do phase 6 tạo. Chèn engine trước phase 6 là tạo phụ thuộc vòng: engine cần chỗ của tenant, tenant overlay lại chờ engine.
- Thí điểm `customer_type` sửa `dim_customers.sql`, `fact_orders.sql`, `int_customer_benchmarks.sql`; đây là các file analyst sửa thường xuyên nhất trên `main` (sửa ngày 05/06 về `customer_type` là ví dụ). Nhánh engine sống lâu sẽ va chạm với các hotfix này.
- Phase 4 rút gọn và engine cùng đụng `seeds/taxonomy/` và `dbt_project.yml` khối `seeds:`; làm tuần tự (phase 4 deploy xong rồi mới mở nhánh engine) thì không có xung đột.

### a5. Đề xuất thứ tự

1. Phase 4 rút gọn (đặc tả `TAXONOMY.md` + dời seed + `seed_paths.py`), gate S, deploy. Khoảng 2 ngày.
2. Phase 6, gate M, deploy. Phase 7, đóng Đợt 1, xoá shadow.
3. Engine là **plan riêng** (không cần đợi Đợt 3 như roadmap vẽ, vì engine không phụ thuộc dbt package hay contract), mở ngay sau khi Đợt 1 đóng, với gate kiểu "S đọc khác biệt" và dark launch trên prod.

Nếu user vẫn muốn bắt đầu engine sớm, cho phép **thiết kế và spike trên shadow song song** với phase 6–7 (khác thư mục, không deploy), nhưng không nối vào mart trước khi Đợt 1 đóng.

## (b) Rủi ro chuyển cột mart sang đầu ra engine

### b1. 0 khác biệt trên một ngày dữ liệu không chứng minh tương đương

Gate so 83 bảng trên **một** snapshot lake. Luật `CASE` và luật dữ liệu có thể cho cùng kết quả trên tập giá trị hôm nay nhưng khác nhau trên giá trị chưa xuất hiện. Các chỗ dễ lệch âm thầm:

- **Chuẩn hoá chuỗi ở tầng đặc trưng** (§3.1: chữ thường, bỏ dấu, gộp khoảng trắng). SQL hiện tại dùng `LIKE`/`=` phân biệt hoa thường ở nhiều chỗ (chính `'Active'`/`'ACTIVE'` là bằng chứng). Nếu đặc trưng chuẩn hoá còn luật cũ thì không, một nhóm khách mới tên "dai ly" sẽ được phân loại khác giữa hai đường. Quy tắc chuẩn hoá phải được áp **sau** khi chứng minh 0 khác biệt, như một thay đổi có đổi số riêng.
- **NULL**: `CASE WHEN x LIKE ...` với `x` NULL rơi xuống `ELSE`; engine trả `UNKNOWN` theo §3.3. Nếu mart đang hiện `RETAIL` cho khách thiếu nhóm, cột giữ tên sẽ đổi giá trị.
- **Thứ tự khớp**: `CASE` là FIRST theo thứ tự viết; engine dùng `priority`. Hai luật cùng priority sẽ có thứ tự không xác định trên DuckDB. Validator phải cấm trùng priority trong một domain FIRST.

Biện pháp: ngoài gate trên shadow, chạy **dark launch trên prod**: model `lbl_customer_type` chạy hằng đêm nhưng không nối vào mart, cộng một asset check so với cột hiện tại và cảnh báo khi khác biệt > 0. Chỉ đổi cột sau N đêm liên tiếp 0 khác biệt (xem mục e). Dark launch bắt được giá trị mới xuất hiện trong dữ liệu hằng ngày, thứ mà gate một-snapshot không thấy.

### b2. Restate đụng model incremental: mâu thuẫn có sẵn trong repo

`int_customer_entry_attributes.sql` là model incremental, lọc `WHERE customer_type = 'RETAIL'` và ghi rõ "chỉ xử lý khách chưa có trong bảng, giá trị không bao giờ đổi". Nghĩa là **hôm nay đã không restate**: khách đổi từ WHOLESALE sang RETAIL sau lần chạy đầu sẽ không bao giờ vào bảng, và khách đổi ngược lại vẫn nằm trong cohort (`mart_cohort_retention`). `dim_customers_base` cũng incremental. Khi luật thành dữ liệu và được sửa thường xuyên hơn, các bảng incremental sẽ chứa hỗn hợp nhãn của nhiều phiên bản luật mà không ai biết. Thiết kế phải chọn một trong hai: (1) model incremental không lưu nhãn của domain restate (chỉ lưu khoá, join nhãn lúc đọc), hoặc (2) khi `ruleset_version` của domain đổi thì job tự `--full-refresh` các model incremental phụ thuộc domain đó. Tôi chọn (1), vì (2) kéo full-refresh vào nightly và làm dài khung 02:30–04:00. Lưu ý (1) tự nó là thay đổi có đổi số cho `mart_cohort_retention`, phải duyệt riêng.

### b3. Restate làm số lịch sử đổi khi sửa luật

Restate là đúng hành vi hiện nay với các seed ánh xạ (`ref_order_sources` join lại cho mọi kỳ), nên không phải ngữ nghĩa mới. Cái mới là **tần suất và người sửa**: hôm nay sửa seed qua commit và gate; sau này có thể sửa trên Google Sheet. Rủi ro cụ thể: báo cáo theo team và mục tiêu (`scope_retail` → doanh thu bán lẻ theo team so với `seed_channel_targets`) là số đã báo cáo hằng tháng; sửa luật `customer_type` sẽ đổi tỉ lệ đạt mục tiêu của các tháng đã chốt thưởng. Cần hỏi nghiệp vụ trước: có báo cáo nào đã dùng để trả thưởng hoặc gửi ra ngoài không. Nếu có, `freeze_after_close` không chỉ dành cho kế toán.

### b4. Lỗi nhập luật làm gãy nightly

Nếu luật là seed và có test dbt mức `error` (nằm trong bộ mã chuẩn, `UNIQUE` không trùng), một dòng luật sai sẽ làm đỏ nightly toàn hệ thống, không chỉ một domain. Theo quy tắc đóng băng của `plan.md`, nightly đỏ còn chặn mọi deploy khác. Thiết kế cần:

- Validator chạy **trước** khi nạp (kiểu, toán tử, nhãn đã khai báo, đặc trưng tồn tại, `rule_id` không trùng, priority không trùng), như §8.5 mục 2 đã nêu; validator fail thì **giữ bộ luật hợp lệ gần nhất** (last-known-good), gửi cảnh báo Lark, nightly vẫn chạy.
- Test của domain ở mức `warn` cho độ phủ (`UNMAPPED`); chỉ để `error` cho tính hàm "nhãn → mã chuẩn" và "một dòng mỗi đối tượng" với domain `single`.
- `lbl_<domain>` cô lập: lỗi một domain không chặn các asset không phụ thuộc nó (selection Dagster theo domain).

### b5. Google Sheet là đường vào prod không qua gate

Harness §10 ghi rõ: shadow không đọc Google Sheet, và seed do job prod ghi lại sau deploy là điểm mù đã biết (runbook phải commit seed đang sống trước khi merge). Luật nhập từ Sheet sẽ thay đổi số liệu prod **mà không đi qua runbook**, không có shadow gate, không có rollback bằng commit. Đây là thay đổi lớn nhất về mô hình vận hành, lớn hơn bản thân engine. Nếu làm, cần: nạp Sheet vào bảng có phiên bản (mỗi lần nạp là một `ruleset_version` lưu lại), báo cáo tác động tự động (số khách/đơn/doanh thu đổi nhãn) trước khi kích hoạt, và lệnh quay về phiên bản trước không cần deploy. Ngoài ra luật không nên được ghi thành CSV trong checkout prod như seed hiện nay, để không làm bẩn cây làm việc mà runbook deploy phải dọn.

### b6. Thêm cột vào bảng public

Thêm `*_std` vào `dim_customers`/`fact_orders` là thay đổi hợp đồng public dù không đổi số. Phải kiểm: serving view nào chọn cột tường minh, Rill có đọc schema cố định không, CRM adapter DuckDB đọc cột nào (phase 6 đã yêu cầu đọc `crm/src/adapters/outbound/duckdb/` thay vì đoán). Cột chuẩn chưa được kiểm bằng dữ liệu doanh nghiệp thứ hai (§5 tự thừa nhận) thì chưa nên lên bảng public; xem quyết định 1.

## (c) Quản trị và gánh nặng hỗ trợ khi có nhiều khách cài on-prem

1. **Nâng cấp gói mặc định làm đổi số của khách mà khách không sửa gì.** Lớp mặc định sản phẩm và gói connector đi theo image; khách nâng image là luật đổi, số lịch sử đổi (vì restate). Bắt buộc: mỗi tenant **ghim phiên bản** gói luật (`rulepack_version` trong `tenant.yaml`), và lệnh `upgrade` của CLI Đợt 5 chạy chế độ xem trước tác động, chỉ nâng gói luật khi khách đồng ý. Nâng image và nâng gói luật phải là hai bước tách rời.
2. **Mã chuẩn bất biến là cam kết vĩnh viễn.** Sai một mã ở bản đầu (ví dụ CROSSBORDER neo vào OTHER rồi sau thêm mã riêng) thì mọi khách đã neo phải được di trú qua `replaced_by`. Cần một script di trú nhãn riêng đi kèm mỗi lần đổi canonical, và changelog theo CalVer như Shopify.
3. **Không có tầm nhìn tại chỗ khách.** Heartbeat là Đợt 8 và chỉ khi khách đồng ý. Như vậy mình không biết tỉ lệ `UNMAPPED` ở khách nào đang tăng. Heartbeat nên mang các con số tổng hợp không nhạy cảm: % `UNMAPPED` theo domain, `ruleset_version`, số lần validator fail.
4. **Ai chịu trách nhiệm khi số sai.** Khi khách tự sửa luật, ticket "doanh thu bán lẻ tháng trước tự nhiên giảm" sẽ đến bộ phận hỗ trợ. Cần nhật ký thay đổi luật (ai, khi nào, phiên bản trước/sau, tác động) nằm sẵn trong lake để hỗ trợ trả lời trong vài phút, không phải truy lịch sử commit qua TeamViewer.
5. **Không xây khung quản trị cho N khách lúc này.** Chỉ có một tenant. Những thứ rẻ bây giờ và đắt nếu làm sau là: mã bất biến + `introduced_in/deprecated_in`, `ruleset_version` trong đầu ra, tách lớp sản phẩm và lớp tenant thành hai nguồn dữ liệu riêng. Ghim phiên bản, CLI upgrade, heartbeat để tới Đợt 5 và 8.

## (d) Trả lời 6 quyết định ở §8

**1. Mô hình nhãn riêng + mã chuẩn bắt buộc: đồng ý về mô hình, chưa đồng ý về việc công bố.** Hai cột là cách duy nhất để report chuẩn chạy cho nhiều doanh nghiệp, và bốn nguồn tham chiếu thống nhất. Nhưng bộ mã chuẩn mới rút từ một doanh nghiệp; đưa `*_std` lên bảng public ngay là đóng băng một bộ mã chưa kiểm, mà mã thì bất biến. Đề xuất: engine sinh `label_std` trong `entity_labels` (nội bộ, đánh dấu experimental); cột `*_std` trên mart public chỉ thêm sau khi kiểm bằng dữ liệu doanh nghiệp thứ hai hoặc ít nhất một bộ dữ liệu mẫu thật của Haravan/Nhanh.

**2. Thời điểm: không đặt trước phase 6.** Lý do ở mục a1–a4: phase 6 không chứa luật, chèn engine phá bất biến "không đổi số" của Đợt 1, tạo phụ thuộc vòng về thư mục tenant, và kéo dài PII cùng trạng thái nửa vời. Làm engine thành plan riêng ngay sau khi Đợt 1 đóng (sớm hơn Đợt 4 trong roadmap là chấp nhận được, vì engine không cần dbt package hay contract). Spike trên shadow được phép chạy song song, không deploy.

**3. Phase 4: đồng ý bỏ bước macro nguyên văn, có điều kiện.** Làm macro rồi thay bằng engine là làm hai lần, và bước macro tốn công (khoảng 15 domain/biến thể). Điều kiện: ghi vào phase 4 một mốc kiểm lại; nếu tới một ngày cụ thể (ví dụ 6 tuần sau khi Đợt 1 đóng) engine chưa dark launch được `customer_type`, thì làm bước macro như phương án dự phòng. `TAXONOMY.md` (đặc tả) và dời seed + `seed_paths.py` vẫn làm ngay vì chúng đóng rủi ro Critical #5. Acceptance criterion số 5 trong `plan.md` ("mọi luật nằm trong `macros/taxonomy/`") phải sửa tương ứng, nếu không phase 7 sẽ không đóng được plan.

**4. Kênh tách nhiều trục: đồng ý về hướng, hoãn phần cột public.** Tách `order_purpose` khỏi nguồn đơn là sửa một lỗi mô hình có thật (Sapo trộn 5 khái niệm). Nhưng "chỉ thêm cột" vẫn là thay đổi hợp đồng `fact_orders`, bảng có nhiều người đọc nhất. Làm trong engine trước (domain nội bộ), lên mart cùng đợt với quyết định 1.

**5. Restate mặc định: đồng ý, kèm ba điều kiện.** Restate là hành vi hiện có của seed ánh xạ, nên không đổi kỳ vọng người dùng. Điều kiện: (a) model incremental không lưu nhãn của domain restate (mục b2, `int_customer_entry_attributes` đang lệch); (b) mỗi thay đổi luật có báo cáo tác động trước khi áp dụng; (c) hỏi nghiệp vụ Fine Japan danh sách báo cáo đã chốt (thưởng theo team, báo cáo gửi đối tác) để quyết domain nào cần `freeze_after_close` ngoài kế toán. MVP vẫn chỉ cài restate, nhưng phải có câu trả lời cho (c) trước khi cutover `customer_type`.

**6. Ai nhập luật: mình cấu hình hộ qua repo + gate cho tới khi có validator, xem trước tác động và last-known-good; sau đó mới mở Google Sheet cho lớp tenant.** Kết hợp là đích, nhưng thứ tự quan trọng: mở Sheet trước khi có ba thứ trên là mở một đường thay số prod không qua runbook (mục b5). Lớp sản phẩm và gói connector không bao giờ sửa qua Sheet.

## (e) Rào chắn và tiêu chí huỷ cho thí điểm `customer_type`

### Trước khi bắt đầu

- Đợt 1 đã đóng (phase 7 xong, shadow đã dọn và dựng lại từ backup mới cho plan engine).
- Câu hỏi §9 về CROSSBORDER và `scope_retail` không cần trả lời để làm 0 khác biệt, nhưng câu hỏi "báo cáo nào đã chốt" (mục b3) phải có câu trả lời trước cutover.
- Ghi số nền: thời gian nightly 7 đêm gần nhất, RAM đỉnh của `data_platform`, phân bố `customer_type` và số dòng rơi vào nhánh `ELSE` hiện tại.

### Các giai đoạn và cổng

| Giai đoạn | Việc | Cổng để qua |
|---|---|---|
| G1 Shadow | Viết luật FJ thành dữ liệu, model `lbl_customer_type`; cột mart vẫn từ SQL cũ | Gate S: 83 bảng giống hệt (engine chưa nối vào mart); diff `lbl_customer_type` với cả 3 biến thể = 0 dòng; chạy thêm trên một cặp backup khác ngày |
| G2 Dark launch prod | Deploy theo runbook; `lbl_customer_type` chạy hằng đêm, asset check so với cột hiện tại | 14 đêm liên tiếp 0 khác biệt; nightly không vượt ngưỡng thời gian/RAM |
| G3 Cutover | Cột mart đọc từ engine, giữ tên; đường SQL cũ giữ sau một biến `var` trong 30 ngày | Gate S chỉ ra 0 giá trị đổi trên 83 bảng; deploy theo runbook |
| G4 Dọn | Xoá đường SQL cũ và biến `var` | 30 ngày không sự cố quy cho engine |

### Tiêu chí huỷ (rơi về macro/SQL)

1. Sau **5 ngày công** ở G1 vẫn không đạt 0 khác biệt cho cả 3 biến thể, hoặc cần **quá 3 đặc trưng** chỉ Fine Japan dùng để đạt được: hình dạng engine sai cho dữ liệu thật; dừng, làm bước macro của phase 4, ghi bài học vào thiết kế.
2. Cần bất kỳ toán tử ngoài danh sách §3.5 hoặc SQL tự do trong luật để biểu diễn luật hiện có: dừng, vì nguyên tắc "không SQL tự do" bị phá ngay từ thí điểm.
3. Nightly dài thêm **quá 10% hoặc quá 10 phút** (lấy cái nhỏ hơn), hoặc RAM đỉnh tăng quá 20%, ở G2: dừng trước cutover, tối ưu hoặc huỷ. Phép dò mẫu là join luật × đối tượng, nên đây là rủi ro có thật trên DuckDB (§10 của standards-and-patterns thừa nhận chưa đo hiệu năng).
4. Bất kỳ đêm nào ở G2 có khác biệt > 0: đếm lại 14 đêm từ đầu; hai lần reset thì quay lại G1 điều tra.
5. Sau cutover, một lần nightly đỏ do dữ liệu luật: rollback ngay bằng biến `var` hoặc revert theo runbook; **hai sự cố trong 30 ngày**: huỷ cutover, giữ engine ở chế độ dark launch.
6. Tỉ lệ `UNMAPPED` + `UNKNOWN` của `customer_type` cao hơn tỉ lệ rơi vào `ELSE` của SQL cũ: coi là khác biệt, không cutover.

### Rollback luôn sẵn

- Tên cột mart không đổi, nên rollback là đổi nguồn tính, không đụng consumer.
- Không xoá SQL cũ cho tới G4. Biến `var` hai đường là phức tạp tạm thời có chủ đích, có ngày xoá ghi trong plan. Đổi biến `var` vẫn đổi compiled SQL nên vẫn đi qua runbook dừng container, nhưng không cần gate mới vì đường cũ đã được chứng minh.
- Luật là dữ liệu có phiên bản: rollback luật không cần deploy code; rollback code engine đi qua runbook.

## Kết luận cho user

Chấp nhận mô hình. Không chèn engine vào giữa Đợt 1: phase 6 không chứa luật nên không có "làm hai lần" đáng kể, còn chèn vào thì phá bất biến không đổi số của plan và kéo dài bản sao PII. Đóng Đợt 1 với phase 4 rút gọn, rồi mở plan engine với dark launch trên prod và các tiêu chí huỷ ở mục e. Hai việc phải sửa trong thiết kế trước khi làm: xử lý model incremental đang lưu nhãn (`int_customer_entry_attributes`, `dim_customers_base`), và đưa chuẩn hoá chuỗi ra sau bước chứng minh 0 khác biệt.

---

Status: DONE
Summary: Khuyến nghị không chèn engine trước phase 6 (phase 6 không chứa luật phân loại; chèn vào phá bất biến "không đổi số" của Đợt 1); đóng Đợt 1 với phase 4 rút gọn, rồi thí điểm `customer_type` thành plan riêng qua shadow → dark launch 14 đêm → cutover có biến `var` và 6 tiêu chí huỷ.
Concerns: (1) `int_customer_entry_attributes` và `dim_customers_base` là incremental và lưu nhãn `customer_type`, mâu thuẫn với restate; thiết kế chưa xử lý. (2) Chuẩn hoá chuỗi ở tầng đặc trưng có thể đổi số âm thầm nếu áp trước khi chứng minh 0 khác biệt. (3) Google Sheet làm nơi nhập luật là đường đổi số prod không qua runbook và harness. (4) Chưa xác minh serving view/Rill/CRM phản ứng thế nào với cột mới trên bảng public. (5) Chưa biết có báo cáo nào đã chốt thưởng cần `freeze_after_close` ngoài kế toán; cần hỏi nghiệp vụ Fine Japan. (6) Acceptance criterion 5 của `plan.md` phải sửa nếu bỏ bước macro.
