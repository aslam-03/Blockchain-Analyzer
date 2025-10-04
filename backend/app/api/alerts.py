"""Endpoints for running and retrieving anomaly-based alerts."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models import AlertResponse
from app.ml.anomaly import fetch_alerts, run_anomaly_detection

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/refresh")
def refresh_alerts(contamination: float = Query(default=0.05, ge=0.01, le=0.3)) -> AlertResponse:
    """Trigger anomaly detection and return the refreshed alerts."""
    try:
        run_anomaly_detection(contamination=contamination)
        alerts = fetch_alerts()
    except RuntimeError as exc:
        LOGGER.exception("Failed to refresh alerts: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AlertResponse(alerts=alerts)


@router.get("/", response_model=AlertResponse)
def list_alerts(limit: int = Query(default=25, ge=1, le=200)) -> AlertResponse:
    """Return the current list of anomaly alerts ordered by risk score."""
    try:
        alerts = fetch_alerts(limit=limit)
    except RuntimeError as exc:
        LOGGER.exception("Failed to fetch alerts: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AlertResponse(alerts=alerts)


__all__ = ["router"]
