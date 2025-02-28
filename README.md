# lewas-backend

docker build -t lewas-backend .
docker run --rm -p 8000:8000 --entrypoint python --env-file .env lewas-backend main.py
