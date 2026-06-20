"""
Unit tests for hug_webhook_consumer.

Verifies that:
- scan events (token-keyed, no 'id') land in table 'scan' with correct columns
- optin events (token-keyed, no 'id') land in table 'optin_event' with correct columns
- neither event type is dropped despite absence of an 'id' field
- ack is called exactly once with both msg_ids after a successful batch
- Sapo-style messages (which do carry 'id') are unaffected (separate consumer path)
- malformed messages (missing token, bad JSON) are skipped without aborting the batch
"""

import json
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

# Make ingestion/src importable without installing as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hug.hug_webhook_consumer import hug_event_dispatcher, hug_webhook_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wrapper(entity_type: str, inner: dict, action: str = "created") -> str:
    """Build the outer JSON envelope that D1 stores in the 'payload' column."""
    return json.dumps({
        "source_system": "hug",
        "entity_type": entity_type,
        "action": action,
        "received_at": "2026-06-19T10:00:00Z",
        "payload": inner,
    })


SCAN_INNER = {
    "token": "ABC123XYZ789",
    "customer_id": "cust_42",
    "op_type": "package_insert",
    "channel": "offline",
    "campaign_id": "default",
    "tier": "REPEAT_BUYER",
    "scanned_at": "2026-06-19T10:00:00Z",
}

OPTIN_INNER = {
    "token": "ABC123XYZ789",
    "buyer_customer_id": "cust_42",
    "phone": "0901234567",
    "zalo_uid": None,
    "name": "Nguyen Van A",
    "consent": {"marketing": True},
    "ts": "2026-06-19T10:01:00Z",
}

SCAN_MSG = {
    "msg_id": "msg_scan_001",
    "entity_type": "scan",
    "source_system": "hug",
    "payload": _make_wrapper("scan", SCAN_INNER),
}

OPTIN_MSG = {
    "msg_id": "msg_optin_001",
    "entity_type": "optin",
    "source_system": "hug",
    "payload": _make_wrapper("optin", OPTIN_INNER),
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHugEventDispatcher:

    def _collect(self, messages: list, worker_url: str = "http://mock-worker") -> tuple[list, list]:
        """
        Run hug_event_dispatcher with mocked HTTP and collect (records, table_names).

        Returns (records, table_names) where records[i] landed in table_names[i].
        """
        records = []
        table_names = []

        with patch("hug.hug_webhook_consumer.CloudflareWorkerClient") as MockClient:
            client_instance = MockClient.return_value
            client_instance.poll_messages.return_value = messages
            client_instance.batch_ack = MagicMock()

            # dlt.mark.with_table_name wraps a record; we capture it directly
            # by intercepting the mark call so we can inspect both the record
            # and the intended table name without needing a real dlt pipeline.
            with patch("hug.hug_webhook_consumer.dlt") as mock_dlt:
                def fake_mark_with_table_name(record, table):
                    records.append(record)
                    table_names.append(table)
                    return (record, table)  # sentinel that the resource will yield

                mock_dlt.mark.with_table_name.side_effect = fake_mark_with_table_name

                # Exhaust the generator manually
                gen = hug_event_dispatcher.__wrapped__(worker_url, poll_limit=100)
                list(gen)  # consume all yields

            return records, table_names, client_instance

    def test_scan_event_lands_in_scan_table(self):
        records, table_names, _ = self._collect([SCAN_MSG])

        assert len(records) == 1
        assert table_names[0] == "scan"

        rec = records[0]
        assert rec["entity_id"] == "ABC123XYZ789"
        assert rec["entity_type"] == "scan"
        assert rec["ingest_method"] == "webhook"
        assert rec["payload"] == SCAN_INNER

    def test_optin_event_lands_in_optin_event_table(self):
        records, table_names, _ = self._collect([OPTIN_MSG])

        assert len(records) == 1
        assert table_names[0] == "optin_event"

        rec = records[0]
        assert rec["entity_id"] == "ABC123XYZ789"
        assert rec["entity_type"] == "optin_event"
        assert rec["payload"]["phone"] == "0901234567"

    def test_both_event_types_in_one_batch_neither_dropped(self):
        """Core regression: token-keyed events without 'id' must not be silently dropped."""
        records, table_names, client = self._collect([SCAN_MSG, OPTIN_MSG])

        assert len(records) == 2, (
            "Both scan and optin events must be yielded — "
            "they have no 'id' field but must not be dropped"
        )
        assert set(table_names) == {"scan", "optin_event"}

    def test_ack_called_with_both_msg_ids_after_successful_batch(self):
        _, _, client = self._collect([SCAN_MSG, OPTIN_MSG])

        client.batch_ack.assert_called_once()
        acked_ids = client.batch_ack.call_args[0][0]
        assert set(acked_ids) == {"msg_scan_001", "msg_optin_001"}

    def test_missing_token_skips_message_without_aborting_batch(self):
        """A message whose inner payload has no 'token' must be skipped; valid messages still process."""
        no_token_msg = {
            "msg_id": "msg_bad_001",
            "entity_type": "scan",
            "source_system": "hug",
            "payload": _make_wrapper("scan", {"op_type": "package_insert"}),  # no token
        }
        records, table_names, client = self._collect([no_token_msg, OPTIN_MSG])

        # Only the valid optin message should land
        assert len(records) == 1
        assert table_names[0] == "optin_event"

        # Only the valid msg_id should be acked
        acked_ids = client.batch_ack.call_args[0][0]
        assert acked_ids == ["msg_optin_001"]

    def test_bad_json_payload_skips_without_aborting_batch(self):
        bad_json_msg = {
            "msg_id": "msg_bad_json",
            "entity_type": "scan",
            "source_system": "hug",
            "payload": "NOT VALID JSON {{{{",
        }
        records, _, client = self._collect([bad_json_msg, SCAN_MSG])

        assert len(records) == 1
        assert records[0]["entity_id"] == "ABC123XYZ789"

    def test_unknown_entity_type_skipped(self):
        unknown_msg = {
            "msg_id": "msg_unk",
            "entity_type": "voucher",
            "source_system": "hug",
            "payload": _make_wrapper("voucher", {"token": "TKN999"}),
        }
        records, _, _ = self._collect([unknown_msg])
        assert records == []

    def test_empty_poll_returns_no_records_and_no_ack(self):
        records, _, client = self._collect([])
        assert records == []
        client.batch_ack.assert_not_called()

    def test_envelope_has_required_columns(self):
        records, _, _ = self._collect([SCAN_MSG])
        rec = records[0]
        required = {
            "entity_id", "entity_type", "ingest_method", "event_type",
            "event_timestamp", "payload_hash", "year", "month",
            "payload", "sync_metadata",
        }
        assert required.issubset(rec.keys()), f"Missing columns: {required - rec.keys()}"

    def test_sync_metadata_source_system_is_hug(self):
        records, _, _ = self._collect([SCAN_MSG])
        assert records[0]["sync_metadata"]["source_system"] == "hug"

    def test_sapo_consumer_unaffected(self):
        """
        Sapo webhook_consumer is NOT imported or modified by this module.
        Confirm the import resolves independently (no monkey-patching occurred).
        """
        from sapo.webhook_consumer import sapo_webhook_source, CloudflareWorkerClient
        assert callable(sapo_webhook_source)
        assert callable(CloudflareWorkerClient)
