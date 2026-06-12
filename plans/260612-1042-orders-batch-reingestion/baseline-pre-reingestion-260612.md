# Baseline: Sapo Orders Raw Lake — Pre Re-ingestion
**Snapshot date:** 2026-06-12 10:51 ICT  
**Purpose:** Reference để so sánh after re-ingest batch_sync

---

## Grand Total

| | Số liệu |
|---|---|
| Distinct orders (raw lake, all methods) | **3,456** |
| Raw rows (all methods, incl. duplicates) | **24,622** |

---

## Distinct Orders by Year (cross all methods)

| Năm | Orders |
|---|---|
| 2021 | 619 |
| 2022 | 654 |
| 2023 | 470 |
| 2024 | 409 |
| 2025 | 395 |
| 2026 | 909 |
| **Tổng** | **3,456** |

---

## Distinct Orders by Channel × Year

| Năm | Channel | Orders |
|---|---|---|
| 2021 | (none) | 599 |
| 2021 | POS | 18 |
| 2021 | sapo_social | 1 |
| 2021 | Sapoweb | 1 |
| 2022 | (none) | 632 |
| 2022 | POS | 21 |
| 2022 | Lazada | 1 |
| 2023 | (none) | 462 |
| 2023 | POS | 5 |
| 2023 | Lazada | 2 |
| 2023 | Shopee | 1 |
| 2024 | (none) | 398 |
| 2024 | sapo_social | 10 |
| 2024 | POS | 1 |
| 2025 | (none) | 390 |
| 2025 | Shopee | 4 |
| 2025 | Sapoweb | 1 |
| 2026 | Shopee | 554 |
| 2026 | (none) | 320 |
| 2026 | Sapoweb | 21 |
| 2026 | sapo_social | 8 |
| 2026 | Lazada | 6 |

**Shopee tổng (all years, distinct):** 559  
⚠️ Shopee trước 2025 gần như không có — 2021–2024 chỉ có 5 đơn Shopee total.

---

## Raw Rows + Distinct per ingest_method

| ingest_method | Raw rows | Distinct orders | Coverage |
|---|---|---|---|
| batch_sync | 20,384 | 3,046 | 2021–2026 |
| history_log | 4,183 | 914 | 2025–2026 |
| text | 55 | 36 | 2026-04 only |

---

## Ingest_method × Year (distinct orders)

| Năm | batch_sync | history_log | text |
|---|---|---|---|
| 2021 | 619 | — | — |
| 2022 | 654 | — | — |
| 2023 | 470 | — | — |
| 2024 | 409 | — | — |
| 2025 | 390 | 8 | — |
| 2026 | 504 | 906 | 36 |

---

## Key Observations

1. **Shopee gap nghiêm trọng:** 2021–2024 gần như 0 Shopee. batch_sync không pull được Shopee cũ.
2. **2026 Shopee = 554** nhưng chủ yếu từ history_log (906 đơn 2026) — batch_sync chỉ đóng góp 504 đơn 2026.
3. **channel=(none) chiếm đa số 2021–2025** — likely là đơn direct/walk-in không có channel tag trong Sapo.
4. Re-ingest sẽ xác nhận: Sapo API còn giữ Shopee cũ không, hay đã purge.
