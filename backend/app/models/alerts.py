"""Schemas for anomaly alert responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AlertRecord(BaseModel):
    """Represents a single suspicious address alert."""

    address: str
    cluster_id: Optional[str] = None
    risk_score: float = Field(..., ge=0.0, le=1.0)
    is_anomaly: bool = False
    is_sanctioned: bool = False
    severity: str = Field(default="LOW")


class AlertResponse(BaseModel):
    """Response payload for alert listings."""

    alerts: list[AlertRecord]
    total: int = Field(default=0, ge=0)


__all__ = ["AlertRecord", "AlertResponse"]
