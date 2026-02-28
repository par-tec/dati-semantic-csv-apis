FROM python:3.14-slim AS base

FROM base AS dev
RUN pip3 install uv && \
     pip3 install tox-uv
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
ENTRYPOINT [ "sleep" ]
CMD ["infinity"]

FROM dev AS test
COPY . /src
WORKDIR /src
RUN tox
