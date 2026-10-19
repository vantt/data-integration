---
title: "Lõi CRM chuẩn ngành, agent-native, chuyển từng bước"
description: "Đưa CRM Fine Japan thành lõi CRM chuẩn ngành (Party, vai trò, quan hệ, contact point, consent có bằng chứng, engagement, module cắm thêm) dùng được cho agent qua REST, CLI, MCP; làm theo 12 phase, sau mỗi phase CRM vẫn chạy như cũ."
status: pending
priority: P1
effort: 46d
branch: feat/crm-core-agent-native
tags: [crm, agent, mcp, api, data-model, consent, pdpl, cache-contract, migration]
blockedBy: []
blocks: []
created: 2026-10-19
---

# Lõi CRM chuẩn ngành, agent-native, chuyển từng bước

## Tổng quan

User chốt ngày 19/10/2026: chuẩn hoá dữ liệu CRM theo chuẩn ngành để lõi đỡ được bốn mảng (bán lẻ, bán sỉ, dịch vụ có lịch hẹn, thành viên), ưu tiên đưa CRM tới trạng thái agent dùng được sớm, và làm từng bước để sau mỗi bước CRM vẫn chạy như cũ.

Plan đi theo ba chặng:

1. **An toàn trước (phase 0–1):** công cụ đo "CRM như cũ", công cụ chạy migration down, bước an toàn cho tag sức khoẻ và bật chặn CSRF.
2. **Agent dùng được (phase 2–4):** danh tính theo người/agent, một policy quyền, audit, idempotency; rồi agent **đọc** (REST v1, CLI, MCP); rồi agent **ghi an toàn** và mô hình đề xuất → người duyệt.
3. **Tái cấu trúc dữ liệu sâu (phase 5–11):** hợp đồng cache chuẩn từ kho; tách identity thành ContactPoint + PartyIdentifier; sổ cái consent và phân loại dữ liệu; vai trò, quan hệ và khách sỉ ẩn; Engagement và cơ chế module; gộp campaign Hug, holdout, quy công; hợp đồng export CRM → kho, dọn bảng cũ, kiểm khả chuyển Postgres.

Thiết kế đầy đủ (mô hình dữ liệu, hợp đồng, kiến trúc agent, ánh xạ schema, phương án đã loại): **[design.md](design.md)**.

Plan này thay phần còn lại của các plan cũ mà báo cáo triage 19/10 đề nghị gộp: `260623-2318-crm-csrf-guard` (bật chặn), `260707-2343-crm-tag-deferred-followups`, `260620-1408-crm-hug-voucher-a2-golive` (phần kỹ thuật), `260620-2357-hug-a2-pilot-holdout`, và phần A2 của `260619-1030-crm-nba-resell-engine`. Cập nhật status các plan đó là việc của người điều phối, không thuộc plan này.

## Yêu cầu bắt buộc (cho người thực thi)

1. **Không làm trên checkout prod.** Mỗi phase làm trong worktree từ `main`, nhánh tên mô tả (ví dụ `feat/crm-sensitive-tags-csrf`). Thử trên bản sao DB trong scratch, không mở `crm.db` prod để ghi.
2. **Sau mỗi phase CRM chạy như cũ.** Mỗi phase phải qua ba lớp kiểm: (a) `pytest crm/src/tests crm/sync/tests` xanh; (b) `crm/ops/parity_snapshot.py` trên bản sao DB khôi phục từ backup mới nhất, trước và sau khi áp code của phase, chỉ khác ở các mục phase đó khai báo trước; (c) kiểm sau deploy (mục "Kiểm sau deploy chung" bên dưới).
3. **Không big bang.** Thay đổi dữ liệu theo khuôn expand → backfill → ghi song song → chuyển đọc sau cờ → contract (design §8.1). Mọi migration mới có file `.down.sql` thử được bằng `crm/ops/migration_down.py`.
4. **Backup trước mỗi migration dữ liệu** theo `crm/docs/backup-restore-runbook.md` mục 1–2 (tạo, rồi `restore_verify_crm.py --backup <ts>` phải PASS), sao bản backup đó ra thư mục an toàn để vòng xoay `--keep 7` không xoá.
5. **Không đổi hành vi người dùng ngoài phạm vi đã duyệt.** Chỉ có các thay đổi user đã chốt: tag sức khoẻ theo phương án C + B (design §6.2: thêm loại "quan tâm nhóm sản phẩm" làm mặc định; tag sức khoẻ chỉ gắn khi khách có đồng ý riêng, chỉ người phụ trách/manager/admin xem, có audit, không ra export/báo cáo/agent; không xoá dữ liệu cũ), bật chặn CSRF, quyền của agent, ngữ nghĩa "không liên hệ" theo sổ cái (chỉ bật sau khi user xem số khách bị ảnh hưởng). Mọi thay đổi hành vi khác (ví dụ che SĐT với nhân viên) phải chờ user.
6. **Không ghi plan ID, số phase hay mã finding** vào comment code, tên migration, tên test, commit message. Commit theo conventional commit, không nhắc AI.
7. **Không đọc `.env*`, không đưa dữ liệu khách** (tên, SĐT, địa chỉ) vào plan, report, test fixture hay log. Parity snapshot chỉ in số đếm và hash.
8. **Deploy prod** theo `docs/operations/deployment.md` (phần data_platform: "Refactor deploys (shadow-verified)", dòng 668–748) và quy trình CRM bên dưới, **tránh 02:30–04:00**, giờ do user duyệt. Theo bộ nhớ dự án: người thực thi tự deploy sau khi user duyệt giờ, và commit + push từng phần ngay sau khi gate của phần đó đạt.
9. **Không lách hook.** Hook repo chặn lệnh shell có chữ "target" kèm "/"; nếu bước nào cần lệnh như vậy thì dừng và hỏi user.
10. **Số migration theo dải** để các phase không đụng nhau: phase 1: 0047–0049; phase 2: 0050–0054; phase 4: 0055–0059; phase 6: 0060–0069; phase 7: 0070–0074; phase 8: 0075–0079; phase 9: 0080–0084; phase 10: 0085–0089; phase 11: 0090–0099. Tên file mô tả nội dung, không chứa số phase.
11. **Tài liệu cập nhật cùng commit với code** khi phase đổi hành vi, lệnh, cấu hình hoặc kiến trúc: `crm/AGENTS.md`, `crm/docs/crm-database-schema-reference.md` (đang dừng ở 0014, phase nào đụng bảng thì cập nhật bảng đó), `orchestration/packs/crm/README.md`, ADR-020 (tạo ở phase 2).

## Quy trình deploy CRM (dùng cho mọi phase có deploy)

Code và migration CRM được bind-mount (`docker-compose.yml:285-296`); migration chạy khi container khởi động và lỗi thì container dừng (`crm/entrypoint.sh` bước 1).

1. Kiểm `docker ps` thấy `crm` khoẻ; `GET /admin/refresh/status` không ở trạng thái `running`.
2. Nếu phase có migration dữ liệu: backup + verify + sao ra thư mục an toàn (yêu cầu 4).
3. Ghi SHA hiện tại làm điểm rollback; nếu phase đụng `orchestration/` hoặc `transformation/` thì theo runbook data_platform (dừng `data_platform` trước khi merge).
4. `docker stop crm` (tránh process đang chạy nạp lẫn code cũ/mới), `git merge --ff-only <nhánh>` trên checkout prod, rồi `docker start crm`. Nếu phase đổi `docker-compose.yml` hoặc biến môi trường thì lưu log trước (`docker logs -t crm > <file backup>`) và dùng `docker compose up -d crm`. Nếu phase thêm thư viện Python thì `docker compose build crm` trước (ghim digest base image, xem phase 3).
5. Kiểm sau deploy chung: `docker logs crm` có "migrations OK"; `GET /healthz` 200; lần `/admin/refresh` kế tiếp trả 202 và status `ok`; một người dùng thật thao tác một việc trên UI (xem C360, ghi hoạt động); sáng hôm sau job nightly có 11 asset `crm_*_export` xanh và số dòng `stg_crm__*` trong ngưỡng xu hướng.
6. Rollback: `docker stop crm`, `git revert --no-edit <rollback>..<branch>` trên checkout prod, chạy down của migration phase đó bằng `crm/ops/migration_down.py` nếu phase yêu cầu, `docker start crm`. Chỉ khôi phục từ backup khi down thất bại (mất các ghi sau thời điểm backup, phải báo user).

## Phases

| # | Phase | File | Effort | Phụ thuộc | Đụng prod | Cần user duyệt giờ | Giá trị cho user |
|---|---|---|---|---|---|---|---|
| 0 | Đo hiện trạng, công cụ parity và migration down, chốt câu hỏi | [phase-00](phase-00-baseline-and-safety-tools.md) | 1d | — | Chỉ đọc (backup có sẵn) | Không | Có thước đo "CRM như cũ" cho mọi phase sau |
| 1 | Tag sức khoẻ theo C + B (bản tạm: cờ đồng ý riêng, nhật ký, giới hạn xem, lọc export, loại "quan tâm nhóm sản phẩm") + bật chặn CSRF | [phase-01](phase-01-sensitive-tags-and-csrf.md) | 2.5d | 0 | Có (CRM + data_platform export) | **Có** | Giảm rủi ro pháp lý ngay mà không phá quy trình gắn tag của sales/CS; đóng lỗ CSRF |
| 2 | Principal, credential, policy quyền, CommandBus, audit, idempotency | [phase-02](phase-02-principal-policy-audit.md) | 3.5d | 1 | Có (CRM) | **Có** | Biết ai làm gì trên CRM; nền cho agent |
| 3 | Agent đọc: REST v1, CLI, MCP (đọc) | [phase-03](phase-03-agent-read-api-cli-mcp.md) | 4.5d | 2 | Có (CRM, build lại image) | **Có** | CEO và nhân viên hỏi CRM qua Claude Desktop, bot Lark |
| 4 | Agent ghi an toàn + đề xuất → duyệt | [phase-04](phase-04-agent-safe-writes-and-proposals.md) | 5d | 3 | Có (CRM) | **Có** | Agent ghi kết quả gọi, task, ghi chú; việc nguy hiểm có người duyệt |
| 5 | Hợp đồng cache chuẩn từ kho (v1) | [phase-05](phase-05-warehouse-cache-contract.md) | 5d | 0 (nửa kho); 4 (nửa CRM đọc) | Có (data_platform + CRM) | **Có** | CRM không còn gắn chặt với mart riêng của Fine Japan |
| 6 | Tách identity: ContactPoint + PartyIdentifier, merge mở rộng | [phase-06](phase-06-contact-point-and-identifier.md) | 6d | 5 | Có (CRM, migration dữ liệu) | **Có** | Hết ba bảng identity chồng nhau; nền cho consent theo kênh |
| 7 | Sổ cái consent (chuyển cờ đồng ý riêng của phase 1 sang) + phân loại dữ liệu cho ghi chú, trường tuỳ biến + bật "không liên hệ" theo sổ cái sau khi user duyệt | [phase-07](phase-07-consent-ledger-and-data-class.md) | 4d | 6 | Có (CRM + export) | **Có** | Chứng minh được consent theo Luật 91/2025 |
| 8 | Vai trò, quan hệ, Person/Organization, khách sỉ ẩn | [phase-08](phase-08-party-role-relationship-b2b-lite.md) | 4d | 6 (và 4 cho đề xuất) | Có (CRM + export) | **Có** | Xác nhận khách sỉ, người nhận quà; loại khỏi tệp bán lẻ |
| 9 | Engagement + cơ chế module + module bán lẻ | [phase-09](phase-09-engagement-and-modules.md) | 3.5d | 8 | Có (CRM) | **Có** | Khung để thêm hợp đồng, lịch hẹn, gói mà không sửa lõi |
| 10 | Campaign hợp nhất (gộp Hug), holdout, quy công | [phase-10](phase-10-campaign-holdout-and-hug-merge.md) | 4d | 4, 5 | Có (CRM + export) | **Có** | Đo được doanh thu tăng thêm thật nhờ CRM |
| 11 | Hợp đồng export CRM → kho v1, dọn bảng cũ, kiểm khả chuyển Postgres, tài liệu | [phase-11](phase-11-export-contract-and-cleanup.md) | 3d | 5–10 (mỗi mục ≥ 7 ngày ổn định) | Có (CRM + data_platform) | **Có** | Schema gọn, một nguồn sự thật, sẵn sàng tenant thứ hai |

Tổng: 46 ngày công (khoảng 9–10 tuần một người làm), chưa tính thời gian chờ quan sát 7 ngày giữa các bước contract.

## Phụ thuộc

```text
0 ─► 1 ─► 2 ─► 3 ─► 4 ─┬─► 5(nửa CRM) ─► 6 ─┬─► 7 ─────────┐
│                      │                    └─► 8 ─► 9 ────┼─► 11
└─► 5(nửa kho: model dbt, sync ghi song song) ─┘            │
                       └──────────► 10 (cần 4 và 5) ────────┘
```

Nửa kho của phase 5 (model `crm_contract__*`, bộ sync ghi song song bảng mới) không đụng file của phase 1–4 nên làm song song được sau phase 0. Phase 10 có thể làm song song với 6–9 vì sở hữu file riêng (`campaign_*`, `hug/*`) và dải migration riêng. Một người làm thì đi tuần tự theo số phase.

## Sở hữu file (không hai phase song song đụng cùng file)

| Phase | File sở hữu chính |
|---|---|
| 0 | `crm/ops/parity_snapshot.py`, `crm/ops/migration_down.py`, test của chúng (mới) |
| 1 | migration 0047–0049, `application/sensitive_consent_service.py` (mới), `application/tag_service.py`, `tag_governance_service.py`, `health_domain_collect.py`, `adapters/outbound/sqlite/tag_note_repository.py`, `profile_repository.py` (lọc tag), các screen tag/C360 liệt kê ở phase, `adapters/inbound/http/csrf_guard.py`, `docker-compose.yml` (một dòng), `orchestration/packs/crm/crm_writeback_assets.py` (lọc) |
| 2 | migration 0050–0054, `domain/policy.py`, `application/command_bus.py`, `application/authorization_service.py`, `adapters/inbound/http/auth_dependency.py`, `cf_access_middleware.py`, `composition.py` (đoạn wiring bus), ADR-020 |
| 3 | `adapters/inbound/api_v1/**`, `adapters/inbound/mcp/**`, `application/queries/**`, `crm/ops/crmctl.py`, `crm/src/requirements.txt`, `Dockerfile.crm`, `composition.py` (đăng ký router) |
| 4 | migration 0055–0059, `application/commands/**`, `application/proposal_service.py`, screen "Hàng chờ duyệt" (mới), các handler web gọi service ghi (chuyển sang bus) |
| 5 | `transformation/models/packs/crm/contract/**`, `crm/sync/**`, `adapters/outbound/sqlite/cache_repository.py`, `domain/ports/cache_repository.py`, `scripts/checks/public_models.yaml` |
| 6 | migration 0060–0069, `domain/ports/identity_repository.py` (mới), `adapters/outbound/sqlite/party_repository*.py`, `dedup_repository*.py`, `application/merge_service.py`, `party_seed_service.py`, `sync_parties.py`, `hug/identity_resolver*.py`, các file trong design §7.2 |
| 7 | migration 0070–0074, `application/consent_service.py` (mới), `profile_service.py`, `worklist_query_service.py`, `campaign_repository.py` (đoạn consent), `crm_writeback_assets.py` (bảng consent) |
| 8 | migration 0075–0079, `application/party_role_service.py`, `party_relationship_service.py` (mới), screen C360 phần vai trò/quan hệ |
| 9 | migration 0080–0084, `crm/src/modules/**`, `application/engagement_service.py` (mới), `activity_service.py`, `task_service.py`, `note_service.py` (thêm `engagement_ref`) |
| 10 | migration 0085–0089, `application/campaign_service.py`, `adapters/outbound/sqlite/campaign_repository.py` (phần campaign), `crm/src/hug/campaign_*`, `voucher_*`, screen Hug |
| 11 | migration 0090–0099, `orchestration/packs/crm/crm_writeback_assets.py`, `transformation/models/packs/crm/staging/**`, `crm/ops/check_sql_portability.py`, tài liệu |

`composition.py` được phase 2, 3, 4, 6, 9 sửa; `crm_writeback_assets.py` được phase 1, 2 (lọc principal hệ thống), 7, 8, 10, 11 sửa. Các phase này đều nằm trên chuỗi tuần tự hoặc phải merge `main` mới nhất trước khi sửa; không giao chúng cho hai người song song.

## Tiêu chí chấp nhận (đo được)

1. **CRM như cũ sau mỗi phase:** parity snapshot (trước/sau, cùng bản sao DB) chỉ khác ở mục phase khai báo; 11 export `crm_*_export` cho cùng số dòng và cùng hash nội dung trên bản sao, trừ các lọc dữ liệu nhạy cảm đã khai báo; test hiện có (69 file trong `crm/src/tests`, 2 file trong `crm/sync/tests`) xanh, không test nào bị xoá hay nới để qua.
2. **Agent đọc (sau phase 3):** 9 tool đọc chạy được từ Claude Desktop qua `mcp-remote`; 100% lời gọi có dòng `crm_audit_event`; 0 trường hoặc tag thuộc loại `sensitive` trong mọi phản hồi agent, kể cả với khách đã đồng ý riêng (test tự động quét phản hồi của bộ 30 câu kịch bản); SĐT và tên luôn bị che trong phản hồi agent.
3. **Agent ghi (sau phase 4):** gửi lại cùng `idempotency_key` 3 lần chỉ tạo 1 bản ghi; lệnh nguy hiểm từ agent luôn tạo `crm_proposal` và 0 thay đổi dữ liệu cho tới khi người duyệt; người không có quyền duyệt bị từ chối 403; test chứng minh agent không gọi được tool gửi tin (không tồn tại).
4. **Audit:** mọi lệnh ghi qua UI, REST cũ, REST v1, CLI, MCP, sync đều sinh đúng một `crm_audit_event` có `principal_id`, `channel`, `request_id` (test cho từng kênh).
5. **Pháp lý (sau phase 1 và 7):** tag sức khoẻ không gắn được cho khách chưa có đồng ý riêng qua mọi đường ghi (test từng route trả 403, trigger chặn insert trực tiếp) và gắn được khi đã có (quy trình sales/CS còn nguyên); chỉ người phụ trách, manager, admin thấy tag sức khoẻ ở C360, API 360, danh sách tag; 100% lần gắn, gỡ, xem tag sức khoẻ và ghi nhận đồng ý riêng có dòng nhật ký/audit; 2 lần gắn hiện có còn nguyên trong DB; parquet export, `stg_crm__party_tag`, báo cáo và phản hồi agent không có dòng thuộc loại nhạy cảm; loại `product_interest` có trên picker của mọi khách; mỗi `crm_consent_event` mới có `method`, `evidence_type`, `captured_by` khác NULL.
6. **Identity (sau phase 6):** mỗi dòng `crm_party_identity` có đúng một dòng tương ứng (cùng id) ở `crm_contact_point` hoặc `crm_party_identifier`; tìm khách theo SĐT và theo mã Sapo cho cùng kết quả trước/sau trên 100% khoá của bản sao; merge rồi undo trên bản sao trả về trạng thái giống hệt (hash các bảng liên quan).
7. **Hợp đồng cache (sau phase 5):** với mỗi bảng `wh_*` cũ, phép so theo khoá với bảng hợp đồng mới cho 0 khác biệt ở các cột được ánh xạ; `wh_contract_meta` có phiên bản và `data_as_of` cho từng hợp đồng.
8. **Engagement và module (sau phase 9):** bật/tắt module `b2b_lite` bằng cấu hình không cần sửa code lõi; test dựng module giả `appointment` (chỉ trong test) đăng ký loại engagement, bảng chi tiết và chạy được tạo, đọc, gắn Interaction qua API chung.
9. **Campaign (sau phase 10):** một campaign có holdout chia arm ổn định (cùng party luôn cùng arm khi tạo lại); báo cáo kết quả có lift so với holdout; quy tắc chuyển đổi mới chỉ tính đơn sau tiếp xúc thành công trong cửa sổ có trần.
10. **Khả chuyển (sau phase 11):** `crm/ops/check_sql_portability.py` báo 0 vi phạm ngoài danh sách cho phép đối với migration từ 0047 và adapter mới.

## Rủi ro chính

| Rủi ro | Khả năng × tác động | Giảm thiểu |
|---|---|---|
| Migration dữ liệu làm container không khởi động (hard-fail) giữa giờ làm | Thấp × Cao | Chạy migration trên bản sao trước; deploy ngoài giờ làm do user duyệt; backup đã verify; down đã thử |
| Tách identity làm vỡ export dbt (`stg_crm__*` công khai) hoặc Hug | Trung bình × Cao | Ghi song song; giữ `crm_party_identity` là bảng thật tới phase 11 rồi mới thành view cùng cột; parity export |
| Agent ghi sai hàng loạt | Trung bình × Cao | Lệnh hàng loạt chỉ là đề xuất, chạy thử mặc định, giới hạn số party, audit, thu hồi credential tức thì |
| Dữ liệu cá nhân khách đi tới nhà cung cấp mô hình qua MCP | Chắc chắn (nếu bật) × Cao (pháp lý) | Đã chốt Q2: SĐT và tên luôn che khi tới agent; v1 không có đường mở |
| Build lại image kéo base mới làm đổi phiên bản sqlite/python | Trung bình × Trung bình | Ghim digest base image; kiểm `sqlite3.sqlite_version` trong image mới trước khi deploy |
| Ghi song song hai nơi lệch nhau âm thầm | Trung bình × Trung bình | Parity chạy hằng ngày trong thời gian ghi song song (job nhẹ trong process, chỉ log số khác biệt); chuyển đọc chỉ khi 0 khác biệt 3 ngày liền |
| Hợp đồng cache mới từ dbt đổi số so với mart cũ | Thấp × Trung bình | Model hợp đồng chỉ chọn cột, không tính lại; gate S `--allow-new`; so theo khoá trước khi chuyển đọc |
| Đổi ngữ nghĩa "không liên hệ" (H4, đã chốt Q6) làm thay đổi danh sách gọi | Chắc chắn × Trung bình | Deploy với bộ lọc cũ; báo cáo số khách bị ảnh hưởng; chỉ bật sau khi user duyệt số; rollback bằng một cờ |
| Cờ đồng ý riêng bị ghi cho có, không có đồng ý thật | Trung bình × Cao (pháp lý) | Bắt buộc cách thu thập và bằng chứng; nhật ký người ghi; manager xem được |
| Phạm vi lớn kéo dài, dễ bỏ dở giữa chừng | Trung bình × Trung bình | Mỗi phase tự có giá trị và deploy độc lập; trạng thái dở dang luôn là trạng thái hợp lệ (bảng mới tồn tại, đọc vẫn ở bảng cũ) |

## Rollback

Mỗi phase có rollback riêng trong file phase. Nguyên tắc chung: code rollback bằng `git revert` phạm vi đã deploy; migration chỉ-thêm rollback bằng file down (hoặc để lại bảng rỗng vô hại, ghi rõ trong phase); migration dữ liệu không cần rollback dữ liệu vì bảng cũ vẫn là nguồn đọc cho tới khi chuyển cờ; chuyển đọc rollback bằng đặt lại cờ `old`. Chỉ phase 11 (contract) là bước khó đảo, nên chỉ làm sau 7 ngày ổn định và sau backup đã verify.

## Đã chốt (user, 19/10/2026 ~15:35–15:40)

- **Q1. CSDL:** giữ SQLite cho Fine Japan; schema, migration, repository viết trung lập để chuyển Postgres sau (design §8.2).
- **Q2. PII tới agent:** SĐT và tên khách **luôn che** khi đưa tới agent (tên còn chữ cái đầu + mã khách).
- **Q3. Tag sức khoẻ: phương án C + B** (thay cho "chặn gắn, chỉ admin xem"; design §6.2): loại "quan tâm nhóm sản phẩm" (dữ liệu thường) là mặc định cho sales/CS; tag sức khoẻ thật (`health_concern`, `health_domain`) giữ lại, gắn được khi khách đã có đồng ý riêng `sensitive_profile` có bằng chứng; người xem là người phụ trách khách, manager, admin; mọi lần gắn/xem có audit; không ra export, báo cáo, agent/MCP; không xoá 2 lần gắn hiện có, chỉ ẩn theo quyền. Phase 1 làm bản tạm (cờ đồng ý riêng), phase 7 chuyển sang sổ cái consent.
- **Q4. Người duyệt đề xuất của agent:** manager và admin; đề xuất hết hạn sau 7 ngày.
- **Q6. "Không liên hệ":** lệnh rút lại có hiệu lực tới khi khách đồng ý lại; phase 7 cho user xem số khách bị ảnh hưởng trước khi bật.
- **Q8. Kênh mạng cho MCP và CLI:** LAN + Tailscale qua Caddy, không mở công khai.

## Câu hỏi còn mở (kèm đề xuất)

1. **Q5. Giữ audit bao lâu?** **Đề xuất:** 24 tháng, dọn tự động.
2. **Q7. Mặc định khi chưa có consent:** hôm nay chưa có thông tin là được gọi cả chăm sóc lẫn tiếp thị. Giữ vậy hay chặn tiếp thị khi chưa có consent? **Đề xuất:** giữ cho chăm sóc; tiếp thị chờ ý kiến pháp chế (phase 7 để là cấu hình).
3. **Q9. Holdout:** tỉ lệ bao nhiêu là chấp nhận được, và có đưa go-live A2 (mã HUG50, in tem) vào phase 10 không? **Đề xuất:** 20% (như `wh_deadstock_target.is_holdout`); phase 10 chỉ làm phần kỹ thuật, go-live là việc vận hành riêng.
4. **Q10. Thắt quyền cho người** (staff thấy SĐT che với khách không thuộc mình, research §5): có muốn làm không? **Đề xuất:** chưa làm trong plan này; policy đã sẵn chỗ để bật bằng cấu hình sau.
5. **Q11. Danh mục "quan tâm nhóm sản phẩm":** ai đặt tên và duyệt danh sách (ví dụ "Quan tâm nhóm hỗ trợ giấc ngủ"), và có cần sẵn danh mục trước khi deploy phase 1 không? **Đề xuất:** quản lý bán hàng đặt tên theo nhóm sản phẩm thật đang bán (khoảng 8–12 nhóm, tương ứng 16 tag sức khoẻ hiện có), admin tạo trong `/settings/tags` trước deploy phase 1; tên chỉ nói về sản phẩm, không nói về bệnh.
6. **Q12. Khách chưa có người phụ trách:** theo quy tắc đã chốt, sales gắn tag sức khoẻ cho khách chưa có người phụ trách sẽ không xem lại được tag đó (chỉ manager/admin xem). Có cho người đã ghi nhận đồng ý riêng của khách cũng được xem không? **Đề xuất:** có, giới hạn ở người đã ghi nhận đồng ý đó; mọi lần xem vẫn có audit.
