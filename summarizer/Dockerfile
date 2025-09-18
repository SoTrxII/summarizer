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

# Production stage - copy only runtime files
FROM python:3.12-slim AS production

# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV="/opt/pysetup/venv"

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from build stage
COPY --from=python-poetry-build-base $VIRTUAL_ENV $VIRTUAL_ENV

# Copy project configuration files needed for pip install
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ src/

# Install the root package without cache
RUN pip install --no-cache-dir --no-deps -e .

# Clean up any remaining cache
RUN find /opt/pysetup/venv -name "*.pyc" -delete \
    && find /opt/pysetup/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /root/.cache

ENTRYPOINT [ "python", "-m", "summarizer" ]