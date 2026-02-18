# Dati Semantic APIs

This repository provides documents, tools and PoC
for the management of semantic assets in the context
of the National Data Catalog for Semantic Interoperability.

## Table of contents

- 💻 [Usage](#usage)
<!-- - 🚀 [API](#api) -->
<!-- - 📋 [Development](#development) -->
- 📝 [Contributing](#contributing)
- ⚖️ [License](#license)

## Usage

The core documentation for this project
is in :flag-it: Italian.
You can find it in the [docs](docs) folder.

- [CSV Serialization](docs/README.csv.md)
- [REST API for Controlled Vocabularies](docs/README.api.md)

## Contributing

Please, see [CONTRIBUTING.md](CONTRIBUTING.md) for more details on:

- using [pre-commit](CONTRIBUTING.md#pre-commit);
- following the git flow and making good [pull requests](CONTRIBUTING.md#making-a-pr).

## Using this repository

You can create new projects starting from this repository,
so you can use a consistent CI and checks for different projects.

Besides all the explanations in the [CONTRIBUTING.md](CONTRIBUTING.md) file, you can use the docker-compose file
(e.g. if you prefer to use docker instead of installing the tools locally)

```bash
docker-compose run pre-commit
```

## Testing github actions

Tune the Github pipelines in [.github/workflows](.github/workflows/).

To speed up the development, you can test the pipeline with [act](https://github.com/nektos/act).
Installing `act` is beyond the scope of this document.

To test the pipeline locally and ensure that secrets (e.g., service accounts and other credentials)
are correctly configured, use:

 ```bash
 # Run a specific job in the pipeline
 act -j test -s CI_API_TOKEN="$(cat gh-ci.json)" \
      -s CI_ACCOUNT=my-secret-account
 ```
