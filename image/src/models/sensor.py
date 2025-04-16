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
    sample: Dict[str, str] = Field(
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
