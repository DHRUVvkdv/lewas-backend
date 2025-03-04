from fastapi import FastAPI, Depends, HTTPException, Security, status, Body, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from mangum import Mangum
import uvicorn
from datetime import datetime, timedelta
import logging
import os
import boto3
from boto3.dynamodb.conditions import Key
import os
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
import random

# Load environment variables
load_dotenv()

# Get API key and DynamoDB table name from environment variables
API_KEY = os.getenv("API_KEY", "test-api-key")
API_KEY_NAME = "X-API-Key"
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "lewas-sensors-table")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

from animal_data_routes import router as animal_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize DynamoDB resource with explicit region
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# Initialize FastAPI app
app = FastAPI(
    title="LEWAS Lab API",
    description="LEWAS Lab API for environmental sensor data collection and retrieval",
    version="0.1.0",
)

app.include_router(animal_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key header not found"
        )
    if api_key_header != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key"
        )
    return api_key_header


# Data models
class SensorReading(BaseModel):
    sensor_id: str
    value: Decimal
    unit: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    location: Optional[str] = None
    parameter_type: str  # e.g., temperature, pH, dissolved_oxygen, conductivity


class SensorReadingResponse(SensorReading):
    reading_id: str


class SensorReadingsResponse(BaseModel):
    readings: List[SensorReadingResponse]
    count: int


# Public route
@app.get("/", tags=["Public"])
async def root():
    return {
        "message": "Welcome to the LEWAS Lab API. Use the /sensors endpoints with proper authentication."
    }


# Health check route
@app.get("/health", tags=["Health"], dependencies=[Depends(get_api_key)])
async def health_check():
    logger.info("Health check endpoint called")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "lewas-sensor-api",
    }


# Create a new sensor reading
@app.post(
    "/sensors/readings",
    response_model=SensorReadingResponse,
    tags=["Sensors"],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
async def create_sensor_reading(reading: SensorReading = Body(...)):
    try:
        # Generate a unique reading ID (timestamp + sensor_id)
        reading_id = f"{reading.timestamp.isoformat()}-{reading.sensor_id}"

        # Prepare item for DynamoDB
        item = {
            "reading_id": reading_id,
            "sensor_id": reading.sensor_id,
            "value": reading.value,
            "unit": reading.unit,
            "timestamp": reading.timestamp.isoformat(),
            "parameter_type": reading.parameter_type,
        }

        # Add optional fields if provided
        if reading.location:
            item["location"] = reading.location

        # Store in DynamoDB
        table.put_item(Item=item)

        # Return the created reading with its ID
        return {**reading.dict(), "reading_id": reading_id}

    except Exception as e:
        logger.error(f"Error creating sensor reading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sensor reading: {str(e)}",
        )


# Get readings for a specific sensor
@app.get(
    "/sensors/{sensor_id}/readings",
    response_model=SensorReadingsResponse,
    tags=["Sensors"],
    dependencies=[Depends(get_api_key)],
)
async def get_sensor_readings(
    sensor_id: str = Path(..., description="The sensor ID"),
    start_time: Optional[datetime] = Query(
        None, description="Start time for data range"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    parameter_type: Optional[str] = Query(None, description="Filter by parameter type"),
    limit: int = Query(100, description="Maximum number of readings to return"),
):
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=1)

        # Query parameters
        key_condition = Key("sensor_id").eq(sensor_id)

        # Build filter expression if parameter_type is provided
        filter_expression = None
        if parameter_type:
            filter_expression = Key("parameter_type").eq(parameter_type)

        # Query DynamoDB - first try with GSI if available, fall back to scan if not
        try:
            response = table.query(
                IndexName="SensorIdTimestampIndex",
                KeyConditionExpression=key_condition
                & Key("timestamp").between(
                    start_time.isoformat(), end_time.isoformat()
                ),
                FilterExpression=filter_expression,
                Limit=limit,
            )
        except Exception as e:
            logger.warning(f"GSI query failed, falling back to scan: {e}")
            # Fall back to scan with filter if GSI is not available
            filter_expression = Key("sensor_id").eq(sensor_id)
            if parameter_type:
                filter_expression = filter_expression & Key("parameter_type").eq(
                    parameter_type
                )

            response = table.scan(FilterExpression=filter_expression, Limit=limit)

        # Format the response
        readings = []
        for item in response.get("Items", []):
            # Convert timestamp string back to datetime
            item["timestamp"] = datetime.fromisoformat(item["timestamp"])
            readings.append(SensorReadingResponse(**item))

        return {"readings": readings, "count": len(readings)}

    except Exception as e:
        logger.error(f"Error retrieving sensor readings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sensor readings: {str(e)}",
        )


# Get latest reading for all sensors
@app.get("/sensors/latest", tags=["Sensors"], dependencies=[Depends(get_api_key)])
async def get_latest_readings(
    limit: int = Query(10, description="Maximum number of sensors to return")
):
    try:
        # This is a simplified implementation - in production you might
        # want to use a GSI with a more complex query to efficiently get latest readings

        # Scan the table to get all sensor IDs (not efficient for large datasets)
        response = table.scan(ProjectionExpression="sensor_id", Limit=limit)

        # Get unique sensor IDs
        sensor_ids = {item["sensor_id"] for item in response.get("Items", [])}

        # Get the latest reading for each sensor
        latest_readings = []
        for sensor_id in sensor_ids:
            try:
                # Try to use GSI if available
                response = table.query(
                    IndexName="SensorIdTimestampIndex",
                    KeyConditionExpression=Key("sensor_id").eq(sensor_id),
                    ScanIndexForward=False,  # descending order
                    Limit=1,
                )
            except Exception as e:
                logger.warning(f"GSI query failed, falling back to scan: {e}")
                # Fall back to scan with filter
                response = table.scan(
                    FilterExpression=Key("sensor_id").eq(sensor_id),
                    Limit=10,  # Get a few items to sort them
                )
                # Sort manually to get the latest
                if response.get("Items"):
                    items = sorted(
                        response["Items"],
                        key=lambda x: x.get("timestamp", ""),
                        reverse=True,
                    )
                    response["Items"] = items[:1]  # Just keep the first/latest one

            if response.get("Items"):
                item = response["Items"][0]
                item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                latest_readings.append(item)

        return {"readings": latest_readings, "count": len(latest_readings)}

    except Exception as e:
        logger.error(f"Error retrieving latest readings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest readings: {str(e)}",
        )


# Batch upload sensor readings
@app.post(
    "/sensors/readings/batch",
    tags=["Sensors"],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
async def batch_create_sensor_readings(readings: List[SensorReading] = Body(...)):
    try:
        # Process each reading
        reading_ids = []
        successful_items = 0
        failed_items = 0

        # Use individual put_item operations instead of batch_writer to avoid duplicate key issues
        for reading in readings:
            try:
                # Generate a unique reading ID with additional randomness
                timestamp_part = reading.timestamp.isoformat()
                random_suffix = "".join(
                    random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8)
                )
                reading_id = f"{timestamp_part}-{reading.sensor_id}-{random_suffix}"
                reading_ids.append(reading_id)

                # Prepare item for DynamoDB
                item = {
                    "reading_id": reading_id,
                    "sensor_id": reading.sensor_id,
                    "value": reading.value,
                    "unit": reading.unit,
                    "timestamp": reading.timestamp.isoformat(),
                    "parameter_type": reading.parameter_type,
                }

                # Add optional fields if provided
                if reading.location:
                    item["location"] = reading.location

                # Optional UUID field if provided by client
                if hasattr(reading, "reading_uuid") and reading.reading_uuid:
                    item["reading_uuid"] = reading.reading_uuid

                # Store in DynamoDB
                table.put_item(Item=item)
                successful_items += 1

            except Exception as item_error:
                failed_items += 1
                logger.warning(f"Error processing individual reading: {item_error}")

        # Return summary of the operation
        return {
            "message": f"Successfully created {successful_items} sensor readings (failed: {failed_items})",
            "reading_ids": reading_ids,
            "successful": successful_items,
            "failed": failed_items,
        }

    except Exception as e:
        logger.error(f"Error batch creating sensor readings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create sensor readings: {str(e)}",
        )


# Fixed route to get all sensor readings with pagination
@app.get("/sensors/readings", tags=["Sensors"], dependencies=[Depends(get_api_key)])
async def get_all_sensor_readings(
    start_time: Optional[datetime] = Query(
        None, description="Start time for data range"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    parameter_type: Optional[str] = Query(None, description="Filter by parameter type"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    limit: int = Query(100, description="Maximum number of readings to return"),
    next_token: Optional[str] = Query(
        None, description="Pagination token for getting next set of results"
    ),
):
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=7)  # Default to last 7 days

        # Ensure datetimes are timezone-naive for consistent comparison
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        # Prepare scan parameters
        scan_params = {"Limit": limit}

        # Add pagination token if provided
        if next_token:
            try:
                import base64
                import json

                decoded_token = json.loads(
                    base64.b64decode(next_token.encode()).decode()
                )
                scan_params["ExclusiveStartKey"] = decoded_token
            except Exception as e:
                logger.error(f"Error decoding pagination token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid pagination token",
                )

        # Build filter expressions
        filter_expressions = []

        if parameter_type:
            filter_expressions.append(Key("parameter_type").eq(parameter_type))

        if sensor_id:
            filter_expressions.append(Key("sensor_id").eq(sensor_id))

        # Execute the scan
        if filter_expressions:
            # Combine filter expressions if there are multiple
            combined_filter = filter_expressions[0]
            for expr in filter_expressions[1:]:
                combined_filter = combined_filter & expr

            scan_params["FilterExpression"] = combined_filter

        response = table.scan(**scan_params)

        # Filter by timestamp (as scan with timestamp conditions can be inefficient)
        items = []
        for item in response.get("Items", []):
            try:
                # Get timestamp from the item and make it timezone-naive for comparison
                timestamp_str = item.get("timestamp")
                if timestamp_str:
                    item_timestamp = datetime.fromisoformat(timestamp_str)
                    # Remove timezone info if present
                    if item_timestamp.tzinfo is not None:
                        item_timestamp = item_timestamp.replace(tzinfo=None)

                    # Check if timestamp is within the specified range
                    if start_time <= item_timestamp <= end_time:
                        # Keep the original timestamp string for the response
                        items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping item with invalid timestamp: {e}")

        # Prepare pagination token for next page if there are more results
        next_page_token = None
        if "LastEvaluatedKey" in response:
            import base64
            import json

            next_page_token = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"]).encode()
            ).decode()

        return {"readings": items, "count": len(items), "next_token": next_page_token}

    except Exception as e:
        logger.error(f"Error retrieving all sensor readings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve all sensor readings: {str(e)}",
        )


# Create Mangum handler for AWS Lambda
handler = Mangum(app)

# Run the application (for development only, not used in Lambda)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
