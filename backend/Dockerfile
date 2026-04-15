FROM python:3.12-slim

# ---- System deps ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Python dependencies ----
# Copy only the dependency manifest first so Docker can cache this layer
# and skip re-installing packages when only source code changes.
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]"

# ---- Application source ----
COPY . .

# ---- Runtime ----
EXPOSE 8000

# The --factory flag tells uvicorn to call create_app() to get the ASGI app.
# --reload watches for file changes — useful in development with a bind mount.
CMD ["uvicorn", "app.main:create_app", "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload"]
