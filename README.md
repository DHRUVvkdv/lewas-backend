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

# LEWAS Lab API

This API provides access to LEWAS lab sensor data. The API is built using FastAPI and deployed on AWS Lambda with data stored in DynamoDB.

## Project Structure

```
dhruvvkdv-lewas-backend/
├── image/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── src/
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── sensors.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── sensor.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── sensor.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── sensor.py
│       ├── utils/
│       │   ├── __init__.py
│       │   └── reference_data.py
│       ├── reference_data/
│       │   ├── instruments.json
│       │   ├── metrics.json
│       │   ├── units.json
│       │   └── meta_cells.json
│       ├── animal_data_routes.py (existing code)
│       └── main.py
```

## API Endpoints

### Sensor Data

- `POST /v1/sensors/observations` - Create a new sensor observation
- `POST /v1/sensors/observations/batch` - Create multiple sensor observations
- `GET /v1/sensors/observations` - Get sensor observations with optional filtering
- `GET /v1/sensors/latest` - Get latest observations for each instrument
- `GET /v1/sensors/metadata` - Get sensor metadata

## Environment Variables

- `API_KEY` - API key for authentication
- `DYNAMODB_TABLE_NAME` - DynamoDB table name
- `AWS_REGION` - AWS region

## DynamoDB Table Structure

The DynamoDB table `lewas-observations` has the following structure:

**Main Table:**

- `PK` (Partition Key): `sensor#{instrument_id}`
- `SK` (Sort Key): `timestamp#{iso_timestamp}`
- `metric_id`: Number
- `meta_id`: Number (optional)
- `unit_id`: Number
- `value`: Number
- `stderr`: Number (optional)
- `medium`: String
- `metric_name`: String
- `unit_name`: String

**Indexes:**

- GSI1 (metric-timestamp-index):
  - `PK`: `metric#{metric_id}`
  - `SK`: `timestamp#{iso_timestamp}`
- GSI2 (unit-timestamp-index):
  - `PK`: `unit#{unit_id}`
  - `SK`: `timestamp#{iso_timestamp}`

## Local Development

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with the necessary environment variables.

3. Run the API locally:

   ```bash
   uvicorn main:app --reload
   ```

4. Access the API documentation at `http://localhost:8000/docs`.

## Deployment

This project is deployed on AWS Lambda using the AWS CDK with the infrastructure code located in the `lewas-backend-infra` directory.
