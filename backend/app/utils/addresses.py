"""Helpers for validating and normalizing blockchain addresses."""

from __future__ import annotations

import re

ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")


def normalize_eth_address(value: str) -> str:
    """Validate and normalize an Ethereum address to lowercase hex."""
    if value is None:
        raise ValueError("Address cannot be null")
    address = value.strip()
    if not ADDRESS_PATTERN.fullmatch(address):
        raise ValueError("Invalid Ethereum address format")
    return address.lower()


__all__ = ["normalize_eth_address"]
