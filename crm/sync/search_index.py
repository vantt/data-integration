"""search_index.py — Rebuild crm_party_search FTS5 table from crm.db + cache.db."""

from __future__ import annotations

import logging
import re
import sqlite3

log = logging.getLogger(__name__)

# Identity types that contribute tokens to the search blob.
# Phones are normalized; others are added verbatim.
_PHONE_TYPES = {"phone", "phone_secondary"}
_VERBATIM_TYPES = {"email", "sapo_customer", "customer_code", "zalo_uid", "facebook", "psid"}
_INDEXED_TYPES = _PHONE_TYPES | _VERBATIM_TYPES


def _to_local_phone(v: str) -> str:
    """Convert any stored format to local 09... for FTS token."""
    digits = re.sub(r"\D", "", v)
    if digits.startswith("84") and len(digits) == 11:
        return "0" + digits[2:]
    return digits  # already local or unrecognized


# ─── Data loading helpers ────────────────────────────────────────────────────

def _load_parties(crm_conn: sqlite3.Connection) -> dict[str, list[str]]:
    """
    Load party_id → token list from crm.db.

    Returns {party_id: [token, ...]} with display_name and identity values.
    Skips identities with contact_status='invalid'.
    """
    # Build party base: {party_id: [display_name_token]}
    parties: dict[str, list[str]] = {}
    for row in crm_conn.execute("SELECT party_id, display_name FROM crm_party"):
        pid = row["party_id"]
        tokens: list[str] = []
        if row["display_name"]:
            tokens.append(row["display_name"])
        parties[pid] = tokens

    # Append identity tokens (skip invalid contact_status)
    sql = (
        "SELECT party_id, identity_type, identity_value"
        " FROM crm_party_identity"
        " WHERE contact_status != 'invalid'"
        "   AND identity_type IN ({})".format(
            ",".join("?" for _ in _INDEXED_TYPES)
        )
    )
    for row in crm_conn.execute(sql, list(_INDEXED_TYPES)):
        pid = row["party_id"]
        if pid not in parties:
            continue  # orphan identity — skip
        itype = row["identity_type"]
        val = row["identity_value"]
        if not val:
            continue
        if itype in _PHONE_TYPES:
            val = _to_local_phone(val)
        if val:
            parties[pid].append(val)

    return parties


def _build_customer_id_to_party(crm_conn: sqlite3.Connection) -> dict[str, str]:
    """
    Build {customer_id_str: party_id} from sapo_customer identities in crm.db.

    Used to join order tokens from cache.db to the correct party.
    """
    mapping: dict[str, str] = {}
    rows = crm_conn.execute(
        "SELECT party_id, identity_value"
        " FROM crm_party_identity"
        " WHERE identity_type = 'sapo_customer'"
        "   AND contact_status != 'invalid'"
    )
    for row in rows:
        mapping[str(row["identity_value"])] = row["party_id"]
    return mapping


def _load_warehouse_names(
    cache_conn: sqlite3.Connection,
    customer_id_to_party: dict[str, str],
) -> dict[str, list[str]]:
    """
    Load display_name (= Sapo full_name) from wh_customer_base in cache.db.

    Supplements crm_party.display_name — ensures the Sapo full name is
    searchable even when the CRM name was manually edited or is null.
    """
    exists = cache_conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='wh_customer_base'"
    ).fetchone()
    if not exists:
        log.debug("wh_customer_base not found in cache.db — skipping warehouse names")
        return {}

    name_tokens: dict[str, list[str]] = {}
    for row in cache_conn.execute(
        "SELECT customer_id, display_name FROM wh_customer_base"
        " WHERE customer_id IS NOT NULL AND display_name IS NOT NULL AND display_name != ''"
    ):
        cid_str = str(row["customer_id"])
        party_id = customer_id_to_party.get(cid_str)
        if not party_id:
            continue
        name_tokens.setdefault(party_id, []).append(row["display_name"])
    return name_tokens


def _load_order_tokens(
    cache_conn: sqlite3.Connection,
    customer_id_to_party: dict[str, str],
) -> dict[str, list[str]]:
    """
    Build {party_id: [order_code, order_id, ...]} from wh_order_hdr in cache.db.

    Skips rows where customer_id IS NULL (guest orders).
    Returns empty dict if wh_order_hdr table does not exist.
    """
    # Guard: table may not exist in all environments (e.g. fresh test DB)
    exists = cache_conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='wh_order_hdr'"
    ).fetchone()
    if not exists:
        log.debug("wh_order_hdr not found in cache.db — skipping order tokens")
        return {}

    order_tokens: dict[str, list[str]] = {}
    rows = cache_conn.execute(
        "SELECT order_id, order_code, customer_id FROM wh_order_hdr"
        " WHERE customer_id IS NOT NULL"
    )
    for row in rows:
        cid_str = str(row["customer_id"])
        party_id = customer_id_to_party.get(cid_str)
        if not party_id:
            continue  # no CRM party for this customer
        bucket = order_tokens.setdefault(party_id, [])
        if row["order_code"]:
            bucket.append(str(row["order_code"]))
        if row["order_id"]:
            bucket.append(str(row["order_id"]))

    return order_tokens


# ─── Main rebuild ─────────────────────────────────────────────────────────────

def rebuild_search_index(crm_db_path: str, cache_db_path: str) -> int:
    """Full rebuild of crm_party_search. Returns count of indexed parties."""
    log.info("rebuild_search_index: starting full rebuild")

    # ── 1. Load party data from crm.db ───────────────────────────────────────
    crm_conn = sqlite3.connect(crm_db_path)
    crm_conn.row_factory = sqlite3.Row
    try:
        parties = _load_parties(crm_conn)
        customer_id_to_party = _build_customer_id_to_party(crm_conn)
    finally:
        # Keep crm_conn open for the final write — close after insert
        pass

    # ── 2. Load supplementary tokens from cache.db (read-only) ──────────────
    cache_conn = sqlite3.connect(f"file:{cache_db_path}?mode=ro", uri=True)
    cache_conn.row_factory = sqlite3.Row
    try:
        order_tokens = _load_order_tokens(cache_conn, customer_id_to_party)
        warehouse_names = _load_warehouse_names(cache_conn, customer_id_to_party)
    finally:
        cache_conn.close()

    # ── 3. Merge supplementary tokens into party token lists ─────────────────
    for party_id, tokens in order_tokens.items():
        if party_id in parties:
            parties[party_id].extend(tokens)
    for party_id, names in warehouse_names.items():
        if party_id in parties:
            parties[party_id].extend(names)

    # ── 4. DELETE all + INSERT batch into crm_party_search ───────────────────
    rows = [
        (pid, " ".join(tokens))
        for pid, tokens in parties.items()
        if tokens  # skip parties with nothing to index
    ]

    try:
        crm_conn.execute("DELETE FROM crm_party_search")
        crm_conn.executemany(
            "INSERT INTO crm_party_search (party_id, tokens) VALUES (?, ?)",
            rows,
        )
        crm_conn.commit()
    finally:
        crm_conn.close()

    count = len(rows)
    log.info("rebuild_search_index: indexed %d parties", count)
    return count
