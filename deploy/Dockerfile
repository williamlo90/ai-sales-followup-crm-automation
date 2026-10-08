# Static preparation only. Build/start and Linux acceptance belong to Phase 7.
FROM python:3.13.6-slim
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock
COPY backend /app/backend
RUN useradd --create-home --uid 10001 sales && mkdir /app/local && chown sales:sales /app/local
USER sales
EXPOSE 8040
CMD ["python", "-m", "uvicorn", "backend.app:from_environment", "--factory", "--host", "0.0.0.0", "--port", "8040"]
