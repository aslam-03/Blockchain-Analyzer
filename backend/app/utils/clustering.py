"""Utility functions for clustering addresses into connected components."""

from __future__ import annotations

import logging
from typing import Iterable, List
from uuid import uuid4

from neo4j import Session
from neo4j.exceptions import Neo4jError

from app.db.neo4j_client import get_driver
from app.utils.addresses import normalize_eth_address

LOGGER = logging.getLogger(__name__)

MAX_CLUSTER_DEPTH = 6
BATCH_SIZE = 50


def _fetch_unclustered_addresses(session: Session, limit: int) -> List[str]:
    query = """
    MATCH (a:Address)
    WHERE a.cluster_id IS NULL
    RETURN a.address AS address
    LIMIT $limit
    """
    records = session.run(query, limit=limit)
    return [record["address"] for record in records]


def _component_members(session: Session, seed: str) -> List[str]:
    query = f"""
    MATCH (start:Address {{address: $seed}})
    MATCH (start)-[:SENT*0..{MAX_CLUSTER_DEPTH}]-(member:Address)
    RETURN DISTINCT member.address AS address
    """
    records = session.run(query, seed=seed)
    return [record["address"] for record in records]


def _assign_cluster(session: Session, members: Iterable[str], cluster_id: str) -> None:
    members = list(members)
    if not members:
        return
    query = """
    MATCH (a:Address)
    WHERE a.address IN $members
    SET a.cluster_id = coalesce(a.cluster_id, $cluster_id)
    """
    session.run(query, members=members, cluster_id=cluster_id)


def assign_clusters(batch_size: int = BATCH_SIZE) -> int:
    """Assign connected component cluster identifiers for unclustered addresses."""
    driver = get_driver()
    assigned_total = 0

    try:
        with driver.session() as session:
            while True:
                pending = _fetch_unclustered_addresses(session, batch_size)
                if not pending:
                    break
                for address in pending:
                    cluster_members = _component_members(session, address)
                    if not cluster_members:
                        cluster_members = [address]
                    cluster_id = str(uuid4())
                    _assign_cluster(session, cluster_members, cluster_id)
                    assigned_total += len(cluster_members)
            if assigned_total:
                LOGGER.info("Assigned %d addresses to clusters", assigned_total)
    except Neo4jError as exc:
        LOGGER.exception("Failed assigning clusters: %s", exc)
        raise RuntimeError("Failed to compute clusters") from exc

    return assigned_total


def fetch_address_profile(address: str) -> dict:
    """Fetch metadata for an address including cluster attribution metrics."""
    normalized = normalize_eth_address(address)
    driver = get_driver()

    query = """
    MATCH (a:Address {address: $address})
    OPTIONAL MATCH (a)-[out:SENT]->(out_neighbor:Address)
    WITH a, count(out) AS out_count, collect(DISTINCT out_neighbor.address) AS out_neighbors
    OPTIONAL MATCH (in_neighbor:Address)-[inc:SENT]->(a)
    WITH a, out_count, out_neighbors, count(inc) AS in_count, collect(DISTINCT in_neighbor.address) AS in_neighbors
    RETURN {
        address: a.address,
        cluster_id: a.cluster_id,
        risk_score: a.risk_score,
        is_anomaly: coalesce(a.is_anomaly, false),
        is_sanctioned: coalesce(a.is_sanctioned, false),
        in_count: in_count,
        out_count: out_count,
        out_neighbors: out_neighbors,
        in_neighbors: in_neighbors
    } AS profile
    """

    try:
        with driver.session() as session:
            record = session.run(query, address=normalized).single()
    except Neo4jError as exc:
        LOGGER.exception("Unable to fetch address profile: %s", exc)
        raise RuntimeError("Failed to fetch address metadata") from exc

    if not record or not record.get("profile"):
        raise ValueError("Address not found")

    profile = record["profile"]
    counterparties = set(filter(None, profile.pop("out_neighbors", [])))
    counterparties.update(filter(None, profile.pop("in_neighbors", [])))
    profile["unique_counterparties"] = len(counterparties)

    return profile


__all__ = ["assign_clusters", "fetch_address_profile"]
