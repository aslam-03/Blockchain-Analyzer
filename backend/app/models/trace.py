"""Pydantic models used by the transaction tracing API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class TraceRequest(BaseModel):
    """Client request payload for tracing funds between addresses."""

    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(..., alias="from", description="Source Ethereum address")
    target: Optional[str] = Field(
        None, alias="to", description="Optional destination Ethereum address"
    )
    max_hops: int = Field(
        4,
        ge=1,
        le=8,
        description="Maximum hop depth to explore along SENT relationships",
    )


class TraceNode(BaseModel):
    """Graph node returned by trace requests."""

    address: str
    cluster_id: Optional[str] = None
    risk_score: Optional[float] = None
    is_anomaly: Optional[bool] = None
    is_sanctioned: Optional[bool] = None


class TraceEdge(BaseModel):
    """Directed relationship returned in trace responses."""

    tx_hash: str
    source: str = Field(..., description="Sender address")
    target: str = Field(..., description="Receiver address")
    value_wei: Optional[int] = None
    timestamp: Optional[int] = None
    block_number: Optional[int] = None


class TraceResponse(BaseModel):
    """Response payload containing traced subgraph."""

    nodes: List[TraceNode]
    edges: List[TraceEdge]
    metadata: dict = Field(default_factory=dict)
