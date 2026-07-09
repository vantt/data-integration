# Phase 03 — Sync Parse + Mutual-Exclusivity Validation + Lark Reject Notify

**Status:** NOT STARTED
**Depends on:** Phase 01 (`account_code` seed column), Phase 02 (`__REF` dropdown nguồn thật)

## Context

- `ingestion/src/gsheet_budget_sync/budget_transform.py::validate_and_build_budget_rows` hiện validate `cashflow_line` (recurring) phải khớp `ref_lines` (set từ `__REF`) — đây là nơi cần đổi sang parse `account_code` từ label có prefix.
- `orchestration/notifications/lark_client.py::send_lark_card(title, fields, color, webhook, secret)` — đã có sẵn, dùng ở `orchestration/sensors/failure_alerting.py`. Không cần hạ tầng mới.
- Pattern abort hiện tại: validate lỗi → `errors` list → caller không ghi seed (giữ seed cũ) — xem `__main__.py` (đọc thêm để xác nhận đúng chỗ gọi trước khi sửa).

## Requirements

### 1. Parse `account_code` từ label có prefix

```python
_ACCOUNT_PREFIX_RE = re.compile(r"^\s*(\d+)\s+(.+)$")

def _parse_account_prefixed_label(raw: str) -> tuple[str | None, str]:
    """Trả (account_code, display_name). account_code=None nếu raw không có prefix số
    (case one_off/reserve — free text, không parse)."""
    m = _ACCOUNT_PREFIX_RE.match(raw)
    if not m:
        return None, raw.strip()
    return m.group(1), m.group(2).strip()
```

Áp dụng: `item_type=recurring` → bắt buộc parse ra `account_code` không None, validate `account_code` tồn tại trong `dim_gl_account` (set đọc từ DuckDB, giống cách `ref_lines` được nạp hiện nay — đổi nguồn từ `__REF` text-set sang `dim_gl_account.account_code` set). Nếu không parse được hoặc code không tồn tại → error (như cũ, add vào `errors` list, abort toàn sheet).

**Lưu ý:** không dùng lại phần "tên" bóc tách được (`m.group(2)`) cho bất kỳ logic nào — theo quyết định đã chốt, tên chỉ để hiển thị, KHÔNG phải nguồn dữ liệu tin cậy (finance có thể chọn nhầm dòng có tên đúng nhưng khác code do lỗi ở __REF cũ — luôn ưu tiên account_code làm nguồn thật).

### 2. Mutual-exclusivity validation — scope `(period_month, direction)`

Sau khi build xong toàn bộ `out_rows` (đã có `account_code` mỗi dòng recurring), thêm 1 pass kiểm tra **trước khi return**:

```python
def _validate_no_prefix_collision(rows: list[dict]) -> list[str]:
    """rows: out_rows đã build (chỉ xét account_code not-null).
    Group theo (period_month, direction); trong mỗi group, nếu tồn tại 2 account_code
    A, B mà A là tiền tố string của B (hoặc ngược lại) -> lỗi.
    """
    errors = []
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        if r.get("account_code"):
            groups[(r["period_month"], r["direction"])].append(r["account_code"])
    for (period, direction), codes in groups.items():
        codes = sorted(set(codes))
        for i, a in enumerate(codes):
            for b in codes[i+1:]:
                if b.startswith(a):
                    errors.append(
                        f"Cha/con trùng trong cùng kỳ {period} ({direction}): "
                        f"'{a}' là tiền tố của '{b}' — chỉ được chọn 1 trong 2, không cả hai"
                    )
    return errors
```

**Quan trọng — KHÔNG chạy check này trên `old_kept` (rows lịch sử từ `merge.py`)**, chỉ chạy trên `new_kept`/`out_rows` của lần sync hiện tại (tháng hiện tại + tương lai) — đúng lý do đã phân tích (khó khăn #4 trong plan.md): tháng đã đóng không được xét lại, tránh reject nhầm khi finance đổi granularity giữa các tháng.

### 3. Reject → Lark notify

Khi `errors` non-empty (bao gồm cả lỗi cha/con lẫn lỗi parse account_code cũ), sau khi abort (không ghi seed) — gọi thêm:

```python
from orchestration.notifications.lark_client import send_lark_card

send_lark_card(
    title="Budget sheet sync REJECTED",
    fields={"errors": "\n".join(errors[:10]), "total_errors": str(len(errors)), "sheet": SHEET_URL},
    color="red",
)
```
Giới hạn 10 dòng lỗi đầu trong card (Lark card không nên quá dài) — full list vẫn nằm trong log/exception message như hiện tại.

### 4. Sheet-level cảnh báo (Apps Script, mirror validate)

`scripts/budget/validate-budget-sheet.gs` cần thêm hàm JS tương đương check #2 (mirror pattern đã ghi trong phase-06 gốc: "Validation mirror .gs") — chạy on-edit hoặc on-open trigger, highlight ô lỗi (background đỏ + note) thay vì chỉ báo lỗi lúc sync đêm. Không cần identical logic phức tạp — chỉ cần bắt đúng case cha/con trùng để finance thấy NGAY lúc nhập, không phải đợi tới sáng hôm sau xem Lark.

## Files

- **Modify** `ingestion/src/gsheet_budget_sync/budget_transform.py` — parse function + `_validate_no_prefix_collision`
- **Modify** `ingestion/src/gsheet_budget_sync/fetch.py` hoặc nơi nạp `ref_lines` hiện tại — đổi nguồn sang `dim_gl_account.account_code` (đọc qua `duckdb_actuals.py` pattern có sẵn)
- **Modify** nơi gọi `validate_and_build_budget_rows` (kiểm tra `__main__.py`) — thêm nhánh gọi `send_lark_card` khi abort
- **Modify** `scripts/budget/validate-budget-sheet.gs` — thêm check cha/con trùng

## Tests / verify

- Unit: `_parse_account_prefixed_label` — case có prefix, không prefix, prefix nhiều khoảng trắng.
- Unit: `_validate_no_prefix_collision` — case cha+con cùng period/direction (reject), case cha+con khác period (không reject), case cha+con khác direction cùng period (không reject), case 2 con không liên quan (không reject).
- Integration: fixture sheet có lỗi cố ý → xác nhận seed KHÔNG bị ghi đè + `send_lark_card` được gọi (mock trong test, không gửi Lark thật).

## Risks & rollback

- Đổi nguồn `ref_lines` từ `__REF` text sang `dim_gl_account.account_code` (DuckDB) — sync giờ **phụ thuộc `dbt build` đã chạy** (giống pattern `duckdb_actuals.py` đã có, không phải rủi ro mới, nhưng cần đảm bảo thứ tự: `dim_gl_account` phải tồn tại trước khi `budget_sheet_sync_asset` chạy — kiểm tra Dagster asset dependency graph).
- Rollback: revert `budget_transform.py` về validate theo `__REF` text set cũ; seed cũ (không có cột `account_code`) vẫn tương thích nếu revert luôn phase-01's seed column addition.
