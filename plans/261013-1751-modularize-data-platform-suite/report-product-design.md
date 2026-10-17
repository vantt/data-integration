---
title: "Thiết kế: đóng gói report thành sản phẩm (xưởng report)"
status: draft v2 — sau hội đồng 5 thành viên, chờ user duyệt
date: 2026-10-14
inputs: [references/reports/handbook-inventory.md, references/reports/skills-audit.md, references/reports/external-references.md, reports/report-council/*.md, taxonomy-engine-design.md, roadmap.md (Đợt 7)]
supersedes: plans/260528-1325-tool-agnostic-design-spec (kế thừa quyết định D1–D8, xem §10)
---

# Thiết kế: đóng gói report thành sản phẩm

> **v2.** Hội đồng 5 thành viên (BI, công cụ report, kiến trúc dữ liệu, sản phẩm SME, vận hành/rủi ro) đã phản biện v1; báo cáo ở `reports/report-council/`. Mục **[Quyết định]** cần user chốt; §11 liệt kê.

## 1. Mục tiêu và không làm gì

**Mục tiêu:** biến report và công cụ đang có của Fine Japan thành sản phẩm cài được cho bất kỳ khách nào, và làm được report riêng cho từng khách bằng cùng bộ công cụ.

**Thước đo:** (1) cài bộ report chuẩn lên một Metabase mới bằng một lệnh, không sửa tay; (2) chạy lại lệnh đó không đổi gì; (3) một report riêng cho khách đi qua cùng đường deploy.

**Không làm:** thiết kế lại nội dung report; chuẩn hoá CRM/HUG; BI riêng; phân quyền theo dòng (chi nhánh, kênh) ở v1.

## 2. Hiện trạng: những gì hội đồng tìm thấy

| Vấn đề | Mức | Nguồn |
|---|---|---|
| Blueprint ghi cứng `field_id` (26/45 blueprint), DB `"Sapo"`, hostname, VAT `/1.08` | Chặn cài sang khách khác | skills-audit, tooling |
| ~110 artifact → ~45 họ báo cáo, 7 cụm trùng, 4 họ riêng FJ lẫn phần chung | Không rõ bộ chuẩn | handbook-inventory |
| Một chỉ tiêu định nghĩa ở 3 chỗ, **đang cho số khác nhau**: Rill tự tính `scope_*` khác mart dbt (`rill/models/orders_enriched.sql:79-83`); `Total Orders` không lọc `is_active_order` trong khi doanh thu có lọc | **Lệch số hôm nay** | data-architect, tooling |
| `channel_net_profit` dùng `COALESCE(cogs_amount, 0)` → đơn thiếu giá vốn có lợi nhuận bằng doanh thu (`fact_order_economics.sql:172`) | **Sai số hôm nay** | data-architect (đã kiểm) |
| Tên `net_revenue` hai nghĩa: `metrics.md` = sau giảm giá, **trước** hoàn; chuẩn kế toán VN = **sau** hoàn | Nhầm nghĩa khi gộp | BI |
| Deployer: `Dashboard.find` tìm theo tên trên mọi dashboard rồi dời và ghi đè card (D1, Critical); card tìm theo tên trong collection, collection `Executive` có 3 tên trùng (D2); lỗi bị nuốt, exit 0 (D3); tắt kiểm TLS (D4); thay toàn bộ danh sách card và bộ lọc | **Có thể ghi đè dashboard prod** | tooling, ops |
| **Metabase (file H2 `app_data/metabase_data`) có vẻ không nằm trong backup hằng đêm**; runbook không có mục Metabase | **Không có điểm khôi phục** | ops (controller đã đọc `backup.sh`) |
| Evidence: 3 gói `latest`, không lockfile; 2 trang thật đều đã có bản Metabase | Build lại image có thể vỡ | tooling, ops |
| Metabase OSS 0.62.3: không serialization, không metric dùng được trong SQL | Mọi deploy qua API | external, tooling |

## 3. Khung tổ chức (đã chốt 14/10, chỉnh sau hội đồng)

- Catalog xếp theo ô **chức năng × cấp** (7 × 3). Hai ô cố ý để trống: Điều hành × ngày (trang chủ chủ shop đảm nhận), Marketing × ngày (nền tảng quảng cáo đã có).
- Persona là người cụ thể của doanh nghiệp, gán ô; sản phẩm kèm bộ persona mẫu theo cỡ doanh nghiệp. **[Quyết định]** số persona mẫu.
- **Phân quyền theo chức năng** (tối đa 7 nhóm), không theo 21 ô; cấp chỉ để sắp xếp catalog và trang chủ (đề xuất của sản phẩm, đơn giản hơn v1).
- **Cờ "nhạy cảm chi phí" trên chỉ tiêu** (giá vốn, biên, lợi nhuận): deployer không đặt thẻ có cờ này vào report/trang chủ của nhóm không được xem chi phí. Đây là nhu cầu thật của chủ shop Việt (giấu lợi nhuận với nhân viên) mà phân quyền theo ô không chặn được.
- Trang chủ theo vai trò, 6–8 thẻ, ghép từ KPI của report.

## 4. Kiến trúc

```
dbt marts (giữ dữ liệu thô: đủ mốc ngày, tiền tách cột, cờ)
   │
   ▼
① Registry chỉ tiêu ──► ② Catalog ──► ③ Spec v2 (mỗi report một file)
   (module code, JSON Schema, CI)                     │
                                                      ▼
④ Hồ sơ khách ─────────────► ⑤ Renderer Metabase ─► ⑦ Deployer an toàn ─► Metabase của khách
   (ngoài image)                (Rill: sinh measure, sau)      ▲
⑥ Overlay khách ──────────────────────────────────────────────┘
```

### ① Registry chỉ tiêu

- **Module code** (`analytics/`, đề xuất), JSON Schema, validator Python trong `scripts/checks/`, chạy CI. `metrics.md` và bảng chú giải Việt–Anh **sinh ra** từ registry.
- **Hai lớp, cùng dạng MetricFlow:** lớp ngữ nghĩa mô tả mart (grain, cột thời gian, join, measure gốc, bộ lọc trạng thái có tên); lớp chỉ tiêu (simple, ratio, derived, snapshot). Trường bắt buộc: `additivity`, `null_policy`, `cost_sensitive`, bộ lọc viết dạng có cấu trúc (không chuỗi SQL).
- **Bộ sinh giới hạn:** chỉ sum/count/ratio, một trục thời gian, một join nhiều-một. Window, lịch sử, phân bổ chi phí, hai fact khác grain **phải làm trong dbt**. Đây là chặn chống "registry phình thành semantic layer tự chế".
- **Tham số doanh thu áp lúc sinh truy vấn, không build lại dbt cho từng khách**, với điều kiện mart giữ dữ liệu thô. Chỉ tham số làm đổi thực thể đã materialize (múi giờ, nguồn giá vốn, ngưỡng hạng khách/RFM) đi vào dbt vars. Đề xuất model `fact_revenue_events`.
- **Đổi tên không đổi số:** `net_sales` = doanh thu sau giảm giá, trước hoàn (là `net_revenue` hôm nay, giữ alias trong lúc chuyển); `returns_amount`; `net_revenue` = `net_sales` − `returns_amount` (đúng nghĩa kế toán). **[Quyết định]**
- **Mặc định ghi nhận doanh thu** (khớp mart hiện tại, Fine Japan không đổi số): ghi nhận khi tạo đơn (trừ huỷ, nháp); trừ hoàn vào kỳ hoàn hoàn tất, dòng riêng; **sàn trợ giá không phải tham số**: phần sàn trả tính là doanh thu, hiện dòng riêng; AOV = `net_sales` / số đơn tính doanh thu, không gồm ship và VAT; **VAT là tham số** (giá gồm VAT / chưa VAT / không VAT cho hộ kinh doanh), thay `/1.08` viết cứng. Kèm chỉ tiêu riêng "doanh thu đã giao" cho shop COD. Sản phẩm đóng gói thành 2 preset: "Như Sapo" (mặc định) và "Theo kế toán". **[Quyết định]**
- **Thang lợi nhuận:** CM1 = doanh thu thuần − giá vốn; CM2 = CM1 − phí sàn − ship shop trả − phí thanh toán; CM3 = CM2 − quảng cáo; lợi nhuận vận hành = CM3 − chi phí chung. MER = doanh thu / chi quảng cáo.
- **Độ phủ dữ liệu:** chỉ tiêu biên/lợi nhuận đi kèm "% đơn có giá vốn"; thiếu giá vốn thì để trống, không coi là 0.
- **Bước 0 bắt buộc:** bảng so sánh 3 định nghĩa hiện có (metrics.md, Rill, blueprint) cho từng chỉ tiêu, đánh dấu chỗ lệch; mỗi chỗ lệch là một quyết định có đổi số, user duyệt riêng.

### ② Catalog

- Mỗi report: `id`, `title`, `cell` + `primary_cell`, `question`, `metrics` (từ đó **suy ra** `requires`/`enhances`, không gõ tay), `kpi_tiles`, `spec`, `status`.
- **Mở khoá theo tập khả năng**, kiểm 3 mức: khai báo (connector), bật (pack), quan sát được (dữ liệu thật có; model `mart_capabilities`). Thiếu `enhances` → thẻ hiện "–" kèm lý do.
- Catalog đề xuất của trưởng BI: 19 report chuẩn + 2 report tiện ích luôn cài (**Sức khoẻ dữ liệu**, **Đối soát với Sapo**); shop chỉ có POS vẫn có khoảng 12 report chạy được. Phần riêng FJ sang overlay FJ; các explorer chuyển thành phân tích tự do (Rill), không là report.

### ③ Spec v2

- Kế thừa Design Spec (`analytics-design` Phase 0–6) và quyết định của plan 260528 (§10): thẻ tham chiếu `metric_ref` + chiều chuẩn; cho phép `inline_sql` có khai báo cột đầu ra (bậc đệm, đánh dấu "không chuẩn"); `spec_version`.
- Thêm trường so sánh kỳ, trục thời gian (ngày đơn / ngày hoàn / ngày đối soát), chú thích tự sinh cho thẻ và chân trang "doanh thu được tính thế nào".

### ④ Hồ sơ khách và ⑥ Overlay

- Một **repo cấu hình riêng phía mình** giữ hồ sơ + overlay của mọi khách (ngoài image, cùng chỗ với luật phân loại). Tham số doanh thu **ghi tường minh** vào hồ sơ, không thừa kế mặc định, để nâng cấp không âm thầm đổi số.
- Overlay chỉ được: thêm report riêng, ẩn, đổi nhãn, đổi ngưỡng, đổi thứ tự trang chủ; metric riêng có id tiền tố tenant. Không sửa định nghĩa chuẩn.
- Một collection **"Tự làm"** cho khách tự tạo, deployer không bao giờ đụng.

### ⑤ Renderer

- **Hai renderer, chia vai theo nhịp thay đổi (user 14/10):**
  - **Evidence = report định kỳ, ít thay đổi** (báo cáo ngày, tuần, tháng: Weekly Pulse, Monthly Scorecard, P&L, Sales Review, Marketing Monthly…). Build **một lần sau nightly** thành trang tĩnh: tải nhanh, không tốn tài nguyên mỗi lần mở, widget tuỳ biến được, thân thiện điện thoại. User định chuyển dần các report loại này từ Metabase sang Evidence.
  - **Metabase = report tương tác và tác nghiệp:** tra cứu đơn, đối soát, danh sách việc (khách cần chăm, hàng sắp hết), câu hỏi tự phục vụ, cảnh báo.
  - Catalog ghi `engine` cho từng report (quyết định cũ "chọn công cụ theo report"); spec v2 không phụ thuộc công cụ nên đổi engine của một report không phải viết lại.
  - Renderer Evidence chỉ sinh file và build tĩnh, không ghi vào prod qua API → **rủi ro thấp hơn deployer Metabase, nên làm trước.**
  - **Điều kiện trước khi đầu tư:**
    1. Ghim phiên bản (3 gói đang `latest`, không lockfile).
    2. Spike tương lai Evidence: gói legacy ra bản cuối 02/2026; bản mới có đọc DuckDB file cục bộ không (chưa xác minh). Kết quả quyết định ở lại bản legacy đã ghim hay đổi kiến trúc.
    3. **Build theo lịch:** Dagster chạy `evidence build` sau nightly, phục vụ thư mục tĩnh; không build lại khi restart container.
    4. **Bảo mật dữ liệu trong trang tĩnh:** bản build chứa sẵn dữ liệu trích (file dữ liệu tải xuống trình duyệt), ai có URL là xem được. Hiện `evidence.lan.fwg.vn` chỉ qua Caddy, không có đăng nhập. Cần lớp đăng nhập ở reverse proxy, phân quyền theo đường dẫn (chức năng), và report có cờ nhạy cảm chi phí chỉ build vào khu vực có quyền; giới hạn dữ liệu trích đúng mức report cần.
    5. Thay thế "gửi định kỳ" của Metabase: tin tóm tắt kèm link trang Evidence.
- Rill: dùng nội bộ (phân tích tự do, hỗ trợ); sinh measure từ registry **sau thí điểm** (2–3 ngày), sau khi thống nhất định nghĩa.
- Renderer Metabase: viết mới bộ chuyển metric → SQL; sinh ra đúng dạng object mà `markdown_parser` đang trả về; tách `deployConfig()` để blueprint cũ và spec v2 dùng chung tầng API (`MetabaseClient`, `lib/resources/*` dùng lại được).

### ⑦ Deployer an toàn (điều kiện trước mọi lần ghi vào Metabase prod)

1. Sửa D1/D2/D3/D4 (tìm theo tên toàn cục, card trùng tên, nuốt lỗi, tắt TLS).
2. **Sổ deploy** làm nguồn định danh (`spec_id` marker trong `description` + file khoá phiên bản đã cài); không dùng `entity_id` làm khoá chính.
3. Chỉ đụng object do chính nó tạo, trong collection được cho phép.
4. **Phát hiện chỉnh sửa của người dùng** (drift) và từ chối ghi đè.
5. Không thay toàn bộ danh sách card/bộ lọc; cập nhật có chọn lọc.
6. Tra field theo `schema.bảng.cột` qua `GET /api/database/:id/metadata`, thiếu thì `sync_schema` một lần rồi báo lỗi rõ.
7. `--render-only` (offline) và `--plan` (đọc server, in khác biệt) bắt buộc trước khi ghi.
8. **Snapshot trước mỗi deploy:** xuất JSON các object liên quan + bản sao file H2 lúc Metabase dừng.
9. Khoá chống hai deploy chạy cùng lúc; timeout, thử lại có giới hạn.
10. Test: phần nối card trên Metabase tạm (container), so số bằng cách chạy SQL mới và SQL blueprint cũ trên cùng bản chụp DuckDB.
11. Ghi phiên bản catalog/registry đã cài cho mỗi khách, ở cả repo cấu hình và trong Metabase.

Thêm mục **Metabase** vào runbook deploy (`docs/operations/deployment.md`).

## 5. Report riêng cho khách

| Loại | Ví dụ | Ai làm | Chi phí |
|---|---|---|---|
| L0 | Report đã có trong catalog | Bật | Miễn phí |
| L1 | Đổi nhãn, ẩn, đổi ngưỡng (overlay) | Mình | Trong gói |
| L2 | Report mới trên chỉ tiêu có sẵn | Agent (`analytics-design`) soạn, analyst duyệt | Giá cố định |
| L3 | Cần chỉ tiêu mới hoặc SQL riêng | Mình | Báo giá + phí bảo trì năm |

**Đưa lên chuẩn** khi: ≥ 3 khách cần, chỉ dùng chỉ tiêu chuẩn, không SQL riêng, so số đạt trên dữ liệu 2 khách. Trước mỗi nâng cấp, kiểm overlay của mọi khách.

## 6. Bàn giao cho khách mới

- Ngày đầu (shop chỉ có Sapo): 7 report + 2 tiện ích + trang chủ "Chủ shop" thân thiện điện thoại.
- **Ký xác nhận khớp số với Sapo** khi bàn giao (báo cáo đối soát), trong 7 ngày.
- **Tin tóm tắt ngày/tuần qua Zalo/Telegram/Lark** dựng từ thẻ KPI: chủ shop không vào được Metabase on-prem từ điện thoại. Gắn với notifier của Đợt 8; **[Quyết định]** có đưa lên sớm không.
- Nhập dữ liệu tay (chỉ tiêu, giá vốn) không qua YAML: dùng Google Sheet như hiện nay.

## 7. Áp vào Fine Japan

- Thí điểm **Weekly Pulse** trong collection ẩn; mốc so số là **blueprint đang chạy**, không phải design spec (design đã lệch). Cổng: cả 30 card khớp; 4 chu kỳ tuần liên tiếp khớp trên tuần đã đóng, có một lần qua ranh giới tháng.
- **Chuyển giao giữ nguyên id:** ghi truy vấn mới vào dashboard/card cũ để lịch gửi email, cảnh báo, bookmark, link, câu hỏi dựa trên câu hỏi khác không gãy. **[Quyết định]**
- Tham số doanh thu của FJ ghi đúng như hôm nay vào hồ sơ FJ.
- Nếu thí điểm thất bại: FJ giữ blueprint hiện tại, công cụ mới chỉ dùng cho khách mới.
- **Điều kiện dừng thí điểm:** deployer đổi gì ngoài collection thí điểm; một chỉ tiêu vẫn lệch sau 2 vòng sửa; > 30% card cần SQL riêng; vượt 2 lần ước lượng (~10 ngày); sự cố prod truy được về việc này; chạy lại deploy vẫn còn thay đổi.

## 8. Thứ tự

**Việc vận hành độc lập, nên làm ngay (cần user duyệt vì đụng prod):**
1. Đưa `metabase_data` vào backup (copy H2 lúc Metabase dừng, hoặc xuất qua API); cân nhắc chuyển Metabase sang Postgres trước khách thứ hai.
2. Ghim phiên bản Evidence (đọc bản đang chạy, ghim, thêm lockfile, `npm ci`), ~1 giờ.
3. Sửa 2 lỗi số: Rill `scope_*` lệch mart; `channel_net_profit` coi thiếu giá vốn là 0. Có đổi số → gate + user duyệt.

**Plan report (sau phase 7 và cơ chế pack, vì phải có bước 1–2 trước khi ghi Metabase prod):**

| Phase | Việc | Đổi số? |
|---|---|---|
| 0 | Bảng so sánh định nghĩa 3 nguồn; quyết định từng chỗ lệch | Có (từng chỗ duyệt riêng) |
| 1 | Registry tối thiểu: chỉ tiêu Weekly Pulse dùng; JSON Schema + validator | Không |
| 2 | Spec v2 cho Weekly Pulse | Không |
| 3 | Ghim Evidence + spike tương lai Evidence; renderer Evidence + build theo lịch sau nightly + lớp đăng nhập | Không |
| 4 | **Thí điểm Weekly Pulse trên Evidence** (đã có bản Evidence và Metabase để so), 4 chu kỳ | Không (so số) |
| 4b | Deployer Metabase an toàn (§4 ⑦) cho report tương tác, test trên Metabase tạm | Không |
| 5 | Mở rộng catalog chuẩn, overlay FJ, gộp bản trùng, report tiện ích | Không |
| 6 | Trang chủ vai trò, phân quyền theo chức năng, cờ chi phí, persona mẫu | Không |
| 7 | Chuyển dần report định kỳ còn lại từ Metabase sang Evidence (chạy song song, so số, rồi tắt bản Metabase) | Không |
| 8 | Rill sinh từ registry; tin tóm tắt (nếu đưa lên sớm) | Không |

Catalog lớn, trang chủ, persona mẫu chỉ làm sau khi thí điểm đạt.

## 9. Quan hệ với các plan khác

- Cơ chế pack + lớp ánh xạ nhãn → mã chuẩn: cung cấp `*_std` (hiện **chưa có cột nào**) và khả năng dữ liệu. Thí điểm Weekly Pulse **không phụ thuộc** `*_std`.
- Bộ máy phân loại: `scope_*` nên thành domain `order_scope_std` (khớp đề xuất `sales_line` của thiết kế phân loại).
- MetricFlow: để Đợt 3, chỉ khi cần agent/MCP truy vấn chỉ tiêu động; spike trong project dbt riêng chỉ đọc serving.
- Serving: chuyển `SELECT *` sang view `serving_vN` liệt kê cột; ghim `duckdb` trong image; `contract: enforced` cho mart public **[Quyết định]** có làm trước Đợt 3 không.

## 10. Kế thừa plan 260528 (tool-agnostic design spec)

Plan `260528-1325-tool-agnostic-design-spec` (đang hoãn) đã khoá 8 quyết định cho đúng bài toán spec → deployer. Thiết kế này **thay thế plan đó và kế thừa**: D1 (spec → API trực tiếp, bỏ blueprint trung gian), D2 (hybrid `metric_ref` + inline SQL), D3 (capture-first: chụp dashboard đang chạy làm mốc), D4 (`spec_version`), D5 (deployer theo từng công cụ), D7 (JSON Schema từ đầu), D8 (`analytics-design` sở hữu schema spec). D6 (badge portability) giữ nhưng ưu tiên thấp vì sản phẩm chỉ dùng Metabase. Khi duyệt, đánh dấu plan 260528 là superseded.

## 11. Quyết định cần user chốt

**Tất cả đã chốt (user, 14/10/2026 ~20:00):**

| # | Quyết định | Chốt |
|---|---|---|
| 1 | Tên doanh thu | `net_revenue` hiện tại → `net_sales` (alias trong lúc chuyển, không đổi số); `net_revenue` = `net_sales` − hàng hoàn (nghĩa kế toán) |
| 2 | Mặc định doanh thu | Như §4 ①; 2 preset "Như Sapo" (mặc định) / "Theo kế toán"; thêm chỉ tiêu "doanh thu đã giao" cho shop COD |
| 3 | Renderer | Evidence cho report định kỳ (build sau nightly), Metabase cho report tương tác; thí điểm Weekly Pulse trên Evidence. Đã ghim phiên bản Evidence (main `c2915881`, chưa rebuild) |
| 4 | Phân quyền | Theo chức năng (≤ 7 nhóm) + cờ nhạy cảm chi phí; không phân quyền theo dòng ở v1 |
| 5 | Chuyển FJ (Metabase) | Chạy song song, so số, rồi ghi đè vào dashboard/card cũ để giữ id |
| 6 | Tin tóm tắt | Đưa vào plan report, làm cùng thí điểm Weekly Pulse (tin + link trang Evidence, dùng notifier sẵn có) |
| 7 | Persona mẫu | 2 bộ theo cỡ: "shop nhỏ" (Chủ shop + Nhân viên), "doanh nghiệp vừa" (Giám đốc, Kế toán, Marketing, Trưởng bán hàng, Kho/vận hành, CSKH) |
| 8 | Backup Metabase | Session thực thi kiểm (chỉ đọc) có cơ chế backup nào khác; nếu không, thêm xuất qua API hằng đêm + bản sao H2 lúc Metabase dừng trong khung bảo trì, qua runbook |
| 9 | `contract: enforced` | Chỉ cho các mart mà registry/report chuẩn dựa vào, làm cùng plan report; còn lại để Đợt 3 |
| 10 | Plan 260528 | Đánh dấu superseded bởi thiết kế này |
| — | Hai lỗi số | Sửa cả hai, qua gate S, user duyệt danh sách đổi trước deploy, làm sau phase 6–7: (a) Rill dùng thẳng cột `scope_*` của mart; (b) thiếu giá vốn thì lợi nhuận để trống + cột độ phủ giá vốn |



1. Đổi tên `net_revenue` hiện tại thành `net_sales` (không đổi số), `net_revenue` dùng đúng nghĩa kế toán (sau hoàn).
2. Mặc định doanh thu như §4 ①, đóng gói 2 preset "Như Sapo" / "Theo kế toán".
3. Hai renderer chia vai theo nhịp: Evidence cho report định kỳ ít thay đổi (build một lần sau nightly), Metabase cho report tương tác/tác nghiệp. Thí điểm Weekly Pulse trên Evidence trước; cần lớp đăng nhập cho trang tĩnh.
4. Phân quyền theo chức năng (7 nhóm) + cờ nhạy cảm chi phí; không phân quyền theo dòng ở v1.
5. Chuyển giao FJ bằng cách ghi đè vào dashboard cũ để giữ id.
6. Tin tóm tắt Zalo/Telegram/Lark: đưa vào plan report (phase 7) hay giữ ở Đợt 8.
7. Số persona mẫu đi kèm: 2 bộ theo cỡ (đề xuất của vận hành) hay 6–7 persona (BI, sản phẩm).
8. Ba việc vận hành ở §8 (backup Metabase, ghim Evidence, sửa 2 lỗi số): duyệt làm ngay.
9. `contract: enforced` cho mart public trước Đợt 3.
10. Đánh dấu plan 260528 là superseded.
