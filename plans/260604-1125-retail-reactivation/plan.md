---
title: "Retail Reactivation — Hub & Path"
created: 2026-06-04
updated: 2026-06-09
status: active
structure: pipeline-6-stage
source: ./reference/sales-slowdown-diagnosis-and-action-playbook.md
---

# Retail Reactivation — Hub & Path

> **Câu hỏi gốc:** "Bán ế — khai thác data nào để gợi ý hành động cho Marketing / CSKH / Sales?"
> Tài liệu tổ chức thành **PIPELINE 6 stage** = một path xuyên suốt để từng bước: brainstorm góc nhìn →
> khám phá/điều tra → đánh giá → tìm hướng action → lập kế hoạch → thực thi → (học, lặp lại).

---

> **🎯 Trọng tâm (2026-06-09): BÁN LẺ/B2C.** Đòn bẩy lớn nhất nằm NGOÀI hệ thống — data nói CÁI GÌ không nói TẠI SAO. Việc #1: [VOC phỏng vấn khách](./02-understand/voc-customer-interviews.md).

## Bối cảnh số (1 phút) — vì sao "ế"

- **"Sụp cấp tính" phần lớn là ẢO GIÁC ĐO LƯỜNG** (cập nhật 2026-06-09): điều tra cho thấy B2B **KHÔNG sụp** —
  cầu 2026 = **2–3× mức 2025**; "T1 278→T5 2tr" là artifact completed-only + lag hoàn tất COD ~46–78 ngày + 491tr đang chờ thu.
  → Nghi phạm "ế" thật = **cashflow** (hàng đã giao chờ thu COD) hoặc **margin**, KHÔNG phải mất cầu. [b2b](./02-understand/b2b-collapse-root-cause.md) · [cashflow](./02-understand/cashflow-collection-ar.md)
- **Vấn đề mạn tính (THẬT, bền):** **71.8% khách lẻ mua 1 lần**, M1 repeat **3–17%** (lành mạnh 30–50%).
- **Tài sản ẩn:** ~824 người nhận quà US (76% tệp liên hệ được) đã dùng sản phẩm, chưa từng tự mua.

→ Chi tiết số thật: [`02-understand/`](./02-understand/README.md) · Provenance: [`reference/`](./reference/sales-slowdown-diagnosis-and-action-playbook.md)

> **Reframe sản phẩm (2026-06-10):** hero SKU = đồ sức khỏe người lớn tuổi (cordyceps/khớp/tim mạch), KHÔNG phải collagen làm đẹp. Retention theo SẢN PHẨM: Cordyceps dính (25%), Fucoidan bẫy volume (11%), Gaba/Chondroitin gateway vàng. 🔴 bug margin H010 bán dưới giá vốn (~440M). [chi tiết](./02-understand/product-performance-assessment.md).

---

## THE PATH — 6 stage (số thứ tự = luồng đi)

```
        ┌──────────────────────── vòng lặp học (kết quả → finding mới) ────────────────────────┐
        ↓                                                                                       │
┌───────────────┐   ┌──────────────┐   ┌─────────────┐   ┌────────────────┐   ┌──────────────┐   ┌────────────┐
│01-perspectives│ → │02-understand │ → │03-evaluate  │ → │04-opportunities│ → │05-action-    │ → │06-execute  │
│ góc nhìn/lens │   │ khám phá +   │   │ đánh giá +  │   │ hướng action   │   │ plans        │   │ thực thi + │
│ (brainstorm)  │   │ điều tra     │   │ quyết định  │   │ (backlog mở)   │   │ (đã cam kết) │   │ đo lường   │
└───────────────┘   └──────────────┘   └─────────────┘   └────────────────┘   └──────────────┘   └────────────┘
   diverge ◄─────────────────────────────────────────────────────────────────────────► converge → act → learn
```

**Cách một ý tưởng chảy qua path:** một *lens* (01) sinh ra *câu hỏi điều tra* (02) hoặc *cơ hội* (04);
điều tra cho ra *finding* (02); *đánh giá* finding + chấm điểm cơ hội (03) → *promote* cơ hội thành *plan* (05);
*thực thi* + đo (06); kết quả thành *finding mới* → quay lại 02. Path không phải đường thẳng — nó là vòng học.

---

## Cách đi path này (workflow cùng nhau)

| Bạn muốn… | Vào stage | Làm gì |
|---|---|---|
| Thêm 1 góc nhìn mới | **01** | tạo file lens mới; ghi nó dẫn tới điều tra (02) / cơ hội (04) nào |
| Tìm hiểu / điều tra 1 nghi vấn | **02** | mở file điều tra (status `open`); có kết luận → `resolved` |
| Ưu tiên / chốt 1 quyết định | **03** | chấm điểm bằng `evaluation-framework`; ghi `decision-log`; quyết định mở ở `open-decisions` |
| Brainstorm nhiều hướng action | **04** | thêm opportunity card (`_TEMPLATE-opportunity.md`) — không gian mở rộng chính |
| Cam kết 1 kế hoạch | **05** | promote opportunity đã chấm điểm thành plan có owner/KPI |
| Chạy & theo dõi | **06** | ghi `execution-log`; cập nhật `kpi`; feed kết quả ngược 02 |

> Quy ước: mỗi file có `status` (resolved/open/idea/evaluating/promoted/committed/tracking) để biết nó đang ở đâu trong path.

---

## Trạng thái hiện tại theo stage

| Stage | Folder | Item chính | Status |
|---|---|---|---|
| 01 Góc nhìn | [`01-perspectives/`](./01-perspectives/README.md) | product×customer journey · lens A/B/C · retail-lenses L1–L6 | living |
| 02 Hiểu vấn đề | [`02-understand/`](./02-understand/README.md) | channel-illusion · retention-leak · segments · b2b-root-cause(✅ resolved: B2B không sụp) · demand-migration · cashflow-AR(🟠 blocked: data gap) · open-questions(🔴) · voc-interviews⭐(🔴 open) · unboxing-audit(🔴 open) · product-performance-assessment(✅ resolved: data đủ, KHÔNG cần pipeline; reframe portfolio sức khỏe người lớn tuổi) | 5 resolved · 5 open |
| 03 Đánh giá | [`03-evaluate/`](./03-evaluate/README.md) | sequencing · open-decisions · evaluation-framework · decision-log | 🟢 #1 chốt retail |
| 04 Hướng action | [`04-opportunities/`](./04-opportunities/README.md) | retention-mechanisms (4 play) · data-backlog (~21 cơ hội) · retail-offline-plays (7 card) | idea |
| 05 Kế hoạch | [`05-action-plans/`](./05-action-plans/README.md) | b2c-phases P0–P4 · action-flows · us-gift | committed/pending |
| 06 Thực thi | [`06-execute/`](./06-execute/README.md) | kpi · execution-log | tracking (chưa chạy) |
| — | [`reference/`](./reference/sales-slowdown-diagnosis-and-action-playbook.md) | playbook gốc (archive) | read-only |

---

## Quyết định gốc đang chặn → [`03-evaluate/open-decisions.md`](./03-evaluate/open-decisions.md)

> **Cập nhật 2026-06-09:** điều tra B2B RESOLVED — B2B KHÔNG sụp (artifact đo lường). Câu #2 trả lời xong; trọng tâm dời về B2C retention + cashflow ([cashflow-collection-ar](./02-understand/cashflow-collection-ar.md)).
>
> **Cashflow (2026-06-09):** ~2.7 tỷ AR B2B (84% >90 ngày, 77% vào CUZN00015+CUZN03970) — nhưng `fact_payments` rỗng nên CHƯA chắc nợ thật hay data gap. **Hành động #1: hỏi chủ/kế toán về nợ thật 2 VIP + fix pipeline thanh toán** trước khi làm gì khác.

Path đang **kẹt ở stage 03** — 3 câu cần chủ chốt trước khi cam kết plan:
1. ✅ **ĐÃ CHỐT 2026-06-09: focus = bán lẻ.** ~~"Ế" = dòng tiền tháng này hay tăng trưởng bền vững?~~ → B2B-first gác lại; toàn path ưu tiên retail ([sequencing](./03-evaluate/sequencing.md)).
2. **Đã biết nhóm sỉ 2025 vỡ vì gì chưa?** → mở khóa [b2b-collapse-root-cause](./02-understand/b2b-collapse-root-cause.md).
3. **Đội CSKH chạy bao nhiêu cuộc/ngày?** → một-mũi-nhọn vs 5 luồng song song.

Điều tra còn mở đáng làm **tuần này**: [demand-migration](./02-understand/demand-migration-recon.md) (cầu dịch sang TikTok Shop?) và [cashflow-AR](./02-understand/cashflow-collection-ar.md) (nghi phạm thật của "ế"). (b2b-root-cause đã ✅ resolved.)

---

## Lưu ý xuyên suốt

- **PII:** worklist export (tên/SĐT) chỉ lưu ngoài git.
- **DuckDB/Windows:** `fact_orders` là view không resolve trên Windows — query trực tiếp parquet `app_data/data_lake/export/marts/rolling/`.
- **Đo đúng:** luôn tách kênh lõi vs marketplace, completed-only, waterfall point-in-time (không dùng `mart_customer_status_snapshot_monthly` cho trend) — xem [06-execute/kpi.md](./06-execute/kpi.md).
