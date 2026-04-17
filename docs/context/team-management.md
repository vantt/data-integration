# Hướng dẫn Quản lý Team & Tính Doanh thu Team

> **Dành cho:** Tất cả nhân sự quản lý team, xem báo cáo doanh thu team
> **Cập nhật:** 2026-04-17
> **Bảo trì:** Data Team

## Tài liệu này trả lời những câu hỏi nào?

1. Team là gì? Khác gì với kênh và chi nhánh?
2. Có những cách nào để tính doanh thu team theo tiêu chuẩn ngành?
3. FG Care chọn cách nào và tại sao?
4. Cách cấu hình team trên Google Sheet như thế nào?
5. Nhân viên chuyển team thì doanh thu tính cho team nào?

---

## TL;DR — Nắm bắt cơ bản trong 5 phút

- **Team là đơn vị tổ chức bán hàng** — ai chịu KPI, ai ăn commission. Khác với kênh (bán ở đâu) và chi nhánh (ai đóng gói/giao hàng).
- **Có 2 cách tính doanh thu team phổ biến:** Member-based (tổng doanh thu nhân viên) và Channel-based (tổng doanh thu từ kênh team sở hữu).
- **FG Care hỗ trợ cả 2 cách** — mỗi team tự chọn cách tính phù hợp với đặc thù vận hành.
- **Cấu hình qua Google Sheet** — 2 tab: `teams` (định nghĩa team) và `team_members` (nhân viên thuộc team).
- **Lịch sử được track** — nhân viên chuyển team không làm sai lệch báo cáo quá khứ (SCD2).

---

## PHẦN A: TIÊU CHUẨN NGÀNH (INDUSTRY NORMS)

---

## 1. Team là gì?

**Định nghĩa:** Team là đơn vị tổ chức bán hàng chịu trách nhiệm doanh số. Team phản ánh **cơ cấu sales** — ai chịu KPI, ai ăn commission.

### So sánh Team với các khái niệm khác

| Khái niệm | Trả lời câu hỏi | Ví dụ |
|-----------|-----------------|-------|
| **Team** | Ai sở hữu doanh số? Ai chịu KPI? | Team Marketplace, Team Social, Team B2B |
| **Kênh (Channel)** | Bán ở đâu? | Shopee, Facebook, POS |
| **Chi nhánh (Branch)** | Ai xử lý đơn? Ai đóng gói/giao hàng? | Trương Định, Hậu Giang |

**Lưu ý quan trọng:**
- **Team ≠ Chi nhánh:** Một đơn Shopee giao từ kho Trương Định (chi nhánh) nhưng thuộc Team Marketplace (team).
- **Team ≠ Kênh:** Team là chiều độc lập với kênh. Một nhân viên có thể bán trên nhiều kênh nhưng chỉ thuộc 1 team.

---

## 2. Các phương pháp tính doanh thu Team (Industry Norms)

### 2.1. Tổng quan 6 nhóm mô hình Attribution

| Nhóm | Tên | Cách tính | Phù hợp khi |
|------|-----|-----------|-------------|
| **1** | Single-owner | 1 người ăn 100% doanh số | Retail, ecom, telesale |
| **2** | Split/Shared | 2+ người chia % credit | SaaS B2B, có pipeline rõ |
| **3** | Multi-touch | Chia theo touchpoint marketing | Marketing ROI analysis |
| **4** | Pooled/Team-based | Team share quota, không track cá nhân | POS quầy, CS ca kíp |
| **5** | Account/Territory | Theo khách hàng hoặc vùng địa lý | B2B, Key Account Management |
| **6** | Channel/Source | Theo nguồn đơn, không theo người | Marketplace auto-sync, Web DTC |

### 2.2. Chi tiết từng nhóm

#### Nhóm 1 — Single-owner Attribution (1 người ăn số)

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Last-touch / Closer-based** | Người chốt đơn cuối cùng ăn 100% | Retail, ecom chat-to-close, telesale |
| **First-touch / Creator-based** | Người tạo lead đầu tiên ăn 100% | B2B dài hạn, khi nuôi lead quan trọng hơn chốt |
| **Order-creator** | Người tạo đơn trong hệ thống ăn 100% | Đơn giản nhất, nhưng sai khi creator ≠ seller |

→ Phổ biến nhất trong retail/ecom.

#### Nhóm 2 — Split/Shared Attribution (2+ người chia credit)

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Equal split** | Chia đều, vd SDR 50% + AE 50% | SaaS B2B, có quy trình lead qualification rõ |
| **Weighted split** | Tỷ lệ cố định, vd SDR 30% + AE 70% | Khi đóng góp không cân nhau |
| **Role-based split** | Theo vai trò trong deal | Enterprise B2B, deal cycle dài |

→ Phức tạp, cần policy rõ. Ít phổ biến trong retail B2C.

#### Nhóm 3 — Multi-touch Attribution (Marketing Analytics)

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Linear** | Chia đều cho mọi touchpoint | Khi không biết touch nào quan trọng hơn |
| **Time-decay** | Touch gần close có trọng số cao hơn | Sales cycle ngắn-trung bình |
| **U-shape** | 40% first + 40% last + 20% middle | Khi acquisition và close đều quan trọng |
| **Data-driven** | Algorithm học từ data lịch sử | Có đủ data, có data team mạnh |

→ Chủ yếu cho **marketing ROI**, không dùng cho commission cá nhân.

#### Nhóm 4 — Pooled/Team-based Attribution

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Team quota** | Cả team share 1 quota | POS retail, team CS ca kíp |
| **Shift-based** | Doanh số trong ca → chia đều | Quầy bán, call center |

→ Phù hợp khi **không track được cá nhân** (shared account, POS quầy).

#### Nhóm 5 — Account/Territory-based Attribution

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Account ownership** | 1 nhân viên sở hữu 1 account | B2B, Key Account Manager |
| **Territory-based** | Chia theo vùng địa lý | Sales field, FMCG |

→ Phù hợp cho B2B — 1 KAM sở hữu 1 cụm đại lý.

#### Nhóm 6 — Channel/Source-based Attribution

| Mô hình | Cách tính | Phù hợp khi |
|---------|-----------|-------------|
| **Pure channel** | Doanh số kênh X → Team quản kênh X | Đơn auto (marketplace sync), không có user |
| **Hybrid user-then-channel** | User nếu có, fallback channel | Thực tế nhất |

→ Đơn giản nhất, không cần data user.

### 2.3. Bảng khuyến nghị theo bối cảnh

| Bối cảnh | Mô hình khuyến nghị | Lý do |
|----------|---------------------|-------|
| Marketplace (Shopee, Lazada auto-sync) | Channel-based (Nhóm 6) | Không có user thật |
| Social (FB, Zalo) — chat chốt đơn | Last-touch (Nhóm 1) | Có user chốt rõ ràng |
| CS/Telesale | Last-touch + Shift fallback (1+4) | Có user nhưng ca kíp share account |
| B2B Đại Lý | Account ownership (Nhóm 5) | KAM sở hữu cụm đại lý |
| Retail POS | Pooled/Team-based (Nhóm 4) | Staff quầy dùng chung account |
| Web DTC | Channel-based (Nhóm 6) | Khách tự đặt, không có seller |

---

## 3. Hai cách tiếp cận chính: Member-based vs Channel-based

Trong thực tế, đa số tổ chức chọn 1 trong 2 cách tiếp cận chính:

### 3.1. Member-based (Tổng doanh thu nhân viên)

```
Team Revenue = Σ Doanh thu của từng nhân viên trong team
```

**Ưu điểm:**
- Chính xác theo bản chất "người bán chịu KPI"
- Hỗ trợ nhân viên bán chéo kênh (1 người bán trên nhiều kênh)
- Công bằng khi track cá nhân

**Nhược điểm:**
- Đòi hỏi data hygiene cao (user sạch, không shared account)
- Đơn auto-sync không có user → rớt ra ngoài
- Cần track lịch sử membership (SCD2)

**Phù hợp cho:** Team Social, Team B2B, Team Direct Sales

### 3.2. Channel-based (Tổng doanh thu từ kênh)

```
Team Revenue = Σ Doanh thu từ các kênh team sở hữu
```

**Ưu điểm:**
- Đơn giản, không phụ thuộc data user
- Hoạt động tốt với đơn auto-sync (marketplace)
- Dễ triển khai

**Nhược điểm:**
- Không track được đóng góp cá nhân
- Không hỗ trợ nhân viên bán chéo kênh

**Phù hợp cho:** Team Marketplace, Team Web, Team Retail (nếu POS dùng chung account)

### 3.3. Hybrid — Kết hợp cả hai

Thực tế, **đa số tổ chức dùng hybrid** — mỗi team chọn cách tính phù hợp:

| Team | Cách tính | Lý do |
|------|-----------|-------|
| Team Marketplace | Channel-based | Đơn auto-sync, không có user thật |
| Team Social | Member-based | Có user chốt rõ ràng, bán chéo kênh |
| Team B2B | Member-based | KAM sở hữu account, cần track cá nhân |
| Team Retail | Channel-based hoặc Pooled | POS có thể dùng chung account |

---

## 4. Vấn đề thường gặp khi tính doanh thu theo Member

| # | Vấn đề | Mức độ | Giải pháp |
|---|--------|--------|-----------|
| 1 | Đơn auto không có user | Cao | Hybrid: fallback channel-based |
| 2 | Nhân viên chuyển team | Cao | SCD2: track effective_from/to |
| 3 | Ai sở hữu đơn? Creator vs Closer | Cao | Policy rõ: dùng assignee_id (closer) |
| 4 | Cross-sell / bán hộ | TB | Dùng assignee_id, không phải account_id |
| 5 | Shared account (POS, CS ca kíp) | TB | Enforce 1 user = 1 account hoặc Pooled |
| 6 | Returns xuyên kỳ | TB | Gán theo order_date gốc, không current |

---

## PHẦN B: CÁCH TỔ CHỨC CỦA FG CARE

---

## 5. Quyết định thiết kế của FG Care

### 5.1. Ràng buộc business

| Ràng buộc | Mô tả |
|-----------|-------|
| **Exclusivity** | 1 nhân viên = 1 team tại mỗi thời điểm. Không chia tỷ lệ, không tranh giữa các team. |
| **Hỗ trợ bán chéo kênh** | Nhân viên có thể bán trên nhiều kênh, doanh thu vẫn thuộc team của họ. |
| **Lịch sử chính xác** | Nhân viên chuyển team không làm sai lệch báo cáo quá khứ. |

### 5.2. Lựa chọn mô hình

FG Care chọn **Hybrid** — mỗi team tự chọn 1 trong 3 cách tính:

| `revenue_type` | Cách tính | Dùng cho |
|----------------|-----------|----------|
| `member` | Σ doanh thu nhân viên trong team | Team Social, Team B2B, Team Direct |
| `platform` | Σ doanh thu từ platform (cấp 3) | Team Marketplace (filter: Shopee, Lazada...) |
| `channel_name` | Σ doanh thu từ channel_name (cấp 4) | Team Retail (filter: POS - Trương Định...) |

### 5.3. Attribution logic

```
Nếu revenue_type = 'member':
  → Lấy seller_email từ đơn hàng
  → Map với team_members (có SCD2)
  → Doanh thu thuộc team tại thời điểm order_date

Nếu revenue_type = 'platform':
  → Lấy platform từ dim_channels
  → Filter theo revenue_filter
  → Doanh thu thuộc team sở hữu platform đó

Nếu revenue_type = 'channel_name':
  → Lấy channel_name từ dim_channels
  → Filter theo revenue_filter
  → Doanh thu thuộc team sở hữu channel đó
```

---

## 6. Cấu hình trên Google Sheet

### 6.1. Thông tin Google Sheet

- **Tên Sheet:** `Team Config`
- **Tabs:** `teams`, `team_members`

### 6.2. Tab `teams` — Định nghĩa team

| Cột | Bắt buộc | Mô tả | Ví dụ |
|-----|----------|-------|-------|
| `team_code` | ✓ | Mã team (PK, dùng trong targets) | `MKT`, `SOC`, `B2B` |
| `team_name` | ✓ | Tên hiển thị | `Marketplace`, `Social`, `Đại Lý` |
| `revenue_type` | ✓ | Cách tính doanh thu | `member`, `platform`, `channel_name` |
| `revenue_filter` | Tùy | Danh sách filter (phân cách bởi dấu phẩy) | `Shopee,Lazada,Tiki` |
| `leader_email` | | Email team leader | `leader@company.com` |
| `description` | | Mô tả | `Team quản lý các sàn TMDT` |

**Ví dụ dữ liệu:**

| team_code | team_name | revenue_type | revenue_filter | leader_email |
|-----------|-----------|--------------|----------------|--------------|
| MKT | Marketplace | platform | Shopee,Lazada,Tiki,TikTok,Sendo,Grab | mkt.lead@company.com |
| SOC | Social | member | | soc.lead@company.com |
| B2B | Đại Lý | member | | b2b.lead@company.com |
| RET | Retail | channel_name | POS - 16 Trương Định,POS - Hậu Giang | ret.lead@company.com |
| DIR | Direct Sales | member | | dir.lead@company.com |
| WEB | Web DTC | platform | Website | web.lead@company.com |

**Quy tắc `revenue_type`:**

| Giá trị | Ý nghĩa | `revenue_filter` |
|---------|---------|------------------|
| `member` | Tính theo nhân viên trong team | Để trống |
| `platform` | Filter theo cấp 3 (platform) | Danh sách platform, phân cách bởi dấu phẩy |
| `channel_name` | Filter theo cấp 4 (storefront) | Danh sách channel_name, phân cách bởi dấu phẩy |

### 6.3. Tab `team_members` — Membership với SCD2

| Cột | Bắt buộc | Mô tả | Ví dụ |
|-----|----------|-------|-------|
| `staff_email` | ✓ | Email nhân viên (khớp với Sapo) | `nv1@company.com` |
| `team_code` | ✓ | Mã team (FK về tab teams) | `SOC` |
| `effective_from` | ✓ | Ngày bắt đầu thuộc team | `2025-01-01` |
| `effective_to` | | Ngày kết thúc (trống = đang active) | `2026-03-31` |

**Ví dụ dữ liệu:**

| staff_email | team_code | effective_from | effective_to |
|-------------|-----------|----------------|--------------|
| vu.ngoc@company.com | SOC | 2025-01-01 | |
| ngoc.anh@company.com | SOC | 2025-01-01 | 2026-03-31 |
| ngoc.anh@company.com | B2B | 2026-04-01 | |
| thanh.huyen@company.com | B2B | 2025-01-01 | |
| minh.tuan@company.com | DIR | 2025-06-01 | |

**Quy tắc SCD2:**

1. **Mỗi thời điểm, 1 nhân viên chỉ thuộc 1 team** — không được overlap `effective_from`/`effective_to`
2. **`effective_to` trống = đang active**
3. **Khi nhân viên chuyển team:**
   - Đóng bản ghi cũ: điền `effective_to` = ngày cuối cùng ở team cũ
   - Tạo bản ghi mới: `effective_from` = ngày đầu tiên ở team mới, `effective_to` trống
4. **Báo cáo lịch sử:** Doanh thu tháng X của nhân viên Y → team mà Y thuộc vào tháng X

---

## 7. Ví dụ thực tế

### 7.1. Nhân viên chuyển team

**Scenario:** Ngọc Anh chuyển từ Team Social → Team B2B ngày 01/04/2026

**Trước khi chuyển:**

| staff_email | team_code | effective_from | effective_to |
|-------------|-----------|----------------|--------------|
| ngoc.anh@company.com | SOC | 2025-01-01 | |

**Sau khi chuyển:**

| staff_email | team_code | effective_from | effective_to |
|-------------|-----------|----------------|--------------|
| ngoc.anh@company.com | SOC | 2025-01-01 | 2026-03-31 |
| ngoc.anh@company.com | B2B | 2026-04-01 | |

**Kết quả báo cáo:**
- Doanh thu tháng 3/2026 của Ngọc Anh → Team Social
- Doanh thu tháng 4/2026 của Ngọc Anh → Team B2B

### 7.2. Nhân viên bán chéo kênh

**Scenario:** Vũ Ngọc (Team Social) bán trên cả Facebook và Zalo

**Cấu hình:**

| team_code | revenue_type | revenue_filter |
|-----------|--------------|----------------|
| SOC | member | |

**Kết quả:** Tất cả doanh thu của Vũ Ngọc (dù bán trên Facebook hay Zalo) đều thuộc Team Social.

### 7.3. Team tính theo platform

**Scenario:** Team Marketplace sở hữu tất cả sàn TMDT

**Cấu hình:**

| team_code | revenue_type | revenue_filter |
|-----------|--------------|----------------|
| MKT | platform | Shopee,Lazada,Tiki,TikTok,Sendo,Grab |

**Kết quả:** Tất cả doanh thu từ Shopee, Lazada, Tiki, TikTok, Sendo, Grab → Team Marketplace (bất kể ai tạo đơn).

---

## 8. Tích hợp với hệ thống hiện tại

### 8.1. Liên kết với Targets

Sheet `targets` hiện tại có cột `team_code` — có thể đặt target cho team:

| cycle_start_date | metric_code | target_value | team_code |
|------------------|-------------|--------------|-----------|
| 2026-04-01 | gmv | 500000000 | MKT |
| 2026-04-01 | gmv | 200000000 | SOC |

### 8.2. Liên kết với Channel Classification

`revenue_type = platform` và `revenue_type = channel_name` sử dụng các cột tương ứng trong `dim_channels`:

| revenue_type | Cột trong dim_channels | Tầng |
|--------------|------------------------|------|
| `platform` | `platform` | Tầng 3 |
| `channel_name` | `channel_name` | Tầng 4 |

Xem thêm: `docs/context/channel-classification.md`

### 8.3. Liên kết với Sapo

`staff_email` trong tab `team_members` phải khớp với email nhân viên trong Sapo:
- Với đơn hàng: `assignee.email` (người được giao đơn / người chốt)
- Pipeline hiện tại dùng `assignee_id` → cần map với email qua `dim_staff`

---

## 9. Checklist triển khai

- [ ] Tạo Google Sheet `Team Config` với 2 tabs: `teams`, `team_members`
- [ ] Điền danh sách team vào tab `teams`
- [ ] Điền danh sách nhân viên + team vào tab `team_members`
- [ ] Tạo ingestion pipeline (tương tự `gsheet_targets.py`)
- [ ] Tạo staging model `stg_teams.sql`, `stg_team_members.sql`
- [ ] Tạo dimension `dim_teams.sql`
- [ ] Cập nhật `fact_orders` / `fact_sales` để gán `team_key`
- [ ] Test báo cáo doanh thu theo team

---

## 10. Câu hỏi thường gặp

### Q: Một kênh có thể thuộc nhiều team không?

**A:** Không. Nếu cần scenario này (vd: POS - Trương Định vừa thuộc Team Retail vừa thuộc Team HN), hãy chuyển sang `revenue_type = member` và cho phép nhân viên bán chéo kênh.

### Q: Nếu nhân viên nghỉ việc thì sao?

**A:** Điền `effective_to` = ngày cuối cùng làm việc. Doanh thu lịch sử vẫn được giữ nguyên thuộc team cũ.

### Q: Đơn marketplace auto-sync không có user, tính cho ai?

**A:** Dùng `revenue_type = platform` cho Team Marketplace. Doanh thu tính theo kênh, không theo user.

### Q: Target đặt cho team hay cho cá nhân?

**A:** Cả hai. Sheet `targets` hỗ trợ:
- `team_code` — target cho team
- `staff_email` — target cho cá nhân
- Cả hai — target cho cá nhân trong team cụ thể

---

## Kết luận

> Team là đơn vị tổ chức bán hàng, độc lập với kênh và chi nhánh. FG Care hỗ trợ 2 cách tính doanh thu team (member-based và channel-based), cho phép mỗi team chọn cách phù hợp với đặc thù vận hành.
