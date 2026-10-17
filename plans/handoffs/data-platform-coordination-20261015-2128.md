---
handoff-version: 1
created: 2026-10-15 21:28 ICT
session-role: coordination / planning (does NOT execute or deploy)
language: Vietnamese with the user
---

# Handoff: điều phối nền tảng dữ liệu FG (sau Đợt 1)

## Mission and current status

**Vai trò của session này:** điều phối và lập plan. User (vantt) giao: session này chỉ điều chỉnh plan, viết plan/thiết kế, giải thích, gom quyết định của user, rồi chuyển lệnh cho **session thực thi** qua `SendMessage`. Session này **không** chạy job, không deploy, không sửa code sản phẩm.

- Session thực thi hiện tại: **`fg-dataware-house-c8`**, ref `[1f3897]` (tên dùng cho `SendMessage`; chỉ thêm ref khi tên bị trùng), socket `uds:/run/user/1000/cc-socks/244059.sock`, Herdr pane w4:p7, chế độ bypass nên tin tới thẳng. Session trước nữa `fg-dataware-house-f6` đã kết thúc 14/10. Session điều phối này tên `fg-dataware-house-73` [bdf7f2]. Nó tự deploy prod theo runbook **chỉ sau khi user duyệt giờ**.
- Trả lời user bằng tiếng Việt, ngắn, rõ, không viết tắt khó hiểu.

**Đã xong (trên prod, `main` = `origin/main` = `b0931f33`):**
- Đợt 1 module hoá (phase 0–7) — đóng 14/10, đủ 6/6 tiêu chí.
- Cơ chế pack (9 phase) — xong 15/10 11:28.
- Bộ máy phân loại: deploy lần 1 15/10 15:19 (`taxonomy_engine_customer_type=false`, chạy song song, **7 đêm** liên tiếp không lệch từ 16/10 → sớm nhất ~22/10 chuyển cột).
- Sửa 2 lỗi số (Rill scope, lợi nhuận kênh khi thiếu COGS) — 15/10 17:25.
- Backup/DR phase 1 — 15/10 17:49 (backup nhất quán, Metabase chép nguội mỗi đêm 00:30, CRM backup 02:00 VN, thẻ Lark theo trạng thái, quyền secret đã áp kể cả tunnel do user chạy sudo).
- Report phase 04 — 15/10 17:55 (Evidence build sau nightly, cổng 3006 đóng, đăng nhập theo người; tin Weekly Pulse vào nhóm Lark hiện có (`LARK_REPORT_LEADERSHIP_*` = bản sao alert), gửi thật thứ Hai 07:00; đã gửi thử OK).
- Lịch sử giá/tồn phase 1 (chụp 560 SP mỗi đêm vào raw chỉ-thêm) — 15/10 18:52.
- Ghim phiên bản Evidence; backup Metabase; sửa cách đo freshness.

**Đang làm (c8):** lịch sử giá phase 2 (gate S 17/10 09:47 sau backup 01:04), report phase 05 (thí điểm Weekly Pulse 4 tuần), DR phase 2–4, QĐ-18/QĐ-20 (đợt sửa sau qua gate S).

## Scope and guardrails

- Repo/prod checkout `/home/vantt/app/fg-dataware-house` được bind-mount vào container `data_platform`: **sửa file ở đây là sửa prod**. Session này chỉ sửa trong `plans/` (và memory của mình).
- Prod chỉ đổi qua runbook `docs/operations/deployment.md` (capture instigator → khoảng trống không run → stop → ff-merge → start/up → kiểm → push), tránh 02:30–04:00. Rollback: `git revert`, không `reset --hard`.
- Không đọc/in `.env`, `.env.docker`, secret; mật khẩu/ webhook/ ping URL do user tự đặt bằng lệnh không echo.
- Không stage/commit `.claude/settings.json`, `.agentkit/`, `.claude/*`, `plans/` chưa track.
- Commit: conventional, không nhắc AI, không plan ID/số phase trong code/test/commit.
- Mỗi lần chỉ một gate shadow; không build shadow nặng 02:30–04:00. Dữ liệu shadow có PII: 0700, xoá khi xong; công cụ ở `~/.cache/fg-dw-tools/deps` giữ lâu dài.
- Hook repo chặn lệnh shell chứa chữ "target" + "/".

## Current state

Quan sát lúc 21:28 ngày 15/10/2026:
- Checkout prod: nhánh `main` @ `b0931f3349aa943285d128736d7417fbdc9f5fe3` (= `origin/main`).
- Thay đổi chưa commit trong checkout prod (cố ý, do session này, chỉ là plan): `plans/260528-1325-tool-agnostic-design-spec/plan.md` (superseded), `plans/260624-2010-warehouse-pipeline-dr-verified-restore/plan.md` (cancelled), `plans/260705-1704-modular-monorepo-boundary-hardening/plan.md` (phase 2/3/6 superseded). `.claude/settings.json` sửa sẵn của user. 132 mục untracked (gồm `plans/`, `.agentkit/`, `.claude/*`).
- Worktree của c8: `fg-dw-baseline` (f7b59ef2, detached), `fg-dw-dr` (`feat/backup-offsite-dr` 4e330772), `fg-dw-price` (`feat/price-inventory-history` 15054360), `fg-dw-report` (`feat/report-productization`), `fg-dw-taxo` (`feat/taxonomy-engine` d31d51f2).
- Nhánh remote: `feat/{backup-offsite-dr,pack-mechanism,price-inventory-history,report-productization,taxonomy-engine}`, `fix/{freshness-counts-skipped,number-bugs}`, `refactor/{modularize-suite,phase-7}`.

## Decisions and rationale

Toàn bộ quyết định nằm trong file plan (mục "Đã chốt"). Quan trọng nhất:
- **Kiến trúc:** logic là pack, dữ liệu/cấu hình là tenant; chỉ US shipment riêng FJ; lõi giữ doanh thu, pack finance giữ chi phí/lợi nhuận; số liệu do nguồn cung cấp thuộc lõi; connector lấy dữ liệu, pack dùng, gặp nhau ở `std_*`. CRM/HUG là pack, chuẩn hoá để sau.
- **Phân loại:** nhãn riêng + mã chuẩn bắt buộc; bộ máy luật là dữ liệu; kiểm soát chất lượng phân loại (roadmap 3b) làm sau khi chuyển xong `customer_type`.
- **Report:** khung 7 chức năng × 3 cấp; Evidence cho report định kỳ, Metabase cho tương tác; registry chỉ tiêu là module code; 17 quyết định định nghĩa Weekly Pulse + QĐ-18..20 đã chốt (áp ở phase 09 / đợt sửa sau); `net_revenue` hiện tại → `net_sales`.
- **Backup:** restic + rclone → Google Drive; FJ dùng Workspace (service account + Shared Drive); khách giữ khoá, FG không vận hành; không lưu image; 7d/4w/12m + 3 năm; off-site 03:30; healthchecks.io tài khoản email của user [REDACTED:email] (ghi trong plan backup; bàn giao sau); máy diễn tập `vantt@fg-server2`; diễn tập mỗi năm + mỗi lần cài khách mới.
- **Pháp lý (Luật 91/2025, NĐ 356/2025):** user hoãn hỏi luật sư; dùng mặc định an toàn.
- **Bảo mật dịch vụ web (Dagster UI, Rill…), sensor Google Sheet, CRM/HUG chuẩn hoá:** hoãn theo user.

## Work performed

- Session này viết/sửa plan và thiết kế: `plans/261013-1751-modularize-data-platform-suite/{roadmap.md, taxonomy-engine-design.md, report-product-design.md, phase-04/06/07}`, các plan mới `plans/261014-2225-{pack-mechanism,taxonomy-engine,report-productization}`, `plans/261015-1140-backup-restore-dr`, `plans/261015-1730-price-inventory-history`, `plans/261015-1815-inventory-dashboards-on-snapshots`; nghiên cứu ở `plans/reports/research-*` và `plans/261013-1751-modularize-data-platform-suite/references/`.
- Đã dọn `/tmp` (xoá scratchpad/cache không ai mở; swap 8,1 → 3,2 GB).
- Mọi deploy do c8 thực hiện; báo cáo deploy nằm trong `reports/` của từng plan.

## Verification

- Prod sau các deploy 15/10: instigator không đổi (28 sau khi thêm asset chụp), serving 152 view, nightly chạy tay xanh, 0 check đỏ mới (theo báo cáo c8; session này kiểm `docker ps` healthy và git log).
- Chưa kiểm trực tiếp: nightly 16/10 03:00 (lần chụp giá theo lịch đầu tiên, timer Metabase 00:30 đầu tiên, CRM backup 02:00 đầu tiên) — c8 kiểm buổi sáng.
- Dashboard tồn kho hiện **sai** (thẻ "hôm nay" lọc `MAX(snapshot_date)`): biết rõ, chờ plan inventory.

## Open risks and blockers

Chờ user quyết:
1. Plan `261015-1815-inventory-dashboards-on-snapshots`: duyệt; QĐ-TK-03 (thẻ SKU hết hàng), QĐ-TK-05 (`is_oos` 99/99); có sửa tạm các thẻ tồn kho "hôm nay" trước (cần chép nguội H2 + sửa card Metabase prod)?
2. QĐ-21: so tuần chưa hết với tuần trước (đề xuất so cùng kỳ).
3. MCP cho CEO: "lợi nhuận" mặc định CM2 hay hỏi lại; Claude Desktop hay bot Lark; số mỗi đêm có đủ.
4. FJ: ai là admin Workspace (Shared Drive + service account), ai giữ 2 khoá backup (trước DR phase 5).
5. Báo cáo nào của FJ dùng chốt thưởng (trước lần đổi luật phân loại đầu tiên sau pilot).
Rủi ro: tin Lark có lợi nhuận đi vào nhóm alert hiện có (user đã biết); `docs/operations/deployment.md` > 800 dòng (cần tách sau); tag sức khoẻ trong CRM có thể là dữ liệu nhạy cảm (chờ luật sư).

## Exact next actions

1. **First safe step:** đọc file này, rồi kiểm lại `git -C /home/vantt/app/fg-dataware-house log --oneline -3 main` và `docker ps` để xác nhận trạng thái; dùng `ListAgents` để chắc session thực thi vẫn là `fg-dataware-house-c8` (nếu tên đổi, hỏi user).
2. Sáng 16/10: nhận báo cáo của c8 về nightly 03:00, lần chụp giá theo lịch đầu tiên, Metabase 00:30, CRM 02:00; chuyển tóm tắt cho user.
3. Hằng ngày từ 16/10: theo dõi kiểm parity bộ máy phân loại (09:13); ~22/10 hỏi user giờ chuyển cột (phase 7 taxonomy).
4. 17/10 sau 09:47: nhận kết quả gate lịch sử giá phase 2 → xin user giờ deploy D2.
5. Hỏi user các câu ở mục Open risks khi phù hợp (ưu tiên plan dashboard tồn kho vì dashboard đang sai).
6. Khi user chốt, ghi vào mục "Đã chốt" của plan liên quan và `roadmap.md`, rồi `SendMessage` cho c8.

## Source pointers

- Roadmap tổng: `plans/261013-1751-modularize-data-platform-suite/roadmap.md` (thứ tự ưu tiên, việc vận hành độc lập, backup, lịch sử giá, module sản phẩm, Đợt 7).
- Plans đang chạy: `plans/261014-2225-taxonomy-engine/`, `plans/261014-2225-report-productization/` (+ `definition-decisions.md`), `plans/261015-1140-backup-restore-dr/`, `plans/261015-1730-price-inventory-history/`, `plans/261015-1815-inventory-dashboards-on-snapshots/`.
- Thiết kế: `plans/261013-1751-modularize-data-platform-suite/{taxonomy-engine-design.md, report-product-design.md}`, `docs/architecture/modules.md`, ADR 015–019 trong `docs/decisions/`.
- Runbook: `docs/operations/deployment.md`, `docs/operations/backup-and-recovery.md`, `docs/operations/refactor-safety-harness.md`.
- Nghiên cứu: `plans/reports/research-261014-2333-retail-crm-purpose-core-capabilities.md`, `plans/reports/research-261014-2333-adhoc-query-ceo-mcp.md`, `plans/reports/research-261015-1040-offsite-backup-restore-dr.md`, `plans/reports/assessment-261015-1045-backup-restore-current-state.md`.
- Handoff trước: `plans/handoffs/data-platform-modularization-20261014-1438.md`.
- Memory: `/home/vantt/.claude/projects/-home-vantt-app-fg-dataware-house/memory/prod-deploy-authority.md`.
