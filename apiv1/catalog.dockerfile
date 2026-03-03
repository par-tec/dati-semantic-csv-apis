#
# Application to serve the Vocabulary Catalog API.
#
FROM docker.io/library/python:3.14-slim AS base

# Add security labels
LABEL maintainer="dati-semantic-csv-apis"
LABEL org.opencontainers.image.description="Semantic CSV APIs for controlled vocabularies"
LABEL org.opencontainers.image.source="https://github.com/par-tec/dati-semantic-csv-apis"

FROM base AS api
# To enable OCP to run the container with a randomised UID,
#   containers should not use a specific uid.
# checkov:skip=CKV_DOCKER_3
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/catalog
COPY ./catalog/*.py /app/catalog/
COPY ./openapi/catalog.yaml /app/catalog/openapi.yaml
WORKDIR /app
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "curl", "-f", "http://localhost:8080/status" ]
ENV PYTHONPATH=:.:
ENTRYPOINT [ "python" ]
CMD [ "-m", "catalog" ]
