FROM python:3.13-slim
WORKDIR /app
COPY services/api /app/services/api
RUN pip install --no-cache-dir /app/services/api
ENV NEUROMESH_DB=/tmp/neuromesh.db
EXPOSE 8080
CMD ["sh","-c","uvicorn neuromesh_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
