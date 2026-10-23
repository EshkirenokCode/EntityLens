FROM node:22-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY concord/ concord/
COPY scripts/ scripts/
COPY reports/ reports/
COPY data/manifests/ data/manifests/
COPY --from=web /web/dist/ web/dist/
ENV CONCORD_DB=/state/concord.db
CMD ["uvicorn","concord.api:app","--host","0.0.0.0","--port","8765"]
