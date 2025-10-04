"""Pydantic schemas for address metadata APIs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AddressProfile(BaseModel):
    """Summary metrics for an address node."""

    address: str
    cluster_id: Optional[str] = None
    risk_score: Optional[float] = None
    is_anomaly: bool = Field(default=False)
    is_sanctioned: bool = Field(default=False)
    in_count: int = 0
    out_count: int = 0
    unique_counterparties: int = 0


class ClusterRunResponse(BaseModel):
    """Response payload after running clustering assignment."""

    assigned_addresses: int


__all__ = ["AddressProfile", "ClusterRunResponse"]