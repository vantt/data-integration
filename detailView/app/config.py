"""Application settings (composition-root layer).

Reads from environment so the app runs unchanged on Windows-dev and Linux-container.
No domain logic here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    olap_db_path: str
    app_tz: str
    port: int
    title: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            # Container path; on Windows-dev override OLAP_DB_PATH to the local serving DB.
            olap_db_path=os.environ.get(
                "OLAP_DB_PATH", "/app/var/data_lake/serving/olap.duckdb"
            ),
            app_tz=os.environ.get("APP_TZ", "Asia/Ho_Chi_Minh"),
            port=int(os.environ.get("DETAIL_VIEW_PORT", "8000")),
            title=os.environ.get("DETAIL_VIEW_TITLE", "detailView"),
        )
