"""Compliance-centric endpoints for blacklist ingestion and severity updates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.utils.compliance import apply_blacklist_csv, evaluate_alert_severity

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post("/blacklist")
async def upload_blacklist(file: UploadFile = File(...)) -> dict:
    """Upload a CSV blacklist and mark matching addresses as sanctioned."""
    try:
        content = await file.read()
        updated = apply_blacklist_csv(content)
        evaluate_alert_severity()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        LOGGER.exception("Failed to process blacklist upload: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"updated": updated}


@router.post("/severity")
def recompute_severity() -> dict:
    """Re-evaluate alert severities based on risk scores and sanctions."""
    try:
        updated = evaluate_alert_severity()
    except RuntimeError as exc:
        LOGGER.exception("Failed to recompute severity: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"updated": updated}


__all__ = ["router"]
