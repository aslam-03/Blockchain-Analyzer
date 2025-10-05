"""Utilities for retrieving Ethereum transactions from Etherscan and persisting them in Neo4j."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Any

import requests
from neo4j import Session
from neo4j.exceptions import Neo4jError

from app.db.neo4j_client import get_driver

LOGGER = logging.getLogger(__name__)

ETHERSCAN_BASE_URL = "https://api.etherscan.io/v2/api"


@dataclass
class TransactionRecord:
    """Strongly-typed representation of an Ethereum transaction from Etherscan."""

    hash: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: str
    value_wei: int
    gas: int
    gas_price_wei: int


def _fetch_transactions(address: str) -> List[TransactionRecord]:
    """Fetch all transactions for a given address via the Etherscan API."""
    api_key = os.getenv("ETHERSCAN_API_KEY")
    chain_id = os.getenv("ETHERSCAN_CHAIN_ID", "1")
    if not api_key:
        raise ValueError("ETHERSCAN_API_KEY environment variable is required for ingestion")

    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "chainid": chain_id,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 100,
        "sort": "desc",
        "apikey": api_key,
    }

    try:
        LOGGER.info("Requesting transactions for %s from Etherscan", address)
        response = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        LOGGER.exception("Network error calling Etherscan: %s", exc)
        raise RuntimeError("Failed to fetch transactions from Etherscan") from exc

    status = payload.get("status")
    message = payload.get("message", "")
    raw_result = payload.get("result")

    def _normalize_text(value: Any) -> str:
        return str(value).lower() if value is not None else ""

    normalized_result = _normalize_text(raw_result)

    if status != "1":
        if "no transactions found" in normalized_result:
            LOGGER.info("No transactions available for %s", address)
            return []
        if "max rate limit reached" in normalized_result:
            LOGGER.error("Etherscan rate limit reached while fetching %s", address)
            raise RuntimeError("Etherscan API rate limit reached. Please retry later.")
        if "invalid api key" in normalized_result:
            raise RuntimeError("Etherscan rejected the API key. Verify ETHERSCAN_API_KEY.")
        if "invalid address format" in normalized_result or "not a valid address" in normalized_result:
            raise ValueError(f"Invalid Ethereum address for Etherscan: {address}")

        error_detail = raw_result if raw_result else message or "Unknown error"
        LOGGER.error("Etherscan API returned error for %s: %s", address, error_detail)
        raise RuntimeError(f"Etherscan API error: {error_detail}")

    if isinstance(raw_result, list):
        results = raw_result
    elif "no transactions found" in normalized_result:
        LOGGER.info("No transactions available for %s", address)
        return []
    else:
        LOGGER.error("Unexpected Etherscan response format for %s: %s", address, raw_result)
        raise RuntimeError("Unexpected Etherscan response format")

    transactions: List[TransactionRecord] = []

    for item in results:
        try:
            to_address = item.get("to")
            if not to_address:
                LOGGER.debug(
                    "Skipping transaction %s because it has no recipient (likely contract creation)",
                    item.get("hash"),
                )
                continue

            transactions.append(
                TransactionRecord(
                    hash=item["hash"],
                    block_number=int(item["blockNumber"]),
                    timestamp=int(item["timeStamp"]),
                    from_address=item["from"].lower(),
                    to_address=to_address.lower(),
                    value_wei=int(item["value"]),
                    gas=int(item["gas"]),
                    gas_price_wei=int(item["gasPrice"]),
                )
            )
        except (KeyError, ValueError) as exc:
            LOGGER.warning("Skipping malformed transaction entry: %s", exc)
            continue

    LOGGER.info("Fetched %d transactions for %s from Etherscan", len(transactions), address)
    return transactions


def _persist_transactions(session: Session, transactions: List[TransactionRecord]) -> int:
    """Persist the provided transactions in Neo4j and return the number ingested."""
    if not transactions:
        return 0

    query = """
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

    session.run(query, transactions=[tx.__dict__ for tx in transactions])
    LOGGER.info("Persisted %d transactions to Neo4j", len(transactions))
    return len(transactions)


def ingest_address_transactions(address: str) -> Dict[str, Any]:
    """Fetch and persist transactions for the supplied address, returning ingestion metadata."""
    driver = get_driver()
    transactions = _fetch_transactions(address)

    ingested = 0
    try:
        with driver.session() as session:
            ingested = _persist_transactions(session, transactions)
    except Neo4jError as exc:
        LOGGER.exception("Failed to persist transactions for %s: %s", address, exc)
        raise RuntimeError("Failed to persist transactions in Neo4j") from exc

    total_value_eth = sum(Decimal(tx.value_wei) / Decimal(10**18) for tx in transactions)

    LOGGER.info("Ingested %s transactions for %s", ingested, address)

    return {
        "address": address,
        "fetched_count": len(transactions),
        "ingested_count": ingested,
        "total_value_eth": float(total_value_eth),
    }


__all__ = ["ingest_address_transactions"]
