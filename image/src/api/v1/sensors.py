"""
API routes for sensor data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
from typing import Dict, List, Optional, Any
from datetime import datetime

from models.sensor import (
    SensorObservationCreate,
    SensorObservationResponse,
    SensorObservationsResponse,
    SensorMetadataResponse,
)
import services.sensor as sensor_service
from api.dependencies import get_api_key

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/v1/sensors", tags=["Sensors"], dependencies=[Depends(get_api_key)]
)


@router.post(
    "/observations",
    response_model=SensorObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sensor observation",
)
async def create_observation(observation: SensorObservationCreate = Body(...)):
    """
    Create a new sensor observation.

    Args:
        observation: The observation to create

    Returns:
        The created observation
    """
    try:
        return sensor_service.process_observation(observation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create observation: {str(e)}",
        )


@router.post(
    "/observations/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple sensor observations",
)
async def create_observations_batch(
    observations: List[SensorObservationCreate] = Body(...),
):
    """
    Create multiple sensor observations in a batch.

    Args:
        observations: The observations to create

    Returns:
        Summary of the batch operation
    """
    try:
        # Process each observation
        successful = []
        failed = []

        for observation in observations:
            try:
                result = sensor_service.process_observation(observation)
                successful.append(result)
            except Exception as item_error:
                failed.append({"observation": observation, "error": str(item_error)})
                logger.warning(f"Error processing observation in batch: {item_error}")

        return {
            "message": f"Successfully created {len(successful)} observations (failed: {len(failed)})",
            "successful_count": len(successful),
            "failed_count": len(failed),
            "failed_items": failed if failed else None,
        }
    except Exception as e:
        logger.error(f"Error creating observations batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create observations batch: {str(e)}",
        )


@router.get(
    "/observations",
    response_model=SensorObservationsResponse,
    summary="Get sensor observations",
)
async def get_observations(
    instrument: Optional[str] = Query(None, description="Filter by instrument name"),
    metric: Optional[str] = Query(None, description="Filter by metric name"),
    medium: Optional[str] = Query(
        None, description="Filter by medium (required if metric is provided)"
    ),
    unit: Optional[str] = Query(None, description="Filter by unit abbreviation"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    limit: int = Query(100, description="Maximum number of results to return"),
    next_token: Optional[str] = Query(None, description="Pagination token"),
):
    """
    Get sensor observations with optional filtering.

    Args:
        instrument: Optional instrument name to filter by
        metric: Optional metric name to filter by
        medium: Optional medium to filter by
        unit: Optional unit abbreviation to filter by
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of results to return
        next_token: Pagination token

    Returns:
        List of observations and pagination token
    """
    try:
        # Validate that medium is provided if metric is provided
        if metric and not medium:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medium is required when filtering by metric",
            )

        results = sensor_service.get_observations(
            instrument_name=instrument,
            metric_name=metric,
            medium=medium,
            unit_abbv=unit,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            next_token=next_token,
        )

        return SensorObservationsResponse(
            observations=results["observations"],
            count=results["count"],
            next_token=results.get("next_token"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get observations: {str(e)}",
        )


@router.get(
    "/latest",
    response_model=SensorObservationsResponse,
    summary="Get latest observations for each instrument",
)
async def get_latest_observations(
    limit: int = Query(10, description="Maximum number of instruments to return")
):
    """
    Get the latest observations for each instrument.

    Args:
        limit: Maximum number of instruments to return

    Returns:
        Latest observations for each instrument
    """
    try:
        results = sensor_service.get_latest_observations(limit=limit)

        return SensorObservationsResponse(
            observations=results["observations"], count=results["count"]
        )
    except Exception as e:
        logger.error(f"Error getting latest observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest observations: {str(e)}",
        )


@router.get(
    "/metadata", response_model=SensorMetadataResponse, summary="Get sensor metadata"
)
async def get_metadata():
    """
    Get all reference data for sensors.

    Returns:
        All reference data for sensors
    """
    try:
        metadata = sensor_service.get_metadata()

        return SensorMetadataResponse(data=metadata)
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metadata: {str(e)}",
        )
