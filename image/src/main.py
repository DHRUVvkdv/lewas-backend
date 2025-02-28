from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from mangum import Mangum
import uvicorn
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variable (or use a default for development)
API_KEY = os.getenv("API_KEY", "test-api-key")
API_KEY_NAME = "X-API-Key"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LEWAS Lab API",
    description="LEWAS Lab API built with FastAPI with API key authentication, Lambda-ready",
    version="0.1.0",
)

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


# Public route
@app.get("/", tags=["Public"])
async def root():
    return {
        "message": "Welcome to the LEWAS Lab API. Use the /health endpoint with proper authentication."
    }


# Protected route
@app.get("/health", tags=["Health"], dependencies=[Depends(get_api_key)])
async def health_check():
    logger.info("Health check endpoint called")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "test-api",
    }


# Create Mangum handler for AWS Lambda
handler = Mangum(app)

# Run the application (for development only, not used in Lambda)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
