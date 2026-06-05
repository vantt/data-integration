# Overhead Account-Ledger Ingestion — Design (MISA "Sổ chi tiết các tài khoản")

> Thiết kế ingest report MISA thứ 2 (account ledger → overhead 6421/6422) song song với report bán hàng (sales ledger → COGS). Chốt trước khi code. Feeds phase-04 (overhead allocation). Quyết định overhead: xem `overhead-cost-allocation-design.md` §Quyết định Q1–Q5 (TT133).

## Bối cảnh — 2 report MISA, format KHÁC NHAU HOÀN TOÀN

| | Sổ chi tiết **bán hàng** (đang có) | Sổ chi tiết **các tài khoản** (MỚI) |
|---|---|---|
| Dùng cho | COGS (tier-1) → `std_misa_sales_lines` | Overhead 6421/6422 (tier-3) → pool phase-04 |
| Format | 1 dòng / invoice-line; account là **cột** `cogs_account` | **Section-based**: marker `Tài khoản: 64211` → dòng chi tiết → `Cộng`; account là **dòng marker** (forward-fill) |
| Cột chi tiết | product/customer/cogs… | Ngày HT · Số CT · Ngày HĐ · Số HĐ · Diễn giải · **TK đối ứng** · Nợ · Có |
| Parser | `sales-ledger-parser.py` | **CHƯA CÓ** — section-based mới |

File mẫu: `app_data/input_source/So_chi_tiet_6421 6422.xlsx` — 1 sheet `SỔ CHI TIẾT CÁC TÀI KHOẢN`, ~920 dòng chi tiết, kỳ Dec-2025→Apr-2026, ΣNợ = 3,919,486,302; ΣCó = 0 (chưa kèm kết chuyển).

## 1. Folder & nhận diện file — folder-per-report-type

Convention sẵn có = mỗi nguồn 1 folder. **RENAME** cho rõ report-type (đối xứng):
```
input_source/
  shopee/
  misa-sales-ledger/     ← RENAME từ misa-amis/: Sổ bán hàng → COGS
  misa-account-ledger/   ← THÊM: Sổ tài khoản → overhead
      _archive/
```
- **Routing = folder** (robust nhất; 0 logic đoán — bài học drift Shopee). KHÔNG content-sniffing để chọn parser.
- **Guard nhận diện (defense-in-depth):** parser assert sheet-title = `SỔ CHI TIẾT CÁC TÀI KHOẢN` → drop nhầm folder thì **FAIL TO**, không corrupt im lặng.
- Sensor mới `ingest_filedrop_misa_account_ledger_sensor` → job mới → parser mới → `std_misa_account_ledger` (đúng phase-01: report-specific std, không monolithic `std_misa`).
- **Rename `misa-amis/` → `misa-sales-ledger/`:** đụng `MISA_INPUT_DIR` env (.env*), sensor `_MISA_INPUT_DIR`, default trong `run-misa-sales-file-drop.py`, archive path. Churn vừa phải, đáng vì rõ + đối xứng. *(Nested `misa/sales-ledger/`+`misa/account-ledger/` sạch hơn nhưng churn hơn — chọn flat.)*

## 2. Parser (section-based) — tái dùng pattern Shopee-Adjustment

- Scan cột A: gặp `Tài khoản: X` → set `current_account = X`; bỏ dòng title/`Loại tiền`/`Cộng`.
- Forward-fill `current_account` vào mỗi dòng chi tiết (dòng có Nợ/Có).
- Cột chuẩn hóa: `posting_date`, `voucher_no`, `invoice_date`, `invoice_no`, `description`, `offset_account` (TK đối ứng), `debit`, `credit`; + derived `account` (forward-filled), `account_group` (3 ký tự đầu: 642 → tách 6421/6422 theo prefix con: 6421x→`6421`, 6422x/6422→`6422`).
- **Reconcile checksum:** Σ(lines.debit) per account == dòng `Cộng` == marker total (Phát sinh Nợ ở dòng `Tài khoản:`). Lệch → cảnh báo to (như checksum "Tổng cộng" của sales parser).
- **Guard 911:** nếu có dòng Có với `offset_account='911'` → cảnh báo "file kèm kết chuyển cuối kỳ — kiểm tra" (xem §5).

## 3. Grain + raw retention

- **Working data = grain `(account, period_month)`** (account = leaf sâu nhất file cho: 64211, 64214, 642172, 6422…). 6422 = 1 dòng/tháng; mỗi 6421-sub 1 dòng/tháng → ~10–12 dòng/tháng. Roll-up 6421/6422 lúc nào cũng được; KHÔNG gộp sớm (keep/drop quyết ở mức sub-account).
- **Idempotency (chống trùng) NẰM Ở ROLLUP** `std_misa_account_ledger` (key `(account, month)`), KHÔNG phải ở việc giữ raw → raw bản chất là **tầng tạm, prune được**.
- **Raw line-level** (`misa_raw/account_ledger`, partition year/month): nguồn cho rollup + audit + re-classify + checksum.
  - **v1:** rollup là VIEW re-derive từ raw → tạm **GIỮ raw** (prune lúc này sẽ mất lịch sử rollup).
  - **Prune (chu kỳ đúng) = khi rollup thành persistent-incremental** (tự giữ lịch sử, không re-derive) → raw thành tầng tạm xóa được sau khi qua **horizon re-export/điều chỉnh kế toán** (kỳ còn bị re-stated tới ~chốt năm + audit). Đề xuất cửa sổ **rolling ~18 tháng / "năm tài chính trước"** — data nhỏ nên generous OK, chỉnh dễ.

## 4. Idempotency — UPSERT, KHÔNG append (kế toán xuất trùng/xuất lại)

> **Key = `(account, period_month)`. Mỗi ingest: REPLACE mọi ô (account, month) file đụng tới — last-write-wins.**

| Case | Kết quả |
|---|---|
| Xuất lại tháng đã sửa | thay ô (account, month) → bản mới thắng ✓ |
| File chồng dải ngày | tháng giao bị thay bản mới nhất ✓ (không cộng dồn) |
| Drop trùng 1 file | thay = chính nó ✓ |
| Export thiếu account | chỉ thay account có mặt; account cũ giữ ✓ |

Mạnh hơn append-only của shopee/sales (vốn double khi re-export). Triển khai: full-refresh các (account,month) partition file chứa, trước khi ghi.

> ⚠️ **Key idempotency KHÁC nhau từng nguồn — KHÔNG dùng 1 hàm chung mù:** account-ledger = `(account, month)`, 1 export/kỳ → replace-by-month an toàn. **Shopee = nhiều shop/tháng** (FINE/JPC/THU) → replace-by-month sẽ XÓA shop khác → Shopee phải key `(shop|source_file, month)`. → **Roll-out theo nhịp:** (1) làm upsert cho account-ledger trước (greenfield), verify Dagster; (2) pass RIÊNG retrofit shopee + misa-sales với key riêng + verify lại pipeline đang chạy. Không big-bang.
> 🔧 **Micro-fix tách riêng (an toàn, lợi tất cả ngay):** `write_partitioned_parquet` đặt tên file theo ts mức GIÂY → 2 file cùng giây ghi đè (bug đã gặp). Thêm discriminator (hash source_file / counter) vào filename — KHÔNG đổi semantics, fix luôn cùng đợt account-ledger.

## 5. Net cost rule — `Nợ − (Có WHERE TK đối ứng ≠ 911)`

642 là TK chi phí (bản chất Nợ): Nợ = chi phí phát sinh; Có = giảm chi phí (hoàn nhập rebate/sửa) HOẶC **kết chuyển 911 cuối kỳ** (chuyển toàn bộ số dư sang xác định KQKD).
- ⚠️ Nếu `Nợ − Có` mù mà Có gồm kết chuyển 911 → **net ≈ 0** (bẫy). → trừ hoàn-nhập thật nhưng **bỏ Có-911**.
- File hiện tại: Σ Có = 0, không 911 → `net = Nợ`. Rule vẫn viết robust phòng export sau kèm kết chuyển.

## 6. Classification seed — gsheet (kế toán/bạn sửa nhanh, versioned)

`overhead_account_classification` (pattern `gsheet_marketing_spend`):
`account · account_group · treatment · pool_id · base_metric · channel · effective_from/to · note`

`treatment` ∈ `keep_admin | keep_handling | keep_marketing | keep_selling | drop_traceable | drop_promo_count_once`.

- **Channel attribution (ads-theo-sàn):** FB/Google ads thường đa-kênh, khó gán 1 channel. → **v1: ads = `keep_marketing` → common, base `net_revenue`, cột `channel` để TRỐNG.** v2 bật channel-weighted khi map được ad-platform→channel tin cậy (YAGNI giờ). Shopee Ads (rõ kênh) có thể gán sớm nếu tách được.
- **Guard:** account xuất hiện trong data mà **chưa có** trong seed → cảnh báo "chưa phân loại" — KHÔNG tự đưa vào/ra pool mù.
- Map sơ bộ từ file mẫu (chốt cuối khi reconcile):

| Account | Diễn giải | treatment dự kiến |
|---|---|---|
| 64211 | màng PE, hộp carton | `keep_handling` (bao bì → order_count) |
| 64213 | phân bổ chi phí trả trước | điều tra (thuê/bảo hiểm?) |
| **64214** | **hàng tặng (tên SP)** | **`drop_promo_count_once`** (đã ở tier-2a Sapo-MAC) |
| 64217 / 642174 / 642176 | phí ship/hoa hồng/xử lý GD | `drop_traceable` (đã tier-2 Shopee) |
| 642172 / 642175 | quảng cáo FB / hỗ trợ QC | `keep_marketing` (**dedup vs gsheet_marketing_spend**; ads-theo-sàn→channel) |
| 6422 | internet, thuê bao, G&A | `keep_admin` (→ net_revenue) |

## 7. Count-once + reconciliation (PHASE-04, sau khi ingest xong)

- **64214 = hàng tặng, có Sapo inventory_transaction (Nợ 64214/Có 156)** = CÙNG sự kiện Sapo `trans_type=301 OUT` → đã bắt qua `promo_goods_cost` (Sapo-MAC, tier-2a). → **DROP khỏi pool**.
- **Account-ledger granularity LÀM ĐƠN GIẢN count-once:** chỉ cần EXCLUDE 64214 (và account hàng-tặng khác) trong classification seed. **KHÔNG cần** phép trừ cục `int_promo_642_monthly_total` nữa → nó hạ cấp thành **reconciliation check**.
- **Reconcile 3-chiều (phase-04, cần CẢ 2 report trong model):**
  1. Sapo-MAC `promo_goods_cost` (464M, giá trị DÙNG) vs MISA 64214 (103M) → variance định giá, surface không cộng.
  2. MISA account-ledger 64214 (103M) vs sales-ledger 642 (1.08B) → **lệch ~10×, PHẢI làm rõ** (khác kỳ/phạm vi/sub-account) trước khi tin count-once.
  3. Xác nhận account-ledger không còn sub-account hàng-tặng nào bị sót (sẽ giữ nhầm vào pool).
- Đây là **bước phân tích + model phase-04**, không thuộc ingestion. Kết quả → chốt `treatment` cuối trong seed.

## 8. Models / data flow

```
input_source/misa-account-ledger/*.xlsx
  └─[parser section-based + checksum + 911 guard]→ misa_raw/account_ledger (RAW line, retention ~12m, prune)
        └─[rollup (account,month), net=Nợ−Có≠911]→ std_misa_account_ledger  (grain account×month, upsert)
              ├─ JOIN gsheet overhead_account_classification (treatment/pool/base)
              └─[phase-04] int_order_overhead_allocation (KEEP accounts → pool → allocate; DROP traceable/promo)
reconcile (phase-04): std_misa_account_ledger ⨯ std_misa_sales_lines ⨯ int_order_promo_goods_cost
```

## Open items
1. Prune raw: idempotency ở rollup → raw prune được. **v1 giữ raw** (rollup là VIEW re-derive); **prune = v1.1** khi rollup thành persistent-incremental, cửa sổ ~18 tháng/năm-tài-chính-trước (horizon re-export). Data nhỏ → chưa gấp.
2. `64213` (phân bổ chi phí trả trước) — phân bổ cái gì? Nếu không rõ → **default `keep_admin`** (9.68M nhỏ, sai số bé); xác nhận khi tiện.
3. Reconcile 64214(103M) vs sales-642(1.08B) — **phase-04** (cần cả 2 report trong model).
4. gsheet: ai duy trì; channel-attribution ads = **v1 common (net_revenue)**, v2 mới gán channel.
5. Upsert retrofit shopee + misa-sales (key riêng) + micro-fix filename-collision — **pass RIÊNG sau account-ledger**, verify lại pipeline đang chạy. Không bundle.
