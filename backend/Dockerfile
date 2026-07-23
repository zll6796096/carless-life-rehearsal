FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml uv.lock /app/

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Copy application code
COPY . /app

# Default Cloud Run port
ENV PORT=8080
EXPOSE ${PORT}

# Run uvicorn dynamically binding to PORT
CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
