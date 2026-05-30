"""Application settings (composition-root layer).

Reads from environment so the app runs unchanged on Windows-dev and Linux-container.
No domain logic here.

Derived paths (rolling_dir, known_tables_path) are computed from olap_db_path so a
single env-var override covers all three — no need to set them individually.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    olap_db_path: str
    app_tz: str
    port: int
    title: str
    # Filesystem path to rolling parquet export dirs: .../marts/rolling/<table>/*.parquet
    rolling_dir: str = field(default="")
    # Path to .known_tables.json drift marker written by refresh_rolling.py
    known_tables_path: str = field(default="")

    @classmethod
    def from_env(cls) -> "Settings":
        olap_db_path = os.environ.get(
            "OLAP_DB_PATH", "/app/var/data_lake/serving/olap.duckdb"
        )
        # Derive sibling paths from the serving DB location.
        # Structure (container): /app/var/data_lake/
        #   serving/olap.duckdb
        #   export/marts/rolling/<table>/*.parquet
        #   serving/.known_tables.json
        serving_dir = os.path.dirname(olap_db_path)
        data_lake_dir = os.path.dirname(serving_dir)
        default_rolling = os.path.join(data_lake_dir, "export", "marts", "rolling")
        default_known = os.path.join(serving_dir, ".known_tables.json")

        return cls(
            olap_db_path=olap_db_path,
            app_tz=os.environ.get("APP_TZ", "Asia/Ho_Chi_Minh"),
            port=int(os.environ.get("DETAIL_VIEW_PORT", "8000")),
            title=os.environ.get("DETAIL_VIEW_TITLE", "detailView"),
            rolling_dir=os.environ.get("ROLLING_DIR", default_rolling),
            known_tables_path=os.environ.get("KNOWN_TABLES_PATH", default_known),
        )
