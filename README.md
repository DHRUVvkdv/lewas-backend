# lewas-backend

docker build -t lewas-backend .
docker run --rm -p 8000:8000 --entrypoint python --env-file .env lewas-backend main.py

First
cdk init app --language=typescript
cdk bootstrap --region us-east-1 --profile lewas
cdk deploy --profile lewas

Deleted 909 images using this command:
docker system prune -a --volumes

400GB was occupied on PC, after the command it is 340 GB.

Total reclaimed space: 39.94GB (output from the command)

curl -X 'POST' \
 'URL' \
 -H 'accept: application/json' \
 -H 'X-API-Key: KEY' \
 -H 'Content-Type: application/json' \
 -d '{
"sensor_id": "sondeonsitetest",
"value": 10,
"unit": "m",
"timestamp": "2025-04-08T20:12:30.884Z",
"location": "onsitepi",
"parameter_type": "idk"
}'

# LEWAS Lab Serverless Sensor API

## Overview

The Learning Enhanced Watershed Assessment System (LEWAS) Lab is a field laboratory at Virginia Tech that collects real-time environmental data from the Webb Branch watershed. This repository contains the serverless API infrastructure for collecting, storing, and retrieving sensor data from multiple environmental monitoring instruments deployed in the watershed.

## Project Background

The LEWAS Lab monitors water quality, flow, and weather conditions using a suite of sophisticated sensors:

- **Argonaut ADV** - Acoustic Doppler Velocimeter for water velocity measurements
- **YSI Sonde** - Multi-parameter probe for water quality (temperature, pH, conductivity, dissolved oxygen)
- **Weather Station** - For atmospheric conditions (temperature, humidity, pressure)
- **Rain Gauge** - For precipitation measurement
- **Ultrasonic Sensor** - For water level monitoring
- **Power Meters** - For monitoring system power consumption

Each of these sensors collects data at regular intervals, which must be reliably stored, processed, and made available for research, education, and public access.

## Architectural Migration

### Previous Architecture

The previous system architecture was:

- Self-hosted on dedicated servers
- Used PostgreSQL relational database
- Custom JWT authentication for API access
- Direct SSH server access

### Current Serverless Architecture

This project represents a complete migration to a modern, cloud-native architecture:

- **AWS Lambda** - Serverless compute for API endpoints, eliminating server management overhead
- **Amazon DynamoDB** - Highly available NoSQL database with automatic scaling
- **API Gateway** - For API management and key-based authentication
- **AWS CDK** - Infrastructure as code for reliable deployments

This migration provides significant benefits:

- Reduced operational costs (pay-per-use vs. 24/7 servers)
- Improved scalability to handle variable data loads
- Enhanced reliability with AWS's managed services
- Simplified maintenance and deployment

## Technical Implementation

### API Design

The API follows RESTful design principles and industry best practices:

- **Versioned Endpoints** - Using `/v1/sensors/...` for API evolution
- **Modular Organization** - Separation of concerns between routes, models, services, and data access
- **Domain-Driven Design** - Models reflect the environmental monitoring domain
- **Comprehensive Documentation** - OpenAPI/Swagger integration for self-documenting endpoints

### Key Features

1. **Real-time Data Collection** - Optimized endpoints for receiving sensor data with minimal latency
2. **Flexible Query Capabilities** - Filter data by sensor, metric type, time range, and more
3. **Metadata Management** - Reference data for sensors, metrics, and units of measurement
4. **Time-Series Data Handling** - Specialized timestamp normalization and storage
5. **Batch Operations** - Support for bulk data uploads to handle connectivity issues
6. **Robust Error Handling** - Comprehensive error detection, reporting, and recovery

### Technology Stack

- **Backend Framework** - FastAPI for high-performance, async API endpoints
- **Database** - DynamoDB with optimized access patterns and indexes
- **Deployment** - AWS CDK with TypeScript for infrastructure as code
- **Runtime** - Python 3.11+ with type annotations
- **Authentication** - API key-based security
- **Containerization** - Docker for consistent deployments
- **Field Devices** - Raspberry Pi computer running custom data collection software

### Data Flow

1. Environmental sensors collect measurements (water quality, velocity, weather data, etc.)
2. Raspberry Pi devices read data from sensors through various protocols (serial, modbus, etc.)
3. Data is transmitted to the API with appropriate metadata (timestamp, sensor info, units)
4. The serverless API processes, validates, and stores the data in DynamoDB
5. Data can be queried through specialized endpoints for visualization and analysis

## Data Model

The DynamoDB table is structured to support efficient access patterns:

**Main Table**:

- Partition Key: `instrument_id` (String) - Identifies the sensor
- Sort Key: `datetime` (String) - ISO8601 timestamp for time-series organization
- Additional fields include `metric_id`, `unit_id`, `value`, and `stderr`

**Global Secondary Indexes**:

- `metric_id-datetime-index` - For querying by measurement type
- `unit_id-datetime-index` - For querying by unit of measurement

This structure allows for efficient queries across different dimensions of the data.

## Code Organization

```
project/
├── api/                  # API routes and endpoints
│   ├── dependencies.py   # Shared API dependencies
│   └── v1/               # Version 1 API routes
│       └── sensors.py    # Sensor data endpoints
├── db/                   # Database operations
│   └── sensor.py         # Sensor data DB operations
├── models/               # Data models
│   ├── base.py           # Base models
│   └── sensor.py         # Sensor-specific models
├── services/             # Business logic
│   └── sensor.py         # Sensor data processing
├── utils/                # Utility functions
│   └── reference_data.py # Reference data management
├── reference_data/       # Static reference data
│   ├── instruments.json  # Instrument definitions
│   ├── metrics.json      # Metric definitions
│   ├── units.json        # Unit definitions
│   └── meta_cells.json   # Metadata definitions
└── main.py               # Application entry point
```

## Deployment

The system is deployed using AWS CDK, which creates:

1. DynamoDB table with appropriate capacity and indexes
2. Lambda function with the containerized API
3. API Gateway with key authentication
4. IAM roles with least-privilege permissions
5. CloudWatch logs for monitoring

The CDK code handles all the complex infrastructure configuration in a repeatable, version-controlled manner.

## Future Enhancements

TODO

## Conclusion

This project represents a comprehensive modernization of environmental monitoring infrastructure, combining state-of-the-art cloud services with specialized environmental sensing technology. By leveraging serverless architecture, we've created a system that's more resilient, cost-effective, and maintainable while preserving the scientific integrity of the data collection process.

The implementation demonstrates advanced proficiency in:

- Cloud-native application design
- Serverless architecture patterns
- Infrastructure as code
- Database optimization for time-series data
- Environmental monitoring systems integration
- Robust API design and implementation

This system ensures that the valuable environmental data collected by the LEWAS Lab is reliably preserved and readily accessible for research, education, and watershed management applications.
