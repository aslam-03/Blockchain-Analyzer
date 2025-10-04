"""FastAPI entry point for the Blockchain Analyzer backend service."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api import api_router
from app.db.neo4j_client import close_driver
from app.ingest.etherscan_ingest import ingest_address_transactions
from app.utils.addresses import normalize_eth_address


LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
	title="Blockchain Analyzer Backend",
	version="1.0.0",
	description="Backend service for ingesting Ethereum transactions into Neo4j.",
)

app.include_router(api_router)


@app.get("/health")
def healthcheck() -> Dict[str, str]:
	"""Basic readiness probe."""
	return {"status": "ok"}


@app.on_event("shutdown")
def shutdown_event() -> None:
	"""Ensure the Neo4j driver is closed when the service stops."""
	close_driver()


@app.get("/ingest/{address}")
async def ingest_transactions(address: str) -> Dict[str, Any]:
	"""Trigger ingestion of transactions for the provided Ethereum address."""
	try:
		normalized_address = normalize_eth_address(address)
		result = await run_in_threadpool(ingest_address_transactions, normalized_address)
	except ValueError as exc:
		LOGGER.warning("Validation error for address %s: %s", address, exc)
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except RuntimeError as exc:
		LOGGER.error("Ingestion failure for %s: %s", address, exc)
		raise HTTPException(status_code=502, detail=str(exc)) from exc

	return {
		"status": "success",
		"message": f"Ingestion completed for {normalized_address}",
		"data": result,
	}