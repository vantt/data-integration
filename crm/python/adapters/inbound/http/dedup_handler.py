"""FastAPI router — dedup HTTP handlers.

Auth: DEFERRED — LAN-trust only, no auth middleware.
Routes mirror dedup_handler.go (chi → FastAPI).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crm.python.domain.entities.party import DedupCandidate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Service protocols ─────────────────────────────────────────────────────────

class DedupQuerier(Protocol):
    def list_candidates(self, status: str) -> list[DedupCandidate]: ...
    def get_candidate(self, candidate_id: str) -> Optional[DedupCandidate]: ...
    def update_candidate_status(
        self, candidate_id: str, status: str, reviewed_by: Optional[str]
    ) -> None: ...


class DedupMerger(Protocol):
    def merge(
        self,
        surviving_party_id: str,
        merged_party_id: str,
        reason: str,
        merged_by: Optional[str],
    ) -> str: ...

    def undo_merge(self, merge_id: str, undone_by: Optional[str] = None) -> None: ...


# ── Pydantic request models ───────────────────────────────────────────────────

class MergeRequest(BaseModel):
    surviving_id: str
    merged_id: str
    reason: str = ""
    merged_by: Optional[str] = None


class UndoMergeRequest(BaseModel):
    undone_by: Optional[str] = None


# ── Handler factory ───────────────────────────────────────────────────────────

def make_dedup_router(querier: DedupQuerier, merger: DedupMerger) -> APIRouter:
    """Return a configured APIRouter with all dedup endpoints wired."""

    # GET /api/dedup/candidates?status=pending|merged|rejected
    @router.get("/dedup/candidates")
    def list_candidates(status: str = "pending") -> Any:
        candidates = querier.list_candidates(status)
        return {
            "status": "ok",
            "count": len(candidates),
            "candidates": candidates or [],
        }

    # POST /api/dedup/merge/{candidate_id}
    @router.post("/dedup/merge/{candidate_id}")
    def merge_candidate(candidate_id: str, body: MergeRequest) -> Any:
        if not body.surviving_id or not body.merged_id:
            raise HTTPException(
                status_code=400,
                detail="surviving_id and merged_id are required",
            )
        candidate = querier.get_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        try:
            merge_id = merger.merge(
                body.surviving_id,
                body.merged_id,
                body.reason,
                body.merged_by,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        querier.update_candidate_status(candidate_id, "merged", body.merged_by)
        return {"status": "ok", "merge_id": merge_id, "candidate_id": candidate_id}

    # POST /api/dedup/undo/{merge_id}
    @router.post("/dedup/undo/{merge_id}")
    def undo_merge(merge_id: str, body: UndoMergeRequest = UndoMergeRequest()) -> Any:
        try:
            merger.undo_merge(merge_id, body.undone_by)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"status": "ok", "merge_id": merge_id}

    return router
