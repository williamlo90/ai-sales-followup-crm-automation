# Optional container runtime; currently validated application profile is native.
FROM python:3.13.6-slim
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
COPY backend/requirements-postgres.txt /app/requirements-postgres.txt
RUN pip install --no-cache-dir -r /app/requirements.lock -r /app/requirements-postgres.txt
COPY backend /app/backend
RUN useradd --create-home --uid 10001 sales && mkdir /app/local && chown sales:sales /app/local
USER sales
EXPOSE 8040
CMD ["python", "-m", "uvicorn", "backend.app:from_environment", "--factory", "--host", "0.0.0.0", "--port", "8040"]
