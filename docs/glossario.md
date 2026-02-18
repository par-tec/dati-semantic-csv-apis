---
title: Glossario
description: Glossario dei termini e tecnologie chiave utilizzati nel progetto Dati Semantic CSV
---
## Glossario

### Tecnologie e Formati

- RDF (Resource Description Framework): Framework W3C per
    rappresentare informazioni sul web tramite grafi di
    triple soggetto-predicato-oggetto. Standard per il web
    semantico.

- TTL (Turtle): Formato testuale compatto per serializzare
    dati RDF. Più leggibile rispetto a RDF/XML.

- JSON-LD (JSON for Linking Data): Formato per
    rappresentare dati strutturati usando JSON con
    annotazioni semantiche tramite `@context`, `@id`,
    `@type`.

- YAML-LD: Variante di JSON-LD che utilizza la sintassi
    YAML invece di JSON, più leggibile per gli esseri umani.

- SKOS (Simple Knowledge Organization System): Vocabolario
    W3C per rappresentare thesauri, tassonomie, schemi di
    classificazione e vocabolari controllati in RDF.

- CSV (Comma-Separated Values): Formato tabulare per
    rappresentare dati in forma lineare, ampiamente usato
    per l'interscambio di dati.

### Concetti Chiave

- Vocabolario Controllato: Asset semantico contenente
    codelist, tassonomie o classificazioni utilizzate per
    standardizzare la terminologia nei servizi pubblici
    digitali.

- Proiezione/Framing: Processo di trasformazione di un
    grafo RDF in una rappresentazione lineare (CSV) o
    strutturata (JSON/YAML-LD) secondo uno schema definito.
    Il framing JSON-LD permette di specificare quali
    proprietà includere e come strutturare l'output.

- Flatten di gerarchie: Trasformazione di strutture
    gerarchiche (es. relazioni parent-child in SKOS) in
    formato tabulare mantenendo riferimenti espliciti.

- Frictionless Data: Insieme di specifiche per descrivere,
    validare e condividere dataset anche in formati
    tabulari.

- DataPackage: Specifica di metadatazione dei dataset,
    inclusi schema dei campi, tipi di dati, vincoli e
    relazioni.

## Riferimenti

- [RDF 1.1 Concepts and Abstract
    Syntax](https://www.w3.org/TR/rdf11-concepts/)

- [RDF 1.1 Turtle](https://www.w3.org/TR/turtle/)

- [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)

- [JSON-LD 1.1
    Framing](https://www.w3.org/TR/json-ld11-framing/)

- [SKOS Simple Knowledge Organization
    System](https://www.w3.org/TR/skos-reference/)

- [XKOS - Extended Knowledge Organization
    System](http://rdf-vocabulary.ddialliance.org/xkos.html)

- [Dublin Core Terms](http://purl.org/dc/terms/)

- [CLV-AP_IT - Core Location Vocabulary Italian
    Application Profile](https://w3id.org/italia/onto/CLV/)

- [RFC 8288 - Web
    Linking](https://datatracker.ietf.org/doc/html/rfc8288)

- [RFC 4180 - Common Format and MIME Type for CSV
    Files](https://datatracker.ietf.org/doc/html/rfc4180)

- [Frictionless Data](https://frictionlessdata.io/)

- [Rest API Linked Data Keyword](https://datatracker.ietf.org/doc/draft-polli-restapi-ld-keywords/)
