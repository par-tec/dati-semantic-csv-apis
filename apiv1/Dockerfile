#
# Shared multi-target Dockerfile for the API services.
#
FROM docker.io/library/python:3.14-slim AS base

LABEL maintainer="dati-semantic-csv-apis"
LABEL org.opencontainers.image.description="Semantic CSV APIs for controlled vocabularies"
LABEL org.opencontainers.image.source="https://github.com/par-tec/dati-semantic-csv-apis"

FROM base AS api-base
# To enable OCP to run the container with a randomised UID,
# containers should not use a specific uid.
# checkov:skip=CKV_DOCKER_3
COPY apiv1/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1001 -m -s /bin/bash appuser

ENV SPARQL_URL=https://schema.gov.it/sparql
ENV API_BASE_URL=https://schema.gov.it/vocabularies/v1
ENV PYTHONPATH=/app
WORKDIR /app

COPY apiv1/common /app/common
RUN mkdir -p /app/tools && touch /app/tools/__init__.py
COPY tools/store/__init__.py /app/tools/store/__init__.py

RUN chown -R appuser:appuser /app

FROM api-base AS data-api
COPY apiv1/vocabularies /app/vocabularies
COPY apiv1/openapi/vocabularies.yaml /app/vocabularies/openapi.yaml
COPY apiv1/components.oas3.yaml /app/vocabularies/components.oas3.yaml

RUN chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://localhost:8080/status')"]
ENTRYPOINT ["python"]
CMD ["-m", "vocabularies"]
