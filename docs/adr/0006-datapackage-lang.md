# 5. Snapshot Testing

<!-- In vim, use !!date -I to get current date. -->

Date: 2026-02-26

## Status

<!-- Proposed, Accepted, Deprecated, Superseded, or Rejected -->

Accepted

## Context

RDF Vocabularies provide metadata that
can be either language tagged or not.
Moreover, it defines the overall languages
used in the vocabulary in the `dcterms:language` property.

Nonetheless, vocabularies may have language inconsistencies,
such as using both untagged and language-tagged literals
for the same property.

Example:

```text
dcterms:language ex:ITA .
ex:untagged skos:prefLabel "Concept 1" .
ex:multiple rdfs:label "Concept 1", "Concept 1"@it
```

To create a Frictionless Data Package,
we need to select a single value for each property.

## Decision

Use the following heuristics to select the appropriate language value for properties:

- [x] Only consider `it` and `en` language tags
- [x] Select the first value defined in `dcterms:language`
- [x] if a property does not have a value with the selected language tag, use the first untagged value

## Consequences

- This approach ensures that each property has a single, consistent language value, simplifying the creation of Frictionless Data Packages.
