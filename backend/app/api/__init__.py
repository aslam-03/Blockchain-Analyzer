"""API route definitions for Blockchain Analyzer."""

from fastapi import APIRouter

from .trace import router as trace_router
from .address import router as address_router
from .alerts import router as alerts_router
from .compliance import router as compliance_router


api_router = APIRouter()
api_router.include_router(trace_router)
api_router.include_router(address_router)
api_router.include_router(alerts_router)
api_router.include_router(compliance_router)


__all__ = ["api_router"]
