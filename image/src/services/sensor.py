"""
Service layer for sensor data processing.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from decimal import Decimal

from models.sensor import (
    SensorObservationCreate,
    SensorObservationInDB,
    SensorObservationResponse,
    SensorMetadata,
)
import db.sensor as sensor_db
import utils.reference_data as ref_data

# Configure logging
logger = logging.getLogger(__name__)


def process_observation(
    observation: SensorObservationCreate,
) -> SensorObservationResponse:
    """
    Process a sensor observation and store it in the database.

    Args:
        observation: The observation to process

    Returns:
        The processed observation
    """
    try:
        # Extract data from the observation
        instrument_name = observation.instrument
        unit_abbv = observation.unit
        metric_name = observation.sample.get("metric")
        medium = observation.sample.get("medium")
        meta_name = observation.sample.get("meta")

        # Get reference IDs
        instrument_id = ref_data.get_instrument_id(instrument_name)
        unit_id = ref_data.get_unit_id(unit_abbv)
        metric_id = ref_data.get_metric_id(metric_name, medium)
        meta_id = ref_data.get_meta_id(meta_name) if meta_name else None

        # Validate that we found all the necessary IDs
        if not instrument_id:
            raise ValueError(f"Unknown instrument: {instrument_name}")
        if not unit_id:
            raise ValueError(f"Unknown unit: {unit_abbv}")
        if not metric_id:
            raise ValueError(f"Unknown metric: {metric_name} with medium {medium}")

        # Prepare the timestamp for sorting
        timestamp_iso = observation.timestamp

        # Create the database model
        db_observation = SensorObservationInDB.from_create_model(
            observation,
            # Store primary key fields for DynamoDB in our model
            PK=f"sensor#{instrument_id}",  # Keep for compatibility with model definition
            SK=f"timestamp#{timestamp_iso}",  # Keep for compatibility with model definition
            instrument_id=instrument_id,
            metric_id=metric_id,
            unit_id=unit_id,
            meta_id=meta_id,
            medium=medium,
            metric_name=metric_name,
        )

        # Store in the database
        created_item = sensor_db.create_observation(db_observation)

        # Create response model
        response = SensorObservationResponse(
            timestamp=observation.timestamp,
            sample=observation.sample,
            instrument=observation.instrument,
            unit=observation.unit,
            value=observation.value,
            stderr=observation.stderr,
            instrument_id=instrument_id,
            metric_id=metric_id,
            unit_id=unit_id,
            meta_id=meta_id,
            medium=medium,
        )

        return response
    except Exception as e:
        logger.error(f"Error processing observation: {e}")
        raise


def get_observations(
    instrument_name: Optional[str] = None,
    metric_name: Optional[str] = None,
    medium: Optional[str] = None,
    unit_abbv: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get observations with optional filtering.

    Args:
        instrument_name: Optional instrument name to filter by
        metric_name: Optional metric name to filter by
        medium: Optional medium to filter by
        unit_abbv: Optional unit abbreviation to filter by
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of results to return
        next_token: Pagination token

    Returns:
        Dictionary with observations and pagination token
    """
    try:
        # Convert names to IDs for database filtering
        instrument_id = None
        if instrument_name:
            instrument_id = ref_data.get_instrument_id(instrument_name)
            if not instrument_id:
                raise ValueError(f"Unknown instrument: {instrument_name}")

        metric_id = None
        if metric_name and medium:
            metric_id = ref_data.get_metric_id(metric_name, medium)
            if not metric_id:
                raise ValueError(f"Unknown metric: {metric_name} with medium {medium}")

        unit_id = None
        if unit_abbv:
            unit_id = ref_data.get_unit_id(unit_abbv)
            if not unit_id:
                raise ValueError(f"Unknown unit: {unit_abbv}")

        # Get observations from the database
        results = sensor_db.get_observations(
            instrument_id=instrument_id,
            metric_id=metric_id,
            unit_id=unit_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            next_token=next_token,
        )

        # Convert database models to response models
        observations = []
        for item in results["observations"]:
            # Create response models
            observation = SensorObservationResponse(
                timestamp=item["timestamp"],
                sample={
                    "medium": item["medium"],
                    "metric": item["metric_name"],
                    "meta": (
                        ref_data.get_meta_cells()
                        .get(str(item.get("meta_id")), {})
                        .get("name")
                        if item.get("meta_id")
                        else None
                    ),
                },
                instrument=ref_data.get_instruments()
                .get(str(item["instrument_id"]), {})
                .get("name", ""),
                unit=ref_data.get_units().get(str(item["unit_id"]), {}).get("abbv", ""),
                value=item["value"],
                stderr=item.get("stderr"),
                instrument_id=item["instrument_id"],
                metric_id=item["metric_id"],
                unit_id=item["unit_id"],
                meta_id=item.get("meta_id"),
                medium=item["medium"],
            )
            observations.append(observation)

        return {
            "observations": observations,
            "count": results["count"],
            "next_token": results.get("next_token"),
        }
    except Exception as e:
        logger.error(f"Error getting observations: {e}")
        raise


def get_latest_observations(limit: int = 10) -> Dict[str, Any]:
    """
    Get the latest observations for each instrument.

    Args:
        limit: Maximum number of instruments to return

    Returns:
        Dictionary with latest observations for each instrument
    """
    try:
        # Get latest observations from the database
        results = sensor_db.get_latest_observations(limit=limit)

        # Convert database models to response models
        observations = []
        for item in results["observations"]:
            # Create response models
            observation = SensorObservationResponse(
                timestamp=item["timestamp"],
                sample={
                    "medium": item["medium"],
                    "metric": item["metric_name"],
                    "meta": (
                        ref_data.get_meta_cells()
                        .get(str(item.get("meta_id")), {})
                        .get("name")
                        if item.get("meta_id")
                        else None
                    ),
                },
                instrument=ref_data.get_instruments()
                .get(str(item["instrument_id"]), {})
                .get("name", ""),
                unit=ref_data.get_units().get(str(item["unit_id"]), {}).get("abbv", ""),
                value=item["value"],
                stderr=item.get("stderr"),
                instrument_id=item["instrument_id"],
                metric_id=item["metric_id"],
                unit_id=item["unit_id"],
                meta_id=item.get("meta_id"),
                medium=item["medium"],
            )
            observations.append(observation)

        return {"observations": observations, "count": results["count"]}
    except Exception as e:
        logger.error(f"Error getting latest observations: {e}")
        raise


def get_metadata() -> SensorMetadata:
    """
    Get all reference data.

    Returns:
        SensorMetadata object with all reference data
    """
    try:
        return SensorMetadata(
            metrics=ref_data.get_all_metrics(),
            instruments=ref_data.get_all_instruments(),
            units=ref_data.get_all_units(),
        )
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise
