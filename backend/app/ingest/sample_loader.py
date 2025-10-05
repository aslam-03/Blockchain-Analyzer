"""Utility helpers for loading bundled sample transactions into Neo4j."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from neo4j.exceptions import Neo4jError

from app.db.neo4j_client import get_driver

LOGGER = logging.getLogger(__name__)

DEFAULT_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_txns.json"

_CYPHER_INGEST = """
UNWIND $transactions AS tx
MERGE (sender:Address {address: tx.from_address})
MERGE (receiver:Address {address: tx.to_address})
MERGE (txn:Transaction {hash: tx.hash})
SET txn.block_number = tx.block_number,
    txn.timestamp = tx.timestamp,
    txn.value_wei = tx.value_wei,
    txn.gas = tx.gas,
    txn.gas_price_wei = tx.gas_price_wei
MERGE (sender)-[rel:SENT {hash: tx.hash}]->(receiver)
SET rel.value_wei = tx.value_wei,
    rel.gas = tx.gas,
    rel.gas_price_wei = tx.gas_price_wei,
    rel.block_number = tx.block_number,
    rel.timestamp = tx.timestamp
MERGE (sender)<-[:FROM]-(txn)
MERGE (txn)-[:TO]->(receiver)
"""


def _to_epoch_seconds(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            cleaned = value.strip()
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            if "T" not in cleaned:
                cleaned = f"{cleaned}T00:00:00+00:00"
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Unable to parse timestamp '{value}'") from exc

    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")


def _normalize_address(address: str) -> str:
    if not isinstance(address, str):
        raise TypeError("Address must be a string")

    addr = address.strip().lower()
    if not addr.startswith("0x") or len(addr) != 42:
        raise ValueError(f"Invalid Ethereum address: {address}")

    return addr


def _load_transactions(sample_path: Path) -> List[Dict[str, Any]]:
    with sample_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    raw_transactions: Iterable[Dict[str, Any]] = payload.get("sample_transactions", [])
    transactions: List[Dict[str, Any]] = []

    for entry in raw_transactions:
        try:
            txn = {
                "hash": str(entry["hash"]).lower(),
                "from_address": _normalize_address(entry["from"]),
                "to_address": _normalize_address(entry["to"]),
                "value_wei": int(entry["value"]),
                "gas": int(entry["gas"]),
                "gas_price_wei": int(entry["gasPrice"]),
                "block_number": int(entry["blockNumber"]),
                "timestamp": _to_epoch_seconds(entry["timestamp"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            LOGGER.warning("Skipping malformed sample transaction %s: %s", entry, exc)
            continue

        transactions.append(txn)

    return transactions


def load_sample_transactions(sample_path: Optional[str] = None) -> Dict[str, Any]:
    """Persist bundled sample transactions into Neo4j and return ingestion metadata."""
    path = Path(sample_path or DEFAULT_SAMPLE_PATH)

    if not path.exists():
        raise FileNotFoundError(f"Sample transaction file not found at {path}")

    transactions = _load_transactions(path)
    if not transactions:
        raise ValueError("No valid transactions were found in the sample file")

    driver = get_driver()

    try:
        with driver.session() as session:
            session.run(_CYPHER_INGEST, transactions=transactions)
    except Neo4jError as exc:
        LOGGER.exception("Failed to persist sample transactions: %s", exc)
        raise RuntimeError("Failed to persist sample transactions in Neo4j") from exc

    total_value_eth = sum(Decimal(tx["value_wei"]) / Decimal(10**18) for tx in transactions)

    return {
        "transaction_count": len(transactions),
        "unique_addresses": len({tx["from_address"] for tx in transactions} | {tx["to_address"] for tx in transactions}),
        "total_value_eth": float(total_value_eth),
        "source": str(path),
    }


__all__ = ["load_sample_transactions"]
