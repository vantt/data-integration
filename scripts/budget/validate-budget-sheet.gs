/**
 * Budget Sheet Validator — Google Apps Script
 * Attach to spreadsheet: Extensions → Apps Script → paste this file
 *
 * Validates 2 tabs:
 *   BUDGET_ITEMS     — finance enters monthly planned amounts
 *   ALLOCATION_POLICY — quarterly waterfall config
 *
 * Usage:
 *   - Auto: runs on every edit (onEdit trigger — lightweight checks only)
 *   - Manual: menu "Budget Tools → Validate All" — full validation with summary
 *
 * Install triggers: run installTriggers() once after pasting.
 */

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────

const TAB_BUDGET   = 'BUDGET_ITEMS';
const TAB_POLICY   = 'ALLOCATION_POLICY';
// __REF: hidden tab với 2 cột
//   A = direction      (Thu | Chi) — cột đầu để sort/group dễ đọc
//   B = cashflow_line  (khớp chính xác với dim_gl_account.cashflow_line trong MISA)
// Populate từ DuckDB: SELECT direction, cashflow_line FROM dim_gl_account ORDER BY direction DESC, cashflow_line
const TAB_REF      = '__REF';

// BUDGET_ITEMS column positions (1-indexed, A=1)
// Khớp với cấu trúc thực tế của Sheet (đọc từ header row).
// Nếu finance thêm/đổi cột → chỉ cần cập nhật block này.
// Cột B "Ghi chú" thêm 2026-07-09 — free text hiển thị, KHÔNG parse cho logic gì — dùng để
// phân biệt nhiều dòng recurring cùng map 1 account_code (vd "Internet" và "Cloud Hosting"
// cùng lên 642282) — xem plans/260709-1415-budget-account-level-remap/plan.md.
const BI_COL = {
  CASHFLOW_LINE : 1,   // A — Dòng Tiền:
                       //     recurring  → cashflow_line (phải khớp __REF để join MISA)
                       //     reserve/one_off → tên mô tả tự do (chính là item label)
  NOTES         : 2,   // B — Ghi chú (tự do, không validate)
  DIRECTION     : 3,   // C — Chiều: Thu | Chi
  ITEM_TYPE     : 4,   // D — Type: recurring | one_off | reserve
  TARGET_MONTH  : 5,   // E — Tháng Cần (nullable)
  PAYMENT_WEEK  : 6,   // F — Tuần TT: 1|2|3|4|spread
  ITEM_TARGET   : 7,   // G — Tổng Cần (VND, nullable)
  DATA_START_COL: 8,   // H onwards: [Gợi ý Tx] [Budget Tx] pairs
};

// ALLOCATION_POLICY column positions (1-indexed)
const AP_COL = {
  PRIORITY       : 1,  // A — số nguyên dương, nhỏ = ưu tiên cao
  BUCKET         : 2,  // B — tên bucket tự do
  RULE_TYPE      : 3,  // C — fill_to_target | from_plan | fixed | pct_remaining | remainder
  VALUE          : 4,  // D — VND / % / null (phụ thuộc rule_type)
  EFFECTIVE_FROM : 5,  // E — YYYY-MM-DD
  EFFECTIVE_TO   : 6,  // F — YYYY-MM-DD | blank = currently active
};

// Valid enum values
const VALID_ITEM_TYPES  = ['recurring', 'one_off', 'reserve'];
const VALID_DIRECTIONS  = ['Thu', 'Chi'];
const VALID_PAYMENT_WEEKS = ['1', '2', '3', '4', 'spread'];
const VALID_RULE_TYPES  = ['fill_to_target', 'from_plan', 'fixed', 'pct_remaining', 'remainder'];
// rule_types that REQUIRE a numeric value in the VALUE column
const RULE_TYPES_WITH_VALUE = ['fill_to_target', 'fixed', 'pct_remaining'];

// ─────────────────────────────────────────────────────────────────────────────
// ENTRY POINTS
// ─────────────────────────────────────────────────────────────────────────────

/** Run once to install the edit trigger and add the custom menu. */
function installTriggers() {
  const ss = SpreadsheetApp.getActive();
  // Remove duplicate triggers before adding
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'onEditTrigger')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('onEditTrigger').forSpreadsheet(ss).onEdit().create();
  SpreadsheetApp.getUi().alert('Trigger installed. Menu "Budget Tools" ready.');
}

/**
 * Simple trigger — tự động active, không cần installTriggers().
 * Xử lý dropdown Dòng Tiền ngay khi edit (không cần authorization mở rộng).
 */
function onEdit(e) {
  onEditTrigger(e);
}

/** Installable trigger (backup) — cài bằng installTriggers() nếu cần auth mở rộng sau này. */
function onEditTrigger(e) {
  const sheet = e.range.getSheet();
  const name  = sheet.getName();
  if (name === TAB_BUDGET) {
    const row = e.range.getRow();
    if (row <= 2) return; // skip 2 header rows (row1=month, row2=column names)
    // Cách 2: cập nhật dropdown Dòng Tiền ngay khi Type hoặc Chiều thay đổi
    const col = e.range.getColumn();
    if (col === BI_COL.ITEM_TYPE || col === BI_COL.DIRECTION) {
      const itemType  = String(sheet.getRange(row, BI_COL.ITEM_TYPE).getValue() || '').trim();
      const direction = String(sheet.getRange(row, BI_COL.DIRECTION).getValue() || '').trim();
      applyDongTienDropdown(sheet, row, itemType, direction);
    }
    const errors = validateBudgetRow(sheet, row);
    highlightRow(sheet, row, errors);
    // Cha/con trùng (account_code prefix collision) — cross-row, show toast only
    // (giống pattern validatePolicyCrossRows bên dưới)
    const crossErrors = validateBudgetCrossRows(sheet);
    if (crossErrors.length) {
      SpreadsheetApp.getActiveSpreadsheet()
        .toast(crossErrors.join('\n'), '⚠️ Cha/con trùng', 8);
    }
  } else if (name === TAB_POLICY) {
    const row = e.range.getRow();
    if (row <= 2) return; // skip 2 header rows
    const errors = validatePolicyRow(sheet, row);
    highlightRow(sheet, row, errors);
    // Cross-row rules (remainder must be last, no gap/overlap) — show toast only
    const crossErrors = validatePolicyCrossRows(sheet);
    if (crossErrors.length) {
      SpreadsheetApp.getActiveSpreadsheet()
        .toast(crossErrors.join('\n'), '⚠️ Policy Warning', 8);
    }
  }
}

/** Manual: Budget Tools → Validate All */
function validateAll() {
  const ss = SpreadsheetApp.getActive();
  const errors = [];
  errors.push(...validateBudgetTab(ss));
  errors.push(...validatePolicyTab(ss));
  showSummary(errors);
}

/**
 * Setup toàn bộ Sheet lần đầu:
 *   - Tạo/update dropdown Dòng Tiền cho mỗi dòng dựa theo Type
 *   - Set dropdown Type + Chiều cho toàn bộ cột
 *   - Set dropdown rule_type cho ALLOCATION_POLICY
 * Chạy 1 lần sau khi paste script, hoặc sau khi finance thêm dòng mới hàng loạt.
 */
function setupAllDropdowns() {
  const ss = SpreadsheetApp.getActive();
  setupBudgetDropdowns(ss);
  setupPolicyDropdowns(ss);
  SpreadsheetApp.getUi().alert('✅ Setup xong', 'Dropdown đã được cấu hình cho toàn bộ Sheet.', SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * Tạo tab __REF (nếu chưa có) rồi ẩn đi.
 * Data do finance paste trực tiếp vào sheet — script chỉ đọc, không ghi.
 * Format: col A = Chiều (Thu|Chi), col B = Dòng Tiền (cashflow_line khớp MISA)
 */
function createRefTab() {
  const ss = SpreadsheetApp.getActive();
  let refSheet = ss.getSheetByName(TAB_REF);
  if (!refSheet) {
    refSheet = ss.insertSheet(TAB_REF);
  }
  refSheet.hideSheet();
  SpreadsheetApp.getUi().alert(
    '✅ Tab __REF đã tạo',
    'Paste dữ liệu vào __REF:\n  Cột A = Chiều (Thu/Chi)\n  Cột B = Dòng Tiền\n\nUnhide để paste, sau đó hide lại.',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/** Custom menu — added on open. */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Budget Tools')
    .addItem('Validate All', 'validateAll')
    .addItem('Tạo tab __REF (lần đầu)', 'createRefTab')
    .addItem('Setup Dropdowns (chạy lần đầu)', 'setupAllDropdowns')
    .addItem('Clear All Highlights', 'clearHighlights')
    .addToUi();
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: BUDGET_ITEMS — full validation
// ─────────────────────────────────────────────────────────────────────────────

function validateBudgetTab(ss) {
  const sheet  = ss.getSheetByName(TAB_BUDGET);
  if (!sheet) return [`[${TAB_BUDGET}] Tab not found`];

  const validLines = getValidCashflowLines(ss);
  const lastRow    = sheet.getLastRow();
  const errors     = [];

  for (let row = 3; row <= lastRow; row++) {
    const rowErrors = validateBudgetRow(sheet, row, validLines);
    highlightRow(sheet, row, rowErrors);
    rowErrors.forEach(e => errors.push(`[${TAB_BUDGET}] Row ${row}: ${e}`));
  }

  const crossErrors = validateBudgetCrossRows(sheet);
  crossErrors.forEach(e => errors.push(`[${TAB_BUDGET}] ${e}`));

  return errors;
}

/**
 * Validates a single BUDGET_ITEMS row.
 *
 * Rules:
 *   1. Dòng tiền (cashflow_line) must be in __REF list (if __REF exists)
 *   2. Chiều (direction) must be "Thu" or "Chi"
 *   3. Tuần TT (payment_week) must be 1|2|3|4|spread
 *   4. item_type must be recurring|one_off|reserve
 *   5. item_label required when item_type is reserve or one_off
 *   6. target/deadline validation:
 *      a. deadline (target_month) present + target (item_target) absent → REJECT
 *         "có deadline thì phải có target"
 *      b. target present + no deadline → OK (tích lũy đến khi đủ, không áp lực thời gian)
 *      c. both absent → OK (open-ended, finance nhập tay)
 *      d. both present → OK (sinking fund đầy đủ)
 *   7. target_month format: must parse as a valid date if present
 *   8. item_target must be a positive number if present
 */
function validateBudgetRow(sheet, row, validLines) {
  const vals        = sheet.getRange(row, 1, 1, BI_COL.ITEM_TARGET).getValues()[0];
  const cashflowLine = String(vals[BI_COL.CASHFLOW_LINE - 1] || '').trim();
  const direction    = String(vals[BI_COL.DIRECTION    - 1] || '').trim();
  const itemType     = String(vals[BI_COL.ITEM_TYPE    - 1] || '').trim();
  const targetMonthRaw = vals[BI_COL.TARGET_MONTH - 1];
  const paymentWeek  = String(vals[BI_COL.PAYMENT_WEEK - 1] || '').trim();
  const itemTargetRaw = vals[BI_COL.ITEM_TARGET - 1];

  const errors = [];

  // Skip completely empty rows
  if (!cashflowLine && !itemType) return errors;

  // Rule 1: cashflow_line phải match __REF — CHỈ với recurring
  // reserve/one_off: Dòng Tiền là label tự do, không join với actual → không cần validate
  if (itemType === 'recurring' && validLines && validLines.length && cashflowLine && !validLines.includes(cashflowLine)) {
    errors.push(`Dòng tiền "${cashflowLine}" không có trong danh sách hợp lệ (__REF tab) — recurring phải khớp chính xác để join với sổ cái MISA`);
  }

  // Rule 2: direction
  if (direction && !VALID_DIRECTIONS.includes(direction)) {
    errors.push(`Chiều phải là "Thu" hoặc "Chi", nhận được: "${direction}"`);
  }

  // Rule 3: payment_week
  if (paymentWeek && !VALID_PAYMENT_WEEKS.includes(paymentWeek)) {
    errors.push(`Tuần TT phải là 1/2/3/4/spread, nhận được: "${paymentWeek}"`);
  }

  // Rule 4: item_type
  if (!itemType) {
    errors.push('item_type không được để trống');
  } else if (!VALID_ITEM_TYPES.includes(itemType)) {
    errors.push(`item_type không hợp lệ: "${itemType}". Phải là: ${VALID_ITEM_TYPES.join('|')}`);
  }

  // Rule 5: Dòng Tiền bắt buộc với reserve/one_off — vì nó chính là tên mô tả khoản
  // (recurring thì cashflow_line đã validate ở Rule 1; reserve/one_off là free text nhưng không được trống)
  if ((itemType === 'reserve' || itemType === 'one_off') && !cashflowLine) {
    errors.push(`"Dòng Tiền" không được để trống khi Type="${itemType}" — điền tên mô tả khoản, ví dụ: "Để dành mua laptop"`);
  }

  // Parse target & deadline
  const hasTarget   = itemTargetRaw !== '' && itemTargetRaw !== null && itemTargetRaw !== undefined;
  const hasDeadline = targetMonthRaw !== '' && targetMonthRaw !== null && targetMonthRaw !== undefined;

  // Rule 6a: REJECT — deadline có mà target không có
  // "có deadline thì phải có target" — không biết tích lũy đến bao nhiêu thì vô nghĩa
  if (hasDeadline && !hasTarget) {
    errors.push('Tháng Cần có giá trị nhưng Tổng Cần bị trống — phải có target nếu có deadline');
  }

  // Rule 8: item_target must be positive number
  if (hasTarget) {
    const numTarget = Number(itemTargetRaw);
    if (isNaN(numTarget) || numTarget <= 0) {
      errors.push(`Tổng Cần phải là số dương VND, nhận được: "${itemTargetRaw}"`);
    }
  }

  // Rule 7: target_month must be parseable as a date
  if (hasDeadline) {
    const d = new Date(targetMonthRaw);
    if (isNaN(d.getTime())) {
      errors.push(`Tháng Cần không phải ngày hợp lệ: "${targetMonthRaw}". Dùng định dạng YYYY-MM-01`);
    }
  }

  return errors;
}

/**
 * Bóc account_code từ label dạng "  3383  Bảo hiểm xã hội" (fixed-width padded,
 * xem plans/260709-1415-budget-account-level-remap/phase-02). Trả null nếu label
 * không có prefix số (dòng cashflow_line kiểu cũ, hoặc one_off/reserve free text)
 * — các dòng này không tham gia check cha/con.
 */
function parseAccountCodeFromLabel(label) {
  const m = String(label || '').match(/^\s*(\d+)\s+/);
  return m ? m[1] : null;
}

/** Tìm mọi cặp (a, b) trong entries mà code của a là tiền tố của code b (hoặc ngược lại). */
function findPrefixCollisions(entries) {
  const sorted = entries.slice().sort((x, y) => x.code.localeCompare(y.code));
  const collisions = [];
  for (let i = 0; i < sorted.length; i++) {
    for (let j = i + 1; j < sorted.length; j++) {
      if (sorted[i].code !== sorted[j].code && sorted[j].code.startsWith(sorted[i].code)) {
        collisions.push([sorted[i], sorted[j]]);
      }
    }
  }
  return collisions;
}

/**
 * Cha + con account_code không được cùng có Budget trong cùng 1 (tháng, Chiều) —
 * double-count khi actual match cả 2 dòng (prefix-match join). Scope NGHIÊM NGẶT theo
 * từng cột tháng riêng biệt (không xét chéo qua các tháng khác) — vì finance có thể
 * hợp lệ đổi granularity giữa các tháng (tháng này budget ở cha, tháng sau đổi sang con).
 * Chỉ xét dòng item_type=recurring có prefix account_code (Rule 1 vẫn cho phép cashflow_line
 * text kiểu cũ tồn tại song song trong lúc migrate — dòng đó không parse được code, bỏ qua).
 */
function validateBudgetCrossRows(sheet) {
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 3 || lastCol < BI_COL.DATA_START_COL) return [];

  const monthHeader = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const itemTypes   = sheet.getRange(3, BI_COL.ITEM_TYPE, lastRow - 2, 1).getValues().flat();
  const directions   = sheet.getRange(3, BI_COL.DIRECTION, lastRow - 2, 1).getValues().flat();
  const cashflowLines = sheet.getRange(3, BI_COL.CASHFLOW_LINE, lastRow - 2, 1).getValues().flat();

  const errors = [];

  for (let col = BI_COL.DATA_START_COL; col + 1 <= lastCol; col += 2) {
    const budgetCol  = col + 1; // [Gợi ý][Budget] — Budget là cột lẻ tiếp theo
    const monthLabel = String(monthHeader[col - 1] || '').trim();
    if (!monthLabel) continue;

    const budgetVals = sheet.getRange(3, budgetCol, lastRow - 2, 1).getValues().flat();
    const byDirection = { Thu: [], Chi: [] };

    for (let i = 0; i < itemTypes.length; i++) {
      if (String(itemTypes[i]).trim() !== 'recurring') continue;
      const direction = String(directions[i]).trim();
      if (!byDirection[direction]) continue;
      const budgetVal = budgetVals[i];
      if (budgetVal === '' || budgetVal === null || budgetVal === undefined) continue;
      const code = parseAccountCodeFromLabel(cashflowLines[i]);
      if (!code) continue; // dòng cashflow_line kiểu cũ — không parse được, bỏ qua
      byDirection[direction].push({ code, row: i + 3 });
    }

    Object.keys(byDirection).forEach(direction => {
      findPrefixCollisions(byDirection[direction]).forEach(([a, b]) => {
        errors.push(
          `Tháng ${monthLabel} (${direction}): row ${a.row} (account ${a.code}) và row ${b.row} `
          + `(account ${b.code}) trùng cha/con — chỉ chọn 1 trong 2, không cả hai (double-count khi tính actual)`
        );
      });
    });
  }

  return errors;
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB: ALLOCATION_POLICY — full validation
// ─────────────────────────────────────────────────────────────────────────────

function validatePolicyTab(ss) {
  const sheet = ss.getSheetByName(TAB_POLICY);
  if (!sheet) return [`[${TAB_POLICY}] Tab not found`];

  const lastRow = sheet.getLastRow();
  const errors  = [];

  // Row-level validation
  for (let row = 3; row <= lastRow; row++) {
    const rowErrors = validatePolicyRow(sheet, row);
    highlightRow(sheet, row, rowErrors);
    rowErrors.forEach(e => errors.push(`[${TAB_POLICY}] Row ${row}: ${e}`));
  }

  // Cross-row validation
  const crossErrors = validatePolicyCrossRows(sheet);
  crossErrors.forEach(e => errors.push(`[${TAB_POLICY}] ${e}`));

  return errors;
}

/**
 * Validates a single ALLOCATION_POLICY row.
 *
 * Rules:
 *   1. priority phải là số nguyên dương
 *   2. bucket không được trống
 *   3. rule_type phải thuộc danh sách hợp lệ
 *   4. value:
 *      - BẮT BUỘC (số dương) khi rule_type ∈ {fill_to_target, fixed, pct_remaining}
 *      - phải NULL/blank khi rule_type ∈ {from_plan, remainder}
 *   5. effective_from bắt buộc, phải là ngày hợp lệ
 *   6. effective_to: nếu có thì phải là ngày hợp lệ và > effective_from
 */
function validatePolicyRow(sheet, row) {
  const vals          = sheet.getRange(row, 1, 1, AP_COL.EFFECTIVE_TO).getValues()[0];
  const priorityRaw   = vals[AP_COL.PRIORITY       - 1];
  const bucket        = String(vals[AP_COL.BUCKET        - 1] || '').trim();
  const ruleType      = String(vals[AP_COL.RULE_TYPE     - 1] || '').trim();
  const valueRaw      = vals[AP_COL.VALUE          - 1];
  const effectiveFrom = vals[AP_COL.EFFECTIVE_FROM - 1];
  const effectiveTo   = vals[AP_COL.EFFECTIVE_TO   - 1];

  const errors = [];

  // Skip empty rows
  if (!bucket && !ruleType) return errors;

  // Rule 1: priority phải là số nguyên dương
  const priority = Number(priorityRaw);
  if (!priorityRaw && priorityRaw !== 0) {
    errors.push('priority không được để trống');
  } else if (!Number.isInteger(priority) || priority <= 0) {
    errors.push(`priority phải là số nguyên dương, nhận được: "${priorityRaw}"`);
  }

  // Rule 2: bucket
  if (!bucket) {
    errors.push('bucket không được để trống');
  }

  // Rule 3: rule_type
  if (!ruleType) {
    errors.push('rule_type không được để trống');
  } else if (!VALID_RULE_TYPES.includes(ruleType)) {
    errors.push(`rule_type không hợp lệ: "${ruleType}". Phải là: ${VALID_RULE_TYPES.join('|')}`);
  }

  // Rule 4: value — required/forbidden tùy rule_type
  const hasValue = valueRaw !== '' && valueRaw !== null && valueRaw !== undefined;
  if (RULE_TYPES_WITH_VALUE.includes(ruleType)) {
    if (!hasValue) {
      errors.push(`rule_type="${ruleType}" bắt buộc phải có value (VND hoặc %)`);
    } else {
      const numValue = Number(valueRaw);
      if (isNaN(numValue) || numValue <= 0) {
        errors.push(`value phải là số dương cho rule_type="${ruleType}", nhận được: "${valueRaw}"`);
      }
      // pct_remaining: value should be 0-100
      if (ruleType === 'pct_remaining' && (numValue <= 0 || numValue > 100)) {
        errors.push(`pct_remaining value phải từ 0–100 (%), nhận được: ${numValue}`);
      }
    }
  } else if (['from_plan', 'remainder'].includes(ruleType) && hasValue) {
    errors.push(`rule_type="${ruleType}" không dùng value — hãy để trống`);
  }

  // Rule 5: effective_from bắt buộc
  if (!effectiveFrom) {
    errors.push('effective_from bắt buộc');
  } else {
    const fromDate = new Date(effectiveFrom);
    if (isNaN(fromDate.getTime())) {
      errors.push(`effective_from không phải ngày hợp lệ: "${effectiveFrom}"`);
    }
  }

  // Rule 6: effective_to — nếu có thì phải là ngày và > effective_from
  if (effectiveTo) {
    const toDate   = new Date(effectiveTo);
    const fromDate = new Date(effectiveFrom);
    if (isNaN(toDate.getTime())) {
      errors.push(`effective_to không phải ngày hợp lệ: "${effectiveTo}"`);
    } else if (effectiveFrom && toDate <= fromDate) {
      errors.push('effective_to phải sau effective_from');
    }
  }

  return errors;
}

/**
 * Cross-row validation cho ALLOCATION_POLICY.
 *
 * Rules:
 *   A. "remainder phải là priority cuối cùng"
 *      Trong các dòng đang hiệu lực (effective_to trống):
 *      nếu có bucket sau remainder (priority cao hơn số của remainder) → REJECT
 *
 *   B. "không gap, không overlap trong effective_from/effective_to cho cùng bucket"
 *      Với mỗi bucket: sắp xếp theo effective_from, kiểm tra:
 *        - Overlap: effective_from[n+1] < effective_to[n]
 *        - Gap: effective_from[n+1] > effective_to[n] + 1 day
 */
function validatePolicyCrossRows(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const data = sheet.getRange(2, 1, lastRow - 1, AP_COL.EFFECTIVE_TO).getValues();
  const errors = [];

  // ── Rule A: remainder must be last among active rows ───────────────────────
  const activeRows = data.filter(r => {
    const bucket   = String(r[AP_COL.BUCKET       - 1] || '').trim();
    const effectiveTo = r[AP_COL.EFFECTIVE_TO - 1];
    return bucket && !effectiveTo; // active = effective_to blank
  });

  const remainderRows = activeRows.filter(r =>
    String(r[AP_COL.RULE_TYPE - 1] || '').trim() === 'remainder'
  );

  if (remainderRows.length > 0) {
    const remainderPriority = Number(remainderRows[0][AP_COL.PRIORITY - 1]);
    const afterRemainder = activeRows.filter(r => {
      const p = Number(r[AP_COL.PRIORITY - 1]);
      return p > remainderPriority;
    });
    if (afterRemainder.length > 0) {
      const names = afterRemainder.map(r => `"${r[AP_COL.BUCKET - 1]}" (P${r[AP_COL.PRIORITY - 1]})`).join(', ');
      errors.push(`"remainder" không phải priority cuối — có bucket sau nó: ${names}. Các bucket này sẽ không nhận được gì.`);
    }
  }

  // ── Rule B: no gap or overlap per bucket ───────────────────────────────────
  // Group rows by bucket name
  const bucketMap = {};
  data.forEach(r => {
    const bucket = String(r[AP_COL.BUCKET - 1] || '').trim();
    if (!bucket) return;
    if (!bucketMap[bucket]) bucketMap[bucket] = [];
    const fromDate = r[AP_COL.EFFECTIVE_FROM - 1] ? new Date(r[AP_COL.EFFECTIVE_FROM - 1]) : null;
    const toDate   = r[AP_COL.EFFECTIVE_TO   - 1] ? new Date(r[AP_COL.EFFECTIVE_TO   - 1]) : null;
    if (fromDate && !isNaN(fromDate.getTime())) {
      bucketMap[bucket].push({ from: fromDate, to: toDate });
    }
  });

  Object.entries(bucketMap).forEach(([bucket, rows]) => {
    if (rows.length < 2) return;
    // Sort by effective_from ascending
    rows.sort((a, b) => a.from - b.from);

    for (let i = 0; i < rows.length - 1; i++) {
      const curr = rows[i];
      const next = rows[i + 1];

      // curr must have effective_to (can't be open-ended if there's a next row)
      if (!curr.to) {
        errors.push(`Bucket "${bucket}": dòng hiệu lực từ ${fmtDate(curr.from)} không có effective_to nhưng có dòng tiếp theo từ ${fmtDate(next.from)} — phải đặt effective_to`);
        continue;
      }

      const dayAfterCurrEnd = new Date(curr.to);
      dayAfterCurrEnd.setDate(dayAfterCurrEnd.getDate() + 1);

      // Overlap: next starts before current ends
      if (next.from < curr.to) {
        errors.push(`Bucket "${bucket}": OVERLAP — dòng từ ${fmtDate(next.from)} bắt đầu trước khi dòng từ ${fmtDate(curr.from)} kết thúc (${fmtDate(curr.to)})`);
      }
      // Gap: next doesn't start the day after current ends
      else if (next.from > dayAfterCurrEnd) {
        errors.push(`Bucket "${bucket}": GAP — từ ${fmtDate(curr.to)} đến ${fmtDate(next.from)}, không có policy hiệu lực trong khoảng này`);
      }
    }
  });

  return errors;
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// CÁCH 2 — DYNAMIC DROPDOWN
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Áp dụng dropdown Dòng Tiền cho 1 dòng cụ thể.
 *   recurring + Chiều đã chọn → lọc __REF col B theo col A = direction (chỉ thấy đúng chiều)
 *   recurring + chưa chọn Chiều → toàn bộ col B của __REF
 *   reserve / one_off / trống  → xoá validation (label tự do)
 *
 * __REF: col A = direction (Thu|Chi), col B = cashflow_line
 */
function applyDongTienDropdown(sheet, row, itemType, direction) {
  const cell = sheet.getRange(row, BI_COL.CASHFLOW_LINE);

  if (itemType !== 'recurring') {
    cell.clearDataValidations();
    return;
  }

  const ss       = SpreadsheetApp.getActive();
  const refSheet = ss.getSheetByName(TAB_REF);
  if (!refSheet || refSheet.getLastRow() < 1) return;

  const lastRefRow = refSheet.getLastRow();
  const refData    = refSheet.getRange(1, 1, lastRefRow, 2).getValues();

  // Lọc theo chiều nếu đã chọn, còn không thì show tất cả
  const filtered = (direction === 'Thu' || direction === 'Chi')
    ? refData.filter(r => String(r[0] || '').trim() === direction).map(r => String(r[1] || '').trim()).filter(v => v)
    : refData.map(r => String(r[1] || '').trim()).filter(v => v);

  if (!filtered.length) { cell.clearDataValidations(); return; }

  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(filtered, true)
    .setAllowInvalid(false)
    .setHelpText(direction
      ? `recurring (${direction}): chọn Dòng Tiền — phải khớp chính xác sổ cái MISA để join`
      : 'recurring: chọn Chiều (Thu/Chi) trước để lọc danh sách theo chiều')
    .build();
  cell.setDataValidation(rule);
}

/**
 * Setup dropdown cho toàn bộ BUDGET_ITEMS tab.
 * Gọi khi paste script lần đầu, hoặc sau khi finance thêm nhiều dòng mới.
 *
 * Ngoài Dòng Tiền (dynamic per row), còn set:
 *   - Cột Type     → dropdown: recurring | one_off | reserve
 *   - Cột Chiều    → dropdown: Thu | Chi
 *   - Cột Tuần TT  → dropdown: 1 | 2 | 3 | 4 | spread
 */
function setupBudgetDropdowns(ss) {
  const sheet   = ss.getSheetByName(TAB_BUDGET);
  if (!sheet) return;
  const lastRow  = Math.max(sheet.getLastRow(), 3);
  const dataRows = lastRow - 2; // row 1+2 = headers, data từ row 3

  // ── Cột Type (C) — dropdown cố định, tất cả dòng data ──────────────────────
  const typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(VALID_ITEM_TYPES, true)
    .setAllowInvalid(false)
    .setHelpText('Chọn loại khoản: recurring (thường xuyên) | one_off (1 lần) | reserve (để dành)')
    .build();
  sheet.getRange(3, BI_COL.ITEM_TYPE, dataRows, 1).setDataValidation(typeRule);

  // ── Cột Chiều (B) — dropdown cố định ────────────────────────────────────────
  const dirRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(VALID_DIRECTIONS, true)
    .setAllowInvalid(false)
    .setHelpText('Thu hoặc Chi')
    .build();
  sheet.getRange(3, BI_COL.DIRECTION, dataRows, 1).setDataValidation(dirRule);

  // ── Cột Tuần TT (E) — dropdown cố định ─────────────────────────────────────
  const weekRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(VALID_PAYMENT_WEEKS, true)
    .setAllowInvalid(false)
    .setHelpText('Tuần thanh toán trong tháng: 1/2/3/4 hoặc spread (trải đều)')
    .build();
  sheet.getRange(3, BI_COL.PAYMENT_WEEK, dataRows, 1).setDataValidation(weekRule);

  // ── Cột Dòng Tiền (A) — dynamic theo từng dòng (lọc theo Type + Chiều) ────
  for (let row = 3; row <= lastRow; row++) {
    const itemType  = String(sheet.getRange(row, BI_COL.ITEM_TYPE).getValue()  || '').trim();
    const direction = String(sheet.getRange(row, BI_COL.DIRECTION).getValue()  || '').trim();
    applyDongTienDropdown(sheet, row, itemType, direction);
  }
}

/**
 * Setup dropdown cho ALLOCATION_POLICY tab.
 *   - Cột rule_type → dropdown: fill_to_target | from_plan | fixed | pct_remaining | remainder
 */
function setupPolicyDropdowns(ss) {
  const sheet = ss.getSheetByName(TAB_POLICY);
  if (!sheet) return;
  const lastRow = Math.max(sheet.getLastRow(), 3);

  const ruleTypeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(VALID_RULE_TYPES, true)
    .setAllowInvalid(false)
    .setHelpText('fill_to_target: fill đến ngưỡng VND | from_plan: Σ BUDGET_ITEMS | fixed: cố định N/tháng | pct_remaining: N% còn lại | remainder: toàn bộ phần còn (phải là priority cuối)')
    .build();
  sheet.getRange(3, AP_COL.RULE_TYPE, lastRow - 2, 1).setDataValidation(ruleTypeRule);
}

/** Load valid cashflow_line values from hidden __REF tab, col B (col A = direction Thu/Chi). */
function getValidCashflowLines(ss) {
  const refSheet = ss.getSheetByName(TAB_REF);
  if (!refSheet) return null;
  const lastRow = refSheet.getLastRow();
  if (lastRow < 1) return null;
  return refSheet.getRange(1, 2, lastRow, 1).getValues()
    .flat()
    .map(v => String(v).trim())
    .filter(v => v.length > 0);
}

/** Highlight a row red if errors exist, clear if no errors. */
function highlightRow(sheet, row, errors) {
  const lastCol = sheet.getLastColumn() || 10;
  const range   = sheet.getRange(row, 1, 1, lastCol);
  if (errors.length > 0) {
    range.setBackground('#fce8e6'); // light red
    // Add note to first cell with error summary
    sheet.getRange(row, 1).setNote('⚠️ ' + errors.join('\n'));
  } else {
    range.setBackground(null);
    sheet.getRange(row, 1).clearNote();
  }
}

/** Clear all highlights and notes from both tabs. */
function clearHighlights() {
  const ss = SpreadsheetApp.getActive();
  [TAB_BUDGET, TAB_POLICY].forEach(name => {
    const sheet = ss.getSheetByName(name);
    if (!sheet) return;
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) return;
    const range = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn() || 10);
    range.setBackground(null);
    range.clearNote();
  });
}

/** Format Date as YYYY-MM-DD string. */
function fmtDate(d) {
  if (!d) return 'null';
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/** Show a modal with validation summary. */
function showSummary(errors) {
  const ui = SpreadsheetApp.getUi();
  if (errors.length === 0) {
    ui.alert('✅ Validate OK', 'Không có lỗi nào trong cả 2 tabs.', ui.ButtonSet.OK);
  } else {
    const msg = errors.slice(0, 30).join('\n') +
      (errors.length > 30 ? `\n\n... và ${errors.length - 30} lỗi khác.` : '');
    ui.alert(`⚠️ ${errors.length} lỗi`, msg, ui.ButtonSet.OK);
  }
}
