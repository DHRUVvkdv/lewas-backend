"""
Database operations for sensor data.
"""

import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
import json
import base64
from decimal import Decimal

from models.sensor import (
    SensorObservationCreate,
    SensorObservationInDB,
    SensorObservationResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# DynamoDB table name from environment variable
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "lewas-observations")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def create_observation(observation: SensorObservationInDB) -> Dict[str, Any]:
    """
    Create a new observation in DynamoDB.

    Args:
        observation: The observation to create

    Returns:
        The created item
    """
    try:
        # Convert the observation to a dictionary
        item = observation.dict()

        # Adjust keys to match the DynamoDB table structure
        # Remove PK/SK and use instrument_id/datetime directly
        if "PK" in item:
            del item["PK"]
        if "SK" in item:
            del item["SK"]

        # Set the primary key fields based on our model
        item["instrument_id"] = str(
            observation.instrument_id
        )  # Convert to string as per your table
        item["datetime"] = observation.timestamp  # Use the timestamp directly

        # Store in DynamoDB
        response = table.put_item(Item=item)

        return item
    except Exception as e:
        logger.error(f"Error creating observation: {e}")
        raise


def get_observations(
    instrument_id: Optional[int] = None,
    metric_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get observations from DynamoDB with optional filtering.

    Args:
        instrument_id: Optional instrument ID to filter by
        metric_id: Optional metric ID to filter by
        unit_id: Optional unit ID to filter by
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of results to return
        next_token: Pagination token

    Returns:
        Dictionary with observations and pagination token
    """
    try:
        # Decode pagination token if provided
        exclusive_start_key = None
        if next_token:
            try:
                exclusive_start_key = json.loads(
                    base64.b64decode(next_token.encode()).decode()
                )
            except Exception as e:
                logger.error(f"Error decoding pagination token: {e}")
                raise ValueError("Invalid pagination token")

        # Determine the query parameters based on the provided filters
        if instrument_id is not None:
            # Query by instrument ID
            key_condition = Key("instrument_id").eq(str(instrument_id))

            # Add time range condition if provided
            if start_time and end_time:
                key_condition = key_condition & Key("datetime").between(
                    start_time, end_time
                )
            elif start_time:
                key_condition = key_condition & Key("datetime").gte(start_time)
            elif end_time:
                key_condition = key_condition & Key("datetime").lte(end_time)

            # Add filter expression for metric_id if provided
            filter_expression = None
            if metric_id is not None:
                filter_expression = Attr("metric_id").eq(metric_id)

            # Add unit_id to filter expression if provided
            if unit_id is not None:
                unit_filter = Attr("unit_id").eq(unit_id)
                if filter_expression:
                    filter_expression = filter_expression & unit_filter
                else:
                    filter_expression = unit_filter

            # Execute the query
            if filter_expression:
                query_params = {
                    "KeyConditionExpression": key_condition,
                    "FilterExpression": filter_expression,
                    "Limit": limit,
                }
            else:
                query_params = {"KeyConditionExpression": key_condition, "Limit": limit}

            # Add pagination token if provided
            if exclusive_start_key:
                query_params["ExclusiveStartKey"] = exclusive_start_key

            response = table.query(**query_params)
        elif metric_id is not None:
            # Query by metric ID using GSI
            key_condition = Key("metric_id").eq(metric_id)

            # Add time range condition if provided
            if start_time and end_time:
                key_condition = key_condition & Key("datetime").between(
                    start_time, end_time
                )
            elif start_time:
                key_condition = key_condition & Key("datetime").gte(start_time)
            elif end_time:
                key_condition = key_condition & Key("datetime").lte(end_time)

            # Add filter expression for unit_id if provided
            filter_expression = None
            if unit_id is not None:
                filter_expression = Attr("unit_id").eq(unit_id)

            # Execute the query
            query_params = {
                "IndexName": "metric_id-datetime-index",
                "KeyConditionExpression": key_condition,
                "Limit": limit,
            }

            # Add filter expression if provided
            if filter_expression:
                query_params["FilterExpression"] = filter_expression

            # Add pagination token if provided
            if exclusive_start_key:
                query_params["ExclusiveStartKey"] = exclusive_start_key

            response = table.query(**query_params)
        else:
            # Scan the table if no specific index is applicable
            scan_params = {"Limit": limit}

            # Build filter expression
            filter_expressions = []
            if unit_id is not None:
                filter_expressions.append(Attr("unit_id").eq(unit_id))

            # Add time range filter for scans
            if start_time:
                filter_expressions.append(Attr("datetime").gte(start_time))
            if end_time:
                filter_expressions.append(Attr("datetime").lte(end_time))

            # Combine filter expressions if there are multiple
            if filter_expressions:
                combined_filter = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    combined_filter = combined_filter & expr
                scan_params["FilterExpression"] = combined_filter

            # Add pagination token if provided
            if exclusive_start_key:
                scan_params["ExclusiveStartKey"] = exclusive_start_key

            response = table.scan(**scan_params)

        # Prepare the next pagination token if there are more results
        next_page_token = None
        if "LastEvaluatedKey" in response:
            next_page_token = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"], cls=DecimalEncoder).encode()
            ).decode()

        # Return the results
        return {
            "observations": response.get("Items", []),
            "count": len(response.get("Items", [])),
            "next_token": next_page_token,
        }
    except Exception as e:
        logger.error(f"Error getting observations: {e}")
        raise


def get_latest_observations(limit: int = 10):
    """
    Get the latest observations for each instrument.

    Args:
        limit: Maximum number of instruments to return

    Returns:
        Dictionary with latest observations for each instrument
    """
    try:
        # Scan the table to get all instrument IDs
        response = table.scan(ProjectionExpression="instrument_id", Limit=100)

        # Get unique instrument IDs
        instrument_ids = set(
            item["instrument_id"] for item in response.get("Items", [])
        )

        # Get the latest observation for each instrument
        latest_observations = []
        for instrument_id in list(instrument_ids)[:limit]:
            try:
                # Query for the latest observation for this instrument
                response = table.query(
                    KeyConditionExpression=Key("instrument_id").eq(instrument_id),
                    ScanIndexForward=False,  # descending order by sort key
                    Limit=1,
                )

                if response.get("Items"):
                    latest_observations.append(response["Items"][0])
            except Exception as instrument_error:
                logger.warning(
                    f"Error getting latest observation for instrument {instrument_id}: {instrument_error}"
                )

        return {"observations": latest_observations, "count": len(latest_observations)}
    except Exception as e:
        logger.error(f"Error getting latest observations: {e}")
        raise
