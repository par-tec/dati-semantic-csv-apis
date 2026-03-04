#
# Multi-stage Dockerfile for dati-semantic-csv-apis
#
# For production, pin to specific digest: python:3.14-slim@sha256:<digest>
#
# Run tests with:
#
#   docker build --target test -t dati-semantic-csv-apis:test .
#
FROM docker.io/library/python:3.14-slim AS base

# Add security labels
LABEL maintainer="dati-semantic-csv-apis"
LABEL org.opencontainers.image.description="Semantic CSV APIs for controlled vocabularies"
LABEL org.opencontainers.image.source="https://github.com/par-tec/dati-semantic-csv-apis"

# checkov:skip=CKV_DOCKER_3
FROM base AS dev
# No need for health checks in the dev image.
HEALTHCHECK NONE

# Don't need to pin packages in the dev image.
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pin package versions for reproducibility and supply chain security
# Use --no-cache-dir to reduce image size and prevent cache poisoning
# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir uv==0.4.* && \
    pip3 install --no-cache-dir tox-uv==1.11.*

ENTRYPOINT [ "sleep" ]
CMD ["infinity"]

#
# Test stage with non-root user for better security.
#
FROM dev AS test

USER root
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1001 -m -s /bin/bash appuser

WORKDIR /src
RUN chown appuser:appuser /src
COPY --chown=appuser:appuser . /src

USER appuser

# Run fast tests first, then the slower ones.
RUN tox -e coverage -- -v -m "not asset" && \
    tox -e coverage -- -v -m asset
