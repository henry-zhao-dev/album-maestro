# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

# Keep this aligned with the Poetry version recorded in poetry.lock.
ARG POETRY_VERSION=2.4.1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# FFmpeg is a runtime dependency of the local processing pipeline. Poetry is
# kept in the image so the locked environment can be inspected and maintained
# from the same container used to run Album Maestro.
RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

# Install third-party dependencies before copying the source for better layer
# reuse when application code changes.
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main --no-root

COPY src ./src
RUN poetry install --only main

# The library itself is supplied at runtime as /library. The default user is
# intentionally non-root; bind-mount users can pass --user UID:GID when host
# filesystem ownership needs to be preserved.
RUN useradd --create-home --shell /usr/sbin/nologin album-maestro \
    && mkdir -p /library \
    && chown -R album-maestro:album-maestro /app /library

WORKDIR /library
VOLUME ["/library"]
USER album-maestro

ENTRYPOINT ["album-maestro"]
CMD ["--help"]
