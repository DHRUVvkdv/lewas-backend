"""
Sensor models for the LEWAS sensor API.
"""

from pydantic import BaseModel, Field, root_validator, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
import uuid

from .base import ResponseModel, PaginatedResponseModel


class SensorObservationBase(BaseModel):
    """Base model for sensor observations."""

    timestamp: str = Field(..., description="ISO format timestamp")
    sample: Dict[str, Any] = Field(
        ...,
        description="Sample information including medium, metric, and optional meta",
    )
    instrument: str = Field(..., description="Instrument name")
    unit: str = Field(..., description="Unit abbreviation")
    value: Union[float, Decimal] = Field(..., description="Observation value")
    stderr: Optional[Union[float, Decimal]] = Field(None, description="Standard error")

    class Config:
        """Configure the model."""

        json_encoders = {
            Decimal: lambda v: float(v),
        }

    @validator("sample")
    def validate_sample(cls, sample):
        """Validate that the sample contains medium and metric."""
        if "medium" not in sample or not sample["medium"]:
            raise ValueError("Sample must include a 'medium' field")
        if "metric" not in sample or not sample["metric"]:
            raise ValueError("Sample must include a 'metric' field")
        return sample

    @validator("timestamp")
    def validate_timestamp(cls, v):
        """Validate and format the timestamp."""
        # If it's just a time without date, add the current date
        if ":" in v and not any(x in v for x in ["-", "T", "Z"]):
            from datetime import datetime

            today = datetime.now().strftime("%Y-%m-%d")
            return f"{today}T{v}Z"

        # If it already contains T or Z, assume it's correctly formatted
        if "T" in v or "Z" in v:
            return v

        # Try to convert other formats to ISO
        try:
            from datetime import datetime

            parsed_date = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return parsed_date.isoformat() + "Z"
        except ValueError:
            # If all else fails, just return the original
            return v

    @validator("value")
    def convert_value_to_decimal(cls, v):
        """Convert value to Decimal for DynamoDB compatibility."""
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @validator("stderr")
    def convert_stderr_to_decimal(cls, v):
        """Convert stderr to Decimal for DynamoDB compatibility."""
        if v is not None and isinstance(v, float):
            return Decimal(str(v))
        return v


class SensorObservationCreate(SensorObservationBase):
    """Model for creating a sensor observation."""

    pass


class SensorObservationInDB(SensorObservationBase):
    """Model for a sensor observation in the database."""

    # Reference IDs
    instrument_id: int = Field(..., description="Instrument ID")
    metric_id: int = Field(..., description="Metric ID")
    unit_id: int = Field(..., description="Unit ID")
    meta_id: Optional[int] = Field(None, description="Meta ID")

    # Additional fields for GSIs
    medium: str = Field(..., description="Medium")
    metric_name: str = Field(..., description="Metric name")

    # DynamoDB specific fields - kept for compatibility with existing code
    PK: Optional[str] = Field(None, description="Partition key")
    SK: Optional[str] = Field(None, description="Sort key")

    @classmethod
    def from_create_model(
        cls, model: SensorObservationCreate, **kwargs
    ) -> "SensorObservationInDB":
        """Create a DB model from a create model."""
        return cls(**model.dict(), **kwargs)


class SensorObservationResponse(SensorObservationBase):
    """Model for a sensor observation response."""

    instrument_id: int = Field(..., description="Instrument ID")
    metric_id: int = Field(..., description="Metric ID")
    unit_id: int = Field(..., description="Unit ID")
    meta_id: Optional[int] = Field(None, description="Meta ID")
    medium: str = Field(..., description="Medium")


class SensorObservationsResponse(PaginatedResponseModel):
    """Model for multiple sensor observations response."""

    observations: List[SensorObservationResponse] = []


class SensorMetadata(BaseModel):
    """Model for sensor metadata."""

    metrics: List[Dict[str, Any]] = []
    instruments: List[Dict[str, Any]] = []
    units: List[Dict[str, Any]] = []


class SensorMetadataResponse(ResponseModel):
    """Model for sensor metadata response."""

    data: SensorMetadata
