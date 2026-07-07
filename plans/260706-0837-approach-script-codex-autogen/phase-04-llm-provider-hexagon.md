# Phase 04 — Hexagon completion provider cho approach-script (đổi được codex↔API)

## Vì sao
`generate_approach_scripts.py` hiện gọi thẳng `subprocess` tới `codex exec` (hardcode trong `run_codex()`). Ban đầu `data_platform` không cài codex CLI — **đã fix** (2026-07-06, ngoài phase này): `Dockerfile.dataplatform` giờ cài Node 20.x + `npm install -g @openai/codex`; auth (OAuth subscription, không phải API key) sống trong named volume `agent_codex_config:/root/.codex` (`docker-compose.yml`), cùng pattern `../fgos` — cần 1 lần `docker compose exec data_platform codex login` sau khi lên container để volume có session.
Codex giờ **chạy được** trong `data_platform`, nhưng vẫn tách hexagon vì: (1) auth là subscription cá nhân của user — asset nightly (phase 05) gọi hàng loạt mỗi đêm dùng chung quota đó, rủi ro rate-limit/tốn quota cá nhân cho việc tự động; (2) nếu session OAuth hết hạn/cần re-login (không tự động re-auth được trong job nightly), luồng tự động cần fallback không phụ thuộc login tương tác. Tách port để cắm adapter API-based (không phụ thuộc OAuth cá nhân) cho luồng tự động khi cần, giữ codex CLI làm adapter mặc định cho luồng thủ công/dry-run.

**Đặt tên:** port này KHÔNG phải một "LLM provider" tổng quát dùng chung cho repo — nó chỉ làm đúng 1 việc: nhận prompt approach-script đã lắp sẵn, trả raw text completion. Tên phải phản ánh đúng phạm vi hẹp đó (approach-script only), tránh style "LLMProvider"/"generate" chung chung dễ bị hiểu nhầm là abstraction tái dùng được cho các tính năng AI khác trong repo.

## Thiết kế
Port (Protocol, theo đúng convention hexagon đã có ở `crm/src/domain/ports/*.py`):
```python
# scripts/approach_script_completion/port.py
class ApproachScriptCompletionProvider(Protocol):
    def complete(self, prompt: str, timeout: int) -> str:
        """Trả raw text completion (chứa JSON approach-script).
        Raise ApproachScriptCompletionError khi fail."""
```
- `scripts/approach_script_completion/errors.py`: `class ApproachScriptCompletionError(RuntimeError)`.
- `scripts/approach_script_completion/codex_cli_provider.py`: `class CodexCliCompletionProvider` — di chuyển nguyên `run_codex()` + logic `codex_cmd`/`FileNotFoundError`/`TimeoutExpired` từ `generate_approach_scripts.py` vào đây, raise `ApproachScriptCompletionError` thay vì `sys.exit`/tuple lỗi.
- `scripts/approach_script_completion/anthropic_provider.py`: `class AnthropicCompletionProvider` — dùng SDK `anthropic`, model qua env `ANTHROPIC_MODEL` (default `claude-sonnet-5`), key qua env `ANTHROPIC_API_KEY` (bắt buộc, raise rõ ràng nếu thiếu).
- `scripts/approach_script_completion/factory.py`: `get_completion_provider(name: str) -> ApproachScriptCompletionProvider` — map `{"codex": CodexCliCompletionProvider, "anthropic": AnthropicCompletionProvider}`, default `"codex"` (giữ hành vi cũ không đổi khi không truyền `--provider`).

`generate_approach_scripts.py`:
- Thêm `--provider {codex,anthropic}` (default `codex`, hoặc env `APPROACH_SCRIPT_PROVIDER`) — flag CLI giữ tên ngắn `--provider` cho user (chọn giữa 2 adapter), không cần đổi theo tên class dài.
- Thay vòng lặp gọi `run_codex(prompt, args.codex_cmd, args.timeout)` bằng `provider.complete(prompt, args.timeout)`; bắt `ApproachScriptCompletionError` thay cho `subprocess.TimeoutExpired`/`FileNotFoundError` rời rạc hiện tại.
- `--codex-cmd`/`CODEX_CMD` chỉ còn ý nghĩa khi `--provider codex` (truyền vào `CodexCliCompletionProvider(codex_cmd=...)`).
- `build_meta()`: `meta.model`/`meta.generator` lấy từ provider (thêm property `provider.name`/`provider.model_label` thay vì đọc `codex_cmd.split()[0]` cứng).

## Files
- Tạo: `scripts/approach_script_completion/__init__.py`, `port.py`, `errors.py`, `codex_cli_provider.py`, `anthropic_provider.py`, `factory.py`
- Tạo: `scripts/requirements.txt` (mới — pin `anthropic`; `scripts/` hiện chưa có requirements riêng, dùng chung `ingestion/requirements.txt` của `data_platform` image nhưng thêm dep không-ingestion vào đó là sai chỗ)
- Sửa: `Dockerfile.dataplatform` — thêm `COPY scripts/requirements.txt` + `RUN pip install -r scripts/requirements.txt` (sau dòng 19, trước `COPY scripts /app/scripts` dòng 37 — đặt COPY requirements trước để tận dụng layer cache)
- Sửa: `scripts/generate_approach_scripts.py` (bỏ `run_codex()`, `import subprocess/shlex` không cần trực tiếp nữa — chuyển vào `codex_cli_provider.py`)

## Validate
- Unit test `factory.get_completion_provider("codex")` trả `CodexCliCompletionProvider`, `"anthropic"` trả `AnthropicCompletionProvider`, tên lạ → `ValueError`.
- `--dry-run` không đổi hành vi (không gọi provider, chỉ ghi prompt) — test hồi quy trên flow hiện có.
- Mock `AnthropicCompletionProvider.complete` (không gọi API thật trong test) → verify `generate_approach_scripts.py` gọi đúng `provider.complete(prompt, timeout)` và JSON/lint pipeline sau đó không đổi.
- Không có smoke test API thật trong CI/build máy (cần `ANTHROPIC_API_KEY` thật) — user tự smoke `--provider anthropic --ids <1 khách>` khi có key.

## Rủi ro
- Anthropic API tốn phí mỗi lần gọi thật (khác codex CLI dùng subscription sẵn có) — cần user xác nhận key/quota trước khi bật phase 05 (unresolved question).
- Output codex vs Anthropic có thể lệch định dạng JSON (đầu ra thô quanh JSON) — `extract_json_block()` giữ nguyên, không đổi, nên rủi ro thấp nhưng cần validate qua vài lần chạy thật.
