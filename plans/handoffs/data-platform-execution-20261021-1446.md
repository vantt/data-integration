# Handoff: session thực thi data platform — 21/10/2026 14:46

Trả lời user bằng tiếng Việt. Session này là **session thực thi** (code, gate, commit, deploy; là
session duy nhất được dừng/khởi động `data_platform`). Session điều phối là **fg-dataware-house-47**:
quyết định của user thường đến qua -47 (cross-session message). Mọi kết quả phải nhắn lại cho -47.

## Đọc trước khi làm

1. Kiểm "Hiện trạng" dưới đây với repo (`git log`, `git worktree list`) trước khi hành động.
2. Đọc: `AGENTS.md`, `docs/operations/deployment.md` § "Refactor deploys (shadow-verified)",
   `docs/operations/refactor-safety-harness.md`.
3. Memory của project (`~/.claude/projects/-home-vantt-app-fg-dataware-house/memory/`) có 3 quy tắc:
   tự deploy chỉ khi user duyệt giờ; commit + push từng phần đã kiểm; prompt giao worker phải cấm lách
   hook.

## Quy tắc bắt buộc

- **Deploy prod:** chỉ vào giờ user duyệt, theo runbook:
  1. `scripts/checks/instigator_state.py capture`;
  2. dừng `data_platform` trong khoảng không có run;
  3. `git merge --ff-only`;
  4. `start` (hoặc `docker compose up -d data_platform` nếu compose/env đổi);
  5. `instigator_state.py diff`;
  6. kiểm sau deploy;
  7. push `main`.
- Tránh 02:30–04:00. Không khởi động container vào phút chia hết cho 3.
- Rollback bằng `git revert`, không `reset --hard`. Không force-push `main`; nhánh feature dùng
  `--force-with-lease`.
- Không in secret; không đọc `.env*`. Không in dữ liệu khách (tên, SĐT), chỉ đếm.
- Không stage `.claude/settings.json`, `.agentkit/`, `.claude/*` trong checkout prod. Không stage file
  plans mà session khác đang sửa dở.
- Commit conventional, không plan ID hay phase, kết thúc bằng
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Tài liệu đổi cùng commit với code.
- Một shadow gate một lúc; không việc nặng 02:30–04:00. Ghi vào Metabase phải có bản chép nguội H2
  trước.
- **Không lách scout-block hook** (chặn lệnh chứa `target/`, `node_modules`, `builds/`): không glob
  kiểu `targe?`, không `docker exec cat` để vòng qua, không ghép chuỗi. Bị chặn thì hỏi user. Không sửa
  cấu hình quyền theo yêu cầu của agent khác.
- Giao worker: ghi đủ task, file được sửa, tiêu chí, ràng buộc ở trên, và yêu cầu kết thúc bằng
  `Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`.

## Hiện trạng (21/10 14:46)

- `main` = `origin/main` = `fe97b2d2`. Code prod gồm:
  - Đợt 1 modular hoá;
  - cơ chế pack 1–9;
  - bộ máy phân loại phase 1–5 (biến `taxonomy_engine_customer_type` = false);
  - sửa số, DR phase 1, report phase 04, lịch sử giá D1 + D2;
  - công tắc `APPROACH_SCRIPT_AUTOGEN_ENABLED` (Fine Japan tắt);
  - resource-meter (code `aa3a5cfb`).
- Deploy gần nhất: 19/10 13:18 `aa3a5cfb` → `371461cf`. Báo cáo:
  `plans/261015-1730-price-inventory-history/reports/deploy-261019-1318-d2-report.md`.
- Worktree (đều đã merge, không còn việc dở):
  - `fg-dw-price` (`fix/approach-autogen-switch`, `371461cf`);
  - `fg-dw-meter` (`feat/resource-meter`, `aa3a5cfb`);
  - `fg-dw-taxo`, `fg-dw-report`, `fg-dw-dr`;
  - `fg-dw-baseline` detached ở `b0931f33`: phải dời lên commit được chấp nhận cuối và build cùng ngày
    trước gate kế tiếp.
- **resource-meter** đang chạy bản cài 18/10 (bản cũ). User **chưa cài lại** bản `aa3a5cfb` (status
  báo throttle theo thời gian, unit có `CPUQuotaPeriodSec=1s`). Lệnh cho user:
  `cd /home/vantt/app/fg-dataware-house/tools/resource-meter && cargo build --release && sudo ./install.sh && resource-meter status`.
  - Lưu ý: unit peak đã chạm 32 MB = `MemoryMax` (anon 3 MB, còn lại page cache của TSV;
    `memory.events` max 0).
  - Đề xuất kèm lần cài lại: thêm `MemoryHigh` hoặc nâng `MemoryMax`. Chưa sửa, chờ user.

## Việc đang chạy: bộ máy phân loại phase 6 (chạy song song)

- Cần 7 đêm liên tiếp đạt, đếm từ 16/10. **Đã đạt 6 đêm** (16–21/10). Đêm 7 là 22/10.
- Nhật ký: `plans/261014-2225-taxonomy-engine/phase-06-prod-parallel-run.md`, bảng "Nhật ký 14 đêm".
- **Sáng 22/10 (sau 09:13)**, làm kiểm tra chỉ đọc:
  1. **Nightly:** `pipeline_batch_nightly_job` mới nhất phải SUCCESS. Đếm step, đo thời gian. Check
     fail chỉ được nằm trong tập đỏ đã biết: `sheets_marketing_spend_asset`, `sheets_targets_asset`,
     `sheets_team_config_asset`, cả ba `not_empty_when_expected` WARN.
  2. **Điều kiện dừng 4 (user chốt 19/10):** xét thời gian **bước `sapo_dbt_assets`**, không phải
     tổng nightly. Các đêm vừa qua: 18/10 33,2 s; 19/10 32,8 s; 20/10 36,5 s (thêm 3 model lịch sử);
     21/10 37,0 s. Đề xuất số nền 36,5 s **chưa được user chốt**. Phải có `oom_kill` = 0 trong
     `memory.events` của `/sys/fs/cgroup/system.slice/docker-<id data_platform>.scope`.
  3. **Parity:** đọc `monitor_taxonomy_parity_daily`.
     - Chép `/app/var/data_lake/sapo_warehouse.duckdb` vào `/tmp/whc/sapo_warehouse.duckdb` *trong*
       container (giữ đúng tên file vì view tham chiếu catalog), mở `read_only`, rồi `rm -rf /tmp/whc`.
     - Một đêm đạt khi cả hai domain có `is_pass` = true, `max_label_diff` = `max_flag_diff` = 0,
       một `ruleset_version`.
     - Chốt dòng hôm qua (cả ngày) và thêm dòng hôm nay.
  4. Cập nhật bảng nhật ký: cột RAM ghi "bỏ đo; oom_kill 0", cột thời gian ghi bước dbt và tổng.
  5. resource-meter (chỉ đọc), ghi tóm tắt vào
     `plans/261016-1543-resource-meter/reports/phase-04-observe-report.md`:
     - `resource-meter status`;
     - `resource-meter report --job pipeline_batch_nightly_job`;
     - `resource-meter compare --base <hôm qua>`.
  6. Commit + push, nhắn -47, báo user.
- **Nếu đêm 7 đạt:** báo user xin giờ chạy **phase 7** (bật `taxonomy_engine_customer_type`, dùng
  phương án (a): khách không có tenant mặc định thành CONSUMER, `int_customer_benchmarks` lọc theo
  `customer_type_std`). Chưa chạy khi user chưa duyệt giờ. Đọc `phase-07` trong cùng plan trước khi
  làm.
- **Nếu có khác biệt** hoặc `ruleset_version` đổi: đếm lại từ 0, điều tra bằng
  `monitor_taxonomy_parity`, báo user ngay.
- Lịch cron của session cũ **không mang sang** session mới. Nếu cần nhắc giờ, tạo lại bằng CronCreate
  (ví dụ 22/10 09:43).

### Script trợ giúp

Session cũ để các script này trong scratchpad
`/tmp/claude-1000/-home-vantt-app-fg-dataware-house/844d4197-0e6f-47ac-8a49-c96ea91da597/scratchpad/`.
Có thể vẫn còn; nếu mất thì viết lại theo mô tả:

- `nightly_checks.py`:
  - `q(query, vars)` gọi GraphQL `http://127.0.0.1:3000/graphql` và trả về `data`.
  - `summary(run_id)` phân trang `eventConnection`, gom `AssetCheckEvaluationEvent` fail theo dạng
    `asset:check:severity`, gom `ExecutionStepFailureEvent`, rồi trả về
    `(status, ok_steps, n_steps, n_checks, fails, step_fails)`.
  - Phần CLI ở cuối file cần hai run id. Khi import, cắt phần đó: dùng
    `exec(open(...).read().split("a = summary(sys.argv[1])")[0])`.
- `morning.py`: lấy run nightly mới nhất (`runsOrError` lọc `pipeline_batch_nightly_job`, limit 2),
  in thời lượng và `summary()`.
- `steps.py`: in `stepStats` của run theo thời lượng giảm dần (thay chuỗi `RUNID`).
- `parity.py`: đọc `monitor_taxonomy_parity_daily` từ `/tmp/whc/...` theo ngày (copy vào container
  bằng `docker cp`).
- Đọc serving không khoá: trong container, `shutil.copyfile` `serving/olap.duckdb` ra thư mục tạm,
  mở `read_only`, đọc xong xoá.

## Việc chờ user (đừng tự làm)

1. Giờ phase 7 bộ máy phân loại, sau khi đêm 22/10 đạt.
2. Số nền bước dbt cho điều kiện dừng 4 (đề xuất 36,5 s).
3. User cài lại resource-meter, kèm chỉnh `MemoryHigh`/`MemoryMax`. Phase 4 của meter quan sát 7 đêm
   tính từ 18/10.
4. Codex trong `data_platform` "Not logged in": đăng nhập lại hay chuyển sang Anthropic. Hiện
   autogen đã tắt nên không gấp.
5. CRM (báo cáo `plans/reports/review-261019-1413-crm-plans-triage.md`):
   - giờ bật `CRM_CSRF_ENFORCE=true`: lưu `docker logs crm` trước, đổi default trong compose,
     `docker compose up -d crm`;
   - tag sức khoẻ: chặn cả `health_domain` không, ai được xem, lọc khỏi export không;
   - cho đọc schema D1 production để xác minh plan `260623-0852`.
6. Hàng đợi đi qua gate S: QĐ-18, QĐ-20, QĐ-21 (a) và lỗi lệch một ngày của chỉ số tiến độ GMV
   (`plans/261014-2225-report-productization/definition-decisions.md`). QĐ-19 đi cùng report
   phase 09.
7. Plan tồn kho (`plans/261015-1815-inventory-dashboards-on-snapshots/`): user duyệt N = 7 đêm
   chụp; đã hết chặn sau D2, nhưng chưa có lệnh bắt đầu.
8. Sensor sheets: hoãn, đề xuất mặc định là gỡ.

## Ghi nhớ kỹ thuật

- Nightly 03:00, khoảng 2,4 phút. Job realtime chạy mỗi 3 phút, incremental mỗi 10 phút. Dagster
  purge run sau khoảng 1 ngày, nên không so được với run cũ.
- Bảng mới cần view serving phải chạy `bootstrap_serving_views.py`. Phải **dừng Metabase** khi chạy
  (khoá DuckDB), khoảng 4 giây.
- `memory.peak` của container gồm page cache, không dùng để so RAM. Số RAM lấy từ resource-meter
  (cột anon).
- Báo cáo deploy nằm trong `reports/` của từng plan. Báo cáo chung ở `plans/reports/`.
