---
title: "Hội đồng phản biện — vai trò vận hành / red team"
reviewer: council-ops-risk
date: 2026-10-14
target: report-product-design.md (draft v1), chú trọng §4 ⑦, §7, §8, §9
inputs: [report-product-design.md, roadmap.md, plan.md, references/reports/skills-audit.md, reports/red-team-review.md, docs/operations/deployment.md, scripts/backup/backup.sh, .skills/metabase-automation/scripts/deploy_from_markdown.js, docker-compose.yml, Dockerfile.evidence]
---

# Phản biện vận hành: đóng gói report thành sản phẩm

Tôi không gọi Metabase, không đọc `.env*`, không sửa file nào khác. Mọi khẳng định dưới đây có dẫn file; chỗ chưa kiểm chứng được ghi rõ.

## 0. Kết luận ngắn

Thiết kế đúng hướng về kiến trúc nhưng **sai thứ tự về vận hành**: nó đặt việc ghi tự động vào Metabase prod (deployer, §4 ⑦) lên trên một nền mà hôm nay **chưa có điểm rollback cho Metabase**, chưa có runbook deploy cho Metabase, và deployer hiện tại ghi đè chỉnh sửa của người dùng theo thiết kế. Trước khi thí điểm Weekly Pulse, phải có (1) bản sao lưu nhất quán của Metabase app DB trước mỗi lần ghi, (2) một "Metabase shadow" để chạy thử, (3) deployer chỉ được chạm vào đối tượng mà nó sở hữu. Phạm vi §8 (7 phase, catalog 14–18 report, trang chủ vai trò, phân quyền theo ô) đang thiết kế cho N khách khi N = 1; tôi đề nghị cắt thí điểm xuống còn "registry tối thiểu + deployer an toàn + một report", và chỉ mở rộng khi có khách thứ hai.

## 1. Bằng chứng vận hành đã kiểm

| # | Sự thật | Nguồn | Hệ quả |
|---|---|---|---|
| E1 | Metabase dùng app DB **H2** trong `./app_data/metabase_data` (`metabase.db.mv.db`). | `docker-compose.yml:63-83`, `scripts/backup/README.md:10` | Không có dump nóng nhất quán; sao lưu an toàn phải dừng Metabase. |
| E2 | Backup hằng đêm **không chứa Metabase**: chỉ `data_lake`, `dagster_home`, `input_source`, file config. | `scripts/backup/backup.sh:26` (vòng lặp), `app_data/backups/backup-20261014-010406.log` | Hôm nay một lần deploy hỏng **không có điểm khôi phục** cho dashboard, câu hỏi, subscription. README gọi Metabase là "Critical" nhưng script Linux không sao nó. Tôi chưa thấy cơ chế sao lưu Metabase nào khác; cần user xác nhận. |
| E3 | Runbook "Refactor deploys" chỉ nói về container `data_platform`; không có bước nào cho thay đổi Metabase. | `docs/operations/deployment.md:665-735` | Deployer report sẽ ghi vào prod ngoài mọi runbook có kiểm chứng. |
| E4 | Danh tính dashboard là **tên**; card khớp theo tên trong dashboard, rồi theo tên trong cả collection. | `deploy_from_markdown.js:350, 378-384, 426-450`; `skills-audit.md` §2.2 | Một câu hỏi người dùng tự lưu trùng tên trong cùng collection sẽ bị **PUT đè** SQL và viz. |
| E5 | Bộ lọc dashboard **luôn bị ghi lại**, kể cả xoá hết khi blueprint không có ("clearing all"). | `deploy_from_markdown.js:352-357` | Đổi `id`/`slug` tham số làm hỏng subscription có giá trị lọc, link có `?param=`, và mapping của card người dùng tự thêm. |
| E6 | `syncCards` PUT toàn bộ danh sách dashcard theo blueprint. | `lib/resources/Dashboard.js:105-231` | Card người dùng tự thêm vào dashboard bị gỡ. Theo API Metabase, PUT `dashcards` là thay thế toàn phần (cần kiểm chứng trên 0.62.3 trong shadow). |
| E7 | HTTP client không thấy timeout hay retry; deploy gồm nhiều PUT/POST tuần tự, không giao dịch. | `lib/metabase_core.js:11, 87` | Lỗi giữa chừng để dashboard ở trạng thái nửa cũ nửa mới. |
| E8 | Evidence cài `@evidence-dev/*: "latest"`, **không có `package-lock.json`**, `npm install` lúc build image. | `evidence/package.json`, `Dockerfile.evidence` | `docker compose restart` không đổi gì; nhưng **mọi lần build lại image** (đổi Dockerfile, dọn image, máy mới, cài cho khách) sẽ kéo bản mới nhất. |
| E9 | Đường dẫn nội bộ cứng trong tài liệu và ví dụ (`bi.lan.fwg.vn/dashboard/43`). | `skills-audit.md` T10 | Người dùng FJ có link theo ID dashboard; đổi ID là gãy link. |

## 2. (a) Chuyển Fine Japan sang catalog/spec v2 mà không phá dashboard đang dùng

### 2.1 Điều §7 chưa tính tới

§7 nói "cài song song vào collection mới, so số, trùng thì chuyển người dùng, lưu trữ bản cũ". Cách này **tạo ID mới cho mọi dashboard và card**. Những thứ sau gắn vào ID cũ và không tự đi theo:

- **Subscription dashboard (email/Slack)** và **alert trên câu hỏi**: gắn `dashboard_id`/`card_id`, kèm giá trị lọc. Phải tạo lại bằng tay hoặc bằng script, và người nhận sẽ thấy email đổi định dạng.
- **Bookmark, link trong Lark/tài liệu, trang chủ Metabase của từng người**: gắn ID. Lưu trữ bản cũ là gãy link âm thầm.
- **Câu hỏi người dùng tự lưu dựa trên card chuẩn** (Metabase cho phép câu hỏi dựa trên câu hỏi khác qua `card__<id>`): lưu trữ card gốc làm hỏng các câu hỏi phái sinh mà ta không biết tồn tại.
- **Quyền**: collection mới thừa hưởng quyền của collection cha; nếu cha rộng hơn collection cũ, report tài chính lộ cho nhóm không đúng.
- **Thói quen người dùng**: hai bản cùng tên trong thời gian chạy song song làm người dùng xem nhầm bản; nếu hai bản lệch số, niềm tin vào cả hai giảm.

### 2.2 Ba cách khác nhau thật sự

| Tiêu chí | A. Song song collection mới (thiết kế §7) | B. Nhận nuôi tại chỗ (adopt in place) | C. Đóng băng FJ ở blueprint cũ |
|---|---|---|---|
| Cách làm | Cài bản sinh từ spec v2 vào collection mới, so số, chuyển người dùng, lưu trữ bản cũ. | Deployer gắn `spec_id` vào **dashboard và card hiện có** của FJ, rồi cập nhật SQL tại chỗ sau khi so số trên Metabase shadow. ID không đổi. | FJ giữ blueprint viết tay; factory chỉ dùng cho khách mới; report FJ chuyển dần khi tự nhiên phải viết lại. |
| Gãy subscription/link/bookmark | Có, mọi thứ | Không (ID giữ nguyên) | Không |
| Rủi ro sai số trước mắt người dùng | Thấp (bản mới ẩn cho tới khi khớp) | Trung bình: lúc chuyển là chuyển thật; cần shadow tốt | Không |
| Chứng minh factory chạy trên dữ liệu thật | Có | Có | Không cho tới khách thứ hai |
| Công sức thêm | Tạo lại subscription, truyền thông, dọn bản cũ | Bước "adopt" (map card cũ → phần tử spec), một lần cho mỗi dashboard | Gần như không |
| Hệ quả bậc hai | Hai bản tồn tại hàng tuần; rác collection; người dùng mất bookmark | Deployer phải cực kỳ an toàn vì ghi trực tiếp vào thứ người dùng đang xem | Hai đường công cụ song song lâu dài (vi phạm DRY), FJ không hưởng cải tiến |

**Khuyến nghị của tôi:** dùng **A cho thí điểm** (ẩn với người dùng, chỉ nhóm thử nghiệm xem) để đo độ khớp mà không rủi ro, nhưng **cut-over bằng B**: khi bản mới đã khớp, deployer ghi SQL mới vào dashboard/card cũ (giữ ID), rồi xoá bản thí điểm. Như vậy subscription, bookmark, link không gãy. Phương án đơn giản nhất còn đáp ứng yêu cầu "cài được cho khách mới" là C, và nó nên là phương án dự phòng nếu thí điểm dính tiêu chí dừng ở mục 8.

### 2.3 Điều kiện bắt buộc trước khi chạm FJ

1. **Kiểm kê phụ thuộc theo ID** trước thí điểm (chỉ đọc, qua API): subscription, alert, câu hỏi dựa trên câu hỏi, dashboard trỏ link nội bộ, quyền từng collection. Không có kiểm kê thì không biết cut-over làm gãy gì.
2. **Định nghĩa "so số" bằng máy**, không bằng mắt: mỗi card × bộ lọc mặc định × ít nhất 3 tổ hợp lọc (một tuần đã đóng, tuần đang chạy, ranh giới tháng). Tuần đã đóng phải **khớp tuyệt đối** (bất biến "không đổi một con số", `plan.md` "Bất biến dữ liệu"). Tuần đang chạy so cùng thời điểm snapshot.
3. **Không bao giờ xoá**, chỉ lưu trữ; giữ bản lưu trữ ít nhất 90 ngày; đặt text card "đã chuyển tới …" vào bản cũ trước khi lưu trữ (với phương án A).

## 3. (b) Deployer chạm vào Metabase prod

### 3.1 Các cách hỏng cụ thể

| Hỏng | Cơ chế | Mức |
|---|---|---|
| Ghi đè chỉnh sửa của người dùng | E4, E5, E6: khớp theo tên, ghi lại bộ lọc, thay toàn bộ dashcard | Critical |
| Không rollback được | E1, E2: H2 không có trong backup; khôi phục H2 cũ thì mất mọi chỉnh sửa của mọi người kể từ bản sao | Critical |
| Bản trùng | Danh tính theo tên: đổi tên trong spec hoặc người dùng đổi tên trên UI → tạo dashboard mới; `spec_id` trong description có thể bị người dùng sửa mất | High |
| Hai lần deploy chồng nhau | OSS không có serialization hay khoá; hai phiên agent cùng deploy sẽ xen PUT | High |
| Nửa vời | E7: không giao dịch, không timeout; lỗi mạng giữa chừng | High |
| Tải lên DuckDB | Sau deploy, Metabase chạy lại card; thí điểm song song nhân đôi truy vấn trên `olap.duckdb` cùng lúc lịch `*/3` ghi | Medium |
| Tra field theo `schema.bảng.cột` sai | Metadata Metabase chưa sync sau khi mart thêm cột `*_std` → field không tìm thấy hoặc lấy nhầm bảng trùng tên ở schema khác | Medium |

### 3.2 Hàng rào bắt buộc cho deployer (trước thí điểm)

1. **Sổ deploy (deploy ledger)**: mỗi đối tượng deployer tạo được ghi `(spec_id, loại, metabase_id, hash nội dung đã ghi, phiên bản catalog)`. Danh tính lấy từ sổ này, không từ tên, và không chỉ từ description.
2. **Phát hiện trôi (drift)**: trước khi PUT, so nội dung live với hash đã ghi lần trước. Khác → người dùng đã sửa → **từ chối** và in diff, trừ khi có `--force` cho đúng `spec_id` đó.
3. **Chỉ chạm thứ mình sở hữu**: không bao giờ PUT một card không có trong sổ (bỏ đường "tìm theo tên trong collection" ở E4). Khi đồng bộ dashcard, **giữ nguyên** dashcard không thuộc sổ. Không xoá bộ lọc không thuộc spec.
4. **Allowlist đích**: tenant profile khai báo collection gốc; deployer từ chối ghi ngoài cây collection đó.
5. **Snapshot trước khi ghi**: GET đầy đủ JSON của mọi dashboard/card sắp chạm, lưu theo timestamp; lệnh `rollback <deploy_id>` PUT lại từ snapshot. Rollback này phải được **diễn tập trên shadow** trước khi dùng thật.
6. **Bản sao H2 lạnh** trước mỗi đợt deploy vào prod (dừng Metabase khoảng 1 phút, chép file, start), giống cách runbook dừng `data_platform`. Đây là lưới cuối cùng khi snapshot JSON không đủ.
7. **Khoá một người ghi**: `flock` trên file khoá cục bộ cho mỗi tenant; deploy thứ hai thoát ngay.
8. **Timeout, retry có giới hạn và giãn cách** cho GET; **không tự retry** POST (tránh tạo trùng); dừng toàn bộ khi một bước ghi lỗi và in trạng thái dở dang.
9. **`--dry-run` là bước bắt buộc của runbook**, output được người duyệt trước khi chạy thật; lần chạy thứ hai liên tiếp phải ra kế hoạch rỗng (kiểm tra idempotent).
10. **Metabase shadow**: container Metabase cùng phiên bản 0.62.3, mở trên bản sao H2 lạnh và bản sao `olap.duckdb`, không nối mạng ra ngoài, tắt gửi email/Slack (nếu không, subscription chép sang sẽ gửi thư thật). Test tự động của §4 ⑦ "Metabase rỗng" là cần nhưng **không đủ**: lỗi nguy hiểm nhất (ghi đè, trôi, link) chỉ hiện trên bản sao có dữ liệu người dùng.
11. **Bổ sung `docs/operations/deployment.md`** một mục "Report deploys (Metabase)" theo cùng khuôn: snapshot → khoá → dry-run → deploy → kiểm → rollback.

Lựa chọn lớn hơn cần cân nhắc: **chuyển Metabase app DB sang Postgres**. Nó cho `pg_dump` nóng trước mỗi deploy và loại bỏ rủi ro H2 hỏng. Nhưng đó là một migration riêng có rủi ro (Metabase hỗ trợ `load-from-h2`), không nên gộp vào thí điểm. Tối thiểu bây giờ là mục 6 và đưa H2 vào backup.

## 4. (c) Nâng cấp trên nhiều khách on-prem

- **Phiên bản hoá catalog và registry bằng semver**, kèm quy tắc: `metric.id` và `report.id` **không bao giờ đổi nghĩa**; muốn đổi định nghĩa thì tạo id mới và đánh dấu id cũ `deprecated`. Đổi `expression` của metric đã phát hành là thay đổi lớn (major), vì nó đổi số trên dashboard của mọi khách.
- **Overlay tham chiếu theo id, được kiểm tra khi nâng cấp**: overlay ẩn hay đổi nhãn một report đã bị xoá/đổi phải làm `validate` thất bại cứng, không âm thầm bỏ qua.
- **Ghi phiên bản đã cài ở cả hai nơi**: file khoá trong thư mục tenant và trong Metabase (description collection gốc). File trên máy khách có thể mất khi cài lại; Metabase có thể bị khôi phục về bản cũ. Hai nguồn lệch nhau → `doctor` báo.
- **`upgrade` = dry-run trên từng khách, in diff theo report**, phân loại: chỉ đổi nhãn/viz (tự áp) và đổi số (cần duyệt). Không bao giờ có lệnh nâng cấp hàng loạt không có diff.
- **Ma trận phiên bản Metabase**: client đã phải xử lý `dashcards` vs `ordered_cards` (`Dashboard.js:113`). Khách on-prem sẽ ở nhiều phiên bản Metabase; ghim một dải phiên bản được hỗ trợ trong tenant profile và kiểm tra lúc deploy.
- **Tham số doanh thu theo khách phải được ghi tường minh** trong profile của từng khách sau lần cài đầu. Nếu khách "thừa hưởng mặc định", thì đổi mặc định ở bản sau sẽ đổi số của họ khi nâng cấp mà không ai quyết định.
- Đây phụ thuộc vào Đợt 2 (image có version) và Đợt 5 (CLI `doctor/upgrade`). Trước khi có hai thứ đó, "cài cho khách" là thủ công dù deployer có tốt đến đâu.

## 5. (d) Phạm vi và thứ tự

- **Đợt 1 chưa xong**: phase 6 đang làm, phase 7 kế tiếp. Không bắt đầu ghi gì vào Metabase prod cho tới khi phase 7 đóng và shadow được dọn, để mỗi sự cố có một nguyên nhân duy nhất. Thiết kế giấy và registry (chỉ file) có thể làm song song.
- **Pack mechanism (~1–2 ngày) phải đi trước** vì cột `*_std` mà spec v2 dựa vào đến từ lớp ánh xạ nhãn. Thêm cột vào mart là thay đổi tầng dữ liệu, phải qua Gate M và runbook data_platform; đừng để nó lọt vào như "một phần của report".
- **N = 1**: roadmap ghi "Chặn: cần dữ liệu doanh nghiệp thứ hai để chốt bộ mã chuẩn" (`roadmap.md` Đợt 4). Catalog 14–18 report, trang chủ vai trò, phân quyền theo ô, persona mẫu, renderer Rill/Evidence đều là thiết kế cho khách chưa có. Giữ chúng trong thiết kế, **không đưa vào plan đầu tiên**.
- **Đề xuất cắt plan đầu tiên** (đáp ứng đủ thước đo §1 cho một report, không thêm gì): (1) registry chỉ các metric Weekly Pulse dùng, kiểm tra bằng schema; (2) spec v2 cho Weekly Pulse; (3) deployer với 11 hàng rào ở 3.2; (4) cài lên Metabase rỗng bằng một lệnh và lên Metabase shadow của FJ; (5) thí điểm FJ. Hợp nhất toàn bộ 56 + 53 metric là việc tốn công nhất của phase 1 và không cần cho thí điểm.
- **Taxonomy engine song song** thì được, miễn là nó không đổi nhãn mà Weekly Pulse đang lọc trong thời gian so số.

## 6. (e) Ghim Evidence: khẩn đến đâu

- Rủi ro **không phải "hỏng ngày mai"**: `restart` không cài lại gói (E8). Rủi ro nổ khi có ai build lại image, và việc đó dễ xảy ra trong Đợt 2 (Dockerfile theo component), khi dọn image, hoặc khi dựng máy mới. Khi đó Evidence nhận bản mới nhất mà thiết kế §2 nói là không đọc DuckDB file cục bộ (tôi chưa kiểm chứng điều này), tức là 4 trang hỏng hoàn toàn.
- **Làm ngay, độc lập với quyết định giữ hay bỏ**, chi phí khoảng một giờ: đọc phiên bản đang chạy trong container (`npm ls` trong container, chỉ đọc), ghim chính xác các gói `@evidence-dev/*` và cả `tailwindcss`/`autoprefixer`, sinh `package-lock.json`, build image trên shadow, so trang trước và sau, rồi mới thay prod. Đổi `npm install` thành `npm ci` để build lại là tái lập được.
- Cùng loại rủi ro: kiểm tra `Dockerfile.metabase` và `Dockerfile.rill` có ghim phiên bản không (tôi chưa đọc). Metabase phải ghim đúng 0.62.3 vì deployer phụ thuộc hình dạng API.

## 7. (f) Ý kiến về §9 quyết định 1–5 từ góc vận hành

1. **Mặc định ghi nhận doanh thu**: chọn gì cho sản phẩm cũng được, nhưng **giá trị của FJ phải bằng đúng cách dashboard FJ đang tính hôm nay** và được ghi tường minh trong profile FJ. Mọi thay đổi khác là "đổi số", cần quyết định nghiệp vụ riêng theo nguyên tắc roadmap. Mặc định sản phẩm nên là cách đơn giản, ít phụ thuộc dữ liệu nhất (khi tạo đơn, trừ hoàn theo ngày hoàn, trợ giá sàn là dòng riêng), vì khách mới hay thiếu trạng thái giao hàng sạch.
2. **Evidence**: ghim ngay; **đóng băng** (không trang mới, không viết renderer); quyết định bỏ sau thí điểm. Mỗi engine thêm là một bề mặt nâng cấp nhân với số khách. Weekly Pulse có ở cả hai engine; nếu thí điểm Metabase đạt, chính thời điểm cut-over là lúc tắt bản Evidence của nó. Tôi nghiêng về bỏ dần, nhưng không làm trong plan đầu.
3. **Catalog và registry là module code có schema kiểm tra** (cùng repo, có version), còn `docs/analytics-handbook/` chứa tài liệu **sinh ra** từ đó. Vận hành cần kiểm tra bằng máy trong CI và trong `doctor`; markdown văn xuôi không kiểm được.
4. **Phân quyền theo dòng: không ở v1.** Metabase OSS không có sandboxing; tự làm bằng view theo nhóm nhân số view và mở ra lỗi lộ dữ liệu khó phát hiện. Một sai sót quyền là sự cố bảo mật, không phải lỗi hiển thị. Nếu khách cần, ghi là giới hạn của sản phẩm.
5. **Persona mẫu**: tối đa hai ("Chủ shop" cho shop nhỏ, "Giám đốc" cho shop có đội) ở bản đầu. Mỗi persona là một trang chủ phải giữ đúng qua mọi nâng cấp; thêm sau thì rẻ, bớt sau thì làm gãy bookmark của khách.

## 8. (g) Thí điểm Weekly Pulse: hàng rào và tiêu chí dừng

### 8.1 Điều kiện vào (tất cả phải đúng)

- Đợt 1 đã đóng (phase 7 xong), nightly prod xanh, không trong khung đóng băng.
- Metabase H2 có trong backup, và đã diễn tập khôi phục một lần trên shadow.
- Metabase shadow chạy được, đã tắt gửi email/Slack.
- Kiểm kê phụ thuộc theo ID của dashboard Weekly Pulse hiện tại (subscription, alert, câu hỏi phái sinh, link).
- Script so số có sẵn, chạy được trên dashboard cũ với chính nó (tự khớp 100%) trước khi so với bản mới.

### 8.2 Hàng rào trong lúc chạy

- Bản thí điểm nằm trong collection riêng, chỉ nhóm thử nghiệm thấy; không subscription nào trỏ vào nó.
- Không một PUT nào vào dashboard Weekly Pulse cũ cho tới bước cut-over.
- Deploy ngoài 02:30–04:00 và ngoài giờ cao điểm xem báo cáo (sáng thứ Hai cho báo cáo tuần); mỗi deploy có dry-run được duyệt và bản sao H2 lạnh.
- So số tự động chạy mỗi ngày trong suốt thời gian song song, kết quả lưu lại, không dựa vào xem bằng mắt.
- Đo thời gian chạy card: p95 của bản mới không chậm hơn bản cũ quá 50%.

### 8.3 Tiêu chí cut-over

- **Bốn chu kỳ tuần liên tiếp** khớp tuyệt đối cho tuần đã đóng, có ít nhất một ranh giới tháng.
- Lần deploy thứ hai liên tiếp ra kế hoạch rỗng; drift detection đã chặn đúng một lần thử sửa tay trên shadow.
- Rollback bằng snapshot đã diễn tập thành công trên shadow.
- Người dùng chính của Weekly Pulse đã xem và đồng ý; cut-over bằng cách giữ ID (mục 2.2), không gãy subscription.

### 8.4 Tiêu chí dừng (một điều đúng là dừng và quay về phương án C)

1. Deployer thay đổi **bất kỳ đối tượng nào ngoài collection thí điểm**, dù chỉ một lần: dừng ngay, rollback, viết post-mortem trước khi làm tiếp.
2. Sau hai vòng sửa, vẫn còn chỉ tiêu lệch số trên tuần đã đóng mà không giải thích được bằng một quyết định nghiệp vụ đã duyệt.
3. Hơn 30% card của Weekly Pulse phải dùng `custom_sql`: trừu tượng metric + chiều không bù được chi phí, nên quay về làm cứng blueprint hiện có (bỏ `field_id`, `"Sapo"`, danh tính theo tên) thay vì spec v2.
4. Công sức vượt hai lần ước tính của plan thí điểm (tôi đề xuất trần 10 ngày công cho cả registry tối thiểu, spec v2, deployer an toàn và thí điểm).
5. Có một sự cố prod (nightly đỏ, dashboard người dùng sai số, mất chỉnh sửa) truy được về công việc report.
6. Idempotency không đạt sau khi sửa: lần chạy thứ hai vẫn tạo hoặc đổi đối tượng.

## 9. Câu hỏi còn mở cho user

1. Ngoài `backup.sh`, có cơ chế nào đang sao lưu `app_data/metabase_data` không? Nếu không, ta đang không có điểm khôi phục cho toàn bộ dashboard prod, độc lập với đề xuất này.
2. Có subscription hoặc alert Metabase nào đang gửi Weekly Pulse cho ai không, và người dùng mở dashboard bằng link nào (bookmark, Lark, trang chủ)?
3. Chấp nhận cut-over theo kiểu giữ ID (ghi đè dashboard cũ sau khi khớp) hay muốn giữ cả hai bản lâu dài?
4. Có muốn đặt migration Metabase H2 → Postgres thành một việc vận hành riêng trước khi có khách thứ hai không?

---

Status: DONE_WITH_CONCERNS
Summary: Thiết kế đúng hướng nhưng đặt deployer ghi vào Metabase prod lên nền chưa có điểm rollback (H2 không nằm trong backup, không có runbook Metabase) và deployer hiện tại ghi đè chỉnh sửa người dùng; đề xuất cut-over giữ ID, 11 hàng rào cho deployer, cắt plan đầu còn registry tối thiểu + Weekly Pulse, ghim Evidence ngay, cùng tiêu chí vào/cut-over/dừng cho thí điểm.
Concerns: Việc Metabase H2 thiếu trong backup dựa trên `backup.sh` và log 14/10; chưa loại trừ cơ chế sao lưu khác. Hành vi PUT `dashcards` thay thế toàn phần và việc Evidence bản mới không đọc DuckDB cục bộ chưa được kiểm chứng trực tiếp. Chưa đọc `Dockerfile.metabase`/`Dockerfile.rill` để xác nhận ghim phiên bản.
