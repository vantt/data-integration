---
handoff-version: 1
created: 2026-10-21 14:50 ICT
session-role: coordination / planning (does NOT execute or deploy)
language: Vietnamese with the user
supersedes: plans/handoffs/data-platform-coordination-20261015-2128.md
---

# Handoff: điều phối nền tảng dữ liệu FG (21/10/2026)

## Mission and current status

**Vai trò:** session điều phối và lập plan. Chỉ điều chỉnh plan, viết thiết kế, giải thích, gom quyết định của user, rồi chuyển lệnh cho **session thực thi** qua `SendMessage`. Không chạy job, không deploy, không sửa code sản phẩm. Được commit + push các file trong `plans/` (user yêu cầu commit plan thường xuyên).

- Session thực thi: **`fg-dataware-house-c8`** [1f3897], chế độ bypass. c8 tự deploy prod theo runbook **chỉ sau khi user duyệt giờ**; c8 giữ các lịch kiểm buổi sáng (09:13) trong session của nó.
- Session điều phối trước: `fg-dataware-house-47` [dcfa99] (session viết handoff này). Session mới phải nhắn c8 đổi người nhận báo cáo sang tên session mới (xem Exact next actions).
- Trả lời user bằng tiếng Việt, ngắn, rõ, câu đầy đủ, không viết tắt khó hiểu. User đọc kỹ thiết kế và muốn **được phản biện thật** (xem Decisions).

**Đã xong trên prod từ handoff trước (main = origin/main = `fe97b2d2`):**
- Lịch sử giá/tồn phase 2 (D2) deploy gộp 19/10 13:18, cùng công tắc tắt `approach_script_autogen` (setting `APPROACH_SCRIPT_AUTOGEN_ENABLED="false"` trong `orchestration/tenants/fine_japan/config.py`) và log codex giữ 500 ký tự cuối stderr. Báo cáo: `plans/261015-1730-price-inventory-history/reports/deploy-261019-1318-d2-report.md`. Rollback point `aa3a5cfb`.
- Công cụ `resource-meter` (Rust, `tools/resource-meter/`, systemd unit trên host) cài 18/10 00:32, chạy ổn; bản sửa `aa3a5cfb` (CPUQuotaPeriodSec=1s, status báo throttle theo thời gian) **đã ở main nhưng user chưa cài lại**.
- Weekly Pulse gửi thật lần đầu 19/10 07:04 vào nhóm Lark lãnh đạo; số hợp lý.

**Đang chạy:**
- Bộ máy phân loại: parity **đêm 6/7 đạt** (21/10). **Đêm 7 = sáng 22/10**; nếu đạt, xin user giờ chuyển cột `customer_type` (phase 7 plan taxonomy).
- Plan dashboard tồn kho (`plans/261015-1815-inventory-dashboards-on-snapshots/`): đã duyệt, QĐ-TK-01..07 chốt theo đề xuất, giữ N = 7 đêm chụp; c8 code được (sau D2), deploy khi đủ 7 đêm.
- c8 còn: DR phase 2–4, report phase 05 (thí điểm Weekly Pulse 4 tuần tới ~09/11).

## Scope and guardrails

- Checkout prod `/home/vantt/app/fg-dataware-house` bind-mount vào container: **sửa file ở đây là sửa prod**. Session điều phối chỉ sửa `plans/` (và memory). Stage đúng file, không `git add -A`.
- Prod chỉ đổi qua runbook `docs/operations/deployment.md`, tránh 02:30–04:00, rollback bằng `git revert`.
- Không đọc/in `.env*`/secret; user tự đặt secret bằng lệnh không echo. Không đưa dữ liệu khách hay email cá nhân của user vào file commit.
- Không commit `.claude/settings.json`, `.claude/*`, `.agentkit/`.
- Commit: conventional, không plan ID/số phase trong code/test/commit message; kết thúc bằng dòng Co-Authored-By theo hướng dẫn của harness.
- Hook repo chặn lệnh shell chứa chữ "target" kèm "/". **Không lách hook** (glob, docker exec…); mọi prompt giao việc cho c8/worker phải ghi rõ điều này (memory `worker-prompts-forbid-hook-bypass`).
- Feature branch phải rebase lên main mới trước khi ff; kiểm `git merge-base --is-ancestor main <branch>` thay vì tin báo cáo (c8 từng báo nhầm "ff được").

## Current state

Quan sát 21/10/2026 14:50:
- `main` = `origin/main` = `fe97b2d2`. Chỉ `.claude/settings.json` sửa (của user) và ~110 file untracked trong `.claude/`, `.agentkit/` (cố ý không commit).
- Worktree của c8: `fg-dw-baseline` (b0931f33, shadow), `fg-dw-dr` (feat/backup-offsite-dr 4e330772), `fg-dw-meter` (feat/resource-meter aa3a5cfb, đã lên main), `fg-dw-price` (fix/approach-autogen-switch 371461cf, đã lên main, không upstream — không mất gì), `fg-dw-report` (feat/report-productization f7b59ef2), `fg-dw-taxo` (feat/taxonomy-engine d31d51f2).
- Container `data_platform`, `crm`, `metabase` healthy. `resource-meter` active.
- Nightly gần nhất 21/10 03:00: 60/60, 2,4 phút, bước dbt 37,0 s, chỉ 3 check Google Sheet đỏ đã biết, oom_kill 0.

## Decisions and rationale (mới từ 15/10, đã ghi vào plan tương ứng)

**Vận hành / dữ liệu**
- RAM bỏ khỏi điều kiện dừng 4 của taxonomy (đo một lần sau deploy +2%; `memory.peak` cộng dồn + page cache, không so được). Điều kiện thời gian xét theo **bước dbt**, không tổng nightly. Mỗi đêm kiểm oom_kill = 0.
- Nới gate `dfa3a0f3` (asset cũ bắt đầu đại diện một dbt source mới = thêm mới) được chấp nhận.
- Đơn Sapo cũ sửa hàng loạt 18/10: không đổi số (chỉ modified_on, dữ liệu khách nhúng, thứ tự fulfillment).
- Backup FJ: user là admin Workspace FJ; **user giữ khoá tạm**, sau giao người FJ (key add rồi mới key remove). Nguyên tắc "khách giữ khoá" giữ.
- Report: QĐ-21 = so cùng số ngày (WTD vs WTD); lỗi lệch 1 ngày chỉ số tiến độ GMV ghi vào `plans/261014-2225-report-productization/definition-decisions.md`; cả hai đi cùng đợt QĐ-18/20 qua gate S (chưa làm).
- MCP CEO: dùng Claude Desktop + bot Lark; "lợi nhuận" mặc định **CM2** và nêu rõ bậc; số hằng đêm đủ.
- Taxonomy: hiện chưa có báo cáo FJ nào dùng chốt thưởng.

**Công cụ đo tài nguyên** (`plans/261016-1543-resource-meter/`): đã duyệt, đang phase 4 quan sát. Lấy mẫu 250 ms khi có dbt, chỉ ghi model ≥ 0,1 s, có `serde_json`.

**CRM (trọng tâm hiện tại)**
- Rà 12 plan CRM cũ: `plans/reports/review-261019-1413-crm-plans-triage.md`. Không code nào ngoài main; HUG 0 request từ 10/08; CSRF log-only 0 cờ từ 10/08.
- User muốn **chuẩn hoá cấu trúc dữ liệu CRM chuẩn ngành, lõi rất chuẩn, mở rộng được cho 4 mảng** (bán lẻ B2C, bán sỉ B2B, dịch vụ có lịch hẹn, thành viên/thuê bao); **làm từng bước, sau mỗi bước CRM chạy như cũ**; **ưu tiên kỳ này: CRM agent-native**.
- Thiết kế + plan: `plans/261019-1500-crm-core-agent-native/` (`design.md` + 12 phase, **48 ngày công**). Lõi Party/Role/Relationship/ContactPoint/PartyIdentifier/Consent ledger/Interaction-Task-Note/Engagement/Tag-Segment-Campaign/Principal-Audit-Proposal; module cắm thêm theo mảng; hợp đồng cache warehouse↔CRM chuẩn; expand → ghi song song → chuyển đọc → contract; công cụ parity ở phase 0.
- Đã chốt trong plan CRM: SQLite giữ, code trung lập Postgres; che SĐT và tên khi tới agent; "không liên hệ" rút lại có hiệu lực tới khi đồng ý lại (cho user xem số khách ảnh hưởng trước khi bật); MCP/CLI qua LAN + Tailscale + Caddy; người duyệt đề xuất của agent = manager + admin, hết hạn 7 ngày; **UUIDv7** cho mọi id mới (helper riêng, không viết lại id cũ); tag sức khoẻ theo **C + B** (mặc định tag "quan tâm nhóm sản phẩm" do **sales/CS tự đặt tên** trong CRM; tag sức khoẻ thật chỉ gắn khi khách đồng ý riêng, xem: người phụ trách + manager + admin, khách chưa có người phụ trách thì người ghi nhận đồng ý được xem, agent không bao giờ thấy, không ra export/báo cáo).
- **MCP chạy code mode:** chỉ 2 tool `search_api` + `execute`; sandbox = **Pydantic Monty** (pydantic-monty 1.2.0, MIT, worker là binary Rust; agent viết Python); dự phòng `quickjs-rs` (user chấp nhận agent viết JS). Research: `plans/reports/research-261019-1905-agent-code-sandbox-options.md`. Đã loại: Deno (to), tự viết sandbox Rust/QuickJS (QuickJS-ng nhiều CVE 2026), Perplexity Sandbox/SPACE (cloud, nặng).
- **Code mode là thư viện Python độc lập trong repo** (không repo riêng): plan `plans/261020-1310-agent-codemode-host/` (**11 ngày công**), tạm đặt `packages/agent-codemode/`, luật ranh giới cấu hình qua `scripts/checks/libraries.yaml`, cài vào image bằng pip như hiện tại; uv workspace khi có ≥ 2 pyproject. MCP server CRM ở `crm/codemode_server/`, chạy sidecar `crm_codemode` có trần RAM. Plan CRM chỉ phase 3 bị chặn bởi thư viện bản 0.1.0.
- **Bố cục repo chưa chốt:** user muốn đóng gói **theo bộ chức năng** (kho dữ liệu, report, CRM); `packages/`/`apps/` để thiết kế Đợt 2 quyết (roadmap `plans/261013-1751-modularize-data-platform-suite/roadmap.md`, mục Đợt 2). Không dời app hiện có trước đó.

## Verification

- Mọi plan đã commit + push (commit gần nhất của điều phối: `eb97ecad`, `0593a2d8`; c8: `fe97b2d2`).
- Đã tự kiểm: main ff sau mỗi deploy, container healthy, unit resource-meter active, Monty 1.2.0 trên PyPI.
- Chưa kiểm trực tiếp: số trong báo cáo c8 (tin theo báo cáo, đã đối chiếu git/docker khi có thể).

## Open risks and blockers (câu chờ user)

1. **Giờ chuyển cột phân loại** ngày 22/10 nếu đêm 7 đạt (tránh 02:30–04:00).
2. **Mốc thời gian bộ máy phân loại:** xét riêng các model `lbl_*` (điều phối đề xuất, có số từng model từ resource-meter) hay 36,5 s cho cả bước dbt (c8 đề xuất). Cả hai đều đạt đêm nay.
3. **Duyệt plan CRM core + plan thư viện code mode** để c8 bắt đầu phase 0 của cả hai (song song với việc khác).
4. **resource-meter:** chạm trần 32 MB do page cache (anon 3 MB, vô hại). Đề xuất `MemoryHigh=24M`, `MemoryMax=64M`, gộp vào bản cài lại cùng `aa3a5cfb`; user tự chạy `cd /home/vantt/app/fg-dataware-house/tools/resource-meter && cargo build --release && sudo ./install.sh && resource-meter status`.
5. Bật chặn CSRF (đã nằm trong phase 1 plan CRM; có thể bật riêng sớm nếu user muốn).
6. Đợt sửa số QĐ-18/20/21 + lỗi tiến độ GMV: đề xuất làm trong tuần để tin Weekly Pulse thứ Hai đúng — user chưa trả lời.
7. Plan MCP cho CEO: chưa viết; nên làm sau/cùng thư viện code mode.
8. Câu nhỏ plan CRM (trả lời trước phase liên quan): giữ audit bao lâu (đề xuất 24 tháng), mặc định khi chưa có consent, tỷ lệ holdout (đề xuất 20%), thắt quyền xem cho nhân viên; plan thư viện: license (đề xuất nội bộ), RAM sidecar (đề xuất 384 MiB, chốt theo số đo).
9. Codex trong `data_platform` mất đăng nhập (bước sinh kịch bản đang tắt); khi muốn bật lại: đăng nhập lại hoặc chuyển provider Anthropic.
10. Người nhận bàn giao khoá backup phía FJ, Shared Drive/service account (user là admin) — trước DR phase 5.
Rủi ro: tin Lark có lợi nhuận đi vào nhóm alert; `docs/operations/deployment.md` > 800 dòng; QuickJS/Monty còn trẻ (có cổng thực nghiệm).

## Exact next actions

1. **First safe step:** đọc file này; `git -C /home/vantt/app/fg-dataware-house log --oneline -3`, `docker ps`, `ListAgents`. Nếu c8 vẫn là `fg-dataware-house-c8`, nhắn c8: "session điều phối mới là <tên session mới>; từ giờ gửi báo cáo về đây". Đóng/không dùng session `-47` nữa (hỏi user nếu nó vẫn mở).
2. Sáng 22/10 (~09:45): nhận báo cáo parity đêm 7 → nếu đạt, xin user giờ chuyển cột, chuyển cho c8.
3. Hỏi user các câu ở mục Open risks, ưu tiên 1–4.
4. Khi user duyệt plan CRM/thư viện: giao c8 phase 0 của cả hai, kèm ràng buộc (chỉ đọc ở phase 0 CRM, không lách hook, file ownership theo plan).
5. Mỗi khi user chốt: ghi vào plan liên quan (mục "Đã chốt") và roadmap, commit + push `plans/` ngay, rồi `SendMessage` c8.

## Source pointers

- Roadmap: `plans/261013-1751-modularize-data-platform-suite/roadmap.md`.
- CRM: `plans/261019-1500-crm-core-agent-native/{design.md,plan.md,phase-*}`; thư viện code mode: `plans/261020-1310-agent-codemode-host/`; research CRM `plans/reports/research-261014-2333-retail-crm-purpose-core-capabilities.md`; triage `plans/reports/review-261019-1413-crm-plans-triage.md`; sandbox `plans/reports/research-261019-1905-agent-code-sandbox-options.md`; MCP CEO `plans/reports/research-261014-2333-adhoc-query-ceo-mcp.md`.
- Đang chạy: `plans/261014-2225-taxonomy-engine/` (nhật ký phase-06), `plans/261015-1815-inventory-dashboards-on-snapshots/`, `plans/261015-1730-price-inventory-history/`, `plans/261015-1140-backup-restore-dr/`, `plans/261014-2225-report-productization/` (+ `definition-decisions.md`), `plans/261016-1543-resource-meter/`.
- Runbook: `docs/operations/deployment.md`, `docs/operations/backup-and-recovery.md`, `docs/operations/resource-meter.md`.
- Xem markdown trên trình duyệt: skill `mdview` (ví dụ design CRM: http://100.121.46.35:7700/s/239e9782a47e).
- Handoff trước: `plans/handoffs/data-platform-coordination-20261015-2128.md`.
- Memory: `/home/vantt/.claude/projects/-home-vantt-app-fg-dataware-house/memory/` (prod-deploy-authority, commit-each-verified-piece, worker-prompts-forbid-hook-bypass).
