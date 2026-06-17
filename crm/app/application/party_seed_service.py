"""party_seed_service.py — PartySeedService: consume wh_party_seed → crm_party.

Mirrors Go PartySeedService in crm/app/internal/application/party_seed_service.go.
Reads wh_party_seed from cache.db (via CacheRepository) and upserts crm_party +
sapo_customer identity rows via PartyService.

Idempotent: UNIQUE(identity_type, identity_value) prevents duplicates across runs.
Graceful: per-seed errors are logged and counted; the loop continues.
"""
from __future__ import annotations

import logging

from domain.entities.party import PartySeed
from domain.ports.cache_repository import CacheRepository
from domain.ports.party_repository import PartyRepository
from application.party_service import PartyService

log = logging.getLogger(__name__)


class PartySeedService:
    """Reads wh_party_seed (cache.db) and upserts crm_party rows (crm.db)."""

    def __init__(self, cache_repo: CacheRepository, party_repo: PartyRepository) -> None:
        self._party_svc = PartyService(party_repo)

    def sync_parties(self, cache_repo: CacheRepository) -> int:
        """Read all wh_party_seed rows and upsert crm_party + identity for each.

        Per-seed errors are logged and skipped; the loop never aborts on a single
        bad seed. If ALL seeds fail, raises RuntimeError so the caller can exit
        non-zero (mirrors Go behaviour: partial success returns count with no error).

        Returns the number of parties successfully created or updated.
        """
        seeds = cache_repo.list_party_seed()
        if not seeds:
            log.info("party seed service: no seeds to process")
            return 0

        count, failures = 0, 0
        for seed in seeds:
            try:
                self._process_seed(seed)
                count += 1
            except Exception as exc:
                log.error("party seed service: seed customer_id=%d: %s", seed.customer_id, exc)
                failures += 1

        log.info(
            "party seed service: processed %d / %d seeds (%d failures)",
            count, len(seeds), failures,
        )

        if failures > 0 and count == 0:
            raise RuntimeError(f"party seed: all {failures} seeds failed (first error logged)")

        return count

    # ── Private helpers ───────────────────────────────────────────────────────

    def _process_seed(self, seed: PartySeed) -> None:
        """Upsert one crm_party + sapo_customer identity from a seed row."""
        sapo_id = str(seed.customer_id)
        self._party_svc.upsert_from_sapo_identity(
            sapo_id=sapo_id,
            phone=seed.phone,
            email=seed.email,
            display_name=seed.display_name,
            src_quality=seed.source_contact_quality,
            quality=seed.contact_quality,
        )
