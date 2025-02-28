# lewas-backend

docker build -t lewas-backend .
docker run --rm -p 8000:8000 --entrypoint python --env-file .env lewas-backend main.py

First
cdk init app --language=typescript
cdk bootstrap --region us-east-1 --profile lewas
cdk deploy --profile lewas
