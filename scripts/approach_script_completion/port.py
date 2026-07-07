"""port.py — ApproachScriptCompletionProvider outbound port."""
from __future__ import annotations

from typing import Protocol


class ApproachScriptCompletionProvider(Protocol):
    """Nhận prompt approach-script đã lắp sẵn, trả raw text completion.

    KHÔNG phải LLM abstraction tổng quát cho repo — chỉ phục vụ đúng
    scripts/generate_approach_scripts.py.
    """

    name: str

    @property
    def model_label(self) -> str:
        """Nhãn model/binary cụ thể, dùng cho meta.model trong output JSON."""
        ...

    def complete(self, prompt: str, timeout: int) -> str:
        """Trả raw text completion (chứa JSON approach-script).

        Raise ApproachScriptCompletionError khi fail.
        """
        ...
