"""Compliance related helpers such as blacklist ingestion and severity scoring."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from typing import Iterable, List

from neo4j.exceptions import Neo4jError

from app.db.neo4j_client import get_driver
from app.utils.addresses import normalize_eth_address

LOGGER = logging.getLogger(__name__)

BATCH_SIZE = 50


def _normalize_addresses(addresses: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for raw in addresses:
        if not raw:
            continue
        try:
            normalized.append(normalize_eth_address(raw))
        except ValueError:
            LOGGER.debug("Skipping invalid blacklist address: %s", raw)
    return normalized


def apply_blacklist_csv(content: bytes, encoding: str = "utf-8") -> int:
    """Parse a CSV payload and mark sanctioned addresses in Neo4j."""
    text = content.decode(encoding)
    reader = csv.DictReader(StringIO(text))

    addresses: List[str] = []
    if reader.fieldnames is None:
        raise ValueError("CSV must include a header row")

    column = None
    for candidate in ("address", "addr", "wallet"):
        if candidate in reader.fieldnames:
            column = candidate
            break

    if column is None:
        raise ValueError("CSV must contain an 'address' column")

    for row in reader:
        addresses.append(row.get(column, ""))

    return mark_sanctioned_addresses(addresses)


def mark_sanctioned_addresses(addresses: Iterable[str]) -> int:
    """Mark the supplied addresses as sanctioned."""
    normalized = _normalize_addresses(addresses)
    if not normalized:
        return 0

    driver = get_driver()
    updated = 0

    try:
        with driver.session() as session:
            for i in range(0, len(normalized), BATCH_SIZE):
                batch = normalized[i : i + BATCH_SIZE]
                result = session.run(
                    """
                    UNWIND $batch AS address
                    MATCH (a:Address {address: address})
                    SET a.is_sanctioned = true,
                        a.alert_severity = 'HIGH'
                    RETURN count(a) AS updated
                    """,
                    batch=batch,
                )
                record = result.single()
                if record and record.get("updated"):
                    updated += record["updated"]
    except Neo4jError as exc:
        LOGGER.exception("Failed to update sanctioned addresses: %s", exc)
        raise RuntimeError("Unable to update sanctioned addresses") from exc

    if updated:
        LOGGER.info("Flagged %d addresses as sanctioned", updated)
    return updated


def evaluate_alert_severity() -> int:
    """Recompute alert severity levels based on risk score and sanctions."""
    driver = get_driver()
    query = """
    MATCH (a:Address)
    WITH a,
         CASE
             WHEN coalesce(a.is_sanctioned, false) THEN 'HIGH'
             WHEN coalesce(a.risk_score, 0.0) >= 0.95 THEN 'HIGH'
             WHEN coalesce(a.risk_score, 0.0) >= 0.75 THEN 'MEDIUM'
             WHEN coalesce(a.risk_score, 0.0) >= 0.5 THEN 'ELEVATED'
             ELSE 'LOW'
         END AS severity
    SET a.alert_severity = severity
    RETURN count(a) AS updated
    """

    try:
        with driver.session() as session:
            record = session.run(query).single()
            updated = int(record["updated"]) if record and record.get("updated") is not None else 0
            LOGGER.info("Updated alert severity for %d addresses", updated)
            return updated
    except Neo4jError as exc:
        LOGGER.exception("Failed to evaluate alert severity: %s", exc)
        raise RuntimeError("Unable to update alert severity") from exc


__all__ = [
    "apply_blacklist_csv",
    "mark_sanctioned_addresses",
    "evaluate_alert_severity",
]
