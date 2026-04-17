# Hướng dẫn Phân loại Kênh bán hàng & Gom nhóm Báo cáo

> **Dành cho:** Tất cả nhân sự xem/tạo báo cáo doanh thu
> **Cập nhật:** 2026-04-15
> **Bảo trì:** Data Team

## Tài liệu này trả lời những câu hỏi nào?

1. Làm sao để báo cáo doanh thu Ecommerce vs Offline?
2. Doanh thu Fine Japan bao nhiêu? (sản phẩm? hay kênh?)
3. Cần gom nhóm theo cột nào để trả lời câu hỏi của tôi?
4. Thương hiệu sản phẩm khác gì thương hiệu kênh?
5. Dữ liệu phân loại (seed files) lưu ở đâu?

---

## TL;DR — Nắm bắt cơ bản trong 5 phút

- **Hệ thống phân loại dùng 5 chiều độc lập** — Kênh bán, Sản phẩm, Chi nhánh, Thị trường/Segment, Team (sales team sở hữu doanh số) — có thể kết hợp tự do để trả lời bất kỳ câu hỏi nào.
- **Mỗi chiều = một câu hỏi riêng** — Không cần tạo báo cáo khác nhau, cùng dữ liệu, nhìn từ nhiều góc độ.
- **Kênh bán có 4 tầng** — `channel_category` (Online-Ecommerce/Offline/Internal) → `channel_format` (Marketplace/Social/Web/Retail/B2B/Direct) → `platform` (Shopee/Lazada/Facebook/POS...) → `channel_name` (Shopee-JPC OFFICIAL, POS-Trương Dinh...; "storefront" là nhãn khái niệm, cột thật là `channel_name`).
- **Hai loại "thương hiệu" khác nhau** — Thương hiệu sản phẩm (ai làm) vs Thương hiệu kênh (ai bán). Cùng shop JPC có thể bán sản phẩm của Fine Japan, FG Care, v.v.
- **Seed files là dữ liệu tham chiếu** — Lưu trong `transformation/seeds/`, maintain thủ công, sử dụng bởi dbt để tạo dimension tables.

---

## PHẦN A: HƯỚNG DẪN CHO NGƯỜI TẠO BÁO CÁO

---

## 1. Nguyên tắc cốt lõi

**Mỗi đơn hàng có thể được nhìn từ 5 góc độ độc lập. Để báo cáo theo một góc độ, chỉ cần GROUP BY theo cột tương ứng.**

```mermaid
graph TD
    A["📊 Dữ liệu Đơn Hàng<br/>Mỗi dòng = 1 sản phẩm trong 1 đơn"]

    A -->|Góc độ 1: Bán ở đâu?| B["Kênh bán hàng<br/>Ecommerce / Offline / Internal"]
    A -->|Góc độ 2: Bán cho ai?| E["Thị trường & Segment<br/>Domestic/Export, B2C/B2B"]
    A -->|Góc độ 3: Ai sở hữu doanh số?| J["Team bán hàng<br/>Marketplace / Social / Web / B2B / Retail / Direct"]
    A -->|Góc độ 4: Sản phẩm gì?| C["Thương hiệu Sản phẩm<br/>Fine Japan / FG Care / Fine Care"]
    A -->|Góc độ 5: Ai xử lý?| D["Chi nhánh<br/>Trương Dinh / Hậu Giang / ..."]

    B -->|GROUP BY| F["Báo cáo<br/>Doanh thu theo kênh"]
    E -->|GROUP BY| I["Báo cáo<br/>Doanh thu theo thị trường"]
    J -->|GROUP BY| K["Báo cáo<br/>Doanh thu & KPI theo team"]
    C -->|GROUP BY| G["Báo cáo<br/>Doanh thu theo SP"]
    D -->|GROUP BY| H["Báo cáo<br/>Doanh thu theo chi nhánh"]
```

**Ưu điểm:** Không cần tạo báo cáo riêng — cùng một bộ dữ liệu, nhiều cách nhìn.

**Lưu ý về chiều Team:**
- **Team ≠ Chi nhánh:** Chi nhánh là đơn vị **vận hành vật lý** (ai đóng gói, giao hàng). Team là đơn vị **sở hữu doanh số** (ai chịu KPI, ăn commission). Một đơn Shopee giao từ kho Trương Dinh (chi nhánh) nhưng thuộc Team Marketplace (team).
- **Team ≠ Kênh:** Team **trực giao** (orthogonal) với kênh — không thay thế `channel_category`. Một user có thể bán chéo nhiều kênh nhưng chỉ thuộc 1 team.
- **Exclusivity:** 1 source/user = 1 team tại mỗi thời điểm (theo ràng buộc FG Care). Không chia tỷ lệ, không tranh giữa các team.
- **Scope:** Chỉ gán team cho đơn `is_sales_channel = true`. Internal (Test SP, Quà Tặng, NV) và CrossBorder Fulfillment (US) → team = NULL.
- **Attribution:** Ưu tiên user-based (theo `assignee_id` — người chốt đơn), fallback source-based (theo `source_id` → `default_team`) cho đơn auto-sync không có user thật.

---

## 2. Bảng tham chiếu nhanh

Khi cần báo cáo, tra bảng bên dưới để biết cần gom nhóm theo cột nào.

| Tôi muốn xem doanh thu theo...              | Gom nhóm theo                           | Ví dụ kết quả                               |
| --------------------------------------------- | ---------------------------------------- | ----------------------------------------------- |
| Online vs Offline                             | Phân loại kênh (`channel_category`)    | Online-Ecommerce: 70%, Offline: 30%           |
| Loại kênh (Sàn, MXH, Web, Cửa hàng)      | Hình thức kênh (`channel_format`)       | Marketplace: 50%, Social: 15%, Retail: 25%      |
| Từng nền tảng                              | Nền tảng (`platform`)                   | Shopee: 35%, Lazada: 10%, TikTok: 5%            |
| Từng gian hàng / điểm bán cụ thể        | Gian hàng / Điểm bán (`channel_name` — Tầng 4, = `order_source` Sapo; "storefront" = nhãn khái niệm) | Shopee JPC OFFICIAL: 12%, Shopee Fine Japan: 8% |
| Từng thương hiệu sản phẩm               | Thương hiệu SP                        | Fine Japan: 40%, FG Care: 25%, Fine Care: 15%   |
| Từng thương hiệu kênh                    | Thương hiệu kênh                     | JPC: 35%, Fine Japan: 30%, The Healthy Us: 20%  |
| Từng chi nhánh                              | Chi nhánh                               | Trương Dinh: 50%, Hau Giang: 30%              |
| Nội địa vs Xuất khẩu                     | Thị trường                            | Domestic: 95%, Export: 5%                       |
| Bán lẻ vs Bán sỉ                          | Phân khúc KH                           | B2C: 85%, B2B: 15%                              |
| Từng team bán hàng                         | Team                                     | Marketplace: 55%, Social: 20%, B2B: 15%, Direct: 10% |
| Từng nhân viên trong team                  | Team + Seller (user)                     | Team Social → Vũ Ngọc: 40%, Ngoc Anh: 35%... |
| Team nào bán thương hiệu nào tốt?         | Team + Thương hiệu SP                  | *(kết hợp 2 chiều)*                        |
| SP Fine Japan bán ở sàn nào?              | Thương hiệu SP + Nền tảng           | *(kết hợp 2 chiều)*                        |
| JPC bán bao nhiêu SP Fine Japan?            | Thương hiệu kênh + Thương hiệu SP | *(kết hợp 2 chiều)*                        |

---

## 3. Chi tiết từng chiều phân loại

### 3.1. Kênh bán hàng — "Bán ở đâu?"

Kênh bán hàng có 4 tầng, từ tổng quát đến chi tiết:

```mermaid
graph TD
    A["Phân loại kênh — channel_category<br/>(Tầng 1)<br/>Online-Ecommerce / Offline / Internal"]

    A -->|Online-Ecommerce| B1["Hình thức kênh — channel_format<br/>(Tầng 2)<br/>Marketplace / Social / Web"]
    A -->|Offline| B2["Hình thức kênh — channel_format<br/>(Tầng 2)<br/>Retail / B2B / Direct"]
    A -->|Internal| B3["Hình thức kênh — channel_format<br/>(Tầng 2)<br/>System / CrossBorder Fulfillment"]

    B1 -->|Marketplace| C1["Nền tảng — platform<br/>(Tầng 3)<br/>Shopee, Lazada, Tiki, ..."]
    B1 -->|Social| C2["Nền tảng — platform<br/>(Tầng 3)<br/>Facebook, Instagram, Zalo"]
    B1 -->|Web| C3["Nền tảng — platform<br/>(Tầng 3)<br/>Website"]

    B2 -->|Retail| C4["Nền tảng — platform<br/>(Tầng 3)<br/>POS"]
    B2 -->|B2B| C5["Nền tảng — platform<br/>(Tầng 3)<br/>Wholesale"]
    B2 -->|Direct| C6["Nền tảng — platform<br/>(Tầng 3)<br/>Telesale, CS"]

    B3 --> C7["Nền tảng — platform<br/>(Tầng 3)<br/>System, US"]

    C1 --> D1["Gian hàng / Điểm bán — channel_name<br/>(Tầng 4, storefront = nhãn)<br/>Shopee - JPC OFFICIAL,<br/>Shopee - Fine Japan Vietnam, ..."]
    C4 --> D2["Gian hàng / Điểm bán — channel_name<br/>(Tầng 4, storefront = nhãn)<br/>POS - Trương Dinh,<br/>POS - Hau Giang, ..."]
    C5 --> D3["Gian hàng / Điểm bán — channel_name<br/>(Tầng 4, storefront = nhãn)<br/>Đại Lý, Chợ sỉ"]
```

> **Naming note (finalized 2026-04-15):**
> - Tầng 1 column `channel_category` (không đổi), value `Ecommerce` → **`Online-Ecommerce`** (hyphen, không space, không parens) để SQL filter sạch và tầng 1 không overlap value với tầng 2.
> - Tầng 2 column `platform_group` → **`channel_format`** (rename) để semantic rõ + align với 4-tier taxonomy.
> - Tầng 3 giữ `platform`. Tầng 4 **giữ `channel_name`** (không rename sang `storefront`): ưu tiên consistency `channel_*` prefix cho cả 4 tầng; "storefront" chỉ dùng như nhãn khái niệm trong tài liệu vì industry thường hiểu "storefront" = retail outlet vật lý, dễ gây hiểu nhầm cho shop marketplace.
> - Lý do chọn `category` + `format`: safe (không collision với MISA's `channel_group` + marketing_spend's derived bucket — đã rename thành `marketing_spend_bucket`), minimal blast radius (chỉ 1 column rename ở tầng 2).

> **Note về Tầng 4 — Gian hàng / Điểm bán:**
> - Đây là đơn vị cụ thể nhất mà khách hàng tương tác: 1 shop trên marketplace, 1 cửa hàng POS, 1 page Facebook, v.v.
> - **Mapping 1:1 với field `order_source` (source_name/source_id)** của Sapo. Mỗi giá trị Sapo `source_name` = 1 "Gian hàng / Điểm bán".
> - Seed file tham chiếu: `transformation/seeds/ref_order_sources.csv`.

#### Bảng phân loại đầy đủ

| Tầng 1: Phân loại kênh<br/>(`channel_category`)   | Tầng 2: Hình thức kênh<br/>(`channel_format`)                        | Tầng 3: Nền tảng<br/>(`platform`) | Tầng 4: Gian hàng / Điểm bán<br/>(`channel_name` — map 1:1 vào `order_source` của Sapo) |
| ---------------------------- | ------------------------------------------- | ------------------- | ---------------------------------------------------------- |
| **Online-Ecommerce** | Marketplace (Sàn TMDT)                     | Shopee              | Shopee - JPC OFFICIAL, Shopee - Fine Japan Vietnam         |
|                              |                                             | Lazada              | Lazada - JPC SHOP, Lazada - Fine Japan Vietnam             |
|                              |                                             | TikTok              | TiktokShop                                                 |
|                              |                                             | Tiki                | Tiki - FINE WORLD GROUP                                    |
|                              |                                             | Sendo               | Sendo                                                      |
|                              |                                             | Grab                | GrabMart                                                   |
|                              | Social Commerce (MXH)                       | Facebook            | Facebook, FaceBookJPC, FaceBookFJPTViet                    |
|                              |                                             | Instagram           | Instagram                                                  |
|                              |                                             | Zalo                | Zalo                                                       |
|                              | Website (DTC)                               | Website             | Web, WebOrder                                              |
| **Offline**            | Retail (Cửa hàng)                         | POS                 | POS - Trương Dinh, POS - Hau Giang                       |
|                              | B2B (Bán sỉ)                              | Wholesale           | Đại Lý, Chợ sỉ                                        |
|                              | Direct Sales (Bán trực tiếp)              | Direct              | Telesale, CS — đơn tạo thủ công bởi staff, khách mua thật |
| **Internal**           | System (Nội bộ)                           | System              | Test Sản Phẩm, Quà Tặng, Ưu đãi Nhân Viên             |
|                              | CrossBorder Fulfillment (Fulfill xuyên biên giới tại VN) | US                  | Fine Japan-USA — FG Care US đặt hàng, FG Care VN fulfill & giao tại VN theo hợp đồng B2B |

**Lưu ý quan trọng:**

- **Ecommerce** bao gồm tất cả kênh bán hàng trực tuyến: sàn TMDT, mạng xã hội, và website.
- **Direct Sales** (Telesale, CS): Đơn tạo thủ công bởi staff khi khách mua trực tiếp. Đây là **doanh thu bán hàng thật** (`is_sales_channel = true`). Xếp vào Offline vì không chảy qua API marketplace.
- **Internal** (Test SP, Quà Tặng, Ưu đãi NV) **không tính vào doanh thu bán hàng**.
- **CrossBorder Fulfillment** (US): Đây **không phải** cross-border ecommerce theo nghĩa ngành (bán xuyên biên giới qua platform). Đây là **fulfillment service** — FG Care US đặt hàng, FG Care VN fulfill & giao tại VN cho khách hàng cuối của FG Care US. Doanh thu ghi nhận = 0đ trên Sapo — thanh toán qua hợp đồng B2B nội bộ giữa 2 pháp nhân. **Không tính vào doanh thu bán hàng VN.**
- Mỗi nền tảng có thể có nhiều nguồn cụ thể (nhiều shop Shopee, nhiều page Facebook...).

---

### 3.2. Thương hiệu sản phẩm vs. Thương hiệu kênh

**Đây là khái niệm dễ nhầm lẫn nhất. Công ty có hai loại thương hiệu hoàn toàn khác nhau.**

#### Thương hiệu sản phẩm (Product Brand)

**Định nghĩa:** Thương hiệu gắn liền với sản phẩm — ai sản xuất, ai sở hữu sản phẩm đó.

**Ví dụ:** Fine Japan Vietnam, FG Care, Fine Care.

Mỗi sản phẩm (SKU) thuộc về **đúng một** thương hiệu sản phẩm. Thông tin này nằm trên dữ liệu sản phẩm (trường "vendor" trên Sapo).

#### Thương hiệu kênh (Channel Brand)

**Định nghĩa:** Thương hiệu mà công ty **tạo ra để xây kênh bán hàng**. Đây là "danh nghĩa" mà khách hàng nhìn thấy khi mua hàng.

**Ví dụ:**
- **JPC (Japanese Premium Collection)**: Thương hiệu kênh do công ty tạo ra. JPC có shop riêng trên Shopee, Lazada, Website, Facebook.
- **Fine Japan Vietnam**: Vừa là thương hiệu sản phẩm, vừa là thương hiệu kênh (có shop riêng).
- **The Healthy Us**: Chỉ là thương hiệu kênh, bán sản phẩm từ nhiều thương hiệu sản phẩm khác nhau.

#### Tại sao phải phân biệt?

Một shop (kênh) có thể bán sản phẩm của **nhiều thương hiệu sản phẩm**:

```
Shop "JPC OFFICIAL" trên Shopee         (Thương hiệu kênh: JPC)
  ├── Bán sản phẩm Fine Japan           (Thương hiệu SP: Fine Japan)
  ├── Bán sản phẩm FG Care              (Thương hiệu SP: FG Care)
  └── Bán sản phẩm khác...              (Thương hiệu SP: khác)
```

Nếu trộn lẫn hai khái niệm, khi hỏi "doanh thu Fine Japan bao nhiêu?" sẽ không biết đang hỏi:

- **(A)** Tổng doanh thu **sản phẩm** Fine Japan, bất kể bán ở shop nào? (kể cả bán trên shop JPC)
- **(B)** Tổng doanh thu **các kênh** mang tên Fine Japan? (chỉ shop Fine Japan Vietnam, không tính shop JPC)

**Hai con số này khác nhau.** Hệ thống phân loại cho phép trả lời cả hai:

| Câu hỏi                                     | Cách lọc                                                        |
| --------------------------------------------- | ----------------------------------------------------------------- |
| (A) Doanh thu SP Fine Japan ở mọi kênh     | Thương hiệu sản phẩm = "Fine Japan Vietnam"                  |
| (B) Doanh thu các kênh Fine Japan           | Thương hiệu kênh = "Fine Japan Vietnam"                       |
| JPC bán bao nhiêu SP Fine Japan?            | Thương hiệu kênh = "JPC" AND Thương hiệu SP = "Fine Japan" |
| SP Fine Japan bán mạnh nhất ở kênh nào? | Thương hiệu SP = "Fine Japan" + gom theo Thương hiệu kênh  |

#### Bảng tham chiếu thương hiệu

| Tên               | Là TH sản phẩm? | Là TH kênh? | Ghi chú                                 |
| ------------------ | :-----------: | :-----------: | --------------------------------------- |
| Fine Japan Vietnam | ✓           | ✓           | Vừa sản xuất, vừa có kênh riêng           |
| FG Care            | ✓           | ✓           | Vừa sản xuất, vừa có kênh riêng           |
| Fine Care          | ✓           | ✓           | Vừa sản xuất, vừa có kênh riêng           |
| JPC                | ✗           | ✓           | Chỉ là thương hiệu kênh, không sản xuất |
| The Healthy Us     | ✗           | ✓           | Chỉ là thương hiệu kênh, không sản xuất |
| Fine World Group   | ✗           | ✓           | Thương hiệu công ty mẹ                      |

---

### 3.3. Chi nhánh — "Ai xử lý?"

Chi nhánh là đơn vị vật lý chịu trách nhiệm thực hiện đơn hàng (lưu kho, đóng gói, giao hàng, hoặc bán tại quầy).

| Chi nhánh        | Ma  | Ghi chú              |
| ----------------- | --- | --------------------- |
| 16 Trương Dinh  | VVT | Trụ sở / kho chính |
| Hậu Giang        | HG  |                       |
| MM Market An Phú | MMA |                       |
| TheHealthyUs      | HUS |                       |
| ShowroomVVT       | ST  |                       |

**Lưu ý:** Chi nhánh liên quan đến **vận hành**, không liên quan đến kênh bán. Một đơn hàng từ Shopee có thể được xử lý bởi bất kỳ chi nhánh nào.

---

### 3.4. Team — "Ai sở hữu doanh số?"

**Định nghĩa:** Team là đơn vị tổ chức bán hàng chịu trách nhiệm doanh số trên một cụm kênh/nguồn. Khác với chi nhánh (vận hành vật lý), team phản ánh **cơ cấu sales** — ai chịu KPI, ai ăn commission.

**Ràng buộc thiết kế cho FG Care (theo yêu cầu business, không phải chuẩn ngành):**
- **Exclusivity:** 1 source/user = 1 team, không chia tỷ lệ, không tranh giữa các team.
- **Team tổng = Σ doanh số thành viên**, bất kể kênh (user bán chéo kênh).

**Nguyên tắc kỹ thuật (chuẩn dimensional modeling):**
- **Orthogonal với channel:** team là chiều độc lập, không thay thế `channel_category` — đảm bảo star schema không bị denormalize.

> **Lưu ý:** 2 ràng buộc đầu là lựa chọn cụ thể của FG Care, **không phải best practice ngành**. Xem mục *"Các mô hình attribution phổ biến"* bên dưới để hiểu các cách chia khác mà ngành đang dùng — nếu ràng buộc FG Care thay đổi, có thể chuyển sang mô hình khác.

#### Các mô hình attribution phổ biến (industry best practices)

Trong thực tế công nghiệp (retail, ecommerce, B2B sales), có 6 nhóm mô hình attribution chính. Mỗi mô hình phù hợp với bối cảnh khác nhau.

**Nhóm 1 — Single-owner attribution (1 người ăn số)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Last-touch / Closer-based** | Người chốt đơn cuối cùng ăn 100% | Retail, ecom chat-to-close, telesale (phổ biến nhất cho FG Care) |
| **First-touch / Creator-based** | Người tạo lead đầu tiên ăn 100% | B2B dài hạn, khi nuôi lead quan trọng hơn chốt |
| **Order-creator** (Sapo default) | Người tạo đơn trong hệ thống ăn 100% | Đơn giản nhất, nhưng sai khi creator ≠ seller |

→ Phổ biến trong retail/ecom. **FG Care nên dùng Last-touch/Closer-based** cho user-based attribution.

**Nhóm 2 — Split / Shared attribution (2+ người chia credit)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Equal split** | Chia đều, vd SDR 50% + AE 50% | SaaS B2B, có quy trình lead qualification rõ |
| **Weighted split** | Tỷ lệ cố định, vd SDR 30% + AE 70% | Khi đóng góp không cân nhau |
| **Role-based split** | Theo vai trò trong deal (Marketing + SDR + AE + CS) | Enterprise B2B, deal cycle dài |

→ Phức tạp hơn, cần policy rõ. Phù hợp khi có **pipeline rõ ràng** (lead → qualified → closed). Ít phổ biến trong retail B2C.

**Nhóm 3 — Multi-touch attribution (marketing analytics)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Linear** | Chia đều cho mọi touchpoint | Khi không biết touch nào quan trọng hơn |
| **Time-decay** | Touch gần close có trọng số cao hơn | Sales cycle ngắn-trung bình |
| **U-shape (position-based)** | 40% first-touch + 40% last-touch + 20% middle | Khi acquisition và close đều quan trọng |
| **Data-driven (Markov / Shapley)** | Algorithm học từ data lịch sử | Có đủ data, có data team mạnh |

→ Chủ yếu dùng cho **marketing ROI analysis** (ads, channels), không dùng cho commission cá nhân. FG Care nên áp dụng nếu cần phân tích hiệu quả Marketing khi có đa kênh touchpoint.

**Nhóm 4 — Pooled / Team-based attribution (chia theo team, không cá nhân)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Team quota** | Cả team share 1 quota, thưởng chia đều hoặc theo đóng góp | POS retail, team CS ca kíp, team không tracker cá nhân được |
| **Shift-based** | Doanh số trong ca → chia đều cho nhân viên ca đó | Quầy bán, call center |

→ Phù hợp khi **không tracker được cá nhân** (shared account, POS quầy, CS ca kíp). Là **fallback tốt** cho FG Care khi không có `seller_user_id`.

**Nhóm 5 — Account / Territory-based (theo khách hoặc vùng)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Account ownership** | 1 nhân viên sở hữu 1 account, mọi đơn của account đó → của họ | B2B, KAM (Key Account Manager), đại lý |
| **Territory-based** | Chia theo vùng địa lý / segment khách | Sales field, FMCG truyền thống |

→ Phù hợp cho **Team B2B** của FG Care (Đại Lý) — 1 KAM sở hữu 1 cụm đại lý, mọi đơn của cụm đó → của KAM.

**Nhóm 6 — Channel / Source-based (theo nguồn đơn, không theo người)**

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Pure channel** | Doanh số kênh X → Team quản kênh X | Khi không có user, đơn auto (marketplace sync) |
| **Hybrid user-then-channel** | User nếu có, fallback channel | Thực tế nhất cho FG Care |

→ Đơn giản nhất, không cần data user. **Khuyến nghị FG Care dùng Hybrid (user-then-channel)** để tận dụng data user khi có, fallback channel khi không.

#### Bảng so sánh nhanh — chọn mô hình nào?

| Bối cảnh FG Care | Mô hình khuyến nghị | Lý do |
|-----------------|---------------------|-------|
| Team Marketplace (Shopee, Lazada auto-sync) | **Channel-based (Nhóm 6)** | Không có user thật |
| Team Social (FB, Zalo) — chat chốt đơn | **Last-touch / Closer-based (Nhóm 1)** | Có user chốt rõ ràng |
| Team CS/Telesale | **Last-touch + Shift-based fallback (1 + 4)** | Có user nhưng ca kíp share account |
| Team B2B Đại Lý | **Account ownership (Nhóm 5)** | KAM sở hữu cụm đại lý |
| Team Retail POS | **Pooled/Team-based (Nhóm 4)** | Staff quầy dùng chung account |
| Team Web DTC | **Channel-based (Nhóm 6)** | Khách tự đặt, không có seller |
| Marketing ROI analysis | **Multi-touch (Nhóm 3)** | Cần hiểu đóng góp từng touchpoint |

**Kết luận:** Không có 1 mô hình duy nhất áp cho toàn công ty. **FG Care nên dùng hybrid đa mô hình** theo từng team, với source-based (Nhóm 6) làm default fallback khi thiếu data user.

#### So sánh với ràng buộc FG Care hiện tại

Ràng buộc FG Care (exclusivity + Σ user) **tương thích với**:
- Nhóm 1 (Single-owner) ✓
- Nhóm 4 (Team-based) ✓
- Nhóm 5 (Account/Territory) ✓
- Nhóm 6 (Channel-based) ✓

Ràng buộc FG Care **xung đột với**:
- Nhóm 2 (Split) ✗ — vì "không chia tỷ lệ"
- Nhóm 3 (Multi-touch) ✗ — vì "không chia tỷ lệ"

→ Nếu tương lai FG Care muốn đo đóng góp của Marketing, SDR, Closer riêng → **phải nới lỏng ràng buộc exclusivity** để cho phép split/multi-touch.

#### Các mô hình phân team phổ biến (kinh nghiệm thực tế)

**Mô hình 1 — Channel-based (phổ biến nhất, khuyến nghị cho FG Care giai đoạn đầu)**

Mỗi team sở hữu 1 cụm kênh có đặc thù vận hành giống nhau.

| Team | Nguồn quản lý | Lý do nhóm chung |
|------|---------------|------------------|
| Team Marketplace | Shopee, Lazada, Tiki, TikTok Shop, Sendo, Grab | Đấu giá, flash sale, ads sàn, KPI GMV |
| Team Social | Facebook, Zalo, Instagram | Content, chat chốt đơn, KOL/KOC |
| Team Web / DTC | Web, WebOrder | SEO, ads Google/Meta, email |
| Team B2B | Đại Lý, Chợ sỉ | Sales field, hợp đồng, công nợ |
| Team Retail | POS các chi nhánh, Showroom | Vận hành quầy, staff cửa hàng |
| Team Direct Sales | Telesale, CS | Inbound/outbound, chăm khách cũ |

→ **Ưu:** rõ trách nhiệm, KPI dễ set, triển khai nhanh (chỉ cần mapping source→team trong seed). **Nhược:** user bán chéo kênh khó phân bổ chính xác.

**Mô hình 2 — Brand-based**

Mỗi team quản toàn bộ multi-channel của 1 thương hiệu kênh.

| Team | Nguồn quản lý |
|------|---------------|
| Team JPC | Shopee-JPC, Lazada-JPC, Web-JPC, FB-JPC |
| Team Fine Japan | Shopee-FineJapan, Lazada-FineJapan, FB-FineJapan |
| Team The Healthy Us | All kênh THU |

→ **Ưu:** đồng bộ branding, 1 team lo full funnel 1 brand. **Nhược:** cần sales đa kênh giỏi, khó scale khi 1 brand quá lớn.

**Mô hình 3 — Khu vực / Segment khách**

| Team | Phạm vi |
|------|---------|
| Team Miền Bắc / Nam / Trung | Theo vùng địa lý |
| Team B2C / Team B2B / Team VIP | Theo phân khúc khách |
| Team Domestic / Team Export | Theo thị trường |

→ Phù hợp khi kênh B2B offline mạnh (FMCG truyền thống).

**Mô hình 4 — Hybrid (Matrix)**

2 chiều đồng thời: **Brand × Channel-type**. Mỗi đơn có 2 team owner (brand team + channel team). Cần cơ chế ưu tiên khi tính commission (thường brand team ăn số, channel team ăn performance).

→ Phổ biến ở công ty trưởng thành có P&L riêng theo brand.

#### Tiêu chí thiết kế

| Tiêu chí | Quy tắc |
|---------|---------|
| **Exclusivity** | 1 source/user → 1 team duy nhất tại mỗi thời điểm |
| **Attribution** | User-first (theo `seller_user_id`), fallback source→team cho đơn auto |
| **SCD2 membership** | Ràng buộc `effective_from`/`effective_to` trong `ref_user_teams` — user chuyển team không được làm sai lệch báo cáo lịch sử |
| **Scope** | Chỉ gán team cho `is_sales_channel = true`. Internal (Test, Quà Tặng, NV) và CrossBorder Fulfillment (US) = NULL |
| **Returns** | Gán theo team **tại thời điểm order gốc**, không theo team hiện tại |

#### Hai cách attribution & tradeoff

**Cách A — Source-based (Channel → Team):** map mỗi source vào 1 team qua `ref_order_sources.csv` (thêm cột `default_team`).
- Ưu: đơn giản, không phụ thuộc data user, chạy được ngay.
- Nhược: không phân biệt được đóng góp cá nhân, user bán chéo kênh bị sai attribution.

**Cách B — User-based (Σ doanh số nhân viên):** mỗi đơn có `seller_user_id` → map user→team qua `ref_user_teams.csv`.
- Ưu: chính xác theo bản chất "người bán chịu KPI".
- Nhược: đòi hỏi data hygiene cao (xem vấn đề bên dưới).

**Khuyến nghị:** **Hybrid A+B** — ưu tiên user, fallback source khi user NULL/system.

#### Thảo luận sâu: Team = Σ doanh số n nhân viên — có vấn đề gì?

Mô hình đơn giản "team gồm n nhân viên, doanh số team = tổng doanh số của từng nhân viên" nghe hợp lý nhưng trong thực tế vận hành phát sinh 8 nhóm vấn đề sau. Mỗi vấn đề đều có thể làm tổng team ≠ tổng thực tế.

**Vấn đề 1 — Phụ thuộc chất lượng dữ liệu `created_by` / `assigned_to`**

- Đơn marketplace auto-sync (Shopee, Lazada, Tiki) thường không có user thật — Sapo gán `system` hoặc admin mặc định → không attribute được cho ai.
- Đơn cũ trước khi quy trình gán user chặt chẽ → NULL hàng loạt.
- Staff dùng chung account (phổ biến ở team CS ca kíp) → 1 user ID nhưng thực tế 3-4 người.

→ Nếu `created_by` không sạch, tổng team ≠ tổng thực tế, có gap "Unassigned" khó giải thích. **FG Care cần kiểm tra % đơn có `created_by` là user thật trước khi quyết định dùng user-based.**

**Vấn đề 2 — Membership thay đổi theo thời gian (SCD problem)**

- User chuyển team giữa kỳ → doanh số tháng trước thuộc team cũ hay mới?
- User nghỉ việc → orders cũ của họ "mồ côi", tổng team giảm nếu dùng current membership.
- Team tách/gộp/đổi tên → báo cáo YoY bị đứt gãy.

→ **Bắt buộc SCD2** (`effective_from`/`effective_to` trên `ref_user_teams`). Không được dùng snapshot hiện tại để tính lịch sử. Khi tính team cho 1 order: tra user_id + order_date → effective team tại thời điểm đó.

**Vấn đề 3 — Attribution ambiguity: ai "sở hữu" đơn?**

Một đơn có thể đi qua nhiều tay:
- **Marketing** chạy ads kéo khách vào → **CS** tư vấn chốt → **Warehouse staff** tạo đơn Sapo.
- Chỉ tính theo `created_by` = warehouse staff ăn hết doanh số, CS và Marketing không có gì.
- Đơn **re-order** khách cũ: user nào xứng đáng? Người chốt đơn đầu tiên hay người xử lý đơn này?

→ Sales commission và BI metrics thường xung đột. Cần **policy rõ** (business quyết định): attribution theo ai — creator, closer, owner, hay first-touch. Khuyến nghị tách:
- `seller_user_id` — người chốt, ăn doanh số/commission
- `created_by_user_id` — người tạo đơn, chỉ là operational

**Vấn đề 4 — Cross-sell / bán hộ không phản ánh đúng**

User A (Team Social) chốt đơn qua Zalo nhưng **nhờ** user B (Team CS) tạo trên Sapo vì A đang livestream → B ăn số, A mất.

→ Với mô hình "user bán chéo kênh" mà FG Care mô tả, attribution theo `created_by` **sai bản chất**. Phải có custom field `seller_user_id` riêng, hoặc convention ghi vào note/tag đơn và parse ra.

**Vấn đề 5 — Gian lận và xung đột KPI**

- Cuối tháng user "chạy số": nhờ đồng nghiệp team khác **gán tên mình** vào đơn để đạt KPI.
- Manager tự gán user mình vào đơn của cấp dưới nghỉ việc.
- Đơn refund/hủy: user đã nhận thưởng tháng trước → claw-back có thực thi không?

→ Cần **audit log** (ai sửa `seller_user_id` khi nào) và policy rõ ràng. Không có audit → không biết số có bị "chạy" hay không.

**Vấn đề 6 — Đơn không có "người bán" thật**

- Marketplace auto-sync chiếm phần lớn GMV (Shopee, Lazada tự sync, không có nhân viên chốt).
- Website DTC self-service (khách tự đặt).
- POS đôi khi dùng 1 account quầy chung.

→ Nếu team = Σ user **thuần túy**, các đơn này rớt ra ngoài. **Team Marketplace doanh số = 0** dù chiếm 60-70% GMV. Giải pháp: **hybrid attribution** — user nếu có, fallback source→team.

**Vấn đề 7 — Đơn trả hàng / đổi hàng xuyên kỳ**

- Return xảy ra 30-60 ngày sau order, user có thể đã chuyển team hoặc nghỉ việc.
- Net revenue theo team = gross - returns, nhưng returns gán team nào?

→ Quy tắc: **gán team theo thời điểm order gốc** (matching SCD2), không theo team hiện tại của user. Return tháng 4 của đơn tháng 2 → trừ vào team tháng 2, không phải team hiện tại.

**Vấn đề 8 — Granularity & privacy**

- Team nhỏ (2 người) → dễ đoán ai đóng góp bao nhiêu khi nhìn tổng.
- Nhân viên thấy dashboard public so sánh → ảnh hưởng tâm lý.

→ Cần **row-level security** ở BI layer: manager thấy team mình, leadership thấy tổng, nhân viên thấy chính mình.

#### Tóm tắt mức độ nghiêm trọng

| # | Vấn đề | Mức độ | Có fix được không? |
|---|--------|--------|---|
| 1 | Đơn auto không có user | **Cao** | ✓ Hybrid: fallback source→team |
| 2 | SCD membership | **Cao** | ✓ Bắt buộc effective_from/to |
| 3 | Attribution ai sở hữu | **Cao** | ⚠ Cần policy business (creator vs closer) |
| 4 | Cross-sell / bán hộ | **TB** | ✓ Cần `seller_user_id` riêng |
| 5 | Gian lận KPI | **TB** | ⚠ Audit log + policy claw-back |
| 6 | Returns xuyên kỳ | **TB** | ✓ Gán theo order_date, không current |
| 7 | Shared account | **Thấp-TB** | ✓ Enforce 1 user = 1 account |
| 8 | Privacy | **Thấp** | ✓ RLS ở BI layer |

**Kết luận:** Mô hình "Σ user" về lý thuyết chính xác nhất nhưng **đòi hỏi data hygiene tốt** (user sạch, SCD2, `seller_user_id` tin cậy, audit log). Nếu FG Care chưa có quy trình này → bắt đầu bằng **source-based (Cách A)** đơn giản và đáng tin hơn; nâng cấp lên user-based (Cách B) khi các điều kiện trên được đảm bảo.

#### Sapo đã có sẵn 2 user fields — không cần custom field

Sapo order payload (`src_sapo_orders.sql:105-113`) trả về **2 trường user riêng biệt**, đúng với 2 vai trò doc đề cập:

| Doc terminology | Sapo field | Ý nghĩa nghiệp vụ | Các field phụ |
|----------------|-----------|-------------------|---------------|
| `seller_user_id` (người chốt, ăn số) | **`assignee_id`** | Nhân viên được **giao đơn** | `assignee.name`, `assignee.full_name`, `assignee.email` |
| `created_by_user_id` (người tạo, operational) | **`account_id`** | Nhân viên **tạo đơn** trên Sapo | `account.name`, `account.full_name`, `account.email` |

**Pipeline hiện tại (`std_orders.sql:30`)** coalesce 2 fields:

```sql
coalesce(assignee_id, account_id) as salesperson_id
```

→ Ưu tiên `assignee`, fallback `account`. **Mất distinction** sau std_orders → không phân biệt được closer vs creator ở lớp trên.

**Đề xuất:** giữ **cả 2 fields riêng biệt** ở std_orders và fact_orders, để BI layer chọn mô hình attribution linh hoạt.

#### Coverage thực tế trên dữ liệu FG Care

Query mẫu trên `src_sapo_orders` (2,787 đơn, 2021-05 → 2026-04, không bao gồm đơn marketplace sync qua path riêng):

| Metric | Giá trị |
|--------|---------|
| Đơn có `assignee_id` NOT NULL | **100%** |
| Đơn có `account_id` NOT NULL | **100%** |
| Đơn có `assignee_id` ≠ `account_id` | **16.58%** (462/2787) |

**Phân bố diff theo source (trích):**

| Source | Orders | `assignee ≠ account` | Ghi chú |
|--------|-------:|:---:|---------|
| **Đại Lý** | 1,058 | **40.2%** | Data entry tạo đơn, sales được assign — workflow B2B rõ ràng |
| Web | 64 | 25.0% | Có nhiều creator khác assignee |
| Other | 66 | 15.2% | Mixed |
| Pos | 42 | 2.4% | Quầy tự tạo |
| US | 1,096 | 0.6% | Auto-sync, cùng system user |
| Shopee | 319 | **0%** | Auto-sync, 1 admin (`Trà My`) làm cả 2 |
| Lazada/Tiki/Chiaki/... | ~30 | 0% | Marketplace auto-sync |
| Zalo/FaceBook*/CS/Telesale | nhỏ | 0% | Cùng user làm cả 2 |

**Đại Lý pattern mẫu (top assignee-creator pairs):**

| Assignee (người chốt) | Creator (người tạo) | Số đơn |
|----------------------|---------------------|-------:|
| Vũ Ngọc | Vũ Ngọc | 197 (tự tạo) |
| Ngoc Anh | Ngoc Anh | 154 (tự tạo) |
| **Vũ Ngọc** | **Ngoc Vu** | **95 (khác!)** |
| **Vũ Ngọc** | **Nguyễn Thị Thanh Huyền** | **73 (khác — có data entry staff)** |
| **Ngoc Anh** | **Ngoc Vu** | **92 (khác!)** |

→ Xác nhận pattern B2B thực tế: **có nhân viên chuyên tạo đơn (data entry), sau đó assign cho sales rep**. Với những đơn này, dùng `account_id` (creator) sai bản chất — phải dùng `assignee_id`.

#### Kết luận cập nhật cho FG Care

1. **FG Care sẵn sàng làm user-based attribution** cho Đại Lý/Web (data hygiene 100% ở 2 fields).
2. **Marketplace (Shopee, Lazada, Tiki, Chiaki...)** không cần user — assignee = account = system user. Dùng **source-based fallback** cho các kênh này.
3. **Hybrid attribution đề xuất:**
   ```
   seller_user_id = assignee_id (primary)
   → map qua ref_user_teams → team

   IF assignee_id = system_user_ids (Trà My, etc.)
     → fallback source_id → default_team
   ```
4. **Chưa cần thêm custom field trên Sapo** — dùng native fields.
5. **Cần xác nhận business:** liệt kê `system_user_ids` (các account chỉ dùng cho auto-sync) để logic fallback phân biệt được user thật vs system.

#### Checklist trước khi quyết định dùng user-based

- [ ] Tỷ lệ đơn có `created_by` là user thật (không phải system/admin default) > 80%
- [ ] Có cơ chế phân biệt `seller_user_id` vs `created_by_user_id`
- [ ] Mỗi nhân viên 1 account riêng (không shared)
- [ ] Có seed `ref_user_teams.csv` với SCD2
- [ ] Có policy attribution được business duyệt (creator / closer / first-touch)
- [ ] Có audit log thay đổi `seller_user_id` trên đơn
- [ ] Có quy tắc xử lý return/refund xuyên kỳ
- [ ] Đã backfill hoặc loại trừ đơn lịch sử thiếu user

Không đạt đủ các mục trên → **dùng source-based (Cách A)** cho đến khi sẵn sàng.

#### Khuyến nghị cho FG Care (Phase 1)

Dùng **Channel-based (Mô hình 1) + Source-based attribution (Cách A)** — 6 teams như bảng mẫu ở trên. Loại `is_sales_channel = false` (Internal, CrossBorder Fulfillment) khỏi phân bổ team.

**Phase 2 (khi data user sạch):** nâng cấp sang Hybrid attribution (user-first, source fallback) + thêm Brand dimension nếu cần track P&L theo brand.

#### Seed đề xuất (chưa triển khai)

- `ref_teams.csv` — danh sách team + leader + mô tả
- Thêm cột `default_team` vào `ref_order_sources.csv` — fallback attribution
- `ref_user_teams.csv` — membership với SCD2 (`user_id`, `team_id`, `effective_from`, `effective_to`) — chỉ cần khi Phase 2

---

### 3.5. Thị trường & Phân khúc khách hàng

Hai phân loại bổ sung, dùng khi cần tách riêng doanh thu theo đối tượng:

| Chiều phân loại       | Giá trị             | Áp dụng cho                                                                  |
| ------------------------ | --------------------- | ------------------------------------------------------------------------------ |
| **Thị trường**  | Domestic (Nội địa) | Hầu hết các kênh                                                           |
|                          | Export (Xuất khẩu)  | Các kênh xuất khẩu tương lai (US đã chuyển sang Internal/CrossBorder Fulfillment) |
| **Phân khúc KH** | B2C (Bán lẻ)        | Shopee, Lazada, Website, POS...                                                |
|                          | B2B (Bán sỉ)        | Đại Lý, Chợ Sỉ                                                            |

---

### 3.6. Giới hạn của Channel — Khi nào cần thêm Customer?

**Channel trả lời:** Giao dịch xảy ra ở đâu?

**Channel KHÔNG trả lời:** Bản chất giao dịch là gì? (sỉ hay lẻ)

#### Phân loại kênh theo khả năng suy luận bản chất

| Kênh | Channel → Order Nature? | Giải thích |
|------|-------------------------|------------|
| **Đại Lý, Chợ sỉ** | ✅ Đủ | `channel_format = B2B` → chắc chắn wholesale |
| **Shopee, Lazada, Tiki** | ✅ Đủ | Marketplace B2C → chắc chắn retail |
| **POS** | ✅ Đủ | Retail store → chắc chắn retail |
| **Zalo, Facebook** | ❌ Không đủ | Social = dual-purpose → có thể retail HOẶC wholesale |
| **Other** | ❌ Không đủ | Catch-all → không biết |

#### Vấn đề: Social/Other là kênh "dual-purpose"

```
Kênh Zalo
    ├── Khách lẻ nhắn mua 1 hộp     → retail
    └── Khách sỉ nhắn mua 50 hộp    → wholesale
    
    → Cùng 1 kênh, 2 bản chất khác nhau
```

Đây không phải lỗi của channel classification — mà là **bản chất của kênh Social**: ai cũng có thể nhắn tin, bất kể họ là khách lẻ hay sỉ.

#### Giải pháp: Order Nature = f(Channel, Customer)

Để xác định bản chất giao dịch, cần kết hợp **Channel** + **Customer Group**:

```sql
order_nature = CASE
  -- Channel đủ sức suy luận
  WHEN channel_format = 'B2B' THEN 'wholesale'
  WHEN channel_format IN ('Marketplace', 'Retail', 'Web') THEN 'retail_sale'
  WHEN channel_format IN ('System', 'CrossBorder Fulfillment') THEN 'internal'
  
  -- Channel dual-purpose → dựa vào Customer Group
  WHEN channel_format = 'Social' AND customer_group = 'WHOLESALE' THEN 'wholesale'
  WHEN channel_format = 'Social' THEN 'retail_sale'
  
  -- Direct (Telesale, CS) → dựa vào Customer Group
  WHEN channel_format = 'Direct' AND customer_group = 'WHOLESALE' THEN 'wholesale'
  WHEN channel_format = 'Direct' THEN 'retail_sale'
  
  ELSE 'retail_sale'
END
```

#### Tóm lại

| Dimension | Trả lời câu hỏi | Đủ một mình? |
|-----------|-----------------|--------------|
| **Channel** | Giao dịch ở đâu? | Đủ cho ~80% cases (Marketplace, B2B, Retail) |
| **Customer Group** | Khách thuộc tier nào? | Bổ sung cho ~20% còn lại (Social, Direct, Other) |
| **Order Nature** | Bản chất giao dịch? | = Channel + Customer |

> **Xem thêm:** [Customer Segmentation](./customer-segmentation.md) — Chi tiết về phân loại khách hàng và customer_group

---

## 4. Common Misunderstandings — Những nhầm lẫn phổ biến

| Nhầm lẫn | Sai | Đúng |
|---------|-----|------|
| **Ecommerce ≠ Marketplace** | "Ecommerce = chỉ bán trên Shopee/Lazada" | Ecommerce = bất kỳ kênh trực tuyến nào (Marketplace + Social + Website) |
| **channel_category ≠ channel_format** | Dùng "Marketplace" khi báo cáo tầng 1 | Tầng 1 là `channel_category` (`Online-Ecommerce`/`Offline`/`Internal`). Tầng 2 `channel_format` (Marketplace/Social/Web/...). Không lẫn. |
| **channel_brand ≠ brand_name** | "JPC là thương hiệu sản phẩm" | JPC chỉ là thương hiệu kênh. Sản phẩm trên JPC có brand từ Fine Japan, FG Care, v.v. |
| **Chi nhánh ≠ Kênh** | "POS ở Trương Dinh = kênh bán khác" | Chi nhánh là execution, kênh là where. Một shop Shopee có thể xử lý từ nhiều chi nhánh. |
| **is_sales_channel = false ≠ doanh thu = 0** | "Internal không bán hàng" | Internal là kênh nội bộ, không bán (doanh thu = 0). Direct Sales/Telesale là kênh bán thật (is_sales_channel = true) |
| **Social channel ≠ chỉ B2C** | "Zalo/Facebook = bán lẻ" | Social là dual-purpose: có cả khách lẻ và khách sỉ ẩn. Cần kết hợp `customer_group` để xác định. |
| **Discount Social ≠ promotion** | "Discount 50% trên Zalo = KM" | Có thể là giá sỉ (khách WHOLESALE) hoặc promotion (khách RETAIL). Check `customer_group` trước khi kết luận. |

---

## 5. Ví dụ kết hợp thực tế

Sức mạnh của hệ thống phân loại này nằm ở khả năng **kết hợp nhiều chiều** trong cùng một báo cáo.

### Ví dụ 1: "Shopee đang bán thương hiệu nào tốt nhất?"

> Gom nhóm: **Nền tảng** = Shopee + gom theo **Thương hiệu kênh**

| Thương hiệu kênh | Doanh thu Shopee |
| -------------------- | ---------------- |
| JPC                  | 120,000,000      |
| Fine Japan Vietnam   | 85,000,000       |
| The Healthy Us       | 45,000,000       |
| FG Care              | 30,000,000       |

### Ví dụ 2: "SP Fine Japan bán trên kênh nào nhiều nhất?"

> Lọc: **Thương hiệu SP** = Fine Japan + gom theo **Nền tảng**

| Nền tảng | Doanh thu SP Fine Japan |
| ---------- | ----------------------- |
| Shopee     | 95,000,000              |
| Lazada     | 40,000,000              |
| POS        | 35,000,000              |
| Website    | 15,000,000              |

### Ví dụ 3: "So sánh hiệu quả kênh JPC vs Fine Japan trên Marketplace"

> Lọc: **Loại kênh** = Marketplace + gom theo **Thương hiệu kênh** + **Nền tảng**

| TH kênh   | Shopee | Lazada | TikTok | Tiki |
| ---------- | ------ | ------ | ------ | ---- |
| JPC        | 120M   | 45M    | 30M    | 10M  |
| Fine Japan | 85M    | 35M    | —     | 8M   |

### Ví dụ 4: "Báo cáo tổng quát cho CEO"

> Gom nhóm: **Phân loại kênh** (tầng 1)

| Kênh     | Doanh thu   | Tỷ trọng |
| --------- | ----------- | ---------- |
| Online-Ecommerce | 450,000,000 | 72%        |
| Offline          | 175,000,000 | 28%        |

---

## 6. Quick Reference — Một trang để in/screenshot

**Khi bạn cần báo cáo ngay:**

```
PHÂN LOẠI KÊNH (GROUP BY channel_category):
  Online-Ecommerce / Offline / Internal

LOẠI KÊNH (GROUP BY channel_format):
  Marketplace / Social / Web / Retail / B2B / Direct / System / CrossBorder Fulfillment / Other

NỀN TẢNG (GROUP BY platform):
  Shopee, Lazada, TikTok, Tiki, Facebook, Instagram, Website, POS, Wholesale, Telesale, ...

THƯƠNG HIỆU KÊnh (GROUP BY channel_brand):
  JPC / Fine Japan Vietnam / FG Care / Fine Care / The Healthy Us / Fine World Group

THƯƠNG HIỆU SẢN PHẨM (GROUP BY brand_name):
  Fine Japan Vietnam / FG Care / Fine Care / (other vendors)

CHI NHÁNH (GROUP BY branch_location_name):
  16 Trương Dinh / Hậu Giang / MM Market An Phú / TheHealthyUs / ShowroomVVT

THỊ TRƯỜNG (GROUP BY market):
  Domestic / Export

PHÂN KHÚC (GROUP BY customer_segment):
  B2C / B2B
```

**Bảng tra cứu tên cột SQL:**

| Thuật ngữ kinh doanh | Tên cột SQL | Bảng |
|----------------------|-------------|------|
| Phân loại kênh | `channel_category` | dim_channels |
| Loại kênh | `channel_format` | dim_channels |
| Nền tảng | `platform` | dim_channels |
| Thương hiệu kênh | `channel_brand` | dim_channels |
| Thương hiệu SP | `brand_name` | dim_products |
| Chi nhánh | `branch_location_name` | dim_branch_locations |

---

## 7. Known Limitations — Source Field Overloading

### Vấn đề

Sapo `source` field (và `ref_order_sources.csv`) đang trộn lẫn **5 khái niệm khác nhau** vào cùng 1 field:

| Khái niệm | Trả lời câu hỏi | Sources thuộc nhóm | Có phải Channel? |
|-----------|-----------------|-------------------|------------------|
| **Channel** | Mua Ở ĐÂU? | Shopee, Zalo, POS, Web | ✅ Đúng |
| **Customer Type** | AI mua? | Đại Lý, Chợ sỉ | ❌ Không |
| **Team/Function** | AI xử lý? | CS, Telesale | ❌ Không |
| **Order Purpose** | MỤC ĐÍCH gì? | Test SP, Quà Tặng, Ưu đãi NV | ❌ Không |
| **Business Arrangement** | LOẠI HỢP ĐỒNG? | US (CrossBorder) | ❌ Không |

### Minh họa

```
Sapo "source" field (legacy catch-all)
    │
    ├── Channel (WHERE)           → Shopee, Zalo, POS, Web
    │
    ├── Customer Type (WHO)       → Đại Lý, Chợ sỉ
    │
    ├── Team/Function (BY WHOM)   → CS, Telesale
    │
    ├── Order Purpose (WHY)       → Test SP, Quà Tặng, Ưu đãi NV
    │
    └── Business Arrangement      → US (CrossBorder Fulfillment)
```

### Thiết kế lý tưởng (không áp dụng)

Nếu thiết kế từ đầu, nên tách thành các dimension độc lập:

| Dimension | Field | Ví dụ values |
|-----------|-------|--------------|
| Channel | `channel` | Shopee, Zalo, POS, Web, Phone, Email |
| Customer Type | `customer_group` | RETAIL, WHOLESALE, PARTNER, STAFF |
| Team | `team` | Marketplace, Social, CS, B2B |
| Order Purpose | `order_purpose` | Sale, Gift, Test, Staff Benefit |
| Fulfillment Type | `fulfillment_type` | Standard, CrossBorder |

### Cách tiếp cận hiện tại

**Giữ nguyên source + bổ sung bằng các dimension khác:**

| Vấn đề | Giải pháp bổ sung |
|--------|-------------------|
| Đại Lý/Chợ sỉ là Customer Type | → Dùng `customer_group` (xem [Customer Segmentation](./customer-segmentation.md)) |
| CS/Telesale là Team | → Dùng Team dimension (xem Section 3.4) |
| Test/Quà Tặng/NV là Order Purpose | → Filter bằng `is_sales_channel = false` |
| US là Business Arrangement | → Filter bằng `is_sales_channel = false` + `channel_format = CrossBorder Fulfillment` |

### Tại sao không refactor?

1. **Data đã có** — Reports và dashboards đang chạy
2. **Các dimension bổ sung đã cover** — Customer, Team, is_sales_channel
3. **Effort cao, benefit thấp** — Breaking change không đáng

### Lưu ý khi sử dụng

- **Đừng gọi tất cả source là "channel"** — Một số là customer type, team, hoặc order purpose
- **Luôn kết hợp với dimension khác** khi cần phân tích chính xác
- **Document này gọi là "Channel Classification"** vì đó là use case chính, nhưng nhận thức rằng source field overloaded

---

---

## PHẦN B: THAM KHẢO KỸ THUẬT (CHO DATA TEAM)

---

## 7. Tổng quan kiến trúc

Hệ thống phân loại kênh bán hàng được xây dựng trên **Star Schema**. Dữ liệu bán hàng (fact) được phân tích qua nhiều chiều (dimension) độc lập.

```mermaid
erDiagram
    DIM_CHANNELS {
        string channel_key PK
        string channel_name
        string channel_category
        string channel_format
        string platform
        string channel_brand
        string market
        string customer_segment
        boolean is_sales_channel
        string source_id FK
        string location_id FK
        boolean is_active
    }
    
    DIM_PRODUCTS {
        string product_key PK
        string product_id
        string variant_id
        string sku
        string barcode
        string product_name
        string variant_name
        string brand_name
        string brand_code
        numeric last_sold_price
        timestamp last_seen_at
    }
    
    DIM_BRANCH_LOCATIONS {
        string branch_location_key PK
        string branch_location_id
        string branch_location_name
        string branch_location_code
    }
    
    FACT_SALES {
        string product_key FK
        string channel_key FK
        string branch_key FK
        date order_date
        integer quantity
        numeric revenue
        numeric discount
    }
    
    DIM_CHANNELS ||--o{ FACT_SALES : "via channel_key"
    DIM_PRODUCTS ||--o{ FACT_SALES : "via product_key"
    DIM_BRANCH_LOCATIONS ||--o{ FACT_SALES : "via branch_key"
```

---

## 8. Seed Files — Dữ liệu tham chiếu

Seed files là các file CSV chứa dữ liệu phân loại, được maintain thủ công bởi Data Team.

### 8.1. ref_order_sources.csv — Danh sách nguồn đơn hàng

**File:** `transformation/seeds/ref_order_sources.csv`

Mỗi dòng đại diện cho một nguồn đơn hàng cụ thể trong Sapo (một shop trên sàn, một page Facebook, POS, hoặc nguồn nội bộ).

**Schema đầy đủ:**

| Cột                  | Kiểu   | Bắt buộc | Mô tả                                                                                                    | Ví dụ                         |
| --------------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `id`                | string  | Co         | ID nguồn trên Sapo (ví dụ `3988158` hoặc composite `3988158_1`)                                   | `3988158_1`                   |
| `name`              | string  | Co         | Tên hiển thị đầy đủ                                                                                 | `Shopee - Fine Japan Vietnam` |
| `status`            | boolean | Co         | Nguồn còn hoạt động không                                                                            | `true`                        |
| `channel_format`    | string  | Co         | Loại kênh. Giá trị: `Marketplace`, `Social`, `Web`, `Retail`, `B2B`, `Direct`, `System`, `CrossBorder Fulfillment`, `Other` | `Marketplace`                 |
| `platform`          | string  | Co         | Nền tảng cụ thể                                                                                              | `Shopee`                      |
| `is_generic_source` | boolean | Co         | `true` nếu nguồn cần expand theo chi nhánh (hiện chỉ POS)                                          | `false`                       |
| `mapping_tag`       | string  | Khong      | Tag dùng để map đơn hàng từ Sapo vào nguồn cụ thể                                               | `Shopee_Fine Japan Vietnam`   |
| `channel_brand`     | string  | Khong      | Thương hiệu kênh sở hữu nguồn này                                                                  | `Fine Japan Vietnam`          |
| `market`            | string  | Co         | Thị trường. Giá trị: `Domestic`, `Export`                                                          | `Domestic`                    |
| `customer_segment`  | string  | Co         | Phân khúc khách hàng. Giá trị: `B2C`, `B2B`                                                       | `B2C`                         |

**Quy tắc channel_format:**

| Giá trị channel_format | Ý nghĩa                                  | Thuộc channel_category |
| ------------------------ | ---------------------------------------- | ---------------------- |
| `Marketplace`            | Sàn thương mại điện tử                 | Online-Ecommerce       |
| `Social`                 | Mạng xã hội (Social Commerce)          | Online-Ecommerce       |
| `Web`                    | Website công ty (DTC)                 | Online-Ecommerce       |
| `Retail`                 | Cửa hàng vật lý                        | Offline                |
| `B2B`                    | Bán sỉ, đại lý                        | Offline                |
| `Direct`                 | Direct Sales — Telesale, CS (đơn tạo thủ công, khách mua thật) | Offline                |
| `System`                 | Nội bộ (Test SP, Quà Tặng, Ưu đãi NV) | Internal               |
| `CrossBorder Fulfillment`| Fulfill tại VN cho đơn của FG Care US (không phải cross-border ecom) | Internal               |
| `Other`                  | Khác (không xác định)                 | Internal               |

**Quy tắc is_generic_source:**

- `false` (mặc định): Nguồn map 1-1 → 1 channel.
- `true`: Nguồn expand qua chi nhánh (cross-join với `ref_branch_locations`). Chỉ áp dụng cho POS.

**Ví dụ dữ liệu:**

```csv
id,name,status,channel_format,is_generic_source,platform,mapping_tag,channel_brand,market,customer_segment
3988158_1,Shopee - Fine Japan Vietnam,true,Marketplace,false,Shopee,"Shopee_Fine Japan Vietnam",Fine Japan Vietnam,Domestic,B2C
3988158_4,Shopee - JPC OFFICIAL,true,Marketplace,false,Shopee,Shopee_JPC OFFICIAL,JPC,Domestic,B2C
3988155_2,Lazada - JPC SHOP,true,Marketplace,false,Lazada,Lazada_JPC SHOP,JPC,Domestic,B2C
3988153,Facebook,true,Social,false,Facebook,,,Domestic,B2C
3988152,Web,true,Web,false,Website,,,Domestic,B2C
3988157,Pos,true,Retail,true,POS,,,Domestic,B2C
4164989,Đại Lý,false,B2B,false,Wholesale,,,Domestic,B2B
4110169,US,false,CrossBorder Fulfillment,false,US,,,Export,B2B
4517138,Telesale,false,Direct,false,Direct,,,Domestic,B2C
```

### 8.2. ref_brands.csv — Chuẩn hóa vendor

**File:** `transformation/seeds/ref_brands.csv`

Bảng mapping để chuẩn hóa giá trị `vendor` trên Sapo thành tên thương hiệu sản phẩm thống nhất.

**Schema:**

| Cột           | Kiểu  | Mô tả                                      | Ví dụ                |
| -------------- | ------ | ------------------------------------------- | -------------------- |
| `vendor_raw`  | string | Giá trị vendor gốc trên Sapo (khớp chính xác) | `Fine Japan`         |
| `brand_name`  | string | Tên thương hiệu sản phẩm chuẩn              | `Fine Japan Vietnam` |
| `brand_code`  | string | Mã viết tắt                                | `FJV`                |

**Ví dụ dữ liệu:**

```csv
vendor_raw,brand_name,brand_code
Fine Japan,Fine Japan Vietnam,FJV
Fine Japan Vietnam,Fine Japan Vietnam,FJV
FINE JAPAN,Fine Japan Vietnam,FJV
JPC,JPC,JPC
FG Care,FG Care,FGC
FG CARE,FG Care,FGC
The Healthy Us,The Healthy Us,THU
Fine Care,Fine Care,FC
```

**Lưu ý:** Nếu một vendor trên Sapo không có trong bảng này, `dim_products` sẽ giữ nguyên giá trị vendor gốc làm `brand_name` với `brand_code = NULL`.

### 8.3. ref_branch_locations.csv — Danh sách chi nhánh

**File:** `transformation/seeds/ref_branch_locations.csv`

| Cột     | Kiểu   | Mô tả                  | Ví dụ                |
| -------- | ------- | ---------------------- | -------------------- |
| `id`    | integer | ID chi nhánh trên Sapo | `68578`              |
| `code`  | string  | Mã viết tắt            | `VVT`                |
| `name`  | string  | Tên chi nhánh          | `16 Trương Định`    |

---

## 9. Dimension Models

### 9.1. dim_channels

**File:** `transformation/models/marts/core/dim_channels.sql`

**Nguồn:** `ref_order_sources`, `ref_branch_locations`

**Logic xây dựng:**

1. Lấy specific sources (`is_generic_source = false`) → mỗi source = 1 channel
2. Lấy generic sources (`is_generic_source = true`) → cross-join với branches
3. UNION ALL kết quả
4. Derive `channel_category` từ `channel_format` và `is_sales_channel = channel_format NOT IN ('System', 'CrossBorder')`
5. Generate surrogate key từ source_id + location_id
6. Thêm Unknown Member

**Output schema:**

Bảng `dim_channels` materialize đầy đủ **4 tầng** của hệ thống phân loại kênh (xem Phần A, Section 3.1). Mỗi dòng = 1 channel (Gian hàng / Điểm bán cụ thể), với đầy đủ attributes để GROUP BY theo bất kỳ tầng nào.

| Cột                 | Kiểu    | Null  | Tầng | Mô tả | Giá trị hợp lệ |
| ------------------- | ------- | ----- | ---- | ------------- | -------------- |
| `channel_key`       | string  | Khong | —   | Surrogate key (MD5 của `source_id` + `location_id`) | MD5 hash |
| `channel_name`      | string  | Khong | **4** | **Gian hàng / Điểm bán** — tên hiển thị. Map 1:1 với `order_source` Sapo | `Shopee - JPC OFFICIAL`, `POS - Trương Dinh`, `Facebook`, `Đại Lý`... |
| `channel_code`      | string  | Khong | 4   | Mã viết tắt | |
| `channel_category`  | string  | Khong | **1** | **Phân loại kênh** (Channel Category) | `Online-Ecommerce`, `Offline`, `Internal` |
| `channel_format`    | string  | Khong | **2** | **Hình thức kênh** (Channel Format) — renamed từ `platform_group` | `Marketplace`, `Social`, `Web`, `Retail`, `B2B`, `Direct`, `System`, `CrossBorder Fulfillment`, `Other` |
| `platform`          | string  | Khong | **3** | **Nền tảng** (Platform) | `Shopee`, `Lazada`, `TikTok`, `Tiki`, `Sendo`, `Grab`, `Facebook`, `Instagram`, `Zalo`, `Website`, `POS`, `Wholesale`, `Direct`, `System`, `US`, `Other` |
| `channel_brand`     | string  | Co    | —   | Thương hiệu kênh (Channel Brand) — khác thương hiệu sản phẩm | `JPC`, `Fine Japan Vietnam`, `FG Care`, `The Healthy Us`, `Fine World Group`, NULL |
| `market`            | string  | Khong | —   | Thị trường (Market) | `Domestic`, `Export` |
| `customer_segment`  | string  | Khong | —   | Phân khúc khách hàng (Customer Segment) | `B2C`, `B2B` |
| `is_sales_channel`  | boolean | Khong | —   | `true` = kênh bán hàng thật (tính vào doanh thu). `false` = Internal (System) + CrossBorder Fulfillment | true/false |
| `source_id`         | string  | Co    | —   | FK về `ref_order_sources` (= `order_source.id` của Sapo) | |
| `location_id`       | string  | Co    | —   | FK về `ref_branch_locations` (chỉ có giá trị khi `is_generic_source=true`, e.g. POS expand theo chi nhánh) | |
| `is_active`         | boolean | Khong | —   | Nguồn còn hoạt động trên Sapo | true/false |

**Cross-reference tầng ↔ cột:**

| Tầng hệ thống phân loại | Cột trong `dim_channels` | Dùng để GROUP BY |
|-------------------------|--------------------------|------------------|
| Tầng 1: Channel Category (Phân loại kênh) | `channel_category` | Doanh thu Online vs Offline vs Internal |
| Tầng 2: Channel Format (Hình thức kênh) | `channel_format` | Doanh thu Marketplace vs Social vs Web vs Retail vs B2B... |
| Tầng 3: Platform (Nền tảng) | `platform` | Doanh thu từng platform (Shopee, Lazada, Facebook...) |
| Tầng 4: Storefront / Outlet (Gian hàng / Điểm bán) | `channel_name` (hoặc `source_id`) | Doanh thu từng shop/điểm bán cụ thể |

**Các chiều phụ (không thuộc 4 tầng kênh):**

| Chiều phân loại | Cột | Dùng để GROUP BY |
|----------------|-----|------------------|
| Thương hiệu kênh | `channel_brand` | So sánh JPC vs Fine Japan vs THU (ở cấp channel brand, không phải product brand) |
| Thị trường | `market` | Domestic vs Export |
| Phân khúc KH | `customer_segment` | B2C vs B2B |

**Lưu ý quan trọng về `is_sales_channel`:**

- Chỉ các dòng có `is_sales_channel = true` nên vào báo cáo doanh thu bán hàng.
- `is_sales_channel = false` khi `channel_format IN ('System', 'CrossBorder Fulfillment')` — bao gồm Internal (Test SP, Quà Tặng, Ưu đãi NV) và CrossBorder Fulfillment (US — fulfill tại VN cho đơn FG Care US, không phải cross-border ecom).
- Team attribution (xem Section 3.4) cũng chỉ áp cho `is_sales_channel = true`.

### 9.2. dim_products

**File:** `transformation/models/marts/core/dim_products.sql`

**Nguồn:** `std_order_items`, `ref_brands`

**Logic xây dựng:**

1. Lấy order items có `product_id NOT NULL`
2. `ROW_NUMBER() PARTITION BY product_id, variant_id` → bản ghi mới nhất ("Last Record Wins")
3. `LEFT JOIN ref_brands` → map vendor sang brand_name chuẩn hóa
4. Generate surrogate key
5. Thêm Unknown Member

**Output schema:**

| Cột                | Kiểu      | Null  | Mô tả                            |
| ------------------- | --------- | ----- | -------------------------------- |
| `product_key`       | string    | Khong | Surrogate key (MD5)             |
| `product_id`        | string    | Khong | ID sản phẩm trên Sapo           |
| `variant_id`        | string    | Co    | ID biến thể                     |
| `sku`               | string    | Co    | Mã SKU                          |
| `barcode`           | string    | Co    | Mã barcode                      |
| `product_name`      | string    | Khong | Tên sản phẩm                    |
| `variant_name`      | string    | Co    | Tên biến thể                    |
| `product_type`      | string    | Co    | Loại sản phẩm                   |
| `brand_name`        | string    | Co    | Thương hiệu SP chuẩn hóa       |
| `brand_code`        | string    | Co    | Mã TH viết tắt                  |
| `unit`              | string    | Co    | Đơn vị                          |
| `weight_grams`      | numeric   | Co    | Trọng lượng (gram)              |
| `last_sold_price`   | numeric   | Co    | Giá bán gần nhất                |
| `last_seen_at`      | timestamp | Co    | Lần cuối xuất hiện trong đơn    |

### 9.3. dim_branch_locations

**File:** `transformation/models/marts/core/dim_branch_location.sql`

| Cột                     | Kiểu  | Mô tả             |
| ----------------------- | ----- | ----------------- |
| `branch_location_key`   | string | Surrogate key (MD5) |
| `branch_location_id`    | string | ID trên Sapo      |
| `branch_location_name`  | string | Tên chi nhánh     |
| `branch_location_code`  | string | Mã viết tắt       |

---

## 10. Fact Tables

Các bảng fact không cần sửa đổi. Chúng đã có sẵn các foreign key cần thiết:

| Fact Table               | channel_key | product_key | branch_key | Ghi chú                              |
| ----------------------- | ----------- | ----------- | ---------- | ------------------------------------ |
| `fact_orders`           | Co          | Khong       | Co         | Grain: 1 đơn hàng                   |
| `fact_sales`            | Co          | Co          | Co         | Grain: 1 dòng sản phẩm trong đơn |
| `fact_marketing_spend`  | Co          | Khong       | Khong      | Grain: chi phí theo kênh/ngày      |
| `fact_targets`          | Co          | Khong       | Khong      | Grain: chỉ tiêu theo kênh/kỳ       |

**Lưu ý:** Báo cáo theo **thương hiệu sản phẩm** chỉ khả dụng trên `fact_sales` (có `product_key`), không khả dụng trên `fact_orders`.

---

## 11. Quy trình vận hành

### Khi thêm nguồn đơn hàng mới

1. Tạo nguồn đơn hàng trên Sapo
2. Thêm 1 dòng vào `ref_order_sources.csv`
3. Chạy `dbt build --select ref_order_sources+ `
4. Kiểm tra nguồn mới xuất hiện đúng trong `dim_channels`

### Khi phát hiện vendor mới

1. Query `dim_products` tìm `brand_code = NULL`
2. Thêm mapping vào `ref_brands.csv`
3. Chạy `dbt build --select ref_brands dim_products`

### Khi thay đổi cơ cấu tổ chức

- **Thêm chi nhánh:** Thêm dòng vào `ref_branch_locations.csv`. POS channels tự động expand.
- **Đổi team:** Không ảnh hưởng data model. Hiện derive từ `channel_format`.

---

## 12. Lưu ý về chất lượng dữ liệu

| Rủi ro                                  | Ảnh hưởng                                    | Cách phát hiện                              | Cách xử lý                                      |
| --------------------------------------- | -------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| `vendor` trống trên Sapo                | brand_name = NULL, không gom nhóm được      | Query: `WHERE brand_name IS NULL` trên dim_products | Bổ sung vendor hoặc thêm vào ref_brands |
| `vendor` ghi không nhất quán            | Cùng brand tách thành nhiều dòng           | Query: `GROUP BY brand_name` tìm tên gần giống | Thêm tất cả biến thể vào ref_brands    |
| Đơn không có source trên Sapo           | channel = Unknown                          | Query: `WHERE channel_name = 'Unknown'`     | Kiểm tra quy trình tạo đơn trên Sapo          |
| Shop mới chưa thêm vào seed             | Đơn hàng rơi vào source cha                | So sánh source IDs trong raw data vs seed   | Thêm dòng mới vào ref_order_sources            |

---

## Kết luận

> "Phân loại kênh bán hàng chuẩn hóa giúp tất cả người dùng cùng nói một ngôn ngữ, báo cáo từ dữ liệu duy nhất mà không mâu thuẫn."
