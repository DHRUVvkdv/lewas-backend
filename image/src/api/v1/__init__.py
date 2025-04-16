"""Version 1 API package."""

from fastapi import APIRouter
from .sensors import router as sensors_router

router = APIRouter()
router.include_router(sensors_router)
