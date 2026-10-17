---
handoff-version: 1
generated: 2026-10-14T07:38:00Z
generator: ak:handoff
focus: "Continuation for the data platform modularization (plan plans/261013-1751-modularize-data-platform-suite). Phases 0-5 deployed to prod (main 111f1386); next: 15/10 03:00 nightly confirmation, then phase 6, phase 7. User language Vietnamese."
workspace: /home/vantt/app/fg-dataware-house
branch: main (prod checkout) / refactor/modularize-suite (worktree /home/vantt/app/fg-dw-modular)
head: 111f1386 (main = refactor/modularize-suite)
supersedes: plans/handoffs/data-platform-modularization-20261014-0945.md
---

# HANDOFF: Module hoá suite data platform (Fine Japan là tenant #1)

## Mission and current status

"Continuation for the data platform modularization (plan plans/261013-1751-modularize-data-platform-suite). Phases 0-5 deployed to prod (main 111f1386); next: 15/10 03:00 nightly confirmation, then phase 6, phase 7. User language Vietnamese."

Outcome: tách suite dbt-duckdb + Dagster + dlt đang chạy cho Fine Japan thành module (connectors, cdm, core, packs, taxonomy, tenant overlay, kernel) mà **không đổi con số, không đổi tên bảng public**, hệ thống vẫn chạy hằng ngày. Plan: `plans/261013-1751-modularize-data-platform-suite/plan.md` (8 phase, Đợt 1 của `roadmap.md`). Trả lời user bằng tiếng Việt, xưng "em", gọi "anh".

Done (tất cả đã lên prod, `main` = `111f1386`):
- Phase 0 safety harness, phase 1 boundary checks, phase 2 dbt layout — prod 13/10 23:38.
- Phase 3 canonical layer (10 `std_*` view) — prod 14/10 09:22; kiểm chứng bằng nightly chạy tay 09:49 (`856bd0ee`).
- Phase 5 connector packages (`b718befc`) — prod 14/10 10:35; kiểm chứng bằng nightly chạy tay 12:43 (`efb41501`).
- Phase 4 **rút gọn** (`31ae829e` + `111f1386`): `transformation/docs/TAXONOMY.md` (46 domain, 79 khối có sha256), `scripts/checks/check_taxonomy_inventory.py` (WARN only, trong `gate.sh` bước 3c), 8 seed phân loại dời vào `transformation/seeds/taxonomy/`, `ingestion/src/utils/seed_paths.py`, docs `docs/architecture/taxonomy-engine.md` + `docs/reference/taxonomy/`. KHÔNG tách macro, KHÔNG sửa model. Prod 14/10 13:27; nightly chạy tay sau deploy 14:27 (`4c9d9ce6`) xanh.

Remaining:
- Xác nhận nightly 15/10 03:00 cho cả phase 5 và phase 4 (lần chạy theo lịch đầu tiên trên code mới).
- Phase 6 Fine Japan tenant overlay (`phase-06-fine-japan-tenant-overlay.md`); chưa có brief, chờ user/session lập plan.
- Phase 7 docs/ADR/cưỡng chế/dọn shadow.

Urgency: normal; user đi từng phase, quyết định thời điểm deploy.

## Scope and guardrails

Workspace: `/home/vantt/app/fg-dataware-house` (checkout prod, nhánh `main`, bind-mount vào container `data_platform`) + worktree `/home/vantt/app/fg-dw-modular` (nhánh `refactor/modularize-suite`, nơi làm mọi việc) + `/home/vantt/app/fg-dw-baseline` (detached, baseline của gate).

Vai trò (user chốt 14/10): **session thực thi** (session kế nhiệm) làm code, gate, commit, deploy và là session DUY NHẤT dừng/khởi động `data_platform`. **Session lập plan** `fg-dataware-house-73` (herdr pane `w4:p1`) chỉ sửa plan/brief và chuyển quyết định của user. Tin nhắn giữa hai session thường bị giữ (khác chế độ quyền) tới khi user duyệt ở `w4:p1`; báo user khi bị giữ/hết hạn, không gửi lại khi đang bị giữ.

In scope: phase 6, 7; deploy phase đã được chấp nhận khi user cho phép; giữ tài liệu khớp code.

Out of scope (`roadmap.md`): image/GHCR (plan `260705-1704`), dbt local packages, contract enforced, taxonomy rules-as-data / bộ máy phân loại (plan riêng sau Đợt 1, xem `taxonomy-engine-design.md`), connector mới, report catalog.

Constraints (quyết định của user):
- Prod chỉ đổi qua runbook `docs/operations/deployment.md` § Refactor deploys: chụp instigator, khoảng trống không có run, `docker compose stop data_platform`, `git merge --ff-only <SHA ghim>`, start, kiểm tra, rollback bằng `git revert <range>` (không `reset --hard`). Tránh 02:30–04:00. Tránh start container sát mốc tick realtime (phút chia hết cho 3).
- "Làm tới đâu thiết kế và tài liệu hoá chi tiết tới đó": docs đổi cùng commit với code; mỗi component một doc "what/how". User kiểm tra điều này.
- Không sửa SQL để làm đẹp: user quyết KHÔNG sửa hai khối `customer_type` (khác tiền tố `c.`) cho giống từng ký tự; để cho plan bộ máy phân loại gộp.
- Contracts chỉ warn; không `contract: enforced`.
- Commit: conventional, không nhắc AI, không plan ID/số phase trong code comment, test name, commit message. Kết thúc commit message bằng dòng `Co-Authored-By` theo hướng dẫn hệ thống.
- Worker (subagent Sonnet hoặc herdr pane) không commit; coordinator chạy lại gate rồi commit.

Safety boundaries:
- KHÔNG sửa file trong `/home/vantt/app/fg-dataware-house` ngoài `plans/`; không chạy dbt vào `app_data/`.
- Bộ phân loại an toàn của auto mode chặn agent chạy `docker exec ... dagster job launch` ("Remote Shell Writes") và đôi khi chặn stop/merge/start ("Production Deploy", khi lời duyệt đến qua session khác). Khi bị chặn: không lách (không launch qua GraphQL), đưa lệnh cho user gõ với tiền tố `!`. Deploy phase 5 agent tự chạy được; deploy phase 4 user tự gõ.
- Shadow `/home/vantt/app/fg-dw-shadow` chứa PII: giữ 0700, không chép dữ liệu ra, xoá khi đóng plan.
- Không deploy khi user chưa cho phép trực tiếp lần deploy đó.
- `.claude/settings.json` (đã sửa) và các thư mục untracked `.agentkit/`, `.claude/*`, `plans/` trong checkout prod là của user: không stage, stash, xoá.

## Current state

Quan sát 14/10/2026 14:38 ICT:

- Checkout prod `/home/vantt/app/fg-dataware-house`: nhánh `main`, HEAD `111f1386`. Working tree: ` M .claude/settings.json` (của user) + 114 mục untracked (của user, cố ý). Không seed nào bị job ghi đè.
- Worktree `/home/vantt/app/fg-dw-modular`: nhánh `refactor/modularize-suite`, HEAD `111f1386` (trùng prod), sạch.
- Worktree `/home/vantt/app/fg-dw-baseline`: detached `b718befc`. **Phải dời lên `111f1386`** (commit được chấp nhận và deploy gần nhất) và build lại cùng ngày trước gate của phase 6.
- Shadow `/home/vantt/app/fg-dw-shadow` (0700): `lake-base`, `lake-A` (build 14/10 11:32 từ `b718befc`), `lake-A2`, `deps/`, `inventory/`.
- Prod: container `data_platform` healthy (start 14/10 13:27:01); 26/26 instigator running; serving 152 view; mọi run sau 13:36 SUCCESS.
- Lịch kiểm tra nightly 03:17 (CronCreate `f275fcd1`) chỉ sống trong session cũ; **nếu session cũ đã đóng thì lịch đó không còn**, session mới phải tự kiểm tra (Exact next actions bước 2).

Intentional local modifications: có (chỉ `.claude/settings.json` và thư mục untracked của user trong checkout prod).

## Decisions and rationale

- Bucket model trong `scripts/checks/model_buckets.yaml`; thư mục layer quyết định schema/tag, thư mục module không. COGS, inventory là core. Allowlist 46 (37 `dbt-path` FJ chờ phase 6, 9 `dbt-ref`).
- Gate baseline = commit được chấp nhận gần nhất, build cùng ngày (`gate.sh` chỉ tự rebuild khi sang ngày mới, không khi đổi commit; dời baseline theo `docs/operations/refactor-safety-harness.md` §9.2).
- Thứ tự phase: 5 trước 4 (đã làm). Phase 4 rút gọn theo `reports/phase-04-brief-for-executor-261014.md` vì user muốn đầu ra phase 4 làm đặc tả cho bộ máy phân loại chuẩn (features → rules-as-data → nhãn tenant + giá trị chuẩn bắt buộc).
- `customer_type`: 2 logic. `fact_orders` và `int_customer_benchmarks` giống về logic, văn bản khác tiền tố `c.` nên hash khác; comment "mirrors dim_customers" trong `int_customer_benchmarks.sql` sai, để sửa khi gộp ở plan bộ máy. `taxonomy-engine.md` §6 và brief đã sửa câu chữ.
- Nightly chạy tay để kiểm chứng ngay thay vì chờ 03:00 (user duyệt): chạy lần thứ hai trong ngày làm đỏ các check theo thời điểm (`customers_batch freshness`, `orders_batch row_count_within_trend`) — không phải lỗi code.
- Không dùng `dagster schedule list -f`; dùng `scripts/checks/instigator_state.py` (GraphQL).

## Work performed

Commit (cũ → mới) trên `refactor/modularize-suite`, tất cả đã ở `main`: `d210ad98` … `25b6be42` (phase 0–3), `b718befc` (phase 5), `75894f81` (doc baseline), `31ae829e` (phase 4 rút gọn), `111f1386` (doc "giống về logic").

Deploy hôm nay (runbook):
- 10:34 → `b718befc` (agent tự chạy). Báo cáo `reports/deploy-261014-1034-phase-5-report.md`.
- 13:26 → `111f1386` (user tự gõ stop/merge/start). Báo cáo `reports/deploy-261014-1327-phase-4-report.md`. Run `6760a3b1` FAILURE "timed out ... 300 seconds to start": tick 13:27:00 trùng lúc container khởi động, không có step nào chạy; lượt sau SUCCESS.

Nightly chạy tay (user gõ `! docker exec data_platform dagster job launch -f orchestration/definitions.py -j pipeline_batch_nightly_job`): `856bd0ee` 09:49 (prod 25b6be42), `efb41501` 12:43 (b718befc), `4c9d9ce6` 14:27 (111f1386). Báo cáo `reports/nightly-manual-261014-0949-phase-3-validation.md`.

Phase 4: subagent Sonnet thực hiện (báo cáo `reports/phase-04-worker-report.md`); coordinator chạy lại `scripts/shadow/gate.sh M` lúc 11:56: PASS sạch.

## Verification

- Gate M phase 4 (baseline `b718befc` cùng ngày): golden 83/83 giống, dbt inventory 186/186 0 diff, compiled SQL 0/172 đổi, boundaries 0 vi phạm mới, taxonomy 79 khối/46 domain 0 warning, dagster inventory 0 diff, dbt subset qua Dagster PASS, pytest 222 pass, lake trống OK.
- Prod sau deploy phase 4: instigator 26/26 0 diff; serving 152; không seed trùng tên; log không lỗi; nightly `4c9d9ce6` SUCCESS 55/55 step, 487 check, 10/10 `std_column_contract_*`, 6 check đỏ đều có từ trước. Đọc seed qua `seed_path()` đã chạy trên prod (`sheets_marketing_spend_asset`).
- Chưa kiểm: nightly 03:00 theo lịch trên `111f1386`; **ghi** seed trên prod (budget sync dừng trước khi ghi; `sync_seeds.py` chạy tay) — mới kiểm trong shadow.
- Check đỏ đã biết, không do deploy: `ingest_sapo_v2_customers_batch_asset` freshness (ERROR; các lần tải `skipped` 0 dòng không được tính là thành công) + row_count_within_trend; `ingest_sapo_v2_products_batch_asset` freshness (~680h); `sheets_{marketing_spend,targets,team_config}_asset` not_empty_when_expected.
- Flaky đã biết: `orchestration/ops/__tests__/test_ingestion_health_retry.py::test_concurrent_writes_no_lock_error`.

## Open risks and blockers

- `budget_sheet_sync_job` lỗi 02:30 hằng ngày: Google Sheet BUDGET_ITEMS dòng 17–18 dùng mã TK cha `112`, `334` không có trong `dim_gl_account`. Người phụ trách ngân sách phải sửa sheet. Khi sửa xong, đường ghi seed budget qua `seed_paths.py` chạy thật lần đầu — kiểm tra file ghi đúng chỗ.
- Check freshness của customers batch sẽ tiếp tục đỏ khi Sapo không có khách mới (coi `skipped` là không tươi) — vấn đề thiết kế check, ngoài phạm vi.
- Phase 6 chưa có brief; phase file viết trước phase 4/5 — đối chiếu đường dẫn mới (`orchestration/connectors/**`, `seeds/taxonomy/`) trước khi làm.
- Câu hỏi nghiệp vụ mở trong `TAXONOMY.md` §11 (CROSSBORDER chỉ có tín hiệu kênh US; `is_reached` hẹp hay rộng); cột "số bị ảnh hưởng" của Known divergences chưa đo (cần truy vấn PII trong shadow, chưa được duyệt).
- Hook repo chặn lệnh shell chứa chuỗi `target` + `/` (artifact dbt); chép manifest vào `<lake>/_shadow_meta/` hoặc ghép đường dẫn.

## Exact next actions

1. **First safe step**: đọc file này, rồi kiểm tra Current state: `git -C /home/vantt/app/fg-dataware-house log --oneline -1` (kỳ vọng `111f1386`), `git -C /home/vantt/app/fg-dw-modular log --oneline -1` (kỳ vọng `111f1386`), `git worktree list`, `docker ps --filter name=data_platform`, và `cd /home/vantt/app/fg-dw-modular && python3 scripts/checks/instigator_state.py capture --out <scratchpad>/i.json` (kỳ vọng 26 running). Ghi file tạm vào scratchpad của session, không vào `/tmp`.
2. Nếu đã qua 03:00 ngày 15/10 và chưa có mục "Nightly 15/10 03:00" trong hai báo cáo deploy: kiểm tra nightly đó (chỉ đọc). Dùng Dagster GraphQL `http://127.0.0.1:3000/graphql`: tìm run `pipeline_batch_nightly_job` mới nhất; `runOrError.stepStats`; `eventConnection(afterCursor, limit:1000)` phân trang theo `cursor`/`hasMore`, lọc `AssetCheckEvaluationEvent` (`evaluation { checkName success severity description assetKey { path } }`) và `ExecutionStepFailureEvent`; so tập check fail với run `4c9d9ce6-d230-4909-a07d-da5adb0ede45`. Đếm serving view: chép `app_data/data_lake/serving/olap.duckdb` vào scratchpad, `uv run -q --with duckdb==1.5.2 python` mở `read_only`, `select count(*) from information_schema.tables where table_type='VIEW'` (kỳ vọng 152). Liệt kê run FAILURE từ 14/10 14:33. Ghi kết quả vào `reports/deploy-261014-1034-phase-5-report.md` và `reports/deploy-261014-1327-phase-4-report.md`, báo user, nhắn `fg-dataware-house-73`. Nếu lỗi do deploy: chỉ đề xuất rollback (`git revert` theo runbook), không tự làm.
3. Chờ user/session lập plan gửi brief phase 6. Trước gate phase 6: dời baseline `git -C /home/vantt/app/fg-dw-baseline checkout --detach 111f1386`, rebuild lake-A, recapture golden, export lại `dbt-main.json`/`dagster-main.json` từ worktree baseline, xoá `lake-AF` nếu có (`docs/operations/refactor-safety-harness.md` §9.2).
4. Làm phase 6 trong `/home/vantt/app/fg-dw-modular` (worker không commit; coordinator chạy lại `scripts/shadow/gate.sh M`, commit). Tài liệu bắt buộc: `transformation/models/tenants/fine_japan/README.md`, `orchestration/tenants/fine_japan/README.md`, `docs/architecture/modules.md` §10. Deploy khi user cho phép trực tiếp.
5. Phase 7: ADR 015/016, AGENTS.md, `scripts/checks/run-all.sh`, xoá shadow và worktree khi đóng plan.

## Source pointers

- Plan: `/home/vantt/app/fg-dataware-house/plans/261013-1751-modularize-data-platform-suite/` (`plan.md`, `phase-0*.md`, `roadmap.md`, `taxonomy-engine-design.md`, `architecture-boundaries.md`, `references/taxonomy/`).
- Báo cáo hôm nay (`reports/`): `nightly-manual-261014-0949-phase-3-validation.md`, `deploy-261014-1034-phase-5-report.md`, `deploy-261014-1327-phase-4-report.md`, `phase-04-brief-for-executor-261014.md`, `phase-04-worker-report.md`, `taxonomy-docs-gap-261014.md`, `taxonomy-review/synthesis.md`.
- Handoff trước: `plans/handoffs/data-platform-modularization-20261014-0945.md`.
- Docs sống (nhánh = prod): `docs/architecture/modules.md`, `docs/architecture/canonical-layer.md`, `docs/architecture/taxonomy-engine.md`, `transformation/docs/TAXONOMY.md`, `docs/operations/refactor-safety-harness.md`, `docs/operations/deployment.md` § Refactor deploys, `scripts/shadow/README.md`, `scripts/checks/README.md`, `orchestration/connectors/README.md`, `transformation/AGENTS.md`.
- Tools: `scripts/shadow/gate.sh`, `scripts/checks/{check_boundaries,check_taxonomy_inventory,golden_snapshot,dbt_inventory,dagster_inventory,instigator_state}.py`, `ingestion/src/utils/seed_paths.py`.
- Code liên quan check freshness: `orchestration/asset_checks/freshness_checks.py`, `orchestration/asset_checks/health_db.py` (`last_success` chỉ tính `status='success'`).
- Journal: `plans/journals/2026-10-13-plan-module-ho-suite-data-platform.md`.
