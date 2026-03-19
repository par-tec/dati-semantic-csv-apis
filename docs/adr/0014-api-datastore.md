# 14. API Datastore

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-03-17

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

Data API need to publish RDF vocabularies as APIs. To do this, they need to store the RDF data in a way that allows efficient querying and retrieval.

The datastore should be lightweight, and isolate each vocabulary.
Moreover it should support basic JSON operations (e.g., indexing JSON fields).

The Data API will be published in a single container, with multiple vocabularies
and should not rely on external services (e.g., a separate database container) to avoid complexity and deployment issues.

## Decision

- [x] We will use a relational database Sqlite to store the projected data.
- [x] Entries will be stored as JSON in a single column, with an index on the identifier field.
- [x] Searchable fields will be published as columns.
- [x] Each vocabulary will be stored in a separate table, with a shared `_metadata` table to store common information and routing keys.
- [x] The API will read from the Sqlite datafile in read-only mode to serve API requests.
- [x] The table is identified by the pair `(agencyId, keyConcept)`, which is unique across vocabularies and used for API routing.

The CLI:

- [x] can generate the datastore via the `openapi` command starting from a vocabulary and an OAS file.
- [ ] will accept the vocabulary in the `text/turtle` format and a JSON-LD frame.
- [ ] will accept the vocabulary in the `application/ld+json; profile="http://www.w3.org/ns/json-ld#framed"` format,
  which is already framed.
- [ ] will produce a sqlite datafile for each vocabulary.

The Data API:

- [ ] The API will open the sqlite datafile in read-only mode and use it to serve API requests.

## Consequences

- The datastore will be lightweight and easy to deploy, as it does not require a separate database service.
- No shared / external database is needed, which simplifies deployment and avoids potential issues with data consistency and access control.
