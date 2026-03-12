# 13. CI for Datapackage CSV generation

<!-- In vim, use !!date -I to get current date. -->

Date: 2025-12-03

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Providers need a way to integrate CSV creation inside their repository workflow,
using CLI commands.
They should be able to either run the CLI commands locally and commit the generated CSV files to their repository,
automate the CSV generation using a CI workflow, or use a combination of both approaches.
Moreover, in case of automatic CSV generation, providers should be able
to review the data before publishing it.

## Decision

- [x] To ease the integration of the CLI in CIs and workflows,
  it is published as a Linux x86_64 binary as a github artifact
  using pyinstaller.
- [x] A specific build job creates the Linux x86_64 binary and publishes it as a github artifact
  in this repository.

The github CI workflow does the following:

1. it is triggered by a push to a specific branch (e.g., #asset)
   or by a manual workflow.

1. if a commit message contains a specific `skip` keyword (e.g., \[skip ci\]),
   the workflow is not executed.

1. iterates in series or in parallel over the assets/controlled-vocabularies/\* folders,
   and for each of them:

   1. Installs the CLI tool in the CI environment.
   1. If the required files are present,
      it generates the corresponding CSV file
      (e.g., asset_name.csv) using the datapackage.yaml as input
   1. Validates the generated CSV file against the datapackage.yaml file.
   1. Creates a PR against the #asset branch with the generated CSV file,
      if it does not exist already.
      If the PR already exists, it is updated with the new CSV file.
   1. When the PR is merged, the generated CSV file is committed to the #asset branch
      and no further workflows are triggered by this CI.
   1. Repository owners must ensure that enabling such workflow does not create an infinite loop of commits and PRs
      in their repository.

To test the above workflow:

- [x] a separate `#asset` branch has been created in this repository
- [x] a separate job (e.g., ci-pre-tabular) is created to generate the datapackage.yaml file and commit it to the #asset branch

## Consequences

- Users can reuse the Github workflow defined in this repository, or create their own workflow based on it.
- The CLI tool is published as a Linux x86_64 binary as a github artifact, which simplifies the installation in the CI environment.
- Repository owners must ensure that enabling such workflow does not create an infinite loop of commits and PRs in their repository.
- Repository owners can, and must, audit the generated CSV files to ensure data quality and consistency before merging the PRs.
