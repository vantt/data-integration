# Phase 0: kết quả kiểm thực địa

**Ngày:** 17/10/2026, 20:19–20:47 (Asia/Saigon) · **Người làm:** worker phase 0 · **Cách làm:** chỉ đọc, user `vantt` (không root, không sudo)

## Kết luận nhanh

Mọi giả định của phase 1–2 đều kiểm được, nhưng **cách nhận diện bước Dagster khác plan**: không dùng `environ` và không có tiến trình `dagster api execute_step`. Run id và khoá log lấy được **không cần root** từ dòng lệnh của tiến trình `tail` con của mỗi bước. Step key và tên job lấy từ Dagster GraphQL (chỉ đọc): sự kiện `LogsCapturedEvent` có `pid` (pid trong namespace của container), `fileKey` và `stepKeys`. Đã đối chiếu trực tiếp trên 2 run thật: pid và `fileKey` khớp 5/5 bước. `run_results.json` nằm trên thư mục bind-mount của host, sống ít nhất 24 giờ. Root chỉ còn cần cho `/proc/<pid>/io` và tên container; **không cần đọc `environ` nữa**.

## 1. Cgroup

- `/sys/fs/cgroup/system.slice/docker-<id64>.scope`: 21 scope, khớp 21 container đang chạy (`docker ps`); cgroup driver `systemd`, cgroup v2, `CgroupParent` rỗng.
- Đọc được bằng user thường: `memory.stat`, `memory.events`, `memory.current`, `memory.peak`, `memory.max`, `cpu.stat`, `cpu.max`, `io.stat`, `memory.pressure`, `cpu.pressure`, `io.pressure`, `cgroup.procs`.
- Container không có cgroup con (mọi tiến trình nằm thẳng trong scope).
- Khoá dùng được (ví dụ `data_platform`):
  - `memory.stat`: `anon`, `file`, `kernel`, `shmem`, `file_mapped`, `file_dirty`, `sock`, `slab`… (đủ cho anon/file/kernel).
  - `memory.events`: `low high max oom oom_kill oom_group_kill sock_throttled` (hiện `max 60786`, `oom_kill 0`).
  - `cpu.stat`: `usage_usec user_usec system_usec nr_periods nr_throttled throttled_usec …`.
  - `io.stat`: một dòng mỗi thiết bị, dạng `259:0 rbytes=… wbytes=… rios=… wios=… dbytes=… dios=…`; phải cộng mọi dòng.
  - `*.pressure`: hai dòng `some`/`full`, mỗi dòng `avg10 avg60 avg300 total`.
- Map id → tên **không gọi Docker API**: `/var/lib/docker/containers/<id64>/config.v2.json`, trường `"Name":"/<tên>"`. Thư mục `/var/lib/docker` là `drwx--x--- root root`, user thường không đọc được → **cần root**. Dự phòng khi không đọc được: dùng 12 ký tự đầu của id.
- Hai Dagster trên máy: `data_platform` (GraphQL host `127.0.0.1:3000`, mem 8 GiB) và `nu-dataplatform` (host `13000`, mem 6 GiB). Gắn tiến trình theo cgroup trước rồi mới gắn job, như plan.
- Ghi chú ngoài phạm vi: `data_platform` có `cpu.max 400000 100000` (4 nhân); `nr_throttled/nr_periods` ≈ 4%, `throttled_usec` cộng dồn ≈ 53.700 giây. Công cụ nên ghi `cpu.stat throttled_usec` để thấy điều này theo bước.

## 2. Tiến trình bước Dagster (quan sát thật, không tự kích hoạt job)

Dagster **1.13.17** (`{ version }` qua GraphQL). Launcher `DefaultRunLauncher`, `QueuedRunCoordinator` (`orchestration/dagster.yaml`). Không có `dagster api execute_run` hay `execute_step`: mọi thứ đi bằng `multiprocessing` kiểu spawn. Đã theo dõi `cgroup.procs` của `data_platform` khoảng 15 phút (20:23–20:45) trong lúc các job realtime chạy theo lịch (`*/3`), có cả bước `sapo_dbt_assets`.

Cây tiến trình (pid host, dòng lệnh đã che):

```
dagster dev (argv: python3.10 /usr/local/bin/dagster dev …)
└─ python3.10 -m dagster code-server start …
   └─ python3.10 -m dagster api grpc --lazy-load-user-code …        ← server code
      └─ python3.10 -c "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=N, pipe_handle=N)" --multiprocessing-fork   ← RUN WORKER
         └─ (cùng dòng lệnh spawn_main … --multiprocessing-fork)                                                                          ← BƯỚC (multiprocess executor)
            ├─ tail -F -c +0 /app/var/dagster_home/storage/<RUN_ID>/compute_logs/<fileKey>.out
            ├─ tail -F -c +0 /app/var/dagster_home/storage/<RUN_ID>/compute_logs/<fileKey>.err
            ├─ python3.10 /usr/local/lib/python3.10/site-packages/dagster/_core/execution/scripts/watch_orphans.py N N   (×2)
            ├─ python3.10 /usr/local/bin/dbt --version | parse | build --select <11.809 ký tự>
            │  └─ python3.10 -c "from multiprocessing.resource_tracker import main;main(N)"
            └─ python3.10 /app/scripts/provisioning/refresh_rolling.py
```

Trả lời từng câu hỏi:

- **Run id:** không có trong dòng lệnh hay biến môi trường nào đọc được của run worker và bước. Có trong đối số cuối của tiến trình `tail` con của bước: `…/storage/<RUN_ID>/compute_logs/<fileKey>.out`. `fileKey` là 8 chữ thường ngẫu nhiên (ví dụ dạng `abcdefgh`), **không phải** step key. Đọc được không cần root. Hai `tail` sống đúng bằng thời gian của bước (33 giây với bước dbt, khoảng 1 giây với bước ngắn).
- **Step key và tên job:** chỉ có trong event log của Dagster. GraphQL `logsForRun(runId, limit ≤ 1000)` (giới hạn tối đa 1000, phải phân trang bằng `cursor`):
  - `EngineEvent` "Started process for run (pid: N)." → pid run worker.
  - `EngineEvent` "Executing steps using multiprocess executor: parent process (pid: N)" hoặc "Executing steps in process (pid: N)" → loại executor.
  - `LogsCapturedEvent { fileKey stepKeys pid }` → mỗi tiến trình bước một sự kiện.
  - `runOrError` / `runsOrError` → `pipelineName`, `startTime`, `endTime`, `stepStats`.
- **pid trong sự kiện là pid trong namespace của container**, không phải pid host. Map bằng dòng `NSpid:` trong `/proc/<pid>/status` (đọc được không cần root), ví dụ `NSpid: 2068600 202`.
- **Kiểm chéo thật** (2 run, 17/10 20:4x): với mỗi bước, `NSpid` của tiến trình host khớp `LogsCapturedEvent.pid`, `fileKey` từ `tail` khớp `fileKey` của sự kiện, và `NSpid` của run worker khớp "Started process for run (pid: N)". Khớp 5/5, gồm cả bước `sapo_dbt_assets` và các bước asset check.
- **Biến kiểu `DAGSTER_RUN_ID`:** không kiểm được, vì tiến trình trong container chạy bằng root và `/proc/<pid>/environ` trả về `Permission denied` với user thường. Theo code dagster-dbt 1.13.17, tiến trình dbt nhận `DBT_TARGET_PATH`, `DBT_LOG_PATH`, `DBT_PROJECT_DIR` (chỉ biết tên, chưa thấy giá trị). Tuy vậy, **không cần** biến môi trường nào: hai cách ở trên đủ để nhận diện.
- **Tiến trình dbt:** là con trực tiếp của tiến trình bước `sapo_dbt_assets`, có `argv[1]` kết thúc bằng `/dbt`. Trong một bước có 3 lần gọi: `dbt --version` (~2 giây), `dbt parse` (~3 giây), `dbt build --select …` (~26 giây khi realtime). Chỉ `build` có kết quả model. `--select` dài khoảng 11.800 ký tự, nên tuyệt đối không ghi dòng lệnh.
- **Tiến trình nền không thuộc run:** `sh -c …` (pid 1 trong container), `cleanup_dbt_target_dirs_standalone.py --loop-seconds 3600`, `dagster dev`, `code-server`, `api grpc`, `resource_tracker`, `dagster_webserver`, `dagster._daemon`. Nhận diện bằng `comm` và vài đối số đầu, gắn nhãn vai trò.
- Đọc được không cần root cho mọi tiến trình trong container: `status`, `stat`, `cmdline`, `cgroup`. **Không** đọc được: `io`, `environ`. `ns/*` và `fd/*` không dùng tới.

## 3. Job `in_process_executor`

`health_recon_daily_job`, `health_kpi_closure_job`, `health_checks_asset_job` (`orchestration/definitions.py:249`, `:258`, `:306`). Run `health_checks_asset_job` gần nhất cho thấy: "Started process for run (pid: N)", rồi "Executing steps in process (pid: N)" (cùng N), rồi **một** `LogsCapturedEvent` có `pid = N` và 43 step key. Kết luận: mọi bước chạy trong chính run worker (con spawn của `dagster api grpc`), dùng chung một `fileKey`. Vì vậy chỉ ghi được một dòng ở mức job, đúng như plan. Tiến trình `tail` lúc đó là con của run worker; chưa thấy trực tiếp vì job này chạy lúc `5 */2`, ngoài lúc quan sát, nhưng sự kiện GraphQL đủ để gắn.

## 4. `run_results.json`

- **Vị trí** (suy ra từ code và mount; chưa liệt kê được thư mục vì hook chặn mọi lệnh shell có chữ "target", và theo chỉ dẫn điều phối tôi không lách hook):
  - Mount: `/home/vantt/app/fg-dataware-house/transformation` → `/app/transformation`, cùng bind riêng `…/transformation/target` → `/app/transformation/target` (`docker inspect data_platform`).
  - dagster-dbt 1.13.17 (`DbtCliResource._get_unique_target_path`): thư mục con `"{op_name}-{run_id[:7]}-{uuid4()[:7]}"` khi có context, chỉ `"{uuid4()[:7]}"` khi không có context (`dbt parse`, `--version`). Truyền vào dbt bằng biến `DBT_TARGET_PATH`, không bằng `--target-path`.
  - Đường dẫn trên host cho bước build: `/home/vantt/app/fg-dataware-house/transformation/target/sapo_dbt_assets-<run_id[:7]>-<7 hex>/run_results.json`. Docstring `orchestration/ops/purge_runs.py:101` xác nhận tiền tố `sapo_dbt_assets-`.
- **Thời gian tồn tại:** `_cleanup_dbt_target_dirs(keep_days)` xoá thư mục có mtime cũ hơn `keep_days × 86400` giây. `PURGE_KEEP_DAYS` mặc định là 1; không có trong `docker-compose.yml` hay `.env.docker` (chỉ đếm tên biến, không đọc giá trị). Hàm này chạy mỗi 3600 giây (vòng nền) và lúc 01:00 (`maintain_cleanup_job`). Vậy thư mục sống **24–25 giờ**. Công cụ đọc ngay khi `dbt build` thoát, nên còn dư nhiều thời gian; nếu đọc trễ (công cụ khởi động lại) vẫn kịp trong 24 giờ.
- **Cấu trúc** (đọc từ bản chép shadow `/home/vantt/app/fg-dw-shadow/lake-A/_shadow_meta/run_results.json`, cùng dbt-core 1.11.12; chỉ in tên field):
  - Cấp đầu: `metadata`, `results`, `elapsed_time`, `args`.
  - `metadata`: `dbt_schema_version`, `dbt_version`, `generated_at`, `invocation_id`, `invocation_started_at`, `env`.
  - `results[]`: `status`, `timing`, `thread_id`, `execution_time`, `adapter_response`, `message`, `failures`, `unique_id`, `compiled`, `compiled_code`, `relation_name`, `batch_results`.
  - `timing[]`: `{name: compile|execute, started_at, completed_at}`, dạng ISO UTC có micro giây và `Z` (27 ký tự).
  - `adapter_response`: thường chỉ có `_message`. `rows_affected` chỉ có ở 25/779 kết quả với dbt-duckdb, nên cột số dòng sẽ trống phần lớn.
  - `args` **không** có `threads`; `threads: 1` lấy từ `transformation/profiles.yml`. Mọi kết quả có `thread_id` là `Thread-1 (worker)`. `args.invocation_command` chứa dòng lệnh đầy đủ, **không được chép**. `compiled_code` cũng không chép.
  - `unique_id` có các tiền tố `model`, `seed`, `test`, `unit_test`, `exposure`; mức model chỉ lấy `model.` (có thể thêm `seed.`).

## 5. Số nền thời gian nightly

Dagster chỉ giữ run khoảng 1 ngày (`PURGE_KEEP_DAYS=1`; run cũ nhất còn lại là 16/10 08:03). Không có nguồn nào khác trong repo lưu thời gian run, nên **không lấy được trung vị 7 nightly từ Dagster**. Số đang có:

| Ngày | Run | Bắt đầu | Thời gian | Nguồn |
|---|---|---|---|---|
| 15/10 | (theo lịch) | 03:00:55 | 5,2 phút (9 run SUCCESS kể cả chạy tay: 5,0–5,5, p50 5,2) | `plans/261015-1730-price-inventory-history/reports/phase-01-worker-report.md` |
| 16/10 | `3af400cf` | 03:01 | 5,3 phút | `plans/261014-2225-taxonomy-engine/plan.md` |
| 17/10 | `5ee65cf2` | 03:01:03 | 5,39 phút (59 bước) | GraphQL hôm nay |

Trung vị tạm của 3 đêm: **5,3 phút**. Đề nghị điều phối ghi thêm một dòng mỗi sáng, trước 01:00 hôm sau, cho tới khi đủ 7 đêm trước giờ cài. Trong nightly 17/10, bước dài nhất là `approach_script_autogen` 175,9 giây; `sapo_dbt_assets` chỉ 35,6 giây.

## Định dạng file đã chốt

Chung: TSV có dòng tiêu đề, phân tách bằng TAB, `\n`. Thời gian là **epoch giây UTC** (dạng số nguyên; mẫu tiến trình dùng số thập phân 3 chữ số). Ngày của file tính theo **giờ Việt Nam cố định UTC+7** (không có giờ mùa hè, nên không cần thư viện múi giờ); lệnh `report` in giờ địa phương. Byte là số nguyên byte. Bộ đếm cộng dồn được ghi nguyên giá trị thô (`report` tự tính hiệu), giúp chịu được mẫu bị thiếu; container tạo lại thì nhận ra nhờ `cid` đổi. Ô không có dữ liệu để trống.

- `containers-YYYYMMDD.tsv`: `ts container cid12 mem_current anon file kernel shmem mem_max ev_max ev_oom ev_oom_kill cpu_usage_usec cpu_throttled_usec nr_throttled io_rbytes io_wbytes psi_mem_some10 psi_mem_full10 psi_cpu_some10 psi_io_some10`. Dòng `self` dùng `container=self` (`mem_current` = RSS, `cpu_usage_usec` = utime+stime của chính công cụ), mỗi phút một dòng.
- `processes-YYYYMMDD.tsv` (một dòng khi tiến trình thoát): `ts_start ts_end container host_pid ns_pid ns_ppid role name run_id file_key rss_hwm_kb rss_max_kb cpu_s read_bytes write_bytes`. `role` ∈ `run_worker | step | dbt | step_child | service | other`. `name` là tên rút gọn, ví dụ `dbt build`, `refresh_rolling.py`, `dagster_webserver`; không bao giờ là dòng lệnh. `read/write_bytes` trống khi không có root.
- `steps-YYYYMMDD.tsv`: `run_id job step_key executor ts_start ts_end ns_pid rss_peak_tree_kb cpu_s read_bytes write_bytes`. `executor` ∈ `multiprocess | in_process`. Với `in_process`, `step_key` là `*` (dòng mức job).
- `models-YYYYMMDD.tsv`: `run_id unique_id status ts_start ts_end exec_s rss_peak_kb rss_delta_kb cpu_s rows_affected`.

## Những gì phase 1–3 phải đổi

**Phase 1**
1. Phát hiện tiến trình bằng cách **đọc `cgroup.procs` của từng container được theo dõi mỗi 1 giây**, thay cho quét `/proc` mỗi 5 giây. Đây chỉ là một file nhỏ, khoảng 10–60 pid, rẻ hơn quét `/proc`, và bắt được mọi bước. Tiến trình bước spawn sống ít nhất 2–3 giây, nên quét mỗi 5 giây sẽ sót bước ngắn.
2. Đọc thêm `NSpid` trong `/proc/<pid>/status` và lưu `ns_pid`. Không đọc `environ` ở bất cứ đâu, nên bỏ hẳn khỏi thiết kế và tài liệu (yêu cầu 5 được thoả chắc chắn hơn).
3. Lấy run id và `fileKey` bằng regex `/storage/([0-9a-f-]{36})/compute_logs/([a-z]+)\.(out|err)$` trên đối số cuối của tiến trình `tail` con; chỉ giữ hai khoá này. Lưu ý `cmdline` kết thúc bằng `\0`, phải bỏ phần tử rỗng.
4. Phân vai bằng cây cha–con: con `--multiprocessing-fork` của `dagster api grpc` là run worker; con `--multiprocessing-fork` của run worker là bước.
5. `io.stat` cộng mọi thiết bị; PSI lấy cả `full` cho memory.
6. Tên container: đọc `config.v2.json` (root), dự phòng bằng `cid12`.
7. Với tiến trình `dbt build`, nên lấy mẫu nhanh hơn: **250 ms** trong lúc nó sống (chỉ một tiến trình, đọc `status` và `stat`). Lý do: nightly 17/10 chạy cả dbt trong 35,6 giây cho mọi model, và bản shadow không có model nào > 1 giây. Với nhịp 1 giây gần như không model nào có RAM. Cần điều phối quyết (xem câu hỏi 1).

**Phase 2**
1. Gắn bước bằng GraphQL chỉ đọc `http://127.0.0.1:3000/graphql`: tự viết HTTP/1.1 POST trên `std::net::TcpStream`, `Connection: close`, timeout 5 giây. Gọi một lần khi run worker thoát; nếu lỗi thì thử lại mỗi 5 phút, tối đa 12 giờ (run còn trong Dagster ít nhất 24 giờ). Nếu vẫn lỗi: ghi dòng có `run_id` và `file_key`, `step_key` để trống. Nhớ `limit ≤ 1000` và phân trang theo `cursor`. GraphQL cho `nu-dataplatform` (cổng 13000) để ngoài phạm vi lần đầu.
2. Ghép: `(run_id, ns_pid)` → `LogsCapturedEvent.pid` → `stepKeys`; hoặc `(run_id, fileKey)`. Run worker: dò "Started process for run (pid: N)". Executor: dò "Executing steps in process" (`in_process`) hoặc "multiprocess executor".
3. Model: khi `dbt build` thoát, tìm thư mục `transformation/target/sapo_dbt_assets-<run_id[:7]>-*` (đường dẫn host ở mục 4) có mtime gần lúc thoát nhất, rồi đọc `run_results.json` trong đó. Lấy `timing[name=execute]`, parse ISO UTC. Không chép `args`, `compiled_code`, `message`.
4. **Dependency:** cần parse JSON (GraphQL và `run_results.json` vài MB có `compiled_code`). Đề nghị thêm `serde_json` (không cần derive) cạnh crate gzip. Plan nói "ưu tiên chỉ `std` + gzip", nên đây là một lệch nhỏ cần điều phối duyệt. Phương án thay thế là tự viết parser JSON tối thiểu: tốn công hơn và dễ lỗi hơn.

**Phase 3**
1. Unit không cần quyền đọc `environ`; lý do chạy root nay chỉ còn `/proc/<pid>/io` và `/var/lib/docker/containers`. `ProtectHome=read-only` vẫn cho đọc `/home/vantt/app/fg-dataware-house/transformation/target`. Unit cần mạng loopback cho GraphQL, nên **không** đặt `PrivateNetwork=yes`, và nếu dùng `IPAddressDeny=any` thì phải kèm `IPAddressAllow=localhost`.
2. README ghi rõ công cụ gọi GraphQL chỉ đọc (một truy vấn mỗi run đã xong) và đọc `run_results.json` trên host.

## Cần root (unit root của phase 3 sẽ có)

| Dữ kiện | Vì sao | Unit root lấy thế nào |
|---|---|---|
| Đọc/ghi đĩa theo tiến trình | `/proc/<pid>/io` của tiến trình root → `Permission denied` | Đọc trực tiếp; thiếu root thì để trống cột |
| Tên container | `/var/lib/docker` là `0710 root` | Đọc `containers/<id>/config.v2.json`, tìm chuỗi `"Name":"/` |
| `environ` | Không còn cần | Không đọc |
| Giá trị `DBT_TARGET_PATH` | Không cần (đã có cách suy theo thư mục) | Không đọc |

Mọi thứ khác (cgroup, `status`, `stat`, `cmdline`, `cgroup`, `NSpid`, GraphQL, `run_results.json` bản shadow) đọc được bằng user thường.

## Ghi chú tuân thủ

- Không ghi gì vào prod, không gửi tín hiệu, không kích hoạt job, không sửa file của repo hay plan khác.
- Có **một** lần `docker exec data_platform cat /app/var/dagster_home/dagster.yaml` để so với bản trong repo (giống nhau, đã lọc dòng có chữ password/secret/token). Lệnh này chạy một tiến trình ngắn trong container. Lẽ ra nên tránh; từ đó tôi không dùng `docker exec` nữa.
- Các script theo dõi tạm (`nice -n 19`, chu kỳ 0,3–0,5 giây, mỗi lần tối đa 7 phút) nằm trong scratchpad và đã kết thúc. Chỉ in dòng lệnh đã che: chuỗi dài thay bằng độ dài, số thay bằng `N`, UUID thay bằng `<RUN_ID>`.

## Câu hỏi cho điều phối

1. Đồng ý lấy mẫu `dbt build` mỗi 250 ms (thay 1 giây) để mức model có RAM không? Nếu giữ 1 giây, tiêu chí 4 vẫn đạt về hình thức (không model nào > 3 giây) nhưng cột RAM gần như trống.
2. Duyệt thêm `serde_json` làm dependency thứ hai?
3. Ai ghi số nền nightly mỗi sáng tới khi đủ 7 đêm (hiện có 15, 16, 17/10)?
