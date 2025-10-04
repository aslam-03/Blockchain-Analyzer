"""Isolation Forest based anomaly detection for blockchain addresses."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd
from neo4j.exceptions import Neo4jError
from sklearn.ensemble import IsolationForest

from app.db.neo4j_client import get_driver

LOGGER = logging.getLogger(__name__)

FEATURE_QUERY = """
MATCH (a:Address)
OPTIONAL MATCH (a)-[out:SENT]->(out_neighbor:Address)
WITH a,
     count(out) AS out_count,
     avg(out.value_wei) AS avg_out_value,
     min(out.timestamp) AS out_min_ts,
     max(out.timestamp) AS out_max_ts,
     collect(DISTINCT out_neighbor.address) AS out_neighbors
OPTIONAL MATCH (in_neighbor:Address)-[inc:SENT]->(a)
WITH a,
     out_count,
     avg_out_value,
     out_min_ts,
     out_max_ts,
     out_neighbors,
     count(inc) AS in_count,
     avg(inc.value_wei) AS avg_in_value,
     min(inc.timestamp) AS in_min_ts,
     max(inc.timestamp) AS in_max_ts,
     collect(DISTINCT in_neighbor.address) AS in_neighbors
RETURN {
    address: a.address,
    cluster_id: a.cluster_id,
    is_sanctioned: coalesce(a.is_sanctioned, false),
    in_count: in_count,
    out_count: out_count,
    avg_in_value: avg_in_value,
    avg_out_value: avg_out_value,
    in_min_ts: in_min_ts,
    in_max_ts: in_max_ts,
    out_min_ts: out_min_ts,
    out_max_ts: out_max_ts,
    in_neighbors: in_neighbors,
    out_neighbors: out_neighbors
} AS row
"""

BATCH_SIZE = 50


def _fetch_feature_rows() -> List[Dict]:
    driver = get_driver()
    try:
        with driver.session() as session:
            records = session.run(FEATURE_QUERY)
            rows = [record["row"] for record in records if record.get("row")]
    except Neo4jError as exc:
        LOGGER.exception("Failed to fetch features: %s", exc)
        raise RuntimeError("Unable to fetch features from Neo4j") from exc

    return rows


def _prepare_dataframe(rows: List[Dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.fillna(0, inplace=True)

    neighbors = df.get("out_neighbors", pd.Series([[]] * len(df)))
    neighbors_in = df.get("in_neighbors", pd.Series([[]] * len(df)))
    unique_counts = []
    for outs, ins in zip(neighbors, neighbors_in):
        outs = outs if isinstance(outs, list) else []
        ins = ins if isinstance(ins, list) else []
        unique_counts.append(len({addr for addr in outs + ins if addr}))
    df["unique_counterparties"] = unique_counts

    avg_value = (df.get("avg_in_value", 0) + df.get("avg_out_value", 0)) / 2
    df["avg_value"] = avg_value.fillna(0)

    def _tx_rate(row) -> float:
        timestamps = [
            row.get("in_min_ts", 0),
            row.get("in_max_ts", 0),
            row.get("out_min_ts", 0),
            row.get("out_max_ts", 0),
        ]
        timestamps = [int(ts) for ts in timestamps if ts]
        if not timestamps:
            return 0.0
        span = max(timestamps) - min(timestamps)
        span_days = max(span / 86400, 1)
        total_tx = row.get("in_count", 0) + row.get("out_count", 0)
        return float(total_tx) / span_days

    df["tx_rate"] = df.apply(_tx_rate, axis=1)
    df["in_count"] = df["in_count"].astype(float)
    df["out_count"] = df["out_count"].astype(float)
    df["tx_rate"] = df["tx_rate"].astype(float)
    df["unique_counterparties"] = df["unique_counterparties"].astype(float)
    df["avg_value"] = df["avg_value"].astype(float)

    return df


def _write_scores(results: List[Dict]) -> None:
    if not results:
        return

    driver = get_driver()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with driver.session() as session:
            for i in range(0, len(results), BATCH_SIZE):
                batch = results[i : i + BATCH_SIZE]
                session.run(
                    """
                    UNWIND $batch AS row
                    MATCH (a:Address {address: row.address})
                    SET a.risk_score = row.risk_score,
                        a.is_anomaly = row.is_anomaly,
                        a.tx_rate = row.tx_rate,
                        a.unique_counterparties = row.unique_counterparties,
                        a.analyzed_at = $timestamp
                    """,
                    batch=batch,
                    timestamp=timestamp,
                )
    except Neo4jError as exc:
        LOGGER.exception("Failed to persist anomaly scores: %s", exc)
        raise RuntimeError("Unable to write anomaly scores to Neo4j") from exc

    LOGGER.info("Persisted anomaly scores for %d addresses", len(results))


def run_anomaly_detection(contamination: float = 0.05) -> List[Dict]:
    """Compute anomaly scores for all addresses and persist results."""
    rows = _fetch_feature_rows()
    df = _prepare_dataframe(rows)

    if df.empty:
        LOGGER.info("No address data available for anomaly detection")
        return []

    feature_columns = [
        "in_count",
        "out_count",
        "avg_value",
        "unique_counterparties",
        "tx_rate",
    ]

    features = df[feature_columns].to_numpy()

    if len(df) < 10:
        contamination = min(contamination, 0.2)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    model.fit(features)

    raw_scores = model.decision_function(features)
    score_max = float(np.max(raw_scores))
    score_min = float(np.min(raw_scores))
    score_range = max(score_max - score_min, 1e-9)
    risk_scores = (score_max - raw_scores) / score_range
    risk_scores = np.clip(risk_scores, 0.0, 1.0)

    predictions = model.predict(features)
    is_anomaly = predictions == -1

    df["risk_score"] = risk_scores
    df["is_anomaly"] = is_anomaly

    results = df[
        [
            "address",
            "cluster_id",
            "risk_score",
            "is_anomaly",
            "unique_counterparties",
            "in_count",
            "out_count",
            "tx_rate",
        ]
    ].to_dict("records")

    _write_scores(results)
    LOGGER.info("Computed anomaly detection for %d addresses", len(results))
    return results


def fetch_alerts(limit: int = 25) -> List[Dict]:
    """Retrieve the top high-risk addresses from Neo4j."""
    driver = get_driver()

    query = """
    MATCH (a:Address)
    WHERE a.risk_score IS NOT NULL
    RETURN {
        address: a.address,
        cluster_id: a.cluster_id,
        risk_score: a.risk_score,
        is_anomaly: coalesce(a.is_anomaly, false),
        is_sanctioned: coalesce(a.is_sanctioned, false),
        severity: coalesce(a.alert_severity, 'LOW')
    } AS alert
    ORDER BY a.risk_score DESC
    LIMIT $limit
    """

    try:
        with driver.session() as session:
            records = session.run(query, limit=limit)
            return [record["alert"] for record in records if record.get("alert")]
    except Neo4jError as exc:
        LOGGER.exception("Failed to fetch alerts: %s", exc)
        raise RuntimeError("Unable to retrieve alerts from Neo4j") from exc


__all__ = ["run_anomaly_detection", "fetch_alerts"]
