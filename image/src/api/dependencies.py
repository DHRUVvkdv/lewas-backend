"""
Shared dependencies for the API.
"""

import logging
import os
from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

# Configure logging
logger = logging.getLogger(__name__)

# API Key security
API_KEY = os.getenv("API_KEY", "test-api-key")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate the API key.

    Args:
        api_key_header: The API key from the request header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key header not found"
        )
    if api_key_header != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key"
        )
    return api_key_header
