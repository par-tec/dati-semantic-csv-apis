# Schema - Vocabolari Controllati

[Glossario](glossario.md)

## Introduzione

Il progetto schema.gov.it (National Data Catalog for
Semantic Interoperability) è, insieme alla PDND (Piattaforma
Digitale Nazionale dei Dati), uno dei due cardini della
strategia per l'interoperabilità dell'Italia.

L'obiettivo di schema.gov.it è quello di semplificare la
creazione di servizi pubblici digitali ed API
interoperabili.
Questo avviene tramite la catalogazione e la
pubblicazione di ontologie, schemi dati e vocabolari
controllati (codelist, tassonomie) selezionati, insieme a
funzionalità di visualizzazione e ricerca.

In particolare,
i Vocabolari Controllati sono asset semantici contenenti
codelist e tassonomie utilizzate dai servizi pubblici
digitali.

NDC semplifica il riuso del patrimonio informativo nazionale
pubblicando i Vocabolari Controllati sia in formato RDF che
tramite API REST conformi al Modello di Interoperabilità.

Per rendere più accessibile l'uso delle risorse semantiche,
schema.gov.it mette a disposizione una nuova versione
delle API REST dei Vocabolari Controllati,
basata sui meccanismi di proiezione
descritti in [README.csv.md](README.csv.md).

## Obiettivo

Questo documento definisce le specifiche
per pubblicare i contenuti dei Vocabolari Controllati
tramite API REST conformi al Modello di Interoperabilità - in
quanto sistema più accessibile rispetto allo SparQL endpoint.

Inoltre definisce le modalità di integrazione
degli strumenti di supporto all'implementazione delle specifiche
(e.g., strumenti per la generazione delle proiezioni JSON a partire dai dati RDF)
all'interno dello Schema Editor
<https://github.com/teamdigitale/dati-semantic-schema-editor>.

## Descrizione generale

La versione delle API REST attualmente in produzione
<https://schema.gov.it/api/vocabularies>
(v0.0.1) pubblica la proiezione dei dati RDF che gli enti
hanno estratto in formato CSV.
Questa scelta aveva l'obiettivo di
semplificare la fruizione dei dati fornendo
un meccanismo simile a quello che gli enti già usavano.

La v0.0.1 è precedente al lavoro fatto sull'annotazione
degli schemi dati e sulla produzione delle API semantiche
fatto su:

- [Schema Editor](https://github.com/teamdigitale/dati-semantic-schema-editor);
- [REST API Linked Data Keyword](https://datatracker.ietf.org/doc/draft-polli-restapi-ld-keywords/);

Inoltre, l'estensione della platea degli erogatori e
l'arbitrarietà nella produzione dei CSV hanno reso diverse
API pubblicate non consistenti con il modello di
interoperabilità.

E' necessario quindi allineare il lavoro di pubblicazione
dei vocabolari a quello delle API semantiche disaccoppiando
la produzione delle API REST dalla produzione dei CSV.

Inoltre, se per gli enti sussiste la necessità di creare dei
CSV utilizzando campi e valori arbitrari, va individuato un
meccanismo ulteriore per proiettare il grafo RDF di un
vocabolario su un dataset lineare (e.g., codelist), più
usabile nel contesto semplice della produzione di servizi
pubblici digitali.

Le specifiche di metadatazione e di proiezione dei dati RDF
in formato JSON che supporteranno le nuove API REST dei
vocabolari controllati sono definite nel documento
[README.csv.md](README.csv.md).

## API Vocabolari

### API Esistenti

Le API REST attualmente in produzione (v0.0.1) sono
descritte nell'OAS disponibile all'URL
<https://schema.gov.it/api/openapi.yaml>

Queste erogano as-is il contenuto dei CSV pubblicati dagli
enti: se da un lato permettono quindi una rapida
pubblicazione dei dati, dall'altro non garantiscono la
coerenza con il Modello di Interoperabilità e non sfruttano
le annotazioni semantiche presenti nei vocabolari.

L'eterogeneità dei CSV pubblicati dagli enti, inoltre, rende
difficile l'uso delle API da parte degli utenti finali
poiché i nomi dei campi e i valori usati non sono uniformi
tra i vari vocabolari.

#### Breve descrizione

Le API REST attualmente in produzione (v0.0.1) seguono l'OAS
3.0 indicato sopra.

La loro alberatura è la seguente:

- /vocabularies: ritorna l'elenco dei vocabolari
    controllati disponibili. I nomi dei campi e i valori
    ritornati sono uniformi tra i vari vocabolari ma i
    valori nel campo "links" non rispettano le specifiche di
    Link Relation, né contengono le annotazioni semantiche.

    Esempio di risposta:

``` yaml
# GET /vocabularies

totalCount: 157
limit: 10
offset: 0
data:
  - title: "Classificazione delle tipologie di strutture ricettive"
    description: "Classificazione dei tipi di strutture ricettive ai sensi del codice del turismo (Decreto legislativo n°79 del 23 maggio 2011). La classificazione è allineata alla classificazione dei LodgingBusiness del vocabolario schema.org"
    agencyId: "agid"
    keyConcept: "accommodation-typology"
    links:
      - href: "https://www.schema.gov.it/api/vocabularies/agid/accommodation-typology"
        rel: "items"
        type: "GET"
  - title: "Tassonomia dei luoghi pubblici di interesse culturale"
    description: "Tassonomia dei luoghi pubblici di interesse culturale. La tassonomia è nata per supportare il lavoro di re-design dei siti web dei comuni. Ove possibile, la tassonomia è allineata a schema.org."
    agencyId: "m_bac"
    keyConcept: "cultural-interest-places"
    links:
      - href: "https://www.schema.gov.it/api/vocabularies/m_bac/cultural-interest-places"
        rel: "items"
        type: "GET"
```

Questo payload non è conforme alle specifiche di Link
Relation definite da IANA
(<https://www.iana.org/assignments/link-relations/link-relations.xhtml>):

- il campo `rel` non contiene una Link Relation valida,
    poiché `items` non è registrata;

- il campo `type` deve contenere un media type e non un
    metodo.

- /vocabularies/{agencyId}: 404 non è esposto, un
    vocabolario va sempre identificato tramite agencyId e
    vocabularyId

- /vocabularies/{agencyId}/{vocabularyId}: ritorna
    l'elenco paginato dei termini del vocabolario
    controllato specificato, che attualmente è una
    proiezione lineare dei dati RDF presenti nel CSV
    pubblicato dall'ente. I nomi dei campi e i valori
    ritornati dipendono dal CSV pubblicato dall'ente, senza
    nessuna garanzia di uniformità tra i vari vocabolari né
    di coerenza con il Modello di Interoperabilità.

    La lingua utilizza i codici del vocabolario
    <http://publications.europa.eu/resource/dataset/language>,
    ad esempio "ITA" per l'italiano anziché i language tag
    (e.g., `it`, `en`, ..) definiti all'interno dell'RDF e
    raccomandati dalle Linee Guida Agid: questa scelta crea
    un problema di interoperabilità poiché la localizzazione
    delle stringhe in RDF è basata sui language tag.

Esempio di risposta:

``` yaml
# GET /vocabularies/m_bac/cultural-interest-places

totalResults: 81
limit: 10
offset: 0
data:
  - Label_ITA_2_livello: "Castello"
    Definizione: ""
    Label_ITA_2_livello_alternativa_plurale: "Castelli"
    Label_ITA_2_livello_alternativa_2: ""
    Label_ITA_1_livello_alternativa_siti_web_1: "Rocca e castello"
    Label_ITA_1_livello_alternativa_siti_web_plurale: "Rocche e castelli"
    Codice_2_Livello: "A.1"
    id: "A.1"
    Codice_1_livello: "A"
    Label_ITA_1_livello: "Architettura militare e fortificata"
    Label_ITA_1_livello_alternativa_altri_sistemi: ""
  - Label_ITA_2_livello: "Fortezza"
    Definizione: ""
    Label_ITA_2_livello_alternativa_plurale: "Fortezze"
    Label_ITA_2_livello_alternativa_2: "Cassero"
    Label_ITA_1_livello_alternativa_siti_web_1: "Rocca e castello"
    Label_ITA_1_livello_alternativa_siti_web_plurale: "Rocche e castelli"
    Codice_2_Livello: "A.2"
    id: "A.2"
    Codice_1_livello: "A"
    Label_ITA_1_livello: "Architettura militare e fortificata"
    Label_ITA_1_livello_alternativa_altri_sistemi: ""
```

- <https://www.schema.gov.it/api/vocabularies/m_bac/cultural-interest-places/A.1>

Esempio di risposta:

``` yaml
# GET /vocabularies/m_bac/cultural-interest-places/A.1

Label_ITA_2_livello: "Castello"
Definizione: ""
Label_ITA_2_livello_alternativa_plurale: "Castelli"
Label_ITA_2_livello_alternativa_2: ""
Label_ITA_1_livello_alternativa_siti_web_1: "Rocca e castello"
Label_ITA_1_livello_alternativa_siti_web_plurale: "Rocche e castelli"
Codice_2_Livello: "A.1"
id: "A.1"
Codice_1_livello: "A"
Label_ITA_1_livello: "Architettura militare e fortificata"
Label_ITA_1_livello_alternativa_altri_sistemi: ""
```

#### Cosa migliorare

L'OAS delle API esposte è all'URL
<https://schema.gov.it/api/openapi.yaml>

Ogni singolo vocabolario dovrebbe avere un meccanismo di
metadatazione proprio, definito dall'Erogatore.

Lo schema dati può anche essere unico, con una mappatura tra
i campi personalizzata.

``` yaml
openapi: 3.0.1
...
paths:
  /vocabularies/{agencyId}/{vocabularyId}:
    get:
      summary: "Get vocabulary terms"
      parameters:
        - name: agencyId
          in: path
          required: true
          schema:
            type: string
        - name: vocabularyId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: "Vocabulary terms retrieved successfully"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VocabularyTerms'
```

#### Generazione indipendente dai CSV

Nella v1 delle API, i dati non saranno più presi dai CSV
esistenti, ma verranno generati tramite un descrittore
apposito dei nuovi file (e.g., usando JSON-LD Framing).
Questo per
disaccoppiare la distribuzione dei dati presenti nelle API
da quella dei CSV: questo per non impattare sugli utenti che
utilizzano i dati attualmente presenti nei CSV e che
verrebbero impattati da eventuali modifiche.

Quando un erogatore vuole pubblicare l'API REST di un
vocabolario controllato, dovrà produrre un file di
descrizione del mapping tra RDF e contenuto delle API.
Questo descritore verrà usato per generare la proiezione
JSON da esporre nell'API REST.

Il formato di questo file di descrizione del mapping verrà
definito durante la fase di progettazione della v1 delle API
REST.

### API v1

#### Pubblicazione delle API REST v1

1. Analogamente al modello di erogazione attuale, le API
    vengono rese disponibili da un URL centralizzato
    <https://schema.gov.it/api/vocabularies/v1/> che funge
    da catalogo e restituisce un linkset RFC 9727 con le
    distribuzioni API dei vocabolari controllati.

2. L'OAS v1 di riferimento è mantenuto in
    `apiv1/openapi.yaml` ed è basato sulla semantica dei
    vocabolari RDF, disaccoppiando il contenuto esposto
    dalle eventuali proiezioni CSV legacy. che ritorna
    l'elenco di tutti gli endpoint. L'OAS è in linea, ma non
    identico, a quello attuale.

3. L'endpoint `/vocabularies` ritorna un JSON
    machine-readable, con i metadati delle API (href,
    service-desc, version, hreflang, author, description) e
    supporta:

    - paginazione;
    - filtri testuali;
    - filtri per metadata.

4. Lo schema dati presenta una serie di annotazioni
    semantiche che collegano i campi JSON alle proprietà RDF
    del vocabolario controllato.

5. Il campo "predecessor-version" referenzia la versione
    precedente dell'API, facilitando la migrazione degli
    utenti.

``` yaml
# Il risultato è di tipo application/linkset+json:
#   NB: la specifica RFC9727 definisce il formato linkset
#       come un oggetto JSON con la sola proprietà "linkset".
linkset:
-
  # RFC9727 api-catalog indica l'URL del catalogo API
  api-catalog: https://schema.gov.it/api/vocabularies/v1/
  anchor: https://schema.gov.it/api/vocabularies/v1/
  # ... pagination properties  either limit/offset/cursor (non
  #     standard but backward compatible), or prev/next link rel ...
  item:  # RFC6573 indica una serie di elementi contenuti nell'anchor.
  - # Campi definiti in RFC8288 Web Linking
    href: http://api.example.com/foo/v1  # RFC8288
    title: My Foo API
    hreflang: [it, en, de]
    service-desc:  # RFC8631
    - href: http://api.example.com/foo/v1/openapi.yaml
      type: application/openapi+yaml
    predecessor-version: # RFC5829
    - href: http://api.example.com/foo/v0 # RFC8288
    # Campi custom.
    description: "Extracted from vocabulary XYZ"
```

1. <http://purl.org/linked-data/xkos#supersedes> tracks the
    previous version of the vocabulary.

2. L'URL attuale <https://schema.gov.it/api/vocabularies/>
    verrà rediretto sulla versione delle API v0 fino a
    quando la v0 verrà dismessa.

3. Conformemente alle Linee Guida per le API REST del
    Modello di Interoperabilità, l'URL delle API REST
    conterrà la versione dell'API, ad esempio:

    - l'indirizzo con l'elenco dei vocabolari sarà
        <https://schema.gov.it/api/vocabularies/v1>;
    - l'indirizzo di un vocabolario specifico sarà
        <https://schema.gov.it/api/vocabularies/v1/%7BagencyId%7D/%7BvocabularyId%7D>.

4. La precedente versione delle API REST (v0.0.1)
    continuerà ad essere erogata per un periodo di tempo
    concordato con gli erogatori all'URL
    <https://schema.gov.it/api/vocabularies/v0/> per
    permettere la migrazione degli utenti verso la nuova
    versione.

5. L'API REST v1 utilizza i meccanismi di paging descritti
    nelle Linee Guida per le API REST del Modello di
    Interoperabilità.

6. L'API REST v1 permette l'accesso puntuale alle risorse
    del vocabolario.

``` mermaid
---
config:
  layout: elk
---
graph LR
   u((d3f:User))

   subgraph v1["API REST v1"]
   v1-api1[["/vocabularies/v1/agencyId1/vocabularyId1"]]
   v1-api2[["/vocabularies/v1/agencyId2/vocabularyId2"]]
   v1-api-catalog[["/vocabularies/v1/"]]
   v1-api-catalog --> |references| v1-api1 & v1-api2
   end

   subgraph v0["API REST v0"]
   v0-api1[["/vocabularies/agencyId1/vocabularyId1"]]
   v0-api2[["/vocabularies/agencyId2/vocabularyId2"]]
   v0-api-catalog[["/vocabularies/"]] --> |references| v0-api1 & v0-api2
   end

   u --> |d3f:ResourceAccess| v1-api-catalog
   u -.-> |old flows| v0-api-catalog

   v1-api-catalog --> |references| v0-api1 & v0-api2
```

#### Requisiti opzionali

1. Localizzazione: le API REST v1 supporteranno la
    localizzazione dei risultati laddove fornita nei
    vocabolari controllati. La lingua della risposta verrà
    selezionata tramite il query parameter `lang` e/o
    tramite l'header HTTP `Accept-Language`. Verrà stabilita
    una lingua di default.

#### Metadatazione semantica

1. Le API REST v1 pubblicano la specifica OAS all'indirizzo
    <https://schema.gov.it/api/vocabularies/v1/%7BagencyId%7D/%7BvocabularyId%7D/openapi.yaml>

2. Nella v1, la struttura dell'OAS sarà simile a quella
    attuale per facilitare la migrazione degli utenti, e
    seguirà una struttura lineare. Una ulteriore evoluzione
    delle API REST potrà prevedere una struttura più
    aderente al grafo RDF del vocabolario controllato.

3. L'OAS contiene le annotazioni semantiche che collegano i
    campi delle proiezioni JSON alle proprietà RDF del
    vocabolario controllato. Il contenuto delle annotazioni
    semantiche viene definito dall'Erogatore ed è contenuto
    nel file di descrizione del mapping. L'OAS viene
    generato automaticamente a partire dal file di
    descrizione del mapping.

4. I vocabolario possono utilizzare riferimenti semantici
    contenuti o meno in schema.gov.it. Ad esempio, alcuni
    vocabolari utilizzano SKOS o DCAT.

    ``` turtle
     @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
     @prefix dcat: <http://www.w3.org/ns/dcat#> .
     @base   <https://w3id.org/italia> .

     <italia/social-security/controlled-vocabulary/CUStatement/codice_titolo_erogazione_tfr/A>
         rdf:type            skos:Concept;

         # DCAT modeling.
         rdfs:label          "se si tratta di anticipazione;"@it;
         dcterms:identifier  "A";

         # Skos modeling.
         skos:inScheme       <italia/social-security/controlled-vocabulary/CUStatement/codice_titolo_erogazione_tfr>;
         skos:notation       "A";
         skos:prefLabel      "se si tratta di anticipazione;"@it .
    ```

5. Una guida con degli esempi illustrerà vari modi per
    mostrare le mappature tra i campi RDF e JSON, per
    permettere agli erogatori di scegliere la
    rappresentazione più adatta ai loro vocabolari
    controllati. Questo semplificherà anche l'erogazione di
    API basate su vocabolari stratificati.

#### Generazione delle proiezioni JSON e integrazione delle annotazioni semantiche nelle API

1. Il documento [README.csv.md](README.csv.md) descrive il
    processo di proiezione dei dati RDF in formato JSON per
    le API REST v1 in modo da validare che il processo di
    proiezione sia invertibile, ossia che sia possibile
    ricostruire il grafo RDF originale a partire dal JSON e
    dall'annotazione semantica..

2. Verranno forniti dei tool per facilitare la generazione
    delle proiezioni JSON a partire dai dati RDF e per
    l'integrazione delle annotazioni semantiche nelle API
    REST v1. I tool saranno open source in conformità al
    Codice per l'Amministrazione Digitale.

``` mermaid
graph TD

   subgraph E["Erogatore dei Vocabolari Controllati"]
   ttl[/RDF Vocabolario Controllato/]
   frame[/File di Descrizione del Mapping/]
   api-data-processor[[Tool di Generazione]]
   ttl & frame -->|used-by| api-data-processor
   -->|produces| api-content[/Contenuto API REST v1/] & api-spec[/OAS delle API REST v1/]


   subgraph git
   api-content & api-spec

   %% Componenti legacy che gli Erogatori
   %%   possono pubblicare ma che non saranno
   %%   usati dall'harvester.
   legacy-csv[/CSV legacy <br>Vocabolario Controllato/]
   end
   end

   subgraph H["NDC"]
   harvester[[Harvester delle API REST v1]]
   api-content & api-spec -->|used-by| harvester
   end
```

#### PoC di Funzionalità di autocompletamento dei dizionari

1. Verrà fornito un PoC di una API di autocompletamento che
    permetta di cercare i termini di un vocabolario
    controllato tramite una stringa di ricerca parziale.

2. Verrà fornita una PoC di una API che restituisce i
    vocabolari controllati in formato JSON Schema.

#### Limitazioni

1. Le API REST v1 continueranno a erogare solo proiezioni
    lineari dei vocabolari controllati (e.g., codelist). Non
    verranno erogate strutture ad albero o grafi. Queste
    potranno essere oggetto di future evoluzioni delle API
    REST.

2. La piattaforma non validerà nel merito il file di
    descrizione del mapping fornito dagli erogatori. La
    responsabilità della correttezza del file di descrizione
    del mapping rimane all'erogatore. Potrà essere validato
    il formato del file di mappatura (frame) e verificata la
    presenza dei campi obbligatori che ogni API REST v1 deve
    esporre.

3. Il calcolo del Semantic Score delle API dei vocabolari
    potrebbe non tenere conto dei riferimenti semantici
    generici e/o non presenti in schema.gov.it (e.g.,
    riferimenti a vocabolari esterni come schema.org, oppure
    SKOS).

4. I campi ritornati potranno essere limitati ai seguenti
    tipi: string, array, object. Questo perché i valori dei
    vocabolari controllati sono definiti tramite specifiche
    XSD che non sono sempre mappabili in tipi JSON più
    complessi (e.g., date, numeri, booleani). La
    deserializzazione dei campi è lasciata ai fruitori.

5. Gli strumenti forniti a supporto della generazione delle
    proiezioni JSON saranno basati su librerie open source
    che implementano le specifiche JSON-LD e RDF: eventuali
    limitazioni e/o bug di tali librerie si rifletteranno
    sugli strumenti stessi.

6. Quando viene pubblicata una nuova versione di un
    vocabolario controllato, l'API REST v1 erogherà la
    versione nuova del vocabolario controllato, e la vecchia
    versione non sarà più disponibile. La versione dell'API
    dei vocabolari controllati è indipendente dalla versione
    del vocabolario controllato erogato.

    Esempio:

    Il vocabolario controllato "ateco-2007" viene pubblicato
    a partire dai dati nella cartella
    `vocabularies/ISTAT/ateco-2007/latest/`. Quando l'ISTAT
    pubblica una nuova versione del vocabolario controllato
    "ateco-2007" (ad esempio,
    `vocabularies/ISTAT/ateco-2007/2025-01-01/`), con
    `latest/` che punta alla nuova versione, l'API REST v1
    erogherà la nuova versione del vocabolario controllato
    che sarà "ateco 2007 - revisione 2021".

7. TODO: un vocabolario può non avere skos:ConceptScheme ma
    solo dcatapit:Dataset
