# Research: sandbox chạy code cho MCP "code mode" — dùng sẵn hay tự làm?

Ngày: 2026-10-19 (Asia/Saigon). Người nghiên cứu: researcher agent. Phạm vi: chỉ đọc nguồn công khai và kiểm tra máy local (`/dev/kvm`, `bwrap`, RAM); không chạy gì trên prod, không cài gói nào.

## Kết luận trước

Có. Dự án làm gần đúng nhu cầu đã tồn tại và vừa ổn định: **Pydantic Monty** (`pydantic-monty`) ra v1.0.0 ngày **2026-09-25**, bản hiện tại là 1.2.0 (2026-10-18). Monty là interpreter Python viết bằng Rust, deny-by-default, chạy trong pool worker subprocess, có host function sync/async gọi từ Python host, có giới hạn memory/thời gian/đệ quy/số lần gọi host, có type-check bằng stub và snapshot. Đây đúng là thứ mà thiết kế "Rust + QuickJS + bubblewrap + stdio" định tự làm, chỉ khác là agent viết Python (tập con) thay vì JS. Pydantic AI đã dùng nó làm nền cho `CodeMode`.

Đề xuất: **không tự viết binary Rust/QuickJS**. Dùng Monty + một lớp bọc mỏng (MCP `search_api`/`execute`, map hàm CRM, giới hạn, cắt kết quả, audit). Giữ một interface runner nhỏ để thay được; phương án JS dự phòng là `quickjs-rs` (LangChain, QuickJS-ng trong wasmtime, wheel thuần Python). Chốt sau khi qua các thử nghiệm ở mục 6.

Ghi chú cập nhật so với "đã biết": mô tả Monty "thiếu datetime/json/re/class" đã lỗi thời. Bản hiện tại có `datetime`, `json`, `re`, `math`, `dataclasses` (một phần), class đơn giản, `match`, `async/await`; vẫn thiếu kế thừa class, generator, `enum`, thư viện bên thứ ba ([Limitations](https://pydantic.dev/docs/monty/limitations/)).

## 1. Danh sách ứng viên đã kiểm (tồn tại thật, có nguồn)

### Bảng chính — ứng viên đáng kể

| Ứng viên | Ngôn ngữ agent | Cơ chế cô lập | Tự host | Footprint | Giới hạn có sẵn | Bridge host | MCP code mode sẵn | Trưởng thành / license | Rủi ro bảo mật đã biết |
|---|---|---|---|---|---|---|---|---|---|
| **Pydantic Monty** ([repo](https://github.com/pydantic/monty), [docs](https://pydantic.dev/docs/monty/)) | Python 3.14 (tập con) | Interpreter deny-by-default (không có FS/env/net trừ khi host cấp), chạy trong worker subprocess; không có seccomp/VM ([security](https://pydantic.dev/docs/monty/concepts/security/)) | Có, `pip install pydantic-monty` | Wheel runtime ~15.7 MB manylinux x86_64 ([PyPI](https://pypi.org/project/pydantic-monty-runtime/)); sandbox mới <1 ms khi pool đã mở, ~5 ms kể cả tạo pool (đo trên M3 Max) ([alternatives](https://pydantic.dev/docs/monty/reference/alternatives/)); RSS mỗi worker: chưa có số | `max_memory`, `max_feed_duration_secs`, `max_turn_duration_secs`, `max_recursion_depth` (1000), `max_suspensions` (1000), `request_timeout` giết worker ([resource limits](https://pydantic.dev/docs/monty/concepts/resource-limits/)) | In-process callback từ Python host qua `external_lookup` / `ExternalModule`, hỗ trợ `async def` (`AsyncMonty`); worker nói chuyện với host qua giao thức riêng ([quickstart](https://pydantic.dev/docs/monty/quickstart/python/)) | Không có MCP server riêng; Pydantic AI có `CodeMode` (`run_code`) ([docs](https://pydantic.dev/docs/ai/harness/code-mode/)) | v1.2.0 (2026-10-18), ~8.7k stars, MIT; Pydantic AI và Airflow provider dùng ([Airflow](https://airflow.apache.org/docs/apache-airflow-providers-common-ai/0.10.0/code_mode.html)) | Chương trình "Hack Monty" 3 vòng; lỗ hổng vòng 1 (FS giả qua `OSAccess`) đã vá từ v0.0.16, vòng 2 không ai thoát ([postmortem](https://pydantic.dev/articles/hack-monty-postmortem)). Không tìm thấy CVE |
| **quickjs-rs + langchain-quickjs** ([repo](https://github.com/langchain-ai/quickjs-rs), [PyPI](https://pypi.org/project/quickjs-rs/)) | JS/TS (TS bị strip bằng OXC wasm) | QuickJS-ng (rquickjs) biên dịch `wasm32-wasip1`, chạy trong wasmtime; mỗi Context là một wasm instance | Có, wheel thuần Python ~0.8 MB + `wasmtime` | Chưa có số RAM/khởi động | `memory_limit`, timeout mỗi eval (instance sống sót), stack trap trong wasm; deepagents thêm `max_ptc_calls`, `max_result_chars` ([deepagents interpreters](https://docs.langchain.com/oss/python/deepagents/interpreters.md)) | `@ctx.function` đăng ký hàm Python (kể cả async) thành global JS, in-process | Không phải MCP; deepagents có "PTC" gọi tool từ REPL | v0.2.5 (2026-07-24), Alpha, 13 stars, MIT; LangChain dùng trong deepagents (beta) | Rủi ro chính là wasmtime/Cranelift; wasmtime có CVE-2026-34971 (aarch64, cấu hình không mặc định) ([NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-34971)) |
| **modebox** ([repo](https://github.com/farming-labs/modebox)) | JS/TS | QuickJS-ng trong wasmtime (wizer pre-init), không WASI; `sh()` riêng chạy dưới bubblewrap+seccomp | Có, `pip install modebox` (wheel Linux glibc x64/arm64) | Khởi động ~0.2 ms, 1 host call ~0.4 ms (Node, Apple Silicon, tự đo); RAM chưa có số | fuel, epoch interruption, virtual clock; tên tham số/mặc định chưa xác minh | Host functions từ Rust/Node/Python, có approval-gate tạm dừng VM và token tiếp tục mã hoá | **Có**: `modebox mcp` lộ `types` + `execute`, bridge MCP servers thành hàm có kiểu | v0.1.3, 2 stars, MIT — rất non | Chưa có báo cáo; SECURITY.md tự liệt kê "known gaps" (chưa đọc chi tiết) |
| **Hyperlight / hyperlight-sandbox** ([sandbox](https://github.com/hyperlight-dev/hyperlight-sandbox), [hyperlight-js](https://github.com/hyperlight-dev/hyperlight-js)) | JS (HyperlightJS/QuickJS) hoặc Python/JS qua Wasm component | Micro-VM phần cứng (KVM/MSHV), không OS khách | Có, `uv pip install "hyperlight-sandbox[wasm,python_guest]"` | Cold start <2 ms (Microsoft tự công bố) ([blog](https://opensource.microsoft.com/blog/2025/03/10/build-a-hyperlight-c-guest-to-securely-execute-javascript/)); RAM chưa có số | Execution monitors (timeout/resource) — giá trị chưa xác minh; giới hạn ghi file 5/20 MiB | Host đăng ký callable làm tool, guest gọi theo tên, có kiểm schema; SDK Python | Không | hyperlight core ~4.7k stars (CNCF sandbox, Apache-2.0); hyperlight-sandbox 76 stars, chưa có release | Cần `/dev/kvm` trong container; build cần toolchain bare-metal |
| **Cloudflare `@cloudflare/codemode`** ([package](https://github.com/cloudflare/agents/tree/main/packages/codemode)) | JS/TS | V8 isolate qua Dynamic Worker Loader | Chỉ trên Cloudflare Workers (hoặc tự viết `Executor`) | Không áp dụng | Theo nền tảng Workers | Workers RPC; `McpConnector`, `codeMcpServer()` | **Có** (`search`/`execute`) ([guide](https://developers.cloudflare.com/agents/model-context-protocol/guides/build-codemode-mcp-server/)) | Experimental, Apache/MIT (theo repo agents) | Phụ thuộc Cloudflare; không dùng được từ Python host |
| **TanStack AI code mode** ([isolates](https://tanstack.com/ai/latest/docs/code-mode/code-mode-isolates.md)) | TS | isolated-vm, QuickJS WASM, QuickJS Bun FFI, Cloudflare, Daytona, E2B | Có (Node/Bun) | Mặc định 128 MB, 30 s | memory, timeout, stack, `maxToolCalls` | Async function gọi về host JS | Thư viện, không phải MCP proxy | v0.x | Host phải là JS/TS |
| **OpenClaw code mode** ([internals](https://docs.openclaw.ai/tools/code-mode/internals)) | JS/TS | `quickjs-wasi` (Vercel Labs) trong Node worker thread | Gắn trong OpenClaw | Chưa có số | memory, interrupt, snapshot | `ALL_TOOLS`/`tools`, MCP namespace | Trong sản phẩm, không tách | Experimental, tắt mặc định | Không tách ra dùng từ Python được |
| **UTCP code-mode** ([repo](https://github.com/universal-tool-calling-protocol/code-mode)) | TS | "Node.js VM sandboxing" (không ghi rõ engine) | Có (npm, có MCP bridge `@utcp/code-mode-mcp`) | Chưa có số | timeout 30 s | `callToolChain` gọi MCP/UTCP tools | **Có** | ~1.6k stars, MPL-2.0 | Nếu là `node:vm` thì không phải ranh giới bảo mật (chưa xác minh engine) |
| **elusznik/mcp-server-code-execution-mode** ([repo](https://github.com/elusznik/mcp-server-code-execution-mode)) | Python đầy đủ | Container rootless Podman/Docker, `--network none`, read-only, cap-drop | Có | Container 512 MiB mặc định | memory, PIDs 128, timeout 30–120 s | Proxy stdio MCP qua volume `/ipc`, JSON-framed | **Có** | 340 stars, GPL-3.0 | Nặng RAM; GPL |
| **microsandbox** ([repo](https://github.com/superradcompany/microsandbox)) | Bất kỳ (image OCI) | microVM libkrun/KVM | Có, embedded SDK Python | Boot <100 ms (M1); ví dụ cấp 64–512 MiB mỗi VM | CPU/memory theo VM | **Không có** bridge hàm host (chỉ exec + net allowlist) | MCP quản lý sandbox, không phải code mode | ~8.7k stars, beta, Apache-2.0 | Cần KVM; quá nặng cho nhu cầu này |
| **Anthropic sandbox-runtime (srt)** ([repo](https://github.com/anthropic-experimental/sandbox-runtime)) | Bất kỳ process | bubblewrap + netns + proxy | Có (npm) | Nhẹ | Không có giới hạn RAM/CPU riêng | Không | Không | Research preview | Ubuntu 24.04+ có thể phải nới AppArmor userns |

### Ứng viên đã kiểm và loại nhanh

- **mcp-run-python** (Pydantic, Pyodide trong Deno): đã archive ngày 2026-01-30; chính tác giả nói "not a safe sandbox" và khuyên chuyển sang Monty ([repo](https://github.com/pydantic/mcp-run-python)).
- **isolated-vm**: README ghi "maintenance mode", memory limit chỉ là "guideline" (kẻ tấn công có thể dùng 2–3 lần), và cần Node host ([repo](https://github.com/laverdet/isolated-vm)).
- **smolagents LocalPythonExecutor / RestrictedPython-style**: README tự nhận không phải sandbox; từng có CVE-2025-5120 (sandbox escape, vá ở 1.17.0) ([advisory](https://advisories.gitlab.com/pkg/pypi/smolagents/CVE-2025-5120/)).
- **Gói `quickjs` (PyPI, PetterS)**: bản cuối 1.19.4 từ 2023-11; time limit không dùng chung được với callback; Simon Willison kết luận "for hostile inputs, the only real option is a separate process" ([PyPI](https://pypi.org/project/quickjs/), [nghiên cứu](https://github.com/simonw/research/tree/main/quickjs-async-sandbox)).
- **Microsoft Wassette**: biến Wasm component thành MCP tool (Wasmtime, deny-by-default), nhưng là "chạy tool đã biên dịch", không phải "chạy code agent viết lúc runtime" ([blog](https://opensource.microsoft.com/blog/2025/08/06/introducing-wassette-webassembly-based-tools-for-ai-agents/)).
- **AWS LLRT**: runtime Lambda thử nghiệm, Node-compatible, không thiết kế để làm sandbox deny-by-default ([InfoQ](https://www.infoq.com/news/2024/02/aws-llrt-lambda-experimental/)); trạng thái 2026 chưa xác minh.
- **Javy / Extism js-pdk**: biên dịch JS thành module Wasm (QuickJS), hợp cho plugin dựng sẵn; module tĩnh ≥ ~869 KB; không có sẵn vòng "eval code agent + gọi hàm host + MCP" ([Shopify](https://shopify.engineering/javascript-in-webassembly-for-shopify-functions), [Extism host functions](https://extism.org/docs/concepts/host-functions)). Dùng được như viên gạch nhưng vẫn phải tự làm phần còn lại.
- **Boa, deno_core**: engine để nhúng; không tìm thấy giới hạn memory tích hợp của Boa (chưa xác minh); deno_core kéo V8, nặng hơn mục tiêu. Đều là "tự làm" ở mức thấp hơn rquickjs.
- **E2B / Daytona self-host**: E2B cần Firecracker/KVM + Terraform/Nomad; Daytona dùng container và nguồn thứ ba nói repo mở ngừng nhận đóng góp từ 2026-06 (chưa xác minh) ([northflank](https://northflank.com/blog/self-hostable-alternatives-to-e2b-for-ai-agents), [nightona README](https://cdn.jsdelivr.net/gh/nightona-co/nightona@main/README.md)). Quá nặng cho một máy chật RAM.
- **kubernetes-sigs/agent-sandbox, gVisor, Kata**: cần Kubernetes ([site](https://agent-sandbox.sigs.k8s.io)). Không khớp hạ tầng.
- **nsjail**: lớp OS (namespaces + seccomp-bpf + rlimit), tương đương vai trò bubblewrap; không giải bài bridge hàm ([mirror README](https://android-us.linaro.org/platform/external/nsjail.git/tree/README.md)).
- **Riza**: không tìm được nguồn gốc mô tả bản tự host; chưa xác minh.
- Các dự án nhỏ khác (hoangnb24/mcp-code-mode, inhuman/mcp-exec, Redpanda code mode gateway): prototype hoặc gắn với sản phẩm khác ([Redpanda](https://docs.redpanda.com/agentic-data-plane/gateway/code-mode/), [mcp-exec](https://pkg.go.dev/github.com/inhuman/mcp-exec)).

Bối cảnh mẫu thiết kế: mô hình `search` + `execute` mà dự án định dùng chính là mô hình Cloudflare Code Mode và Anthropic mô tả ([Anthropic](https://www.anthropic.com/engineering/code-execution-with-mcp), [Cloudflare changelog](https://developers.cloudflare.com/changelog/post/2026-03-17-codemode-sdk-v021)). Tức là thiết kế đúng hướng; câu hỏi chỉ là phần sandbox nên mua sẵn hay tự làm.

## 2. Xếp hạng top 5 theo độ khớp nhu cầu

Tiêu chí: tự host nhẹ, deny-by-default, bridge hàm host từ **Python host**, giới hạn tài nguyên, trưởng thành, ít bảo trì.

1. **Pydantic Monty** — khớp gần nhất. Python host gốc, async host function, đủ bộ giới hạn, pool subprocess có `request_timeout` giết worker, type-check bằng stub (giảm lỗi code của agent trước khi chạy), v1.x, có đội ngũ thương mại đứng sau và chương trình săn lỗi. Điểm trừ: ngôn ngữ là tập con Python; không có lớp OS sandbox trong bản OSS.
2. **quickjs-rs (LangChain)** — phương án JS tốt nhất cho Python host. Đúng kiến trúc dự án định làm (rquickjs/QuickJS-ng) nhưng đặt trong wasmtime nên lỗi bộ nhớ của QuickJS bị nhốt trong wasm. Điểm trừ: Alpha, 13 stars, chạy in-process (một lỗi wasmtime chạm tới process host), cần tự bọc subprocess nếu muốn cô lập crash.
3. **modebox** — tính năng gần nhất với mong muốn (MCP `types`/`execute`, approval, Python binding), nhưng 0.1.x và 2 stars: rủi ro bỏ dở cao. Đáng theo dõi, chưa nên phụ thuộc.
4. **hyperlight-sandbox** — cô lập mạnh nhất (micro-VM), có SDK Python và tool bridge. Điểm trừ: chưa có release, cần `/dev/kvm` truyền vào container, toolchain build phức tạp. Máy local có `/dev/kvm` (đã kiểm), nên là phương án nâng cấp nếu sau này cần multi-tenant thù địch.
5. **UTCP code-mode** — có sẵn MCP code mode, nhưng engine "Node.js VM" chưa rõ có phải ranh giới bảo mật thật không, và host là Node. Không khớp Python host.

## 3. So với tự làm (Rust + QuickJS + bubblewrap + stdio)

| Tiêu chí | Tự làm Rust+QuickJS+bwrap | Monty + bọc mỏng | quickjs-rs + bọc mỏng |
|---|---|---|---|
| Khối lượng ban đầu | Binary Rust, giao thức stdio JSON, pool/timeout, map lỗi, đóng gói CI cho nhiều kiến trúc, thư viện host Python | Lớp MCP + map hàm CRM + stub kiểu; vài trăm dòng Python | Như Monty + tự bọc subprocess nếu cần |
| Bảo trì dài hạn | Một người phải theo dõi CVE QuickJS-ng (2026 đã có ít nhất 5 CVE: 0821, 0822, 1144, 1145, 37630 — [Red Hat](https://access.redhat.com/security/cve/CVE-2026-1144), [SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2026-37630/)), rquickjs, bwrap | Pydantic bảo trì; ta chỉ nâng version | LangChain bảo trì nhưng Alpha |
| Bảo mật | QuickJS native: lỗi heap overflow trong engine = chạy code trong process sandbox; bwrap chặn FS/net bù lại. Tốt nếu làm đúng, nhưng toàn bộ việc kiểm định là của ta | Không chạy CPython/C; interpreter Rust tự viết, đã qua 3 vòng săn lỗi công khai; không có seccomp/namespace (có thể tự thêm) | Lỗi QuickJS bị wasm nhốt; còn rủi ro wasmtime |
| RAM | Rất thấp (QuickJS vài MB) — ước lượng, chưa đo | Worker subprocess; RSS chưa có số, phải đo | wasmtime + module; chưa có số |
| Ngôn ngữ agent | JS (model viết tốt) | Python tập con (model viết tốt, nhưng sẽ vấp kế thừa class, generator…; type-check bắt sớm) | JS/TS |
| Khớp Python host | Phải tự viết | Gốc, async | Gốc, async |
| Tính năng thêm | Phải tự làm | Snapshot/resume ở host call, type stub, `max_suspensions` = trần số lời gọi CRM | Snapshot heap |

Đánh giá thẳng: tự làm chỉ thắng ở chỗ kiểm soát hoàn toàn và RAM có thể thấp hơn. Mọi thứ khác (thời gian, bảo trì, kiểm định bảo mật, khớp Python) Monty đã làm và đã được người khác tấn công thử. Với một đội nhỏ, gánh CVE của QuickJS native là chi phí thật và lâu dài. "Bộ chạy thay được (QuickJS, sau có thể Monty)" trong thiết kế gốc nên đảo lại: Monty trước, JS sau nếu thực nghiệm cho thấy cần.

## 4. Đề xuất cụ thể

**Chọn: Monty + bọc mỏng, đóng gói thành repo dùng chung như dự định, nhưng repo đó là lớp "code-mode host" bằng Python chứ không phải sandbox runtime.**

Repo dùng chung gồm:
- Interface `Runner` tối thiểu (`run(code, functions, limits) -> result`), cài đặt mặc định bằng `pydantic_monty.AsyncMonty`.
- Bộ sinh stub kiểu từ registry hàm CRM (Monty có type-check; `search_api` trả về stub thay vì JSON schema).
- Áp giới hạn: `max_memory`, `max_feed_duration_secs`, `request_timeout`, `max_suspensions` (trần số lời gọi hàm CRM), cắt kích thước kết quả trước khi trả model.
- Pool riêng cho mỗi MCP server, `max_processes` nhỏ, `max_checkouts_per_worker` để tái chế worker, hủy session sau mỗi lần chạm giới hạn memory/thời gian (docs yêu cầu vì heap có thể hỏng).
- Lớp OS phòng thủ thêm, tuỳ chọn: chạy worker qua `binary_path` trỏ tới script bọc `bwrap --unshare-all` (chưa xác minh Monty chấp nhận wrapper; xem thử nghiệm 3). Nếu không được, dựa vào cgroup/`mem_limit` của Docker cho cả container MCP.

Phân quyền, che PII, audit, proposal→duyệt vẫn ở CRM như thiết kế; sandbox không cần biết. Lưu ý từ deepagents áp dụng tương tự: mọi hàm lộ vào sandbox là quyền thật, nên allowlist hàm phải hẹp ([deepagents](https://docs.langchain.com/oss/python/deepagents/interpreters.md)).

Phương án dự phòng nếu Monty không đạt: `quickjs-rs` sau cùng interface `Runner`, chạy trong subprocess riêng. Phương án nâng cấp cô lập nếu sau này có người dùng ngoài/đa tenant thù địch: hyperlight-sandbox (máy có KVM).

## 5. Rủi ro áp dụng

- Monty v1 mới 3 tuần tuổi; tốc độ release dày (1.0.0 → 1.2.0 trong 23 ngày). Ghim version, đọc changelog trước khi nâng.
- `max_memory` không giới hạn RSS process; docs khuyên dùng cgroup/OS limit thêm ([resource limits](https://pydantic.dev/docs/monty/concepts/resource-limits/)).
- Thời gian chờ host function không bị tính vào giới hạn thời gian Monty; tự đặt timeout cho hàm CRM ở phía host.
- Tập con Python có thể làm agent viết code lỗi; chi phí là một vòng retry, không phải lỗ hổng.
- Bản OSS không có OS isolation; Full Monty (thương mại) mới có.

## 6. Phải kiểm thực nghiệm trước khi chốt

1. **RAM**: đo RSS mỗi worker Monty khi rảnh và khi chạy truy vấn điển hình, với pool 2–4 worker, trong container giới hạn 8 GiB đang chạy CRM. So với quickjs-rs cùng tác vụ.
2. **Chạy trong Docker**: worker subprocess khởi động được dưới seccomp/AppArmor mặc định của container; thời gian checkout lạnh/ấm.
3. **Bọc bwrap**: `binary_path` trỏ tới wrapper `bwrap` có chạy được không (bwrap trong Docker cần user namespace; có thể bị chặn). Nếu không, ghi rõ lớp OS là cgroup của container.
4. **Tấn công cơ bản**: vòng lặp vô hạn, `'x' * 10**12`, list tăng dần, đệ quy sâu, in output khổng lồ, gọi hàm host vượt `max_suspensions`, hàm host chậm (kiểm timeout phía host), worker crash → pool tự thay.
5. **Tỷ lệ thành công của agent**: 20–30 tác vụ CRM thật (tìm khách, ghi kết quả gọi, đếm, lọc) chạy bằng model đang dùng, Monty (có type-check) so với JS (quickjs-rs). Đo tỷ lệ chạy đúng lần đầu và số retry.
6. **Độ trễ end-to-end**: một `execute` với 5–20 lời gọi CRM.

## 7. Giới hạn của nghiên cứu này

- Không chạy thử bất kỳ ứng viên nào; mọi số đo hiệu năng là số tự công bố của dự án (thường trên Apple Silicon), không phải trên máy Linux của chúng ta.
- Không đọc mã nguồn Monty để xác minh giao thức worker, cách bọc `binary_path`, hay seccomp; không đọc SECURITY.md của modebox.
- Số stars/version lấy từ trang GitHub/PyPI tại thời điểm tra cứu; vài số từ trang thứ ba đã được ghi rõ.
- Không đánh giá Full Monty (thương mại), Deno Sandbox, Vercel Sandbox vì là dịch vụ cloud, trái với yêu cầu tự host.

## Câu hỏi còn mở

- Agent viết Python (Monty) có chấp nhận được không, hay đã có lý do bắt buộc JS (ví dụ prompt/stub đã viết theo TS)?
- MCP phân tích cho CEO có cần tính toán nặng (pandas-like) trong sandbox không? Monty và QuickJS đều không hợp việc đó; nếu cần thì là bài toán khác (DuckDB phía host).
- Có kế hoạch cho người ngoài công ty dùng MCP này không? Nếu có, nên đánh giá lại lớp cô lập OS/micro-VM.
