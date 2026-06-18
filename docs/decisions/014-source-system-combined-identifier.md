# ADR-014: source_system = combined `{system}_{version}` identifier

> **Trạng thái:** Accepted  
> **Ngày:** 2026-06-18  
> **Tham chiếu:** [`AGENTS.md` §source_system Convention](../../AGENTS.md), [`docs/architecture/naming-conventions.md`](../architecture/naming-conventions.md)

## Bối cảnh

Codebase ban đầu dùng hai cột riêng biệt: `source_system` (giá trị bare `'sapo'`) và `source_version` (`'v2'`/`'v3'`). Điều này gây ra:

1. **Mapping logic phải join hai cột** — version là load-bearing (Sapo v2 và v3 có schema khác nhau), không thể bỏ qua.
2. **`source_version` không tồn tại nhất quán** — nhiều model output thiếu cột này, gây lỗi binder khi downstream filter.
3. **Bare `'sapo'` mơ hồ** — không phân biệt được API v2 vs v3 vs webhook ingestion path.

## Quyết định

`source_system` là **combined identifier** = `{system}_{version}`:

| Giá trị | Ý nghĩa |
|---|---|
| `'sapo_v2'` | Sapo POS, ingestion qua API v2 |
| `'sapo_v2_mac'` | Sapo POS, MAC variant (kế toán) |
| `'sapo_v2_mac+misa'` | Sapo MAC blended với MISA COGS |
| `'sapo_v3'` | Sapo POS, ingestion qua API v3 (tương lai) |
| `'misa'` | MISA AMIS |
| `'shopee'` | Shopee marketplace |

**Không có cột `source_version` riêng.** Version được encode vào `source_system` và là load-bearing cho mọi mapping/filter logic.

## Hệ quả

- Tất cả `std_*.sql` models output `'sapo_v2' AS source_system` (không có `'v2' AS source_version`).
- Downstream models filter bằng `source_system = 'sapo_v2'` — không cần join thêm cột version.
- Khi thêm Sapo v3: chỉ thêm `source_system = 'sapo_v3'`, `std_<entity>` UNION cả hai.
- Bare `'sapo'` là **invalid** — không được dùng trong bất kỳ code, SQL, hay config nào.

## Alternatives Rejected

- **Giữ hai cột riêng (`source_system` + `source_version`)**: Tăng boilerplate, gây lỗi khi cột thiếu ở downstream, không có lợi thực tế vì version luôn cần đi kèm system name.
- **Enum riêng cho version**: Overkill cho số lượng nguồn hiện tại.
