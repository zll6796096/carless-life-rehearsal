FROM python:3.12-slim

WORKDIR /app/backend

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY backend/pyproject.toml backend/uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/app ./app
COPY data/hakusan /app/data/hakusan

# Default Cloud Run port
ENV PORT=8080
EXPOSE ${PORT}

# Run uvicorn dynamically binding to PORT
CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
