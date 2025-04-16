"""
Main entry point for the LEWAS Lab API.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import uvicorn
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import boto3

# Configure logging first, before other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get configuration from environment variables
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "lewas-observations")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

try:
    # Import existing animal routes (we'll keep these as they are)
    from animal_data_routes import router as animal_router

    # Import our new v1 API routes
    from api.v1 import router as api_v1_router

    # Import dependencies
    from api.dependencies import get_api_key

    # Initialize DynamoDB resource
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)

    # Initialize FastAPI app
    app = FastAPI(
        title="LEWAS Lab API",
        description="LEWAS Lab API for environmental sensor data collection and retrieval",
        version="0.1.0",
    )

    # Include routers
    app.include_router(animal_router)  # Keep existing animal routes
    app.include_router(api_v1_router)  # Add our new v1 API routes

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Public route
    @app.get("/", tags=["Public"])
    async def root():
        """Root endpoint."""
        return {
            "message": "Welcome to the LEWAS Lab API. Use the /v1/sensors endpoints for sensor data access."
        }

    # Health check route
    @app.get("/health", tags=["Health"], dependencies=[Depends(get_api_key)])
    async def health_check():
        """Health check endpoint."""
        logger.info("Health check endpoint called")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "lewas-sensor-api",
        }

    # Create Mangum handler for AWS Lambda
    handler = Mangum(app)

except Exception as e:
    # Log the exception if there's an error during startup
    logger.error(f"Error during application startup: {e}")
    raise

# Run the application (for development only, not used in Lambda)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
