# Build stage with Poetry and build dependencies
FROM python:3.12-slim AS python-poetry-build-base

ARG DAPR_VERSION=1.16.0
# TODO: Remove Cuda on some build

# Python and pip cache settings - DISABLE ALL CACHES
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Poetry settings - DISABLE CACHES
    POETRY_VERSION=2.2.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    # Virtual environment location
    VIRTUAL_ENV="/opt/pysetup/venv"

# Create the venv and activate it
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install poetry and clean up apt cache
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        git \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Install runtime dependencies (ffmpeg) and clean cache
RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY poetry.lock pyproject.toml ./
# Dummy README to satisfy Poetry
RUN touch /app/README.md

# Install dependencies without cache and clean up
RUN poetry config cache-dir /tmp/poetry_cache \
    && poetry install --no-root --only=main --no-cache \
    && pip install --no-cache-dir ctranslate2==4.6.0 \
    && rm -rf /tmp/poetry_cache \
    && rm -rf /root/.cache/pip \
    && find /opt/pysetup/venv -name "*.pyc" -delete \
    && find /opt/pysetup/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Test stage - includes dev dependencies and tests
FROM python-poetry-build-base AS test

# Install ALL dependencies including dev
RUN poetry config cache-dir /tmp/poetry_cache \
    && poetry install --no-root --with dev --no-cache \
    && pip install --no-cache-dir ctranslate2==4.6.0 \
    && rm -rf /tmp/poetry_cache \
    && rm -rf /root/.cache/pip \
    && find /opt/pysetup/venv -name "*.pyc" -delete \
    && find /opt/pysetup/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy project configuration files needed for pip install
COPY pyproject.toml ./
COPY README.md ./

# Copy source code and tests
COPY . .

# Install the root package without cache
RUN pip install --no-cache-dir --no-deps -e .

# Clean up any remaining cache
RUN find /opt/pysetup/venv -name "*.pyc" -delete \
    && find /opt/pysetup/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /root/.cache

# Test entrypoint
ENTRYPOINT ["python", "-m", "pytest"]

# Production stage - build from test stage but remove dev dependencies
FROM test AS production

# Remove dev dependencies using poetry
RUN poetry install --no-root --only=main --sync --no-cache \
    && pip install --no-cache-dir ctranslate2==4.6.0 \
    # Remove tests directory (not needed in production)
    && rm -rf tests/ \
    # Clean up any remaining cache
    && rm -rf /tmp/poetry_cache \
    && rm -rf /root/.cache/pip \
    && find /opt/pysetup/venv -name "*.pyc" -delete \
    && find /opt/pysetup/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /root/.cache

ENTRYPOINT [ "python", "-m", "summarizer" ]