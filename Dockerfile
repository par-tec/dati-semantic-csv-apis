#
# Multi-stage Dockerfile for dati-semantic-csv-apis
#
# For production, pin to specific digest: python:3.14-slim@sha256:<digest>
#
# Run tests with:
#
#   docker build --target test -t dati-semantic-csv-apis:test .
#
FROM python:3.14-slim AS base

# Add security labels
LABEL maintainer="dati-semantic-csv-apis"
LABEL org.opencontainers.image.description="Semantic CSV APIs for controlled vocabularies"
LABEL org.opencontainers.image.source="https://github.com/par-tec/dati-semantic-csv-apis"


FROM base AS dev

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Pin package versions for reproducibility and supply chain security
# Use --no-cache-dir to reduce image size and prevent cache poisoning
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

USER appuser

# Copy only necessary files (ensure .dockerignore is configured)
COPY --chown=appuser:appuser . /src

RUN tox
