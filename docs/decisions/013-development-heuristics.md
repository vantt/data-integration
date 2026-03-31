# ADR-013: Explicit > Implicit, Golden Sample heuristic

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Development Heuristics](../../AGENTS.md), [`transformation/AGENTS.md`](../../transformation/AGENTS.md)

## Bối cảnh

Dự án có nhiều convention ẩn (implicit config, macro behavior, naming patterns). Developers (cả human và AI) thường mắc lỗi vì assume config đã được inherit đúng.

## Quyết định

### 1. Explicit > Implicit

Khi không chắc config đã được inherit → **khai báo explicit**. Ví dụ:
- Mart models PHẢI có `location="{{ get_rolling_location() }}"` dù `dbt_project.yml` đã set `materialized: external`
- Không rely on default values nếu default có thể thay đổi

### 2. Golden Sample heuristic

Khi tạo/sửa model mới → **tìm model working trong cùng directory** và dùng làm reference.

```
Cần tạo src_new_entity.sql?
→ Mở src_orders.sql (đang hoạt động tốt)
→ Copy structure, thay thế entity-specific parts
→ Đảm bảo không miss config patterns
```

## Lý do

**Explicit > Implicit:**
- Đã gặp bug "View Dropped" trong serving layer vì mart thiếu `location` config
- dbt inheritance rules phức tạp và có thể thay đổi giữa versions
- Explicit config = self-documenting, dễ grep

**Golden Sample:**
- Project-specific patterns (partition structure, dedup logic, incremental window) khó nhớ hết
- Working model = proven pattern, đã pass tests
- Nhanh hơn đọc documentation + có thể miss edge cases

## Hệ quả

- Code có thể "dư" config (explicit things that would be inherited anyway) → chấp nhận được
- Cần maintain golden samples tốt (nếu golden sample có bug → bug lan rộng)
- AI agents được instruct dùng heuristic này trong AGENTS.md

## Khi nào xem xét lại

- Nếu dbt/Dagster cải thiện validation cho missing config → có thể relax explicit rule
- Nếu project có code generator → generator thay thế golden sample
