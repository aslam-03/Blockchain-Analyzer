"""Endpoints exposing address metadata and clustering utilities."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from neo4j.exceptions import Neo4jError

from app.models import AddressProfile, ClusterRunResponse
from app.utils.addresses import normalize_eth_address
from app.utils.clustering import BATCH_SIZE, assign_clusters, fetch_address_profile

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/address", tags=["address"])


@router.get("/{address}", response_model=AddressProfile)
def get_address(address: str) -> AddressProfile:
    """Return metadata for a specific address including cluster assignment."""
    try:
        profile = fetch_address_profile(address)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        LOGGER.exception("Error retrieving address %s: %s", address, exc)
        raise HTTPException(status_code=502, detail="Failed to retrieve address metadata") from exc

    return AddressProfile(**profile)


@router.post("/cluster", response_model=ClusterRunResponse)
def run_clustering(batch_size: Optional[int] = Body(default=BATCH_SIZE, embed=True)) -> ClusterRunResponse:
    """Assign cluster identifiers to unclustered addresses."""
    try:
        real_batch = int(batch_size) if batch_size else BATCH_SIZE
        real_batch = max(1, min(500, real_batch))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="batch_size must be an integer") from exc

    try:
        assigned = assign_clusters(batch_size=real_batch)
    except RuntimeError as exc:
        LOGGER.exception("Failed to run clustering: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ClusterRunResponse(assigned_addresses=assigned)


__all__ = ["router"]
