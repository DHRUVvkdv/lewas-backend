from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    Body,
    Query,
    Path,
    status,
)
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
import os
import random
import uuid
import base64
import json

# Configure logging
logger = logging.getLogger(__name__)

# Get environment variables
DYNAMODB_ANIMAL_TABLE = os.getenv("DYNAMODB_TABLE_NAME_ANIMAL")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize DynamoDB resource for animal table
animal_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
animal_table = animal_dynamodb.Table(DYNAMODB_ANIMAL_TABLE)

# Create router
router = APIRouter(tags=["AnimalTest"])


# Data models
class AnimalDataInput(BaseModel):
    cow_id: str
    response_type: str
    time: Optional[datetime] = Field(default_factory=datetime.now)
    source: Optional[str] = Field(default="api")


class AnimalDataResponse(BaseModel):
    entry_id: str
    cow_id: str
    response_type: str
    time: datetime
    source: str


class AnimalDataListResponse(BaseModel):
    data: List[AnimalDataResponse]
    count: int
    next_token: Optional[str] = None
    total_count: Optional[int] = None


# Import security dependency from main app
from fastapi.security.api_key import APIKeyHeader

API_KEY = os.getenv("API_KEY", "test-api-key")
API_KEY_NAME = "X-API-Key"
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


# Create a new animal data entry
@router.post(
    "/animal/data",
    response_model=AnimalDataResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
async def create_animal_data(data: AnimalDataInput = Body(...)):
    try:
        # Generate a unique entry ID
        entry_id = str(uuid.uuid4())
        # Prepare item for DynamoDB
        item = {
            "entry_id": entry_id,
            "cow_id": data.cow_id,
            "response_type": data.response_type,
            "time": data.time.isoformat(),
            "source": data.source,  # Use the source from input
        }
        # Store in DynamoDB
        animal_table.put_item(Item=item)
        # Return the created data with its ID
        return {
            "entry_id": entry_id,
            "cow_id": data.cow_id,
            "response_type": data.response_type,
            "time": data.time,
            "source": data.source,  # Include source in response
        }
    except Exception as e:
        logger.error(f"Error creating animal data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create animal data: {str(e)}",
        )


# Batch upload animal data
@router.post(
    "/animal/data/batch",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_api_key)],
)
async def batch_create_animal_data(data_entries: List[AnimalDataInput] = Body(...)):
    try:
        # Process each data entry
        entry_ids = []
        successful_items = 0
        failed_items = 0

        for data in data_entries:
            try:
                # Generate a unique entry ID
                entry_id = str(uuid.uuid4())
                entry_ids.append(entry_id)

                # Prepare item for DynamoDB
                item = {
                    "entry_id": entry_id,
                    "cow_id": data.cow_id,
                    "response_type": data.response_type,
                    "time": data.time.isoformat(),
                    "source": data.source,
                }

                # Store in DynamoDB
                animal_table.put_item(Item=item)
                successful_items += 1

            except Exception as item_error:
                failed_items += 1
                logger.warning(f"Error processing individual animal data: {item_error}")

        # Return summary of the operation
        return {
            "message": f"Successfully created {successful_items} animal data entries (failed: {failed_items})",
            "entry_ids": entry_ids,
            "successful": successful_items,
            "failed": failed_items,
        }

    except Exception as e:
        logger.error(f"Error batch creating animal data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create animal data: {str(e)}",
        )


# Get all animal data with pagination
@router.get(
    "/animal/data",
    response_model=AnimalDataListResponse,
    dependencies=[Depends(get_api_key)],
)
async def get_all_animal_data(
    start_time: Optional[datetime] = Query(
        None, description="Start time for data range"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    response_type: Optional[str] = Query(None, description="Filter by response type"),
    cow_id: Optional[str] = Query(None, description="Filter by cow ID"),
    limit: int = Query(100, description="Maximum number of entries to return"),
    next_token: Optional[str] = Query(
        None, description="Pagination token for next results"
    ),
):
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = datetime(2000, 1, 1)

        # Convert to ISO format for DynamoDB query
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()

        # Count total items (including both sources)
        count_response = animal_table.scan(Select="COUNT")
        total_count = count_response.get("Count", 0)

        # Prepare filter expressions for both queries
        filter_expressions = []
        if response_type:
            filter_expressions.append(Attr("response_type").eq(response_type))
        if cow_id:
            filter_expressions.append(Attr("cow_id").eq(cow_id))

        combined_filter = None
        if filter_expressions:
            # Combine filter expressions
            combined_filter = filter_expressions[0]
            for expr in filter_expressions[1:]:
                combined_filter = combined_filter & expr

        # Handle pagination token
        decoded_token = None
        if next_token:
            try:
                decoded_token = json.loads(
                    base64.b64decode(next_token.encode()).decode()
                )
                # The token now contains two keys: 'api' and 'raspberry_pi'
            except Exception as e:
                logger.error(f"Error decoding pagination token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid pagination token",
                )

        # Query for "api" source
        api_params = {
            "IndexName": "source-time-index",
            "KeyConditionExpression": Key("source").eq("api")
            & Key("time").between(start_time_iso, end_time_iso),
            "ScanIndexForward": False,  # False = newest first (descending order)
            "Limit": limit,
        }

        if combined_filter:
            api_params["FilterExpression"] = combined_filter

        if decoded_token and "api" in decoded_token:
            api_params["ExclusiveStartKey"] = decoded_token["api"]

        api_response = animal_table.query(**api_params)

        # Query for "Raspberry Pi" source
        pi_params = {
            "IndexName": "source-time-index",
            "KeyConditionExpression": Key("source").eq("Raspberry Pi")
            & Key("time").between(start_time_iso, end_time_iso),
            "ScanIndexForward": False,  # False = newest first (descending order)
            "Limit": limit,
        }

        if combined_filter:
            pi_params["FilterExpression"] = combined_filter

        if decoded_token and "raspberry_pi" in decoded_token:
            pi_params["ExclusiveStartKey"] = decoded_token["raspberry_pi"]

        pi_response = animal_table.query(**pi_params)

        # Combine and sort results
        all_items = []

        # Process API items
        for item in api_response.get("Items", []):
            try:
                if "time" in item:
                    # Convert string to datetime for sorting
                    sort_time = datetime.fromisoformat(item["time"])
                    # Store sort time separately for sorting
                    item["_sort_time"] = sort_time
                    # Format for response
                    item["time"] = sort_time
                all_items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping item with invalid time: {e}")

        # Process Raspberry Pi items
        for item in pi_response.get("Items", []):
            try:
                if "time" in item:
                    # Convert string to datetime for sorting
                    sort_time = datetime.fromisoformat(item["time"])
                    # Store sort time separately for sorting
                    item["_sort_time"] = sort_time
                    # Format for response
                    item["time"] = sort_time
                all_items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping item with invalid time: {e}")

        # Sort by time (newest first)
        all_items.sort(
            key=lambda x: x.get("_sort_time", datetime(1970, 1, 1)), reverse=True
        )

        # Remove the sort time field used for sorting
        for item in all_items:
            if "_sort_time" in item:
                del item["_sort_time"]

        # Limit results to the requested number
        all_items = all_items[:limit]

        # Create combined pagination token
        next_page_token = None
        last_evaluated_keys = {}

        if "LastEvaluatedKey" in api_response:
            last_evaluated_keys["api"] = api_response["LastEvaluatedKey"]

        if "LastEvaluatedKey" in pi_response:
            last_evaluated_keys["raspberry_pi"] = pi_response["LastEvaluatedKey"]

        if last_evaluated_keys:
            next_page_token = base64.b64encode(
                json.dumps(last_evaluated_keys).encode()
            ).decode()

        return {
            "data": all_items,
            "count": len(all_items),
            "next_token": next_page_token,
            "total_count": total_count,
        }

    except Exception as e:
        logger.error(f"Error retrieving animal data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve animal data: {str(e)}",
        )


# Get animal data by cow_id
@router.get(
    "/animal/data/cow/{cow_id}",
    response_model=AnimalDataListResponse,
    dependencies=[Depends(get_api_key)],
)
async def get_animal_data_by_cow_id(
    cow_id: str = Path(..., description="The cow ID"),
    start_time: Optional[datetime] = Query(
        None, description="Start time for data range"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    response_type: Optional[str] = Query(None, description="Filter by response type"),
    limit: int = Query(100, description="Maximum number of entries to return"),
):
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = datetime(2000, 1, 1)
            # start_time = end_time.replace(
            #     hour=0, minute=0, second=0, microsecond=0
            # )  # Default to current day

        # Ensure datetimes are timezone-naive for consistent comparison
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        # Build filter expression
        filter_expression = Key("cow_id").eq(cow_id)

        if response_type:
            filter_expression = filter_expression & Key("response_type").eq(
                response_type
            )

        # Scan the table (no GSI in test setup)
        response = animal_table.scan(
            FilterExpression=filter_expression,
            Limit=limit,
        )

        # Filter by time and convert time strings to datetime objects
        items = []
        for item in response.get("Items", []):
            try:
                time_str = item.get("time")
                if time_str:
                    item_time = datetime.fromisoformat(time_str)
                    # Remove timezone info if present
                    if item_time.tzinfo is not None:
                        item_time = item_time.replace(tzinfo=None)

                    if start_time <= item_time <= end_time:
                        item["time"] = item_time  # Convert to datetime for response
                        items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping item with invalid time: {e}")

        return {
            "data": items,
            "count": len(items),
            "next_token": None,  # No pagination for cow_id specific queries
        }

    except Exception as e:
        logger.error(f"Error retrieving animal data by cow_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve animal data by cow_id: {str(e)}",
        )


# Get animal data by entry_id
@router.get(
    "/animal/data/{entry_id}",
    response_model=AnimalDataResponse,
    dependencies=[Depends(get_api_key)],
)
async def get_animal_data_by_entry_id(
    entry_id: str = Path(..., description="The entry ID"),
):
    try:
        # Get item from DynamoDB
        response = animal_table.get_item(Key={"entry_id": entry_id})

        # Check if item exists
        if "Item" not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Animal data entry with ID {entry_id} not found",
            )

        # Convert time string to datetime
        item = response["Item"]
        if "time" in item:
            item["time"] = datetime.fromisoformat(item["time"])

        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving animal data by entry_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve animal data by entry_id: {str(e)}",
        )


# Get animal data by response_type
@router.get(
    "/animal/data/response/{response_type}",
    response_model=AnimalDataListResponse,
    dependencies=[Depends(get_api_key)],
)
async def get_animal_data_by_response_type(
    response_type: str = Path(..., description="The response type"),
    start_time: Optional[datetime] = Query(
        None, description="Start time for data range"
    ),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    cow_id: Optional[str] = Query(None, description="Filter by cow ID"),
    limit: int = Query(100, description="Maximum number of entries to return"),
):
    try:
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            )  # Default to current day

        # Ensure datetimes are timezone-naive for consistent comparison
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        # Build filter expression
        filter_expression = Key("response_type").eq(response_type)

        if cow_id:
            filter_expression = filter_expression & Key("cow_id").eq(cow_id)

        # Scan the table (no GSI in test setup)
        response = animal_table.scan(
            FilterExpression=filter_expression,
            Limit=limit,
        )

        # Filter by time and convert time strings to datetime objects
        items = []
        for item in response.get("Items", []):
            try:
                time_str = item.get("time")
                if time_str:
                    item_time = datetime.fromisoformat(time_str)
                    # Remove timezone info if present
                    if item_time.tzinfo is not None:
                        item_time = item_time.replace(tzinfo=None)

                    if start_time <= item_time <= end_time:
                        item["time"] = item_time  # Convert to datetime for response
                        items.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping item with invalid time: {e}")

        return {
            "data": items,
            "count": len(items),
            "next_token": None,  # No pagination for response_type specific queries
        }

    except Exception as e:
        logger.error(f"Error retrieving animal data by response_type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve animal data by response_type: {str(e)}",
        )


# For demonstration purposes, adding code to create the DynamoDB table if it doesn't exist
def create_animal_table_if_not_exists():
    """
    Creates the Animal Data table if it doesn't exist.
    This is just for demonstration - in production, tables would typically be created
    through CloudFormation, Terraform, or the AWS Console.
    """
    try:
        client = boto3.client("dynamodb", region_name=AWS_REGION)

        # Check if table exists
        existing_tables = client.list_tables()["TableNames"]
        if DYNAMODB_ANIMAL_TABLE in existing_tables:
            logger.info(f"Table {DYNAMODB_ANIMAL_TABLE} already exists")
            return

        # Create table
        client.create_table(
            TableName=DYNAMODB_ANIMAL_TABLE,
            KeySchema=[
                {"AttributeName": "entry_id", "KeyType": "HASH"}  # Partition key
            ],
            AttributeDefinitions=[{"AttributeName": "entry_id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        logger.info(f"Created table {DYNAMODB_ANIMAL_TABLE}")
    except Exception as e:
        logger.error(f"Error creating DynamoDB table: {e}")


# Uncomment this line to auto-create the table (for testing only)
# create_animal_table_if_not_exists()


@router.post(
    "/admin/update-source-field",
    dependencies=[Depends(get_api_key)],
)
async def update_source_field():
    try:
        # Scan for all items without a source field
        response = animal_table.scan()

        updated_count = 0
        for item in response.get("Items", []):
            if "source" not in item:
                # Update the item to add the source field
                animal_table.update_item(
                    Key={"entry_id": item["entry_id"]},
                    UpdateExpression="SET #src = :val",
                    ExpressionAttributeNames={"#src": "source"},
                    ExpressionAttributeValues={":val": "api"},
                )
                updated_count += 1

        # Handle pagination if there are more items
        while "LastEvaluatedKey" in response:
            response = animal_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            for item in response.get("Items", []):
                if "source" not in item:
                    animal_table.update_item(
                        Key={"entry_id": item["entry_id"]},
                        UpdateExpression="SET #src = :val",
                        ExpressionAttributeNames={"#src": "source"},
                        ExpressionAttributeValues={":val": "api"},
                    )
                    updated_count += 1

        return {"message": f"Updated {updated_count} items to add source field"}
    except Exception as e:
        logger.error(f"Error updating source field: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update source field: {str(e)}",
        )
