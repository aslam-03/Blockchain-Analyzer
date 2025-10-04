"""Utility helpers for managing the shared Neo4j driver instance."""

import logging
import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError

load_dotenv()

LOGGER = logging.getLogger(__name__)

_DRIVER: Optional[Driver] = None


def _build_driver() -> Driver:
    """Create and return a new Neo4j driver from environment configuration."""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not user or not password:
        missing = [key for key, value in {
            "NEO4J_URI": uri,
            "NEO4J_USER": user,
            "NEO4J_PASSWORD": password,
        }.items() if not value]
        raise ValueError(
            "Missing Neo4j configuration. Please supply the following environment variables: "
            + ", ".join(missing)
        )

    LOGGER.info("Initializing Neo4j driver for %s", uri)
    return GraphDatabase.driver(uri, auth=(user, password))


def get_driver() -> Driver:
    """Return the shared Neo4j driver instance, creating it if needed."""
    global _DRIVER

    if _DRIVER is None:
        try:
            _DRIVER = _build_driver()
        except (Neo4jError, ValueError) as exc:
            LOGGER.exception("Unable to initialize Neo4j driver: %s", exc)
            raise

    return _DRIVER


def close_driver() -> None:
    """Close the shared Neo4j driver if it has been initialized."""
    global _DRIVER

    if _DRIVER is not None:
        LOGGER.info("Closing Neo4j driver")
        _DRIVER.close()
        _DRIVER = None


__all__ = ["get_driver", "close_driver"]
