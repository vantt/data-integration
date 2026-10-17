# Nghiên cứu: CRM bán lẻ để làm gì và cần những năng lực cốt lõi nào

Ngày: 2026-10-14 (Asia/Saigon) · Người viết: researcher · Phạm vi: sản phẩm data platform cho SME TMĐT Việt Nam, đối chiếu CRM nội bộ của Fine Japan (tenant #1)
Nguồn nội bộ đã đọc (read-only): `crm/README.md`, `crm/AGENTS.md`, `crm/docs/prd.md`, `crm/docs/crm-database-schema-reference.md`, `crm/docs/ui-spec/20-domain-rules.md`, `crm/docs/workflows/outreach-worklist-call-log-loop.md`, danh sách `crm/migrations/`, `crm/src/application/`, `docs/decisions/017-packs-and-tenants.md`, `docs/architecture/modules.md`, `docs/finejapan-growth-strategy/hug-*.md`. Không đọc dữ liệu khách hàng, `.env` hay `*.db`.

---

## TL;DR

1. **Mục đích của CRM bán lẻ** là lấy được **đơn kế tiếp, có lãi, từ người đã từng mua**, mà không làm khách khó chịu, rồi chứng minh được phần doanh thu đó là nhờ CRM. Khác CRM B2B: đơn vị công việc là **khách × việc nên làm tiếp theo** (next best action), không phải deal trong pipeline. Salesforce, Microsoft (clienteling), Klaviyo (dự đoán CLV, ngày mua tiếp, rủi ro churn) và mô hình 私域 của Trung Quốc (WeCom) đều quy về cùng một ý: CRM tồn tại để tăng giá trị vòng đời của khách đã có.
2. **Sáu năng lực bắt buộc cho SME**, xếp theo thứ tự: (1) hồ sơ khách hợp nhất và identity resolution (SĐT, Zalo, mã khách POS, ID sàn bị che), (2) hàng đợi việc cho nhân viên ("hôm nay gọi ai, vì sao"), lấy tín hiệu từ warehouse, (3) ghi nhận tiếp xúc (kết quả cuộc gọi, ghi chú, task hẹn lại), (4) consent và khả năng liên hệ theo từng kênh, kèm bằng chứng, (5) segment và chiến dịch có nhóm đối chứng, (6) đo doanh thu quy cho CRM và cho từng nhân viên. Các phần **nên hoãn hoặc giao cho hệ khác**: omnichannel inbox (dùng Pancake hoặc chat của sàn và chỉ lưu tham chiếu), loyalty và tích điểm (Sapo Loyalty đã có), ads attribution (thuộc warehouse), gửi tin tự động.
3. **Ranh giới dữ liệu**: warehouse (OLAP) giữ mọi thứ **tính ra được**, gồm đơn hàng, RFM, CLV, tín hiệu và action queue. CRM (OLTP) giữ mọi thứ **do người nhập hoặc người quyết định**, gồm identity link đã xác nhận, consent, ghi chú, tag, task, kết quả tiếp xúc, quyền sở hữu khách và quyết định bỏ qua. Fine Japan đã làm đúng nguyên tắc này (R2 No-Recompute), nên giữ nguyên.
4. **Agent-friendly** nghĩa là một tầng domain service duy nhất với ba adapter mỏng: REST/OpenAPI, CLI và MCP. Khoảng 12 tool là đủ. Lệnh ghi bắt buộc có `actor`, idempotency key và audit log. Các thao tác nguy hiểm (merge, link identity, đổi consent, thao tác hàng loạt) đi theo mô hình **đề xuất rồi người duyệt**. Agent **không gửi tin cho khách** ở v1. App Fine Japan hiện chủ yếu là HTML/HTMX và chỉ có khoảng 5 route JSON, nên đây là khoảng trống lớn nhất.
5. **Rủi ro pháp lý lớn hơn dự kiến.** Decree 13/2023 **đã bị thay** bởi Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 cùng Nghị định 356/2025, hiệu lực từ 01/01/2026. Theo Nghị định 356, "tình trạng sức khỏe" là dữ liệu nhạy cảm, mà CRM Fine Japan đang seed tag `health_concern` như "Huyết áp cao", "Mất ngủ" (migration 0042). Khi xử lý dữ liệu nhạy cảm, doanh nghiệp nhỏ **mất quyền miễn trừ** DPO/DPIA. Trường consent hiện là một enum ở cấp party, không có bằng chứng về thời điểm, cách thức và mục đích, nên chưa đủ chuẩn.
6. **Khuyến nghị (xếp hạng):** **A. Chuẩn hoá app Fine Japan thành CRM core của pack `crm`** (khuyến nghị). Ba lựa chọn còn lại xếp sau: C. dùng CRM hoặc loyalty có sẵn của VN làm bổ trợ, B. dựng trên CRM mã nguồn mở (Twenty), D. công cụ marketing automation kiểu Klaviyo. Lõi gồm 12 entity, 6 năng lực và 12 tool MCP (mục 7). Cần gộp 3 bảng identity chồng nhau, thay consent enum bằng consent ledger, thêm audit log và PartyRelationship (người nhận quà, khách sỉ ẩn), và bỏ phần ads khỏi phạm vi CRM.

---

## 1. Phương pháp và độ tin cậy nguồn

| Loại nguồn | Ví dụ | Trọng số |
|---|---|---|
| Đặc tả hoặc tài liệu chính thức | MCP spec, Shopify Admin API, Salesforce Data Cloud DMO, Microsoft Learn, Klaviyo Help/Dev | Cao |
| Phân tích của hãng luật | Tilleke & Gibbins, EY Vietnam, Apolat Legal, Vietnam Briefing | Cao về pháp lý, nhưng là **thứ cấp** (chưa đọc nguyên văn luật) |
| Blog sản phẩm của hãng | Sapo blog, HubSpot changelog, Klaviyo product page | Trung bình (mang tính quảng bá) |
| Tư vấn hoặc vendor | ITC (WeCom), Rivo/Eightx (benchmark), woshipm/36kr | Thấp đến trung bình, chỉ dùng để định hướng |
| Nội bộ repo | PRD, schema, domain rules, HUG docs | Cao về hiện trạng, nhưng chưa kiểm chứng mức sử dụng thật |

Mỗi kết luận chính đều có ít nhất 3 nguồn độc lập, trừ những chỗ được đánh dấu **[chưa chắc]**.

---

## 2. Mục đích: CRM bán lẻ làm những "job" gì

### 2.1 Các hãng định nghĩa ra sao

| Hãng hoặc mô hình | Cách họ định nghĩa mục đích | Nguồn |
|---|---|---|
| Salesforce (Retail Clienteling) | Mục tiêu cuối là "increase customer lifetime value"; hồ sơ 360 cùng lịch sử đơn để nhân viên bán hàng "drive informed selling interactions" | [S1] |
| Microsoft Dynamics 365 Commerce | Client book: nhân viên giữ quan hệ dài hạn với khách chủ chốt, ghi sở thích và ngày quan trọng, lọc khách theo tiêu chí để báo hàng mới; tích hợp Customer Insights để gợi ý next best action | [S2] |
| Klaviyo | Hồ sơ khách có predicted CLV, expected next order date và churn risk, dùng để tạo segment "sắp đến hạn mua", "nguy cơ rời bỏ" | [S3] |
| Shopify | Customer object có tags, note, amountSpent, numberOfOrders, consent theo kênh (email/SMS), mergeable; segment viết bằng ShopifyQL | [S4][S5] |
| HubSpot (B2B làm đối chứng) | Lấy contact, company, deal, ticket làm trung tâm; activity gồm call, meeting, note, task, email | [S6] |
| 私域 Trung Quốc (WeCom, Youzan) | Kéo khách từ sàn (Tmall/JD, nơi CAC cao và không sở hữu dữ liệu khách) về kênh của mình; nhân viên chăm khách qua WeCom; quan hệ nhân viên–khách là tài sản của doanh nghiệp (在职/离职继承: khi nhân viên nghỉ thì khách được chuyển cho người khác) | [S7][S8][S9] |
| Sapo / Haravan (VN) | Phía POS: loyalty gồm tích điểm, hạng thẻ, chiết khấu theo hạng tại quầy và trên website | [S10] |

**Nhận định.** Có hai trường phái. (a) **Marketing-CRM** (Klaviyo, Shopify) tự động hoá thông điệp hàng loạt qua email/SMS. (b) **Clienteling-CRM** (Salesforce, Microsoft, WeCom) cho nhân viên quan hệ 1-1 với một tệp khách. Với SME TMĐT Việt Nam, kênh chính là gọi điện và Zalo, đội 5–15 người, AOV cao (TPCN ~ tiền triệu), khách mua theo liệu trình, nên **trường phái (b) phù hợp hơn**. Trường phái (a) dùng như kênh phụ (ZNS, broadcast của sàn). Lựa chọn này khớp với hướng Fine Japan đang đi (worklist, call cockpit).

### 2.2 Bảy job của CRM bán lẻ SME (xếp theo giá trị)

| # | Job | Câu hỏi nghiệp vụ | Khác CRM B2B ở đâu |
|---|---|---|---|
| J1 | **Bán lại cho khách cũ** (reorder, nhắc liệu trình, khách mua lần 2) | "Hôm nay gọi ai, nói gì, đáng bao nhiêu tiền?" | Không có deal hay pipeline; tín hiệu đến từ chu kỳ mua |
| J2 | **Win-back** khách sắp rời hoặc đã rời | "Ai đáng kéo lại, ai nên bỏ (margin âm, B2B nhầm)?" | Cần margin để không tặng voucher lỗ |
| J3 | **Biến khách bị che thành khách liên hệ được** (HUG) | "Khách sàn nào có thể thoát mask, qua kênh nào?" | Đặc thù marketplace; B2B không có |
| J4 | **Nhận diện khách đặc biệt**: sỉ ẩn, người nhận quà, đại lý | "Ai mua cho người khác hoặc mua để bán lại?" | B2B có Account; bán lẻ phải *phát hiện* qua hành vi |
| J5 | **Chăm sóc và dịch vụ** (khiếu nại, hướng dẫn dùng) | "Khách này đang có vấn đề gì chưa xử lý?" | Service gắn trực tiếp vào bán lại |
| J6 | **Chứng minh hiệu quả** | "Bao nhiêu doanh thu thật sự nhờ CRM và nhờ ai?" | Cần holdout; B2B quy công cho deal owner |
| J7 | **Giữ tài sản khách khi nhân sự thay đổi** | "Nhân viên nghỉ thì khách và lịch sử đi đâu?" | WeCom 离职继承 là mẫu tham chiếu [S8] |

Loyalty và tích điểm **không nằm trong job lõi** của CRM ta. Đó là chức năng tại điểm giao dịch, và Sapo Loyalty đã làm, kể cả chiết khấu theo hạng trên website (cập nhật 08/2026) [S10]. CRM chỉ cần **đọc** hạng thẻ từ warehouse.

---

## 3. Năng lực cốt lõi: xếp hạng cho SME

Thang đo: **Must** (thiếu thì CRM không làm được J1–J3), **Should** (làm trong 1–2 quý), **Defer** (hoãn hoặc giao cho hệ khác).

| # | Năng lực | Hạng | Lý do | Fine Japan hiện có |
|---|---|---|---|---|
| C1 | **Golden record và identity resolution** (party + nhiều identity + merge có undo) | Must | Không có nó thì mọi chỉ số đều sai; khách VN có nhiều SĐT, nhiều mã Sapo, ID sàn | Có, mạnh (merge log và snapshot undo, E.164) nhưng **3 bảng chồng nhau** (mục 9) |
| C2 | **Action queue → worklist cho nhân viên** (tín hiệu warehouse, claim, snooze/dismiss có TTL) | Must | Là J1/J2; khác biệt cốt lõi so với "sổ danh bạ" | Có, rất kỹ (S01, R8, R15, dismiss TTL) |
| C3 | **Ghi nhận tiếp xúc** (activity + kết quả + lý do + task hẹn lại, một đường ghi) | Must | Dữ liệu này chỉ CRM có; nuôi lại warehouse (`stg_crm__last_contact`) | Có (call cockpit, `execute_side_effects`) |
| C4 | **Contactability và consent** theo contact point × kênh × mục đích, có bằng chứng | Must | Luật 91/2025 và Nghị định 356 yêu cầu chứng minh consent; HUG chính là bài toán contactability | Chỉ có enum `consent_contact` cấp party và `contact_quality`, **chưa đạt** |
| C5 | **Segment và chiến dịch** có target, trạng thái và nhóm đối chứng (holdout) | Must | Để làm J2/J3 theo lô và đo được lift | Có segment và campaign, có HUG campaign riêng; **không có holdout** |
| C6 | **Đo quy công** (doanh thu sau tiếp xúc, theo nhân viên, theo chiến dịch) | Must | J6; không đo được thì chủ shop bỏ CRM | Có conversion window R11, **dễ quy công thừa** (mục 8) |
| C7 | Tag và custom field có quản trị | Should | Làm giàu hồ sơ không cần migration | Có (registry, tag governance, ACL sync với Sapo) |
| C8 | Phân quyền và quyền sở hữu khách | Should (thành Must khi có agent hoặc nhiều chi nhánh) | Mục 5 | Chỉ có role "informational", ủy quyền dựa trên assignee; Cloudflare Access ở cổng vào |
| C9 | API, CLI và MCP cho agent | Should (theo định hướng sản phẩm của user thì là Must) | Mục 6 | Khoảng 5 route `/api/*`; không có CLI nghiệp vụ, không có MCP |
| C10 | Kịch bản tiếp cận (approach script do AI sinh, có cổng cảnh báo) | Should | Tăng chất lượng cuộc gọi; pack `sales_playbook` còn thử nghiệm | Có (R14 warn-with-ack) |
| C11 | Ghi ngược về POS/OMS (tag, nhóm khách, ghi chú) | Defer | Lợi ích là nhân viên quầy thấy được; rủi ro là phụ thuộc API Sapo | Chỉ có inbound tag sync; "writeback" hiện là CRM → parquet cho warehouse, **chưa ghi vào Sapo** |
| C12 | Omnichannel inbox (Messenger, Zalo OA, chat sàn) | Defer | Pancake hoặc chat sàn đã làm tốt; ToS của sàn cấm xin liên hệ qua chat [nội bộ HUG] | Có bảng conversation/message và Messenger ingest v1 (**chưa rõ mức dùng thật**) |
| C13 | Loyalty, điểm, hạng | Defer, giao cho POS | Sapo Loyalty [S10] | Không có |
| C14 | Gửi tin tự động (ZNS, broadcast) | Defer | Tốn phí theo tin [S11], rủi ro consent; v1 để người bấm gửi | Không có |
| C15 | Ads lead và attribution | Bỏ khỏi CRM, giao cho warehouse | Đây là phân tích; PRD M6 dự kiến nhưng **chưa bao giờ tạo bảng** `crm_ad_*` | Không có |

---

## 4. Mô hình dữ liệu chuẩn

### 4.1 Ranh giới warehouse và CRM

| Bucket | Ví dụ | Ai là nguồn sự thật | CRM ghi? |
|---|---|---|---|
| Giao dịch gốc | order, order line, product, store, POS customer | POS/OMS/sàn, sau đó vào warehouse | Không |
| Insight tính ra | RFM, CLV, next purchase, churn, action queue, nghi B2B, hạng loyalty | Warehouse | Không (chỉ cache read-only kèm `refreshed_at`) |
| Sự thật do người nhập hoặc quyết định | identity link đã xác nhận, consent, note, tag, task, activity, kết quả, owner, dismiss | **CRM** | Có |
| Phản hồi ngược | last_contact, tag flags, hug voucher | CRM export, sau đó warehouse (`stg_crm__*`) | Có (export) |

Nguyên tắc này đã có trong ADR và PRD của Fine Japan (R2, R3, 3 bucket) và khớp với cách Salesforce tách Data Cloud (hợp nhất, tính toán) khỏi Sales/Service (tác nghiệp) [S12]. **Giữ nguyên.**

### 4.2 Mười hai entity lõi (đề xuất chuẩn)

| Entity | Vai trò | Thuộc tính chính | Tham chiếu chuẩn |
|---|---|---|---|
| **Party** | Một người hoặc một tổ chức thật (golden record) | `party_id`, `party_type` (person/org), `display_name`, `status`, `merged_into`, `owner_user_id`, `lifecycle_flags` (đọc từ warehouse) | Salesforce Individual/Account (Party) [S12]; schema.org Person/Organization |
| **ContactPoint** | Một kênh liên hệ của party | `type` (phone/email/zalo/address), `value` chuẩn hoá (E.164), `label`, `is_preferred`, `status` (active/invalid/unreachable), `quality` (real/masked/placeholder), `source` | Salesforce ContactPointPhone/Email/Address [S12]; Shopify defaultPhoneNumber [S4] |
| **IdentityLink** | Ánh xạ ID ngoài (mã khách Sapo, buyer ID sàn, PSID, Zalo UID, HUG token) vào party | `source_system`, `external_key`, `status` (proposed/confirmed/rejected), `confidence`, `evidence`, `confirmed_by` | Salesforce Party Identification [S12]; Segment userId/anonymousId [S13] |
| **PartyRelationship** | Quan hệ giữa các party: mua hộ hoặc tặng quà, nhân viên của (khách sỉ), đại lý | `from_party`, `to_party`, `type` (gift_recipient/buys_for/works_for/reseller_of), `source` (inferred/manual) | Dynamics CDM Connection/Relationship **[chưa chắc tên chính xác]** |
| **ConsentRecord** | Consent theo contact point × kênh × mục đích, append-only | `contact_point_id`, `channel`, `purpose` (care/marketing/sensitive_profile), `status` (granted/withdrawn/denied), `captured_at`, `method` (call/form/QR/Zalo), `evidence_ref`, `captured_by` | Salesforce ContactPointConsent [S12]; Shopify/Klaviyo consent per channel [S4][S14]; Nghị định 356 (bằng chứng: khi nào, cách nào, mục đích gì) [S15] |
| **Activity** | Một tiếp xúc đã xảy ra (call, chat, visit, note hệ thống) | `party_id`, `actor_id`, `channel`, `direction`, `occurred_at`, `outcome`, `outcome_reason`, `body`, `related_order_ref`, `campaign_target_id` | HubSpot engagements (call/note/task/email) [S6] |
| **Task** | Việc cần làm cho một party | `party_id`, `assignee_id`, `due_at`, `status`, `kind`, `source` (action_queue/campaign/manual), `source_ref` (idempotent) | HubSpot task [S6] |
| **ActionState** | Quyết định của người về một tín hiệu warehouse | `party_id`, `action_type`, `state` (claimed/snoozed/dismissed), `until`, `by` | Riêng (đã có R15) |
| **Note / Tag / CustomField** | Làm giàu hồ sơ | Tag có `category`, `sensitivity` (normal/sensitive); custom field có registry | Shopify tags/note/metafields [S4] |
| **Segment** | Định nghĩa tệp (rule trên insight) và snapshot thành viên | `rule_json`, `kind` (dynamic/static), `materialized_at` | Shopify ShopifyQL segment [S5]; Klaviyo predictive segment [S3] |
| **Campaign + CampaignTarget** | Một nỗ lực trên tệp: mục tiêu, kênh, offer, **nhóm đối chứng** | target `status` (queued/contacted/converted/skipped), `arm` (treatment/holdout), `converted_order_ref` | Riêng; HUG đã có ledger voucher |
| **User / Team / AuditEvent** | Nhân viên, nhóm, agent (service principal) và nhật ký mọi lệnh ghi | AuditEvent: `actor_type` (human/agent/system), `on_behalf_of`, `action`, `entity`, `before/after`, `request_id` | MCP spec: "Log tool usage for audit purposes" [S16] |

**Order không phải entity CRM.** CRM chỉ tham chiếu `order_ref` (theo ADR-014 source-system combined identifier) và đọc từ cache.

### 4.3 Bốn ca khó mà chủ shop quan tâm

| Ca | Cách mô hình hoá |
|---|---|
| Khách sàn bị che SĐT | Party có IdentityLink `marketplace_buyer` với ContactPoint `quality=masked`. Khi HUG bắt được SĐT thì tạo ContactPoint mới cùng ConsentRecord `method=QR` và IdentityLink `hug_token` `confirmed`. KPI: tỷ lệ masked → contactable (mục 8) |
| Khách sỉ ẩn | Warehouse gắn cờ `suspected_wholesale` (tần suất, số lượng/SKU, chiết khấu 100%, export). Nhân viên xác nhận thì đổi `party_type=org` hoặc tạo PartyRelationship `works_for`; Campaign loại trừ theo cờ. Fine Japan đã gặp: ~15 tài khoản B2B/export lọt vào tệp bán lẻ [nội bộ HUG] |
| Người nhận quà | Đơn có người nhận ≠ người mua (tên hoặc SĐT giao hàng khác). Warehouse đề xuất, CRM lưu PartyRelationship `gift_recipient` ở trạng thái proposed. **Không** tự đưa người nhận vào tệp marketing khi chưa có consent của chính họ |
| Nhân viên nghỉ việc | `owner_user_id` và task mở được chuyển hàng loạt có audit, giống WeCom 在职/离职继承 [S8]; lịch sử thuộc về doanh nghiệp |

---

## 5. Mô hình phân quyền cho đội nhỏ

Hệ CRM lớn (HubSpot, Salesforce) dùng role kết hợp record ownership kết hợp field-level security. Agent gọi qua MCP thì chạy **dưới quyền của user đã kết nối** (HubSpot remote MCP dùng OAuth 2.1 + PKCE) [S6]. Với đội 5–15 người, đề xuất như sau.

| Role | Đọc | Ghi | Đặc biệt |
|---|---|---|---|
| **Owner** | Tất cả | Tất cả | Xuất dữ liệu, xem dữ liệu nhạy cảm, cấu hình consent purpose |
| **Manager** | Tất cả | Tất cả nghiệp vụ; duyệt merge, identity link, chiến dịch, chuyển khách | Xem dismissals, hiệu suất nhân viên |
| **Staff** (sales/care) | Danh sách: tất cả khách, **SĐT che** (09x\*\*\*\*123); hồ sơ: đầy đủ khi là owner hoặc đã claim | Activity, task, note, tag cho khách mình hoặc khách chưa có chủ; đề xuất identity link | "Hiện SĐT" sinh AuditEvent; không export |
| **Viewer** | Báo cáo, không PII | Không | Dành cho kế toán hoặc đối tác |
| **Agent** (service principal) | Bằng quyền của `on_behalf_of` user, trừ PII nhạy cảm | Chỉ tool được allowlist; thao tác nguy hiểm thì tạo đề xuất | Rate limit, audit bắt buộc |

Quy tắc bổ sung:
- **Quyền sở hữu khách** gồm `owner_user_id` và thời gian bảo hộ claim, để tránh tranh khách. Youzan có khái niệm "导购与客户有明确的归属关系" [S9]; chi tiết về "thời gian bảo hộ" của Youzan **[chưa chắc]**.
- **Dữ liệu nhạy cảm** (tag `health_concern`, ghi chú bệnh lý) cần cờ `sensitivity=sensitive`, chỉ hiển thị cho role được cấp và không xuất sang warehouse dưới dạng định danh.
- Fine Japan hiện có `AuthorizationService` chỉ so sánh assignee và role chỉ mang tính thông tin. Đây là hạt giống tốt, nhưng cần đi qua một policy duy nhất mà cả UI, API và MCP cùng gọi.

---

## 6. Thiết kế agent-friendly: API, CLI, MCP

### 6.1 Kiến trúc

```
domain services (hexagonal, đã có)  ← nguồn quy tắc duy nhất
   ├── REST/JSON  (FastAPI → OpenAPI tự sinh)       ← UI tuỳ biến, tích hợp
   ├── CLI        (client mỏng gọi REST)            ← ops, script, agent cục bộ
   └── MCP server (adapter mỏng gọi cùng service)   ← Claude/agent
UI (HTMX hôm nay; UI sinh theo doanh nghiệp sau)    ← chỉ là một consumer của REST
```

Lý do (KISS/DRY): FastAPI đã sinh được OpenAPI, nên REST gần như có sẵn. MCP và CLI chỉ là adapter, tuyệt đối không chứa logic. Đặc tả MCP yêu cầu server "validate inputs, implement access controls, rate limit, sanitize outputs" và khuyến nghị client "prompt for confirmation on sensitive operations… log tool usage for audit" [S16]. Twenty và HubSpot đều đã có MCP server chính chủ, đi qua OAuth [S6][S17], tức đây đang là chuẩn de-facto của CRM năm 2026.

### 6.2 Mười hai tool MCP tối thiểu

| Tool | Loại | Annotation (MCP) | Guardrail |
|---|---|---|---|
| `search_customers(q, filters)` | đọc | readOnly | SĐT che theo role |
| `get_customer_360(party_id)` | đọc | readOnly | Trả kèm `refreshed_at`; bỏ trường nhạy cảm nếu không có quyền |
| `list_worklist(assignee?, date?)` | đọc | readOnly | "Hôm nay gọi ai, vì sao, đáng bao nhiêu" |
| `get_approach_script(party_id)` | đọc | readOnly | Nếu `recommended=false` thì trả cảnh báo (R14) |
| `claim_action(party_id, action_types)` | ghi | idempotent | Kiểm tra quyền sở hữu |
| `log_contact(party_id, channel, outcome, reason, body, followup_at?)` | ghi | không destructive | Đi qua đúng executor side-effects; idempotency key |
| `create_task / update_task_status` | ghi | idempotent theo key | Assignee mặc định là actor |
| `add_note / set_tags` | ghi | — | Tag nhạy cảm cần quyền riêng |
| `propose_identity_link(party_id, source, key, evidence)` | **đề xuất** | — | Tạo `proposed`; người duyệt mới `confirmed` |
| `record_consent(contact_point_id, channel, purpose, status, method, evidence)` | ghi | — | Bắt buộc có evidence; withdrawn có hiệu lực ngay |
| `list_segment_members(segment_id)` | đọc | readOnly | Giới hạn số dòng, che PII |
| `get_campaign_results(campaign_id)` | đọc | readOnly | Gồm cả lift so với holdout |

**Không mở cho agent ở v1:** merge hoặc unmerge party, xoá, export hàng loạt, gửi tin cho khách, sửa consent thay khách khi không có evidence. Mọi thao tác hàng loạt cần `dry_run=true` mặc định và trả về bản xem trước.

**Audit:** mọi lệnh ghi (UI, API, MCP, CLI) tạo một `AuditEvent` gồm `actor_type`, `on_behalf_of`, `tool`, `request_id`, diff. Lưu ý rằng annotation chỉ là gợi ý, vì "clients MUST consider tool annotations untrusted" [S16]. Quyền phải được kiểm tra ở server.

---

## 7. Chỉ số chứng minh giá trị

| Tầng | Chỉ số | Định nghĩa gợi ý | Ghi chú |
|---|---|---|---|
| **North star** | **Doanh thu tăng thêm từ khách do CRM quản lý** | (doanh thu nhóm được tiếp xúc − nhóm holdout) / nhóm, trong cửa sổ N ngày | Bắt buộc có holdout; HUG docs cũng yêu cầu "Holdout bắt buộc" |
| Kết quả | Repeat purchase rate theo cohort (90/180 ngày) | % khách có đơn ≥2 trong cửa sổ | Benchmark vendor: trung bình ~28%, hàng tiêu hao 35–55% [S18] **[độ tin cậy thấp]** |
| Kết quả | Tỷ lệ chuyển sang đơn thứ 2 | % khách mới mua đơn 2 trong 30–60 ngày | Fine Japan có tier SECOND_ORDER |
| Kết quả | Tỷ lệ kéo lại khách lapsed | % khách lapsed có đơn trong 60 ngày sau tiếp xúc | So với holdout |
| Tài sản | **Contactable rate** | % khách có ít nhất 1 contact point `real` cùng consent `granted` | KPI riêng của TMĐT VN; Fine Japan có 3.428/7.565 khách bị che |
| Tài sản | Masked → contactable | Số khách thoát mask mỗi tháng (HUG) | |
| Vận hành | Action-to-contact SLA | % action có activity trong 3 ngày | Đã có trong PRD Fine Japan |
| Vận hành | Contact-to-order conversion theo nhân viên | Đơn trong N ngày sau tiếp xúc thành công | Dùng để quy công (re-sale attribution) |
| Vận hành | Adoption | Số nhân viên ghi activity mỗi tuần | |
| Guardrail | Tỷ lệ opt-out hoặc khiếu nại, chi phí voucher / CM | Không đẩy doanh thu bằng tiền lỗ | Fine Japan đã phát hiện voucher 50K lớn hơn CM ở đơn nhỏ |

**Lỗi quy công cần tránh:** R11 hiện tại tính *mọi* đơn sau `scheduled_at` là converted. Với khách mua lặp mỗi 7 ngày (median của nhóm masked-repeat theo tài liệu HUG), cách này sẽ quy công thừa rất nhiều. Cần thêm ba thứ: (1) chỉ tính sau **tiếp xúc thành công**, (2) cửa sổ có trần (ví dụ 14–30 ngày), (3) báo **lift so với holdout**, không báo conversion thô. Con số "5% retention tăng 25–95% lợi nhuận" (Reichheld/Bain) hay được trích dẫn, nhưng chỉ là trích thứ cấp [S19]. **Không nên dùng làm cam kết với khách hàng.**

---

## 8. Khuyến nghị: lõi CRM chuẩn và so sánh các phương án

### 8.1 Trade-off matrix (điểm 1–5, cao hơn là tốt hơn)

| Tiêu chí | **A. Chuẩn hoá app Fine Japan thành pack `crm` core** | B. Dựng trên CRM OSS (Twenty) | C. CRM hoặc loyalty VN có sẵn (Sapo/Haravan/Pancake…) | D. Marketing automation (kiểu Klaviyo) |
|---|---|---|---|---|
| Khớp job J1–J3 (worklist từ warehouse, HUG, masked) | 5 | 2 (thiên về B2B: company, opportunity) | 2 | 2 (email-centric) |
| Tích hợp warehouse hoặc tín hiệu | 5 (đã chạy) | 3 | 1 | 3 |
| Agent-ready (API/MCP) | 2 hôm nay, 4 sau chuẩn hoá | 4 (có MCP và API) [S17] | 1–2 **[chưa chắc]** | 3 |
| Chi phí xây hoặc bảo trì | 3 | 2 (fork và tùy biến nặng) | 5 | 3 (phí theo contact) |
| Kiểm soát dữ liệu và tuân thủ VN | 5 | 4 (tự host) | 3 | 2 (dữ liệu ra nước ngoài) |
| Rủi ro áp dụng | Thấp (đã dùng thật) | Trung bình (license AGPL **[chưa chắc]**, lệch domain) | Thấp, nhưng bị lock-in | Cao (không phù hợp kênh VN) |
| **Xếp hạng** | **1** | 3 | 2 (bổ trợ cho loyalty, inbox) | 4 |

**Chọn A, kết hợp C ở rìa.** Giữ loyalty ở Sapo và inbox ở Pancake hoặc chat sàn; CRM chỉ lưu tham chiếu và kết quả.

### 8.2 Lõi tối thiểu (v1 sản phẩm)

- **Entity:** 12 entity ở mục 4.2.
- **Năng lực:** C1–C6, cùng C8 và C9 (vì định hướng agent-first).
- **API:** REST cho mọi entity (OpenAPI), CLI mỏng và 12 tool MCP ở mục 6.2.
- **Cấu hình theo tenant** (không hard-code): danh mục tag (kể cả `health_concern`), purpose của consent, loại action, mapping tag Sapo, kịch bản.

### 8.3 Đối chiếu app Fine Japan: giữ, chuẩn hoá, bỏ

| Thành phần hiện có | Quyết định | Ghi chú |
|---|---|---|
| Hexagonal, composition root, ports | **Giữ** | Là nền để thêm adapter REST/MCP mà không lặp logic |
| Party, merge log với snapshot undo (R4), E.164 (R5), fuzzy chỉ tạo candidate (R9) | **Giữ** | Đúng chuẩn ngành |
| `crm_party_identity` + `crm_party_external_id` + `crm_identity_link` | **Chuẩn hoá thành ContactPoint + IdentityLink** | Chính code ghi rằng `crm_party_external_id` "never written"; identity_type đang trộn kênh liên hệ (phone/email) với ID ngoài (sapo_customer/psid) |
| Worklist, action state, dismiss TTL (R15), executor side-effects duy nhất | **Giữ** | Đây là lợi thế khác biệt lớn nhất |
| Activity draft → finalize, outcome_reason | **Giữ**, đổi tên chuẩn `activity` | Migration 0028 đã đổi sang `activity_log`; chốt một tên trong contract công khai |
| `consent_contact` enum cấp party | **Thay bằng ConsentRecord ledger** | Luật 91/2025 và Nghị định 356 [S15][S20] |
| Tag và custom field registry, tag governance | **Giữ**; thêm `sensitivity` | Seed `health_concern` chuyển sang tenant config |
| Segment, campaign, campaign_target + `crm_hug_campaign*` | **Gộp** thành một Campaign có `type` (reactivation/hug/…) và `arm` holdout | Bỏ trùng lặp DRY |
| Conversion R11 | **Sửa** (tiếp xúc thành công, cửa sổ trần, holdout) | Mục 7 |
| Approach script và R14 | **Giữ** dưới dạng tool đọc; pack `sales_playbook` vẫn là thử nghiệm | |
| Messenger ingest và inbox | **Hoãn**; chỉ giữ liên kết conversation → party | Chưa rõ mức sử dụng; xem câu hỏi mở |
| Ads (PRD M6) | **Bỏ khỏi CRM** | Chưa từng có bảng; thuộc warehouse |
| Role `admin|rep|viewer` / `sales|care|manager|admin` (2 tập không khớp nhau giữa tài liệu và code) | **Chuẩn hoá** về owner/manager/staff/viewer/agent | Có thêm Cloudflare Access ở cổng vào |
| "Sapo write-back" | **Đổi tên rõ** thành `crm_export` (CRM → warehouse); việc ghi vào Sapo thật là Defer | Tránh nhầm phạm vi |
| UI Jinja2/HTMX | **Giữ làm UI tham chiếu**, chuyển sang gọi qua REST dần | Đúng hướng "UI là lớp trên, sinh theo doanh nghiệp" |

### 8.4 Thứ tự đề xuất

1. Contract (OpenAPI + entity chuẩn) cùng AuditEvent và policy phân quyền. Đây là điều kiện cho mọi việc khác.
2. Gộp identity, thêm ConsentRecord và PartyRelationship (có migration dữ liệu).
3. MCP server (12 tool) và CLI.
4. Holdout và quy công mới.
5. Tách mọi giá trị riêng của Fine Japan ra cấu hình tenant (theo ADR-017).

---

## 9. Rủi ro áp dụng

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Lưu "tình trạng sức khỏe" (tag health_concern) mà không có consent riêng | **Cao** (pháp lý) | Cờ sensitive, consent purpose riêng, hạn chế role, xin tư vấn luật |
| Gộp 3 bảng identity làm vỡ HUG hoặc export dbt (`stg_crm__*` là public) | Trung bình | Giữ view tương thích; chạy shadow gate |
| MCP mở lệnh ghi khiến agent ghi sai hàng loạt | Trung bình | Allowlist, dry-run, propose-then-approve, rate limit, audit |
| Quy công thừa làm chủ shop mất niềm tin | Trung bình | Holdout bắt buộc trong báo cáo |
| Chuẩn hoá quá sớm khi mới có 1 tenant | Trung bình | Chỉ chuẩn hoá phần đã chạy thật ở Fine Japan; phần còn lại để cấu hình |
| Hệ sinh thái MCP thay đổi nhanh (spec 2025-06-18 → các bản sau) | Thấp | MCP chỉ là adapter mỏng |

---

## 10. Giới hạn của nghiên cứu

- **Chưa đọc nguyên văn** Luật 91/2025/QH15 và Nghị định 356/2025, chỉ qua phân tích của Tilleke, EY, Apolat và Vietnam Briefing. Không có nguồn nào nêu điều khoản riêng về **marketing trực tiếp**, kênh gọi điện hay Zalo. Đây là **[chưa chắc]** quan trọng nhất.
- Không tìm được tài liệu chính thức về Youzan/Weimob, quy tắc quy công nhân viên của Youzan, hay chính sách ZNS (điều kiện người nhận); nguồn về WeCom chủ yếu từ vendor tư vấn.
- Benchmark repeat rate lấy từ blog vendor, chỉ mang tính định hướng; chưa có số liệu ngành TPCN Việt Nam.
- Chưa đo mức sử dụng thật của từng màn hình hay bảng Fine Japan (vì không đọc DB). Các quyết định "hoãn inbox" và "gộp campaign" cần dữ liệu sử dụng xác nhận.
- Chưa đánh giá chi tiết Haravan, KiotViet, Nhanh hay Pancake CRM và license của Twenty.
- Không gọi được Skill Hub `skill_resolve` trong phiên này (tool không khả dụng), nên nghiên cứu dùng web search/fetch trực tiếp.

---

## 11. Câu hỏi còn mở

1. Fine Japan có muốn giữ tag tình trạng sức khỏe không? Nếu giữ thì cần quy trình xin consent riêng và người chịu trách nhiệm DPO; cần ý kiến luật sư về Nghị định 356.
2. Gọi điện hoặc nhắn Zalo cho khách cũ để bán lại cần consent "marketing" riêng, hay dựa được vào quan hệ mua bán? Văn bản chưa rõ ở nguồn thứ cấp.
3. Inbox Messenger trong CRM có đang được CSKH dùng hằng ngày không? Nếu không thì hoãn hoặc bỏ.
4. Chính sách quyền sở hữu khách: staff có được xem SĐT của khách không thuộc mình không? Thời gian bảo hộ sau claim là bao lâu?
5. Holdout bao nhiêu phần trăm là chấp nhận được với chủ shop (doanh thu "bỏ lỡ" ngắn hạn)?
6. Ghi ngược vào Sapo (tag hoặc nhóm khách cho nhân viên quầy) có thật sự cần ở v1 không, hay chỉ cần warehouse → Sapo qua tag sync hai chiều?
7. Tenant #2 dự kiến là ngành gì? Nếu không phải TPCN thì danh mục tag, purpose và action type càng phải là cấu hình.

---

## Nguồn (truy cập 2026-10-14)

- [S1] Salesforce, Retail Clienteling: https://www.salesforce.com/retail/clienteling/
- [S2] Microsoft Learn, Clienteling overview (Dynamics 365 Commerce): https://learn.microsoft.com/fr-fr/dynamics365/commerce/clienteling-overview ; Store Commerce capabilities: https://learn.microsoft.com/th-th/dynamics365/commerce/store-commerce-capabilities
- [S3] Klaviyo Help, Understanding predictive analytics: https://help.klaviyo.com/hc/en-us/articles/360020919731 ; https://www.klaviyo.com/solutions/ai/predictive-analytics-for-ecommerce
- [S4] Shopify Admin GraphQL, Customer object: https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer
- [S5] Shopify Help, Customer segments: https://help.shopify.com/en/manual/customers/customer-segmentation/customer-segments
- [S6] HubSpot Developers changelog, Remote HubSpot MCP server GA: https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available ; https://lagrowthmachine.com/hubspot-mcp/
- [S7] ITC, Ultimate Guide to WeCom clienteling (vendor): https://it-consultis.com/insights/wecom-wechat-work-guide/ ; Galeries Lafayette case: https://it-consultis.com/projects/galeries-lafayette-wecom-clienteling/
- [S8] 企业微信 客户联系 API (在职/离职继承, 客户标签): https://apifox.com/apidoc/docs-site/406014/doc-417828 ; woshipm: https://www.woshipm.com/operate/5788159.html
- [S9] 36kr / Youzan vivo case (导购与客户归属关系): https://www.36kr.com/p/1545254837350405
- [S10] Sapo, Chiết khấu hạng thẻ với Sapo Loyalty: https://www.sapo.vn/cap-nhat-tinh-nang/Ap-dung-chiet-khau-hang-the-tren-website-voi-Sapo-Loyalty ; Loyalty trên Máy Bán Hàng: https://www.sapo.vn/cap-nhat-tinh-nang/tinh-nang-loyalty-tren-may-ban-hang
- [S11] Nhanh.vn, Các loại tin của OA / ZNS: https://pos.manual.nhanh.vn/pos/cai-dat/gui-zalo-zns/cac-loai-tin-cua-oa ; FPT Shop, Zalo ZNS: https://fptshop.com.vn/tin-tuc/thu-thuat/zalo-zns-la-gi-174686
- [S12] Salesforce Data Cloud, Contact Point Phone DMO: https://developer.salesforce.com/docs/data/data-cloud-ref/guide/c360dm-contact-point-phone-dmo.htm ; Contact Point Consent DMO: https://developer.salesforce.com/docs/atlas.en-us.246.0.c360a_api.meta/c360a_api/c360dm_contact_point_consent_dmo.htm ; Trailhead Map Required Objects: https://trailhead.salesforce.com/content/learn/modules/data-and-identity-in-salesforce-cdp/map-required-objects
- [S13] Twilio Segment, Identify spec: https://www.twilio.com/docs/segment/connections/spec/identify
- [S14] Klaviyo, Collect email and SMS consent via API: https://developers.klaviyo.com/en/v2023-09-15/docs/collect_email_and_sms_consent_via_api ; Consent in profiles: https://help.klaviyo.com/hc/en-us/articles/360037101072
- [S15] Vietnam Briefing, Decree 356 key requirements: https://www.vietnam-briefing.com/news/vietnam-personal-data-protection-regulation-decree-356.html ; EY Vietnam legal alert 03/2026: https://www.ey.com/en_vn/technical/tax/tax-and-law-updates/legal-alert-march-2026-decree-no-356-2025-nd-cp-providing-detailed-guidance-for-implementation-of-personal-data-protection-law
- [S16] Model Context Protocol spec 2025-06-18, Tools: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- [S17] Twenty CRM MCP (folk.app): https://www.folk.app/ko/articles/twenty-crm-mcp ; jezweb twenty-mcp: https://lobehub.com/mcp/jezweb-twenty-mcp
- [S18] Rivo, Repeat purchase rate benchmarks: https://rivo.io/blog/repeat-purchase-rate-complete-guide ; Eightx, by vertical: https://eightx.co/blog/average-ecommerce-repeat-purchase-rate-by-vertical-2026 ; Focus Digital: https://focus-digital.co/average-returning-customer-percentage/
- [S19] Trích thứ cấp Reichheld/Bain: https://zenify.vn/blog/retention-profit-impact ; https://www.chiefmarketer.com/customer-retention-the-next-frontier-for-todays-cmo/
- [S20] Tilleke & Gibbins, Vietnam's new PDPL, a closer look: https://tilleke.com/insights/vietnams-new-personal-data-protection-law-a-closer-look ; New decree guidance: https://www.tilleke.com/insights/new-decree-provides-guidance-for-vietnams-personal-data-protection-law ; Apolat Legal: https://datatech.apolatlegal.com/?p=557
