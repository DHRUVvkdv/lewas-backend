"""
Base models for the LEWAS sensor API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ResponseModel(BaseModel):
    """Base model for API responses."""

    success: bool = True
    message: Optional[str] = None


class PaginatedResponseModel(ResponseModel):
    """Base model for paginated API responses."""

    count: int
    next_token: Optional[str] = None
