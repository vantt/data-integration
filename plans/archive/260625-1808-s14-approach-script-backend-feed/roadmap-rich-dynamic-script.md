# Roadmap — Rich Dynamic Script (định hướng v2+, chưa lên lịch)

> Ghi nhận 2026-06-26. Vision: chuyển kịch bản từ **tài liệu tĩnh một-phát** → **engine dẫn thoại động có vòng lặp phản hồi + thu thập dữ liệu lũy tiến + thư viện kịch bản kết hợp**. Đây là định hướng, không phải scope đã chốt; mỗi workstream tách phase khi quyết làm.

## Phát hiện nền tảng: vòng lặp đã dựng MỘT NỬA

| Nửa | Trạng thái | Bằng chứng |
|---|---|---|
| **CAPTURE** (ghi phản hồi) | ✅ ĐÃ CÓ | `crm_activity` có `contact_outcome` (reached/no_answer/callback/refused), `channel_used`, `callback_at`, `task_id` (migration 0013). `ActivityService.log_activity` ghi + upsert `last_contact`. S14 outcome bar (Gọi được/Không nghe/Hẹn lại/Đã mua) + quick-note → M08 → `crm_activity` (SQLite). |
| **READ-BACK** (đọc lại vào prompt) | ❌ HỞ | `build_approach_prompts.py:53-54` hardcode `recent_notes=[]`, `recent_convos=[]`. Nhân viên đang ghi nhưng builder không đọc. |

→ Đòn bẩy lớn nhất KHÔNG phải sửa prompt mà là **nối nửa hở**. Phần lớn `data_gaps` dài thượt ("notes trống...") sẽ tự biến mất.

---

## WS-A — Đóng vòng lặp + thu thập lũy tiến (Stage 1, ưu tiên cao, rủi ro thấp)

> ⏸ **A1 HOÃN (2026-06-26):** CRM mới build → `recent_notes`/`recent_conversations` gần như ZERO. Wiring chưa cho giá trị; làm khi CRM tích lũy đủ ghi chú/hội thoại thật. A2 (progressive profiling) cũng phụ thuộc data này.

**A1 — Read-back notes/conversations thật**
- `build_approach_prompts.py` đọc `crm_activity` cho mỗi khách → fill `recent_notes` (body + outcome + occurred_at, tối đa 5) thay `[]`.
- Map `customer_id ↔ party_id`: reuse pattern `insight_handler` (`list_identities` → `sapo_customer`).
- Nguồn `recent_conversations`: cân nhắc FB messages (`fact_fb_messages`/`dim_fb_conversations`) hoặc tạm gộp vào notes. Quyết khi làm — đừng over-reach.
- Builder chạy trên HOST (duckdb) nhưng `crm_activity` ở SQLite cache.db trong container `crm_data` → cần đường đọc (copy ra / đọc volume / endpoint). **Điểm cần thiết kế.**

**A2 — Tình trạng thiếu dữ liệu = MỤC TIÊU hội thoại (progressive profiling)**
- INPUT: builder tính block `data_completeness` (field giá trị-cao đang NULL: người dùng cuối, nhu cầu/triệu chứng, email, birthday, consent, contact_quality) → inject explicit thay vì để LLM tự suy.
- OUTPUT schema thêm `info_to_collect: [{field, why, how_to_ask}]` — câu hỏi gài nhẹ nhàng vào thoại ("dạ mình mua dùng cho ai để em tư vấn đúng ạ?"). Talk-track tự nhiên lồng vào.
- Vòng khép: nhân viên ghi câu trả lời qua outcome bar/M08 (đã có) → `crm_activity` → A1 đọc lại lần gen sau → ít gap dần. **Cơ chế capture đã sẵn**, chỉ thêm: script bảo HỎI gì + read-back.
- Nâng cấp sau: thêm field structured trên M08 (end_user, symptom) thay vì chỉ free-text body.

Lợi phụ: A2 sinh data thật cho `recommended=false` + triệu chứng/người-dùng → gỡ luôn "Việc còn lại #3" (pilot toàn recommended=true).

---

## WS-B — Script tĩnh có nhánh + backend interpreter (Stage 2, lift trung bình)

**Mô hình chốt (2026-06-26):** tách 3 trục —
- **Sinh:** offline/batch, 1 script/khách (KHÔNG gọi LLM lúc gọi điện).
- **Cấu trúc:** branching/chi tiết — cây nhánh soạn 1 lần.
- **Runtime:** backend **dynamic** = interpreter đọc script tĩnh + tương tác nhân viên → ra node kế. KHÔNG tái sinh script live.

→ "Dynamic" = **điều hướng state-machine trên script tĩnh**, không phải regen. Rẻ + an toàn + testable + cacheable. Entity `data:dict` ôm trọn cây nhánh, **đổi 0 dòng entity**.

**Gỡ coupling (sửa nhận định trước):** branching authored MỘT-LẦN (kể cả dán GPT) vẫn chạy pilot được → dynamic-behavior **TÁCH khỏi** auto-gen. WS-C (auto-gen) chỉ cần khi quy mô/thư viện, KHÔNG phải tiền đề.

**Trigger đã có sẵn:** outcome bar S14 đã phát outcome (answered/no_answer/callback/purchased) → M08 → `crm_activity`. Backend chỉ thêm: nhận outcome → quyết fragment kế. Mỗi bước điều hướng = 1 row `crm_activity` keyed theo node → audit + flywheel (nhánh nào hay dùng, rớt ở đâu) + resumable. Tái dùng nguyên capture.

**State (chọn nhẹ trước):**
| Mức | Cơ chế | Khi nào |
|---|---|---|
| **Light** | Client giữ `current_node_id`, gửi kèm outcome; backend trả node kế (hàm thuần script+node+outcome). Không bảng session | Mặc định — bắt đầu đây |
| Durable | Lưu phiên gọi (node hiện tại + lịch sử); `crm_activity` đã đủ làm lịch sử | Chỉ khi cần resume/audit chặt |

**Schema đổi dạng:** từ list phẳng (`talking_points`/`objection_handling`) → **cây keyed theo outcome**: `{node_id, say, when, options:[{outcome|objection, next_node_id}]}`. `data:dict` absorb; **S14 template phải rework** — render node hiện tại, không render cả tài liệu (coupling chính của WS-B).

**Cái đắt thật:**
- Soạn cây CHẤT LƯỢNG: sâu 2–3 tầng × nhánh 3–4 = 10–40 node/khách → dán-GPT tay OK cho pilot, KHÔNG scale ngàn khách (→ WS-C).
- LLM hay nông ở tầng sâu; giá trị tập trung tầng-1 (mở thoại + phản ứng đầu) → **khởi đầu CÂY NÔNG (1–2 tầng)**, đo drop-off, đào sâu theo data. KHÔNG làm graph tổng quát (KISS: cây quyết định nông, không Turing-complete).

---

## WS-C — Auto-gen + thư viện kịch bản kết hợp (Stage 3, lift cao)

Khao khát "bộ kịch bản thật lớn cho từng sản phẩm × từng loại khách".

**CẢNH BÁO bùng nổ tổ hợp:** SKU (nghìn) × customer_type (5–6) × lifecycle (4) × signal = bất khả thi nếu materialize ma trận đầy. Tạo tay càng không.

**Kiến trúc đúng = MODULE KẾT HỢP, không phải ma trận:**
- Khối tái dùng: pitch-fragment theo category/SKU · objection-snippet theo loại từ chối · probe-question theo field thiếu · opening theo channel×lifecycle.
- Generator (auto-gen) **ráp** per-khách từ khối + data khách + benchmark (phase-06).
- Quản lý được: vài chục khối, không phải nghìn script đầy đủ.
- Outcomes (`crm_activity`) huấn luyện composition nào chốt cao → flywheel.

**Hạ tầng:** chuyển gen sang Dagster + cache table; swap `FileApproachScriptRepository` → `SQLiteApproachScriptRepository` (cùng port, S14 không đổi — đã ghi trong plan gốc "Ngoài scope"). B2 auth GET cân nhắc cùng lúc.

---

## Quyết định: 3 thang thời gian "dynamic" (chốt 2026-06-26)

Câu hỏi: generate full upfront 1 kịch bản, HAY regen động sau mỗi tương tác? → Tách "dynamic" làm 3 thang, KHÁC hẳn nhau:

| Thang | Là gì | Phán quyết (voice outbound bán lẻ) |
|---|---|---|
| **1. Live regen mỗi lượt** (trong cuộc gọi) | Mỗi câu khách nói → gọi LLM → câu kế | ❌ Sai fit: nhân viên cầm máy không chờ 3–10s/lượt; output tươi chưa review bắn tới khách (rủi ro bịa); chi phí ×lượt ×realtime |
| **2. Escape hatch trong cuộc** | Chỉ khi gặp tình huống NGOÀI cây → bấm "soạn giúp" → 1 call LLM | ✅ Fallback tốt: hiếm, nhân viên chủ động, chi phí có chặn. Thêm sau khi data cho thấy hay rớt ngoài cây |
| **3. Regen GIỮA các lần liên hệ** (sau cuộc gọi) | Ghi outcome + điều học → sinh lại script cho lần SAU | ✅ Win thật: batch/offline, rẻ — chính là flywheel WS-A |

**Lý do chọn full-upfront (cây nông) làm default:**
- Không gian nhánh GIÁ TRỊ nhỏ — call resell đi ít macro-path (nghe/không · quan tâm/từ-chối[giá|nhu cầu|tin|thời điểm]/để-sau · mua/không); tầng 1–2 phủ ~80%+.
- Latency = 0 lúc gọi (phone UX, mỗi giây chờ là chết).
- An toàn: cả cây review guardrail TRƯỚC khi dùng.
- Offline = model mạnh + multi-pass + judge; live ép model nhanh/rẻ.
- Tạo tay vẫn chạy (pilot dán GPT).

**Full-dynamic (thang 1) chỉ đáng khi:** kênh async/text (chịu latency) + mỗi lượt phụ thuộc nặng ngữ cảnh tự do + volume thấp. → Hợp chat concierge, KHÔNG hợp outbound phone hiện tại.

**Chốt:** đừng sinh động trong lúc gọi; sinh sẵn cây nông → backend điều hướng → sinh-lại giữa các lần. Được ~90% lợi ích "động" mà tránh hết latency/an toàn/chi phí.

---

## WS-D — Benchmark percentile (data layer) → [phase-06](phase-06-benchmark-percentile-dbt.md) ✅ DONE

Bao gồm cả phần prompt/template (2026-06-26): `build_approach_prompts.py` inject đủ benchmark (all_rankable + in_value_group, lv + clv); template thêm INPUT CONTRACT benchmark + quy tắc "percentile cao + tier thấp → nâng invest_level, verbalize qua *_phrase, không lộ *_pct thô" + ràng buộc làm tròn số.

Vị thế tương đối (top X% CLV, ×median tier). Đường chuẩn dbt (đã chốt). Cấp chiều sâu cho mọi stage. Sẵn-sàng-execute nhất.

---

## Trình tự đề xuất (vì sao)
1. **WS-D (phase-06)** + **WS-A1** — rẻ, độc lập, không đụng UI; A1 đóng vòng lặp đang hở, D gỡ điểm yếu vị thế. Làm trước, đo phản hồi sale.
2. **WS-A2** — additive prompt/schema; tái dùng capture đã có; sinh data thật cho profiling + recommended=false.
3. **WS-B opt-A** — khi script đủ giàu, thêm progressive disclosure client-side.
4. **WS-C** — khi muốn hết tạo tay & cần branching ở quy mô; build component library + auto-gen + flywheel.

## KHÔNG nên làm (chống over-engineering)
- KHÔNG build engine stateful (opt-C) trước khi đo nhu cầu.
- KHÔNG materialize ma trận product×type đầy — dùng module kết hợp.
- KHÔNG thêm output field mà S14 không render (vô dụng + làm `data_gaps` dài).
- KHÔNG ép branching vào quy trình dán-GPT tay (sẽ không nhất quán).

## Unresolved
- A1: đường builder (HOST) đọc `crm_activity` (SQLite trong container) — copy ra / mount / endpoint?
- `recent_conversations` lấy từ FB messages hay chỉ notes?
- M08 có thêm field structured (end_user, symptom) hay giữ free-text + để LLM trích?
- WS-B: render branching trong S14 template — sửa fragment hiện tại hay tách component mới?
- Ngưỡng chuyển tạo-tay → auto-gen (số script/đợt? tần suất?).
