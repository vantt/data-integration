# 30 — States & Errors

Catalogue of UI states (ST-*) and error conditions (ERR-*) referenced across all surfaces.
Prose only — no contract block needed.

---

## Global States

### ST-LOADING
Skeleton/spinner displayed while async data fetch is in progress. All action buttons disabled.

### ST-EMPTY
No records match current filters or the collection is genuinely empty.
Show an empty-state illustration + descriptive text + primary CTA.

### ST-ERROR
Network or server error. Show error banner with retry action and timestamp.

### ST-STALE-CACHE
`refreshed_at` for a cache table is > 24 hours old. Show yellow freshness badge warning NV.

---

## S01 — Worklist States

### ST-WORKLIST-EMPTY
No tasks assigned to current user today. Display "Hôm nay không có task nào" + CTA to browse customers.

### ST-WORKLIST-ALL-DONE
All tasks for today marked done. Celebratory empty state.

---

## S02 — Customer List States

### ST-CUSTOMER-SEARCH-EMPTY
FTS search returned 0 results. Suggest relaxing filters or creating a new party.

### ST-CUSTOMER-SEARCH-LOADING
FTS query in-flight (< 200ms target).

---

## S03 — Customer 360 States

### ST-360-LOADING
Point-lookup in progress (target ≤ 200ms).

### ST-360-NO-PROFILE
Party exists but `crm_customer_profile` not yet created. Show "Tạo hồ sơ" CTA.

### ST-360-NO-INSIGHT
`wh_customer_insight` row not found for this customer_id. Show "Insight chưa có" placeholder + refreshed_at.

### ST-360-MERGED
Party has `is_merged=true`. Show warning banner and link to surviving party.

### ST-360-WARNING
Party has one or more active warning notes (`crm_note.note_type='warning'` AND `is_active=true`). Show red banner at top of sidebar.

---

## S04 — Dedup Review States

### ST-DEDUP-NO-PENDING
Zero pending candidates. Show "Không có trùng lặp nào cần xem xét".

### ST-DEDUP-CONFLICT
Merge attempted but constraint violation detected (duplicate identity). Show conflict detail + manual resolution options.

---

## S05 — Inbox States

### ST-INBOX-EMPTY
No conversations match filter. Show empty state per filter type (all/open/pending/closed).

### ST-INBOX-UNRESOLVED-PSID
Conversation has `party_id=null` — PSID not yet linked. Show amber badge "Chưa link khách".

---

## S06 — Conversation Detail States

### ST-CONV-NO-PARTY
Conversation not linked to a party. Sidebar shows link-party CTA.

### ST-CONV-CLOSED
Conversation status=closed. Input box disabled; show re-open option.

### ST-CONV-LOADING
Messages loading.

---

## P04 — Tasks Panel States

### ST-EMPTY-OPEN
Filter = open (default), không có task đang mở. Show "Không có task nào đang mở." + CTA tạo task.

### ST-EMPTY-ALL
Filter = all, chưa có task nào gắn party này.

---

## S07 — Tasks Board States

### ST-TASKS-EMPTY
No open/doing tasks for this filter. Show empty state.

---

## S08 — Segments List States

### ST-SEGMENT-MATERIALIZING
Segment evaluation job is running. Show spinner + "Đang tính toán thành viên…".

### ST-SEGMENT-EMPTY-MEMBERS
Segment rule returned 0 members (possibly due to consent filtering). Show warning.

---

## S09 — Segment Builder States

### ST-BUILDER-PREVIEW-LOADING
Member preview query in-flight.

### ST-BUILDER-PREVIEW-ZERO
Preview returns 0 parties. Warn user before save.

### ST-BUILDER-CONSENT-FILTERED
Some parties excluded due to `consent_contact=false`. Show count.

---

## S10 — Campaigns List States

### ST-CAMPAIGN-EMPTY
No campaigns yet. Show CTA to create first campaign.

---

## S11 — Campaign Detail States

### ST-CAMPAIGN-NO-TARGETS
Campaign created but segment has 0 members. Show warning.

### ST-CAMPAIGN-CONVERTING
Conversion tracker job running.

---

## S12 — Ads Tracking States

### ST-ADS-NO-DATA
No ad campaigns ingested yet. Show instructions for Python ingest job.

---

## S13 — Settings States

### ST-SETTINGS-SAVED
Toast confirmation after saving custom field / tag / user changes.

---

## S15 — Task Detail States

### ST-TASK-LOADING
Task data fetch in-flight. Skeleton displayed; all lifecycle buttons disabled.

### ST-TASK-CONTACT
`task_kind=contact`. Body shows provenance, customer identity, contact-attempt history,
and "Vào phiên gọi" CTA (A-S15-006 → S14). Internal checklist / tool CTAs hidden.

### ST-TASK-INTERNAL
`task_kind=internal`. Body shows minimal customer facts, checklist items, tool CTAs
(edit contact, add tag). Customer party block visible; "Vào phiên gọi" CTA hidden.

### ST-TASK-GENERIC
`task_kind=generic` or `party_id=null`. Body shows description, checklist, links, notes.
No customer block rendered.

### ST-TASK-DONE
`task.status=done`. Full read-only view. Lifecycle action buttons (start/cancel/postpone)
hidden. Activity log and outcome summary remain visible.

### ST-TASK-CANCELLED
`task.status=cancelled`. Read-only banner "Task đã huỷ". Only "Mở lại" (reopen) CTA shown.

---

## S14 — Call Mode / Strategy Cockpit States

### ST-CALL-NO-SCRIPT
Không có row `cache.wh_approach_script` cho `customer_id` → empty state + CTA quay lại Worklist / Xem 360.

### ST-CALL-STOP
`recommended=false` (R14) → STOP banner: ẩn talk-track/talking_points/objection, hiện lý do + CTA tạo task xác minh tài khoản.

### ST-CALL-LOW-CONFIDENCE
`confidence=low` → talk-track hiển thị nhạt + nhãn "độ tin thấp, kiểm chứng".
(Stale → dùng lại `ST-STALE-CACHE`; loading → `ST-LOADING`.)

### ST-CALL-NO-ACTIONS
`insight.actions` rỗng → rail "Vì sao gọi" (reason_to_call) hiện caveat "Không có đề xuất — dùng kịch bản".

### ST-CALL-COLLECT-DONE
Sau khi bấm [+] ở dòng thu thập (collect) → dòng đó swap thành "✓ đã lưu" (client-side, KHÔNG re-render `#s14-panel-root` để bảo toàn trạng thái tick điểm nói / objection).

### ST-CALL-CONSENT-WARN
`consent_contact='denied'` (R1) → chip đỏ ở alert_row cảnh báo, **nhưng KHÔNG chặn** nút Gọi/Zalo — chỉ cảnh báo, rep tự chịu trách nhiệm (quyết định sản phẩm).

---

## Error Conditions

### ERR-MERGE-CONSTRAINT
Merge failed because moving an identity would violate UNIQUE(identity_type, identity_value) on target party. User must manually resolve the conflict.

### ERR-SEGMENT-RULE-INVALID
Segment rule JSON failed validation (unknown field, invalid operator). Show inline error on builder.

### ERR-TASK-DUE-PAST
Task due_at is in the past. Warn but allow save.

### ERR-PHONE-FORMAT
Phone number cannot be normalized to E.164. Show format hint "+84xxx or 0xxx".

### ERR-DUPLICATE-IDENTITY
Attempting to add an identity (phone/email/psid) that already belongs to another party.

### ERR-CACHE-READ-FAIL
Go app cannot read from cache.db ATTACH. Show "Dữ liệu insight tạm thời không khả dụng" and continue with CRM-owned data only.

### ERR-CAMPAIGN-NO-SEGMENT
Campaign cannot be activated without an attached segment.

### ERR-CONSENT-BLOCK
Operation blocked because party has `consent_contact=false`. Cannot add to campaign target.
