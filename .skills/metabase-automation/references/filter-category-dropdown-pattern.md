# Filter — CategoryDrop Pattern

> **Pattern name:** `CategoryDrop`
> **Dùng cho:** `string/=` dashboard filter hiển thị dưới dạng searchable dropdown (combobox), không phải text input.
> **Canonical example:** `docs/analytics-handbook/blueprints/customer_action_queue.md` (dashboard 99)

Tài liệu này mô tả đầy đủ cách implement category dropdown filter trong Metabase blueprint. Follow đúng tài liệu này — sai bất kỳ bước nào đều dẫn đến text input hoặc crash toàn dashboard khi filter active.

---

## 1. Hai chế độ filter — PHẢI chọn đúng một

| Chế độ | Tên gợi nhớ | Dashboard param | SQL syntax | UI render |
|--------|-------------|----------------|------------|-----------|
| Plain variable | **VarText** | `string/=` (không có `field_id`) | `[[AND col = {{slug}}]]` | Text input |
| Field filter | **CategoryDrop** | `string/=` + `field_id` | `[[AND {{slug}}]]` | Searchable dropdown |

**Không được trộn hai chế độ.** Trộn → crash toàn dashboard khi filter active (L104).

---

## 2. Cơ chế hoạt động của CategoryDrop

Khi có `field_id` trên dashboard parameter:

1. Deploy script tạo template tag loại `dimension` thay vì `text`
2. Metabase tạo parameter_mapping dạng `["dimension", ["template-tag", "slug"]]`
3. Khi user chọn giá trị, Metabase inject **full WHERE clause**: `col = 'value'`
4. SQL `[[AND {{slug}}]]` trở thành `AND col = 'value'` — đúng
5. SQL `[[AND col = {{slug}}]]` trở thành `AND col = col = 'value'` — **INVALID**, crash

**UI:** Metabase render searchable combobox, fetch values từ DB theo `field_id`.

---

## 3. Recipe đầy đủ (copy-paste)

### Bước 1 — Blueprint filter definition

```json metabase-filter
{
  "slug": "action_type",
  "type": "string/=",
  "field_id": 773
}
```

| Field | Bắt buộc | Mô tả |
|-------|----------|-------|
| `slug` | ✅ | Tên biến SQL: `{{action_type}}` |
| `type` | ✅ | Luôn `string/=` cho category filter |
| `field_id` | ✅ | ID của column trong Metabase — quyết định dropdown values |

### Bước 2 — SQL syntax trong mọi card dùng filter này

```sql
-- ✅ ĐÚNG — field filter syntax
WHERE 1=1
[[AND {{action_type}}]]
[[AND {{value_group}}]]

-- ✅ ĐÚNG — kết hợp hardcoded condition + field filter
WHERE action_type = 'CALL_NOW'
[[AND {{value_group}}]]

-- ❌ SAI — variable syntax (chỉ dùng khi KHÔNG có field_id)
WHERE 1=1
[[AND action_type = {{action_type}}]]   -- crash khi filter active
```

### Bước 3 — Verify sau deploy

```js
// Kiểm tra parameter_mappings — PHẢI là "dimension", không phải "variable"
const dash = await fetch('/api/dashboard/:id', {headers: h}).then(r=>r.json());
const card = dash.dashcards[0];
console.log(card.parameter_mappings[0].target[0]);
// Expected: "dimension"
// If "variable": field_id bị thiếu hoặc deploy script không pick up field_id
```

---

## 4. Cách tìm field_id

```js
// Tìm table trước
node -e "
const client = new MetabaseClient(URL, KEY);
await client.connect();
const tables = await fetch(URL + '/api/table', {headers}).then(r=>r.json());
const t = tables.find(t => t.name === '<table_name>');
console.log('Table ID:', t.id);

// Tìm field trong table
const meta = await fetch(URL + '/api/table/' + t.id + '/query_metadata', {headers}).then(r=>r.json());
meta.fields.filter(f => ['col1','col2'].includes(f.name))
  .forEach(f => console.log(f.name, '→ field_id:', f.id));
"
```

**Field_id đã biết (customer_action_queue):**

| field_id | Table | Column | Values |
|----------|-------|--------|--------|
| 773 | `mart_customer_action_queue` | `action_type` | CALL_NOW, REORDER_NUDGE, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK |
| 758 | `mart_customer_action_queue` | `value_group` | VALUE_VIP, VALUE_GOLD, VALUE_SILVER, VALUE_BRONZE |

---

## 5. Anti-patterns (KHÔNG làm)

```sql
-- ❌ Trộn field_id với variable syntax — crash toàn dashboard (L104)
-- blueprint: field_id: 773
[[AND action_type = {{action_type}}]]   -- Metabase inject: action_type = action_type = 'x'

-- ❌ Dùng field_id nhưng quên đổi SQL syntax — cùng crash như trên
-- Chỉ đổi blueprint filter, không đổi SQL → vẫn crash

-- ❌ Dùng values_source_type: "static-list" thay thế field_id — chỉ là workaround
-- UI vẫn text input dù static-list được lưu; không render dropdown trong v0.60
-- (Cách này chỉ work nếu filter KHÔNG wired tới card nào)

-- ❌ Không verify mapping type sau deploy — giả định "có field_id là xong"
-- Phải check parameter_mappings[].target[0] === "dimension"
```

---

## 6. Phân biệt CategoryDrop vs DateBound (date_range)

| | **CategoryDrop** | **DateBound** (`filter-date-range-pattern.md`) |
|-|-----------------|------------------------------------------------|
| `type` | `string/=` | `date/all-options` |
| `field_id` | ✅ bắt buộc | ✅ bắt buộc |
| SQL syntax | `[[AND {{slug}}]]` | `[[AND {{date_range}}]]` trong CTE filter_bounds |
| Extra rules | Không alias table | Không alias table (R2) + CTE ordering (R5) + BIGINT trap (R7) |
| UI render | Searchable combobox | Date picker (daily/weekly/monthly/quarterly/yearly) |
| Metabase inject | `col = 'value'` | `col >= ? AND col < ?` (fully-qualified table name) |

---

## 7. Checklist trước khi deploy

- [ ] Blueprint có `field_id` đúng trên từng filter param
- [ ] Mọi card dùng filter: SQL dùng `[[AND {{slug}}]]` — KHÔNG dùng `[[AND col = {{slug}}]]`
- [ ] Sau deploy: verify `parameter_mappings[].target[0]` === `"dimension"` cho mỗi filter
- [ ] Test: chọn một giá trị từ dropdown → widget load đúng (không crash)
- [ ] Test: không chọn filter → widget vẫn load toàn bộ data

---

## 8. Lessons liên quan

| Lesson | Nội dung |
|--------|----------|
| L102 | `string/=` dropdown cần `field_id` + field filter SQL — đây là CategoryDrop pattern |
| L104 | Crash toàn dashboard khi filter active = `field_id` có nhưng SQL dùng variable syntax |
| L105 | Recipe đầy đủ: `field_id` + `[[AND {{slug}}]]` = dropdown hoạt động |
