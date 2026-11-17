FROM node:24-alpine AS web-build
WORKDIR /src
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY services/api /app/services/api
COPY scripts /app/scripts
COPY --from=web-build /src/apps/web/dist /app/web
RUN python -m pip install --no-cache-dir --upgrade 'pip>=26.2,<27' \
    && python -m pip install --no-cache-dir '/app/services/api[agents]'
ENV NEUROMESH_DB=/tmp/neuromesh.db
ENV NEUROMESH_STATIC_DIR=/app/web
EXPOSE 8080
CMD ["sh","-c","uvicorn neuromesh_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
