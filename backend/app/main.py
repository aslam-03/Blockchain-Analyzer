"""FastAPI entry point for the Blockchain Analyzer backend service."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.db.neo4j_client import close_driver
from app.ingest.etherscan_ingest import ingest_address_transactions
from app.ingest.sample_loader import load_sample_transactions
from app.utils.addresses import normalize_eth_address


LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
	title="Blockchain Analyzer Backend",
	version="1.0.0",
	description="Backend service for ingesting Ethereum transactions into Neo4j.",
)

default_cors: List[str] = [
	"http://localhost:5173",
	"http://127.0.0.1:5173",
]

env_origins = os.getenv("CORS_ALLOW_ORIGINS")
if env_origins:
	allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
	if not allowed_origins:
		allowed_origins = default_cors
else:
	allowed_origins = default_cors

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
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
		LOGGER.info("Received ingestion request for %s", normalized_address)
		result = await run_in_threadpool(ingest_address_transactions, normalized_address)
	except ValueError as exc:
		LOGGER.warning("Validation error for address %s: %s", address, exc)
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except RuntimeError as exc:
		LOGGER.error("Ingestion failure for %s: %s", address, exc)
		raise HTTPException(status_code=502, detail=str(exc)) from exc

	LOGGER.info(
		"Completed ingestion for %s with %d new transactions",
		normalized_address,
		result.get("ingested_count", 0),
	)
	return {
		"status": "success",
		"message": f"Ingestion completed for {normalized_address}",
		"data": result,
	}


@app.post("/ingest/sample")
async def ingest_sample_data(path: str | None = None) -> Dict[str, Any]:
	"""Load the bundled sample dataset into Neo4j for local experimentation."""
	try:
		result = await run_in_threadpool(load_sample_transactions, path)
	except FileNotFoundError as exc:
		LOGGER.warning("Sample data not found: %s", exc)
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	except ValueError as exc:
		LOGGER.warning("Sample data invalid: %s", exc)
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except RuntimeError as exc:
		LOGGER.error("Failed to ingest sample data: %s", exc)
		raise HTTPException(status_code=502, detail=str(exc)) from exc

	return {
		"status": "success",
		"message": "Sample dataset ingested into Neo4j",
		"data": result,
	}