"""crm_history_reader.py — Đọc notes/activities thật từ crm.db cho approach-prompt.

Đóng nửa hở của vòng lặp (WS-A1): nhân viên ghi chú/log cuộc gọi vào CRM →
builder đọc lại → prompt thế hệ sau biết "lần trước khách nói gì".

crm.db nằm trong volume của container `crm` (/data/crm.db). Khi chạy trong
container `data_platform` (phase 05 auto-gen), volume đó đã mount read-only
tại /app/var/crm_data/crm.db — đọc thẳng, không cần docker cp. Khi chạy trên
HOST (không thấy path đó), mặc định `docker cp` ra file tạm rồi đọc (tránh
lock DB sống). Truyền `--crm-db <path>` để ép dùng 1 đường dẫn cụ thể.

API:
  fetch_recent_notes(customer_ids, crm_db=None, limit=5)
    -> dict[customer_id, list[{date, body, kind, channel?, outcome?}]]

Degrade mềm: docker fail / db thiếu / khách không có identity → dict rỗng /
thiếu key, caller tự fallback [] — KHÔNG raise, không chặn batch.
"""
from __future__ import annotations

import logging
import sqlite3
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_CONTAINER_DB = "crm:/data/crm.db"
# Read-only mount của crm_data trong data_platform (docker-compose.yml) — khi chạy
# trong container này, đọc thẳng file thay vì docker cp (không cần docker CLI/socket).
_MOUNTED_RO_DB = Path("/app/var/crm_data/crm.db")


def copy_crm_db_from_container(dest_dir: Path | None = None) -> Path | None:
    """Ưu tiên đọc thẳng crm_data:ro đã mount sẵn (trong data_platform); nếu
    không có (chạy trên HOST) thì docker cp ra file tạm. None nếu cả 2 đều fail."""
    if _MOUNTED_RO_DB.exists():
        return _MOUNTED_RO_DB
    out_dir = dest_dir or Path(tempfile.mkdtemp(prefix="crm_history_"))
    target = out_dir / "crm_history_snapshot.db"
    try:
        subprocess.run(
            ["docker", "cp", _CONTAINER_DB, str(target)],
            check=True, capture_output=True, timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        log.warning("crm_history: docker cp failed (%s) %s", exc, detail.decode(errors="replace").strip())
        return None
    return target


def _map_customer_to_party(con: sqlite3.Connection, customer_ids: list[int]) -> dict[str, int]:
    """party_id -> customer_id qua crm_party_identity (identity_type='sapo_customer')."""
    marks = ",".join("?" * len(customer_ids))
    rows = con.execute(
        f"SELECT party_id, identity_value FROM crm_party_identity "
        f"WHERE identity_type='sapo_customer' AND identity_value IN ({marks})",
        [str(c) for c in customer_ids],
    ).fetchall()
    return {party_id: int(identity_value) for party_id, identity_value in rows}


def fetch_recent_notes(
    customer_ids: list[int],
    crm_db: Path | str | None = None,
    limit: int = 5,
) -> dict[int, list[dict]]:
    """Top-`limit` note + activity gần nhất mỗi khách, sort mới→cũ, gộp chung.

    Shape khớp input contract template ({{recent_notes}}):
      {"date": "2026-07-02", "body": "...", "kind": "note"|"activity",
       "channel": ..., "outcome": ...}  (channel/outcome chỉ có ở activity)
    """
    if not customer_ids:
        return {}
    db_path = Path(crm_db) if crm_db else copy_crm_db_from_container()
    if db_path is None or not db_path.exists():
        log.warning("crm_history: không có crm.db — recent_notes sẽ rỗng")
        return {}

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        party_to_cid = _map_customer_to_party(con, customer_ids)
        if not party_to_cid:
            return {}
        marks = ",".join("?" * len(party_to_cid))
        party_ids = list(party_to_cid)

        result: dict[int, list[dict]] = {}

        for party_id, body, created_at in con.execute(
            f"SELECT party_id, body, created_at FROM crm_note "
            f"WHERE party_id IN ({marks}) AND deleted_at IS NULL AND body IS NOT NULL "
            f"ORDER BY created_at DESC", party_ids,
        ):
            cid = party_to_cid[party_id]
            result.setdefault(cid, []).append(
                {"date": (created_at or "")[:10], "body": body.strip(), "kind": "note"})

        for party_id, body, channel, outcome, contact_outcome, occurred_at in con.execute(
            f"SELECT party_id, body, channel, outcome, contact_outcome, occurred_at "
            f"FROM crm_activity_log WHERE party_id IN ({marks}) AND body IS NOT NULL "
            f"ORDER BY occurred_at DESC", party_ids,
        ):
            cid = party_to_cid[party_id]
            entry = {"date": (occurred_at or "")[:10], "body": body.strip(), "kind": "activity"}
            if channel:
                entry["channel"] = channel
            if contact_outcome or outcome:
                entry["outcome"] = contact_outcome or outcome
            result.setdefault(cid, []).append(entry)

        # Gộp note + activity, mới nhất trước, cắt `limit` mỗi khách
        for cid in result:
            result[cid] = sorted(result[cid], key=lambda e: e["date"], reverse=True)[:limit]
        return result
    finally:
        con.close()
