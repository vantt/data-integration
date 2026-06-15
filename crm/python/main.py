"""CRM Python server entry point.

Run directly:
  python main.py

Or via uvicorn (with reload for development):
  uvicorn main:app --host 0.0.0.0 --port 8090 --reload

Module-level `app` is required for uvicorn --reload to pick up changes.
"""
from __future__ import annotations

import uvicorn

from composition import create_app
from config import server_port

# Module-level instance — required for `uvicorn main:app --reload`.
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=server_port(),
        reload=False,
    )
