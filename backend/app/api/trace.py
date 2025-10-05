"""API endpoints responsible for graph tracing between blockchain addresses."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple

from fastapi import APIRouter, HTTPException
from neo4j import Session
from neo4j.exceptions import Neo4jError

from app.db.neo4j_client import get_driver
from app.models import TraceEdge, TraceNode, TraceRequest, TraceResponse
from app.utils.addresses import normalize_eth_address

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/trace", tags=["trace"])


def _normalize_request(payload: TraceRequest) -> Tuple[str, str | None, int]:
    """Normalize address inputs and guard hop limits."""
    source = normalize_eth_address(payload.source)
    target = normalize_eth_address(payload.target) if payload.target else None
    max_hops = max(1, min(8, payload.max_hops))
    return source, target, max_hops


def _paths_to_graph(records: Iterable) -> Tuple[Dict[str, TraceNode], List[TraceEdge]]:
    """Convert Neo4j path records into node/edge collections."""
    nodes: Dict[str, TraceNode] = {}
    edges: List[TraceEdge] = []

    for record in records:
        path = record.get("path") or record.get("p")
        if path is None:
            continue

        for node in path.nodes:
            if "Address" not in node.labels:
                continue
            address = node.get("address")
            if not address:
                continue
            if address not in nodes:
                nodes[address] = TraceNode(
                    address=address,
                    cluster_id=node.get("cluster_id"),
                    risk_score=node.get("risk_score"),
                    is_anomaly=node.get("is_anomaly"),
                    is_sanctioned=node.get("is_sanctioned"),
                )

        for rel in path.relationships:
            if rel.type != "SENT":
                continue
            source = rel.start_node.get("address")
            target = rel.end_node.get("address")
            if not source or not target:
                continue
            edges.append(
                TraceEdge(
                    tx_hash=rel.get("hash", ""),
                    source=source,
                    target=target,
                    value_wei=rel.get("value_wei"),
                    timestamp=rel.get("timestamp"),
                    block_number=rel.get("block_number"),
                )
            )

    return nodes, edges


def _execute_trace(session: Session, source: str, target: str | None, max_hops: int):
    """Run the tracing Cypher query and return raw records."""
    if target:
        query = f"""
        MATCH (source:Address {{address: $source}})
        MATCH (target:Address {{address: $target}})
        MATCH p = shortestPath((source)-[:SENT*1..{max_hops}]->(target))
        RETURN p AS path
        """
        params = {"source": source, "target": target}
        return session.run(query, params)

    query = f"""
    MATCH (source:Address {{address: $source}})
    MATCH p = (source)-[:SENT*1..{max_hops}]->(neighbor:Address)
    RETURN p AS path
    LIMIT 50
    """
    params = {"source": source}
    return session.run(query, params)


@router.post("/", response_model=TraceResponse)
def trace_route(payload: TraceRequest) -> TraceResponse:
    """Trace funds from a source address to an optional target using graph search."""
    source, target, max_hops = _normalize_request(payload)
    driver = get_driver()

    try:
        with driver.session() as session:
            result = _execute_trace(session, source, target, max_hops)
            records = list(result)
    except Neo4jError as exc:
        LOGGER.exception("Neo4j error during trace: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to query graph database") from exc

    nodes, edges = _paths_to_graph(records)

    if not nodes:
        raise HTTPException(status_code=404, detail="No path found for supplied parameters")

    metadata = {
        "source": source,
        "target": target,
        "max_hops": max_hops,
        "path_count": len(records),
        "edge_count": len(edges),
        "node_count": len(nodes),
    }

    LOGGER.info(
        "Trace completed for %s -> %s (max_hops=%d, paths=%d, edges=%d, nodes=%d)",
        source,
        target or "*",
        max_hops,
        metadata["path_count"],
        metadata["edge_count"],
        metadata["node_count"],
    )

    return TraceResponse(nodes=list(nodes.values()), edges=edges, metadata=metadata)


__all__ = ["router"]
