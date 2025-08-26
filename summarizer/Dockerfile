# `python-base` sets up all our shared environment variables
FROM python:3.12-slim AS python-poetry-build-base

ARG DAPR_VERSION=1.15.1
# TODO: Remove Cuda on some build

    # python no pyc files + pip longer timeout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # poetry set location
    POETRY_VERSION=2.1.1 \
    POETRY_HOME="/opt/poetry" \
    \
    # Poetry can create a venv for you, but it will be a random venv name 
    # You could also have POETRY_VIRTUALENVS_IN_PROJECT=1 to get a deterministic venv name
    # but it will be in the project directory, which might cause problem if you wanna mount your project in dev
    # Instead we create/activate our own venv in a known location, prompting poetry to use it
    # Once poetry lets us set the venv name in its confing, we can remove this 
    # Ref: https://github.com/python-poetry/poetry/issues/263#issuecomment-1404129650
    VIRTUAL_ENV="/opt/pysetup/venv"

# create the venv and activate it
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install poetry 
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential
# use official curl to respect $POETRY_VERSION & $POETRY_HOME
# (pip install poetry doesn't respect $POETRY_HOME)

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# `development` image is used during development
FROM python-poetry-build-base

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    # Dummy README to satisfy Poetry
    touch /app/README.md


COPY poetry.lock pyproject.toml ./
# Install dependencies without the root package first
# https://github.com/m-bain/whisperX/issues/1038
RUN poetry install --no-root && pip install ctranslate2==4.6.0

# Copy source code
COPY src/ src/
# Now install the root package
RUN poetry install --only-root

COPY . .
ENTRYPOINT [ "poetry", "run", "summarizer" ]