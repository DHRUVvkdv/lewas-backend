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
