# Manuale: Generazione di CSV da vocabolari RDF

Questo documento descrive il flusso operativo
per generare e pubblicare CSV a partire da
vocabolari controllati in formato RDF/SKOS,
usando gli strumenti della PoC.

Riferimenti: [README.csv.md](README.csv.md) e
[Glossario](glossario.md).

## Indice

- [Obiettivi](#obiettivi)
- [Flusso di lavoro](#flusso-di-lavoro)
- [Creare il frame e generare la proiezione](#creare-la-proiezione)
- [Requisiti del file di frame](#requisiti-del-frame)
- [Mappare i valori della proiezione](#mappare-i-valori-della-proiezione)
- [Generare lo stub del datapackage](#generare-lo-stub-del-datapackage)
- [Modificare il datapackage.yaml](#modificare-il-datapackageyaml)
- [Generare il CSV](#generare-il-csv)
- [Validare il CSV](#validare-il-csv)
- [Pubblicare il CSV](#pubblicare-il-csv)
- [Scelte di progettazione](#scelte-di-progettazione)
- [Frame CSV-specifico con SUFFIX](#frame-csv-specifico-con-suffix)
- [Troubleshooting](#troubleshooting)

## Obiettivi {#obiettivi}

Il processo descritto in questo documento
permette di:

1. Proiettare un vocabolario RDF/SKOS in una
   rappresentazione JSON-LD strutturata.
1. Generare un file CSV annotato semanticamente
   a partire dalla proiezione JSON-LD.
1. Metadatare il CSV tramite un file
   `datapackage.yaml` conforme a
   [Frictionless Data Package](https://datapackage.org/profiles/2.0/datapackage.json).
1. Validare la correttezza semantica del CSV
   prodotto rispetto al grafo RDF originale.

## Flusso di lavoro {#flusso-di-lavoro}

Il flusso è articolato in questi passi:

1. Creare il frame JSON-LD usando la UI
   dello Schema Editor.
1. Generare la proiezione JSON-LD dei dati
   tramite CLI.
1. Generare lo stub del `datapackage.yaml`
   tramite CLI.
1. Modificare manualmente il
   `datapackage.yaml`.
1. Generare il CSV con il comando
   `csv create`.
1. Validare il CSV con il comando
   `csv validate`.
1. Pubblicare il CSV tramite PR nel repository.

```mermaid
flowchart TD
    Input[/"File sorgente: vocabolario.ttl + vocabolario.frame.yamlld"/]
    GenJsonLD["jsonld create: proietta il vocabolario RDF in JSON-LD strutturato"]
    Projection[/"File generato: proiezione.data.yaml"/]
    GenDatapackage["datapackage create: genera lo stub dei metadati dal grafo RDF"]
    Stub[/"File generato: datapackage.yaml con metadati e schema delle colonne"/]
    ManualEdit["Modifica manuale: completa dialect, tipi di colonna e schema.fields"]
    GenCSV["csv create: serializza la proiezione JSON-LD in CSV"]
    CSV[/"File generato: vocabolario.csv"/]
    Validate["csv validate: verifica che il CSV sia un sottoinsieme semantico del grafo RDF"]
    Publish["Pubblicazione: revisione e approvazione della PR nel repository"]

    Input --> GenJsonLD
    GenJsonLD --> Projection
    Projection --> GenDatapackage
    GenDatapackage --> Stub
    Stub --> ManualEdit
    ManualEdit --> GenCSV
    GenCSV --> CSV
    CSV --> Validate
    Validate --> Publish
```

## Creare il frame e generare la proiezione {#creare-la-proiezione}

Lo Schema Editor fornisce un supporto visuale
alla definizione del frame JSON-LD.
Tramite l'RDF Helper, è possibile accedere
all'interfaccia di framing, basata sul
JSON-LD Playground del W3C.

1. Aprire il vocabolario nello Schema Editor.
1. Accedere alla UI di framing tramite
   l'RDF Helper.
1. Modificare il frame nella UI fino a
   ottenere la proiezione JSON-LD desiderata.
   La UI inserisce automaticamente un
   `@context` e un frame di default
   che dovrà essere adattato alle necessità
   di proiezione.
1. Salvare il frame nella cartella del
   vocabolario come
   `${vocabulary_name}.frame.yamlld`.

Il frame deve includere - tramite appositi commenti - documentazione,
sulle scelte di proiezione e sui campi generati.

Una volta definito il frame, generare la
proiezione JSON-LD con il comando `jsonld create`:

```bash
schema_gov_it_tools.bin jsonld create \
  --ttl agente_causale.ttl \
  --frame agente_causale.frame.yamlld \
  --vocabulary-uri self \
  --output agente_causale.data.yaml \
  --force
```

Il valore `self` indica alla CLI di rilevare automaticamente
l'URI del vocabolario cercando il solo `skos:ConceptScheme`
presente nel file `.ttl`. Il flag `--force` sovrascrive
il file di output se già esistente (necessario per le
rigenerazioni successive).

Per escludere i campi non mappati nel
`@context` (vedi
[Filtro dei campi non mappati](#filtro-dei-campi-non-mappati)):

```bash
schema_gov_it_tools.bin jsonld create \
  --ttl agente_causale.ttl \
  --frame agente_causale.frame.yamlld \
  --vocabulary-uri self \
  --output agente_causale.data.yaml \
  --force \
  --frame-only
```

## Requisiti del file di frame {#requisiti-del-frame}

Il file di frame (`*.frame.yamlld`) è validato
automaticamente da tutti i comandi CLI che
accettano il parametro `--frame`.
La struttura richiesta è definita nello schema
`tools/data/frame.schema.yaml`.

### Struttura obbligatoria del `@context`

Il `@context` deve essere un dizionario:
i contesti remoti (stringa URI) non sono supportati.

Il `@context` deve contenere obbligatoriamente
i seguenti campi:

| Campo   | Valore richiesto | Descrizione                               |
| ------- | ---------------- | ----------------------------------------- |
| `uri`   | `"@id"`          | URI del concetto (identificatore JSON-LD) |
| `label` | qualsiasi        | Etichetta principale del concetto         |

Il campo `uri` identifica univocamente ogni
concetto nella proiezione e diventa una colonna
nel CSV risultante.

Esempio minimale valido:

```yaml
"@context":
  uri: "@id"
  label:
    "@id": skos:prefLabel
    "@language": it
"@type": skos:Concept
uri: {}
label: {}
```

Frame non valido — campo `uri` mancante:

```yaml
"@context":
  label:
    "@id": skos:prefLabel
    "@language": it
```

```
✗ Invalid frame: 'uri' is a required property
```

### `@type` obbligatorio e singolo

Il frame deve specificare esattamente un tipo RDF
con il campo `@type`. Una lista con più valori
non è ammessa.

```yaml
# Valido: valore singolo
"@type": skos:Concept

# Valido: lista con un solo elemento
"@type":
  - skos:Concept

# Non valido: lista con più valori
"@type":
  - skos:Concept
  - owl:Thing
```

```
✗ Invalid frame: Frame must specify a single @type, found list: ['skos:Concept', 'owl:Thing']
```

### Campi gerarchici: `parent` e `vocab`

I campi `parent` e `vocab`, se presenti nel
`@context`, devono rispettare questi vincoli:

- `@container` obbligatorio: valore `"@set"` o
  `"@list"`.
- `@type` non può essere `"@vocab"` o `"@id"`.
- Il `@context` annidato, se presente, deve
  mappare `uri: "@id"`.

Esempio valido:

```yaml
parent:
  "@id": skos:broader
  "@container": "@set"
  "@context":
    uri: "@id"
```

Frame non valido — `@container` mancante su `parent`:

```yaml
parent:
  "@id": skos:broader
```

```
✗ Invalid frame: '@container' is a required property
```

### Valori ammessi in modalità strict

Quando la CLI elabora il frame in modalità
strict (attivata automaticamente durante la
generazione e la validazione di CSV e API), i
campi con nome riservato devono mappare solo le
proprietà RDF elencate. La violazione produce
un errore con i valori ammessi.

| Campo    | Proprietà RDF ammesse                              |
| -------- | -------------------------------------------------- |
| `id`     | `skos:notation`, `dct:identifier`, `dc:identifier` |
| `label`  | `skos:prefLabel`, `rdfs:label`                     |
| `level`  | `clvapit:hasRankOrder`, `xkos:depth`               |
| `parent` | `skos:broader`                                     |
| `vocab`  | `skos:inScheme`                                    |

I campi aggiuntivi per label localizzate
(`label_it`, `label_en`, `label_de` ecc.) non
sono soggetti a questa restrizione.

Frame non valido — `label` mappato su `altLabel`:

```yaml
label:
  "@id": skos:altLabel
  "@language": it
```

```
✗ Invalid frame: Frame field 'label' must be one of ['http://www.w3.org/2004/02/skos/core#prefLabel', 'http://www.w3.org/2000/01/rdf-schema#label'], got http://www.w3.org/2004/02/skos/core#altLabel.
```

## Mappare i valori della proiezione {#mappare-i-valori-della-proiezione}

Ogni campo inserito nella proiezione deve essere
mappato nel `@context` del frame: ogni nome di campo
deve essere associato alla corrispondente proprietà
RDF.

La mappatura definisce come i valori della proiezione
vengono interpretati semanticamente. Senza una
mappatura esplicita, un campo non è riconducibile
a nessuna proprietà RDF e la proiezione non è
verificabile rispetto al vocabolario originale.

I nomi scelti nel `@context` diventano i nomi
delle colonne del CSV risultante: è quindi
importante sceglierli con cura e mantenerli stabili
nel tempo (vedi
[Nomi dei campi nella proiezione](#nomi-dei-campi-nella-proiezione)).

Per i campi con nome riservato (`id`, `label`,
`level`, `parent`, `vocab`) sono ammesse solo
specifiche proprietà RDF: vedi
[Valori ammessi in modalità strict](#valori-ammessi-in-modalità-strict).

## Generare lo stub del datapackage {#generare-lo-stub-del-datapackage}

La CLI genera uno stub del `datapackage.yaml`
a partire dal file RDF e dal file di framing.
Lo stub contiene i metadati estratti
automaticamente dal grafo RDF.

```bash
schema_gov_it_tools.bin datapackage create \
  --ttl agente_causale.ttl \
  --frame agente_causale.frame.yamlld \
  --vocabulary-uri self \
  --output datapackage.yaml
```

Come per `jsonld create`, il valore `self` rileva
automaticamente l'URI del vocabolario dal file `.ttl`
(vedi [Creare la proiezione](#creare-la-proiezione)).

Esempio di stub generato a partire dal
vocabolario `agente_causale`:

```yaml
$schema: >-
  https://datapackage.org/profiles/2.0/datapackage.json
id: >-
  https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale
name: agente_causale
title: >-
  Vocabolario Controllato sulla classificazione
  degli agenti causali adottata dall'INAIL
version: '0.5'
created: '2022-09-06T00:00:00Z'
description: >-
  Decodifica dell'agente, lavorazione, o esposizione
  che puo' essere causa o concausa di malattia
keywords:
- agente causale
- chemical product
- inail
- infortunio
- malattia professionale
- occupational accident
- occupational disease
- prodotto chimico
sources:
- path: >-
    https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale
resources:
- name: agente_causale
  type: table
  path: agente_causale.csv
  format: csv
  encoding: utf-8
  mediatype: text/csv
  schema:
    x-jsonld-context: ...
    fields:
    - name: uri
      type: string
    - name: id
      type: string
    - name: label
      type: string
    - name: level
      type: integer
```

I metadati principali sono estratti dalle
seguenti proprietà RDF:

| Campo datapackage | Proprietà RDF                         |
| ----------------- | ------------------------------------- |
| `name`            | `ndc:keyConcept`                      |
| `title`           | `dct:title` o `skos:prefLabel`        |
| `id`              | URI della risorsa                     |
| `description`     | `dct:description` o `skos:definition` |
| `version`         | `owl:versionInfo`                     |
| `created`         | `dct:issued`                          |

## Modificare il datapackage.yaml {#modificare-il-datapackageyaml}

Lo stub generato automaticamente è un punto
di partenza: l'Erogatore deve revisionarlo
e integrarlo prima di procedere alla
generazione del CSV.

Operazioni tipiche di modifica manuale:

1. Verificare i metadati estratti
   (`title`, `description`, `keywords`, ecc.)
   e correggerli se necessario.
1. Definire il `dialect` CSV, specificando
   delimitatore, encoding, quoting, ecc.
1. Completare il campo `schema.fields`
   con i tipi corretti per ogni colonna.
1. Aggiungere o rimuovere campi dalla lista
   `resources[0].schema.fields` per controllare
   quali colonne saranno presenti nel CSV.
1. Verificare che il campo
   `x-jsonld-context` rispecchi il `@context`
   del file di framing.

Esempio di `schema` completo per una risorsa:

```yaml
resources:
- name: agente_causale
  type: table
  path: agente_causale.csv
  format: csv
  encoding: utf-8
  mediatype: text/csv
  dialect:
    delimiter: ","
    lineTerminator: "\n"
    quoteChar: "\""
    doubleQuote: true
    skipInitialSpace: true
    header: true
    caseSensitiveHeader: false
  schema:
    x-jsonld-context:
      "@base": >-
        https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/
      dct: http://purl.org/dc/terms/
      skos: http://www.w3.org/2004/02/skos/core#
      uri: "@id"
      id:
        "@id": skos:notation
      label:
        "@id": skos:prefLabel
        "@language": it
    fields:
    - name: uri
      type: string
    - name: id
      type: string
    - name: label
      type: string
    - name: level
      type: integer
```

I campi non inclusi in `schema.fields`
non saranno presenti nel CSV, anche se
sono nella proiezione JSON-LD. Questo
consente di escludere campi complessi
(oggetti o array) che non possono essere
rappresentati in modo coerente in CSV.

## Generare il CSV {#generare-il-csv}

Con il `datapackage.yaml` corretto, generare
il CSV:

```bash
schema_gov_it_tools.bin csv create \
  --jsonld agente_causale.data.yaml \
  --datapackage datapackage.yaml \
  --force
```

Il percorso di output viene letto dal campo
`resources[0].path` del `datapackage.yaml`.
Per specificarne uno diverso:

```bash
schema_gov_it_tools.bin csv create \
  --jsonld agente_causale.data.yaml \
  --datapackage datapackage.yaml \
  --output output/agente_causale.csv \
  --force
```

Di default, se il file di destinazione esiste, la CLI non lo sovrascrive.
Il flag `--force` sovrascrive il file esistente ed è richiesto
dal workflow CI per le rigenerazioni successive.

Esempio di CSV prodotto a partire dal
vocabolario `agente_causale`:

```
"uri","id","label","level"
"https://.../agente_causale/grande_gruppo/1","1","Agenti chimici inorganici","1"
"https://.../agente_causale/gruppo/1.1","1.1","Agenti chimici inorganici gruppo a","2"
"https://.../agente_causale/agente/11110101","11110101","Idrogeno","3"
```

Il valore della colonna `uri` dipende dalla
configurazione di `@base` nel frame: senza
`@base` viene serializzato l'URI completo,
con `@base` il suffisso relativo (vedi
[Uso di @base](#uso-di-base)).

## Validare il CSV {#validare-il-csv}

Il comando `csv validate` verifica che il CSV
prodotto sia un sottoinsieme semanticamente
corretto del grafo RDF originale:

```bash
schema_gov_it_tools.bin csv validate \
  --ttl agente_causale.ttl \
  --datapackage datapackage.yaml
```

Il parametro `--vocabulary-uri` è opzionale.
Se omesso, il comando individua automaticamente
l'URI del vocabolario cercando il solo `skos:ConceptScheme`
presente nel file `.ttl`. Questa è la modalità
raccomandata ed è quella usata dal workflow CI.

Se specificato, il valore deve corrispondere esattamente
al campo `id` del `datapackage.yaml`; in caso contrario
la validazione termina con errore. Il valore speciale `self`
(supportato da `jsonld create`) **non** è accettato da
`csv validate` e verrebbe confrontato letteralmente.

```bash
# URI esplicito — deve corrispondere esattamente a datapackage#/id
schema_gov_it_tools.bin csv validate \
  --ttl agente_causale.ttl \
  --datapackage datapackage.yaml \
  --vocabulary-uri https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale
```

Il processo di validazione:

1. Legge il CSV usando il `dialect`
   definito nel `datapackage.yaml`.
1. Converte il CSV in JSON-LD usando
   l'`x-jsonld-context` del datapackage.
1. Converte il JSON-LD in RDF.
1. Verifica che l'RDF risultante sia
   un sottoinsieme del vocabolario originale.

Per validare solo la struttura del datapackage
senza il CSV:

```bash
schema_gov_it_tools.bin datapackage validate \
  --datapackage datapackage.yaml
```

## Pubblicare il CSV {#pubblicare-il-csv}

Il repository include il workflow CI
[`ci-tabular.yml`](.github/workflows/ci-tabular.yml)
che automatizza la generazione e la validazione
dei CSV.

### Trigger del workflow

Il workflow si attiva su:

- `push` o `pull_request` verso il branch `assets`
  con modifiche in `assets/controlled-vocabularies/**`;
- avvio manuale (`workflow_dispatch`);
- chiamata da un altro workflow (`workflow_call`).

### Logica di rilevamento delle modifiche

Per ogni cartella asset il workflow determina
cosa rigenerare in base ai file cambiati:

| File cambiato | Azione |
|---|---|
| `.ttl` o `.frame.yamlld` | `jsonld create` + `csv create` |
| `datapackage.yaml` o `.data.yaml` | solo `csv create` |
| Nulla di rilevante | asset saltato |
| `workflow_dispatch` | tutto ricalcolato |

Le directory con più di un file `.ttl` vengono
saltate con un avviso. L'asset
`theme-subtheme-mapping` è esplicitamente
escluso dalla generazione.

### Comandi eseguiti dal workflow

Per ogni asset che richiede rigenerazione,
il workflow esegue in sequenza:

```bash
# 1. Genera la proiezione JSON-LD (se .ttl o .frame.yamlld cambiati)
schema_gov_it_tools.bin jsonld create \
  --ttl "${ASSET_NAME}.ttl" \
  --frame "${ASSET_NAME}.frame.yamlld" \
  --vocabulary-uri self \
  --output "${ASSET_NAME}.data.yaml" \
  --force

# 2. Genera il CSV
schema_gov_it_tools.bin csv create \
  --jsonld "${ASSET_NAME}.data.yaml" \
  --datapackage datapackage.yaml \
  --force

# 3. Valida il CSV
schema_gov_it_tools.bin csv validate \
  --ttl "${ASSET_NAME}.ttl" \
  --datapackage datapackage.yaml
```

### Apertura della PR

Se la validazione va a buon fine, il workflow
apre (o aggiorna) automaticamente una PR con:

- branch: `build/csv-generation<path-asset>`
- commit message: `build: CSV regenerate assets for <path> [skip ci]`
  (il `[skip ci]` previene loop infiniti)
- label: `automated, csv-generation`

La PR viene aperta verso il branch che ha
triggerato il workflow.

L'Erogatore deve:

1. Revisionare il CSV generato e validato.
1. Verificare che il CSV rappresenti
   correttamente il vocabolario RDF originale.
1. Approvare la PR generata dal workflow
   per pubblicare il CSV.

## Scelte di progettazione {#scelte-di-progettazione}

### Uso di `@base` {#uso-di-base}

La presenza di `@base` nel `@context` del
frame determina se gli URI dei concetti
vengono serializzati come URI completi o
come identificatori relativi (con il prefisso
rimosso).

Con `@base` impostato:

```yaml
"@context":
  "@base": >-
    https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/
  uri: "@id"
```

Gli URI vengono ridotti al suffisso relativo.
Ad esempio, il concetto
`agente/11110101` nel campo `uri` rappresenta:

```
https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/agente/11110101
```

Senza `@base` (o con `"@base": null`):

```yaml
"@context":
  "@base": null
  uri: "@id"
```

Gli URI vengono serializzati per intero.

Scegliere `@base` in base alle esigenze
dei Fruitori: gli URI completi sono più
portabili, i valori relativi sono più
leggibili e compatti.

### Uso di `parent` e `vocab` {#uso-di-parent-e-vocab}

Il campo `parent` mappa `skos:broader` e
permette di rappresentare le gerarchie del
vocabolario. Deve essere configurato come
array (`@container: @set`) per supportare
concetti con più genitori.

Esempio dal frame di `agente_causale`:

```yaml
parent:
  "@id": skos:broader
  "@container": "@set"
  "@context":
    uri: "@id"
    id:
      "@id": skos:notation
```

Il campo `vocab` mappa `skos:inScheme` e
identifica il vocabolario di appartenenza.
Serve anche come criterio di filtro nel
frame per limitare la proiezione ai soli
concetti del vocabolario indicato:

```yaml
vocab:
  "@id": skos:inScheme
  "@container": "@set"
  "@context":
    uri: "@id"

# Nel corpo del frame:
vocab:
- uri: >-
    https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale
  "@explicit": true
  "@embed": "@never"
```

In questo modo la proiezione include solo
i concetti esplicitamente appartenenti al
vocabolario indicato in `vocab`.

### Nomi dei campi nella proiezione {#nomi-dei-campi-nella-proiezione}

I nomi dei campi definiti nel `@context`
diventano i nomi delle colonne del CSV.
La scelta dei nomi è a discrezione
dell'Erogatore, ma deve rispettare
i seguenti vincoli:

- I nomi devono essere validi come chiavi JSON
  e come intestazioni CSV.
- I nomi devono essere stabili: una modifica
  rompe la compatibilità con i Fruitori
  esistenti.
- Se si usa `@base`, i campi che contengono
  URI (come `uri`, `parent`, `vocab`) avranno
  valori relativi; documentarlo nel
  `datapackage.yaml`.

Per le label localizzate, una convenzione
comune è usare il suffisso della lingua per i
campi aggiuntivi: `label_en`, `label_de`, ecc.
Il campo `label` resta obbligatorio e deve
corrispondere alla lingua principale del vocabolario.

Esempio dal frame di `agente_causale`:

```yaml
"@context":
  # "@base" con URI del vocabolario rende i valori
  # di uri, parent e vocab relativi a questo prefisso.
  "@base": >-
    https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/agente_causale/
  uri: "@id"
  id:
    "@id": skos:notation
  label:
    "@id": skos:prefLabel
    "@language": it
  parent:
    "@id": skos:broader
    "@container": "@set"
    "@context":
      uri: "@id"
  vocab:
    "@id": skos:inScheme
    "@container": "@set"
    "@context":
      uri: "@id"
  level:
    "@id": clvapit:hasRankOrder
    "@type": xsd:int
```

Per vocabolari con label in più lingue, aggiungere
un campo per ciascuna lingua aggiuntiva accanto
al campo `label` obbligatorio:

```yaml
  label:
    "@id": skos:prefLabel
    "@language": it
  label_en:
    "@id": skos:prefLabel
    "@language": en
  label_de:
    "@id": skos:prefLabel
    "@language": de
```

I campi con valori complessi come `parent`
e `vocab` (array di oggetti) vengono
serializzati in CSV come stringhe JSON.
Se non sono utili nel CSV, rimuoverli da
`schema.fields` nel `datapackage.yaml`
senza modificare il frame.

### Filtro dei campi non mappati {#filtro-dei-campi-non-mappati}

Il framing JSON-LD può includere nella
proiezione campi che fanno riferimento alla
stessa proprietà RDF di un campo mappato,
anche se non definiti esplicitamente nel
`@context`.

Ad esempio, se `skos:notation` è mappata
al campo `id` con un tipo specifico
(`euvoc:ISO_639_1`), la notazione con un
altro tipo (`euvoc:ISO_639_3`) potrebbe
comparire nella proiezione come
`skos:notation`.

Per escludere questi campi, usare
`--frame-only` nel comando `jsonld create`.

### Frame CSV-specifico con SUFFIX {#frame-csv-specifico-con-suffix}

Il workflow CI supporta una variabile `SUFFIX`
che consente di usare frame e proiezioni distinti
per la distribuzione CSV rispetto a quelli usati
per l'APIStore.

Con `SUFFIX: ''` (default), il workflow usa gli
stessi file per CSV e API:

```mermaid
flowchart LR
    A["vocabolario.frame.yamlld"] --> B["vocabolario.data.yaml"] --> C["CSV"]
```

Con `SUFFIX: '-csv'`, il workflow cerca file
dedicati per il CSV:

```mermaid
flowchart LR
    A["vocabolario-csv.frame.yamlld"] --> B["vocabolario-csv.data.yaml"] --> C["CSV"]
```

Usare un frame CSV-specifico è utile quando il
frame API include campi ad albero (`parent`,
`vocab`, `broader`) che nel CSV produrrebbero
stringhe JSON non utilizzabili dai consumatori.

#### Campi da escludere nel frame CSV-specifico

I campi da escludere sono quelli che nel frame API
mappano proprietà RDF su **array di oggetti annidati**
(usando `@container: "@set"`). Se inclusi nel CSV,
vengono serializzati come stringhe JSON.

| Campo tipico | Proprietà RDF | Effetto nel CSV |
|---|---|---|
| `parent` / `broader` | `skos:broader` | `"[{'id': '001', 'uri': '...'}]"` |
| `vocab` / `scheme` | `skos:inScheme` | `"[{'uri': '...'}]"` |

Il campo `scheme` può essere mantenuto nel
`@context` e nel corpo del frame: serve a
selezionare solo i concetti del vocabolario
corrente durante il framing. Non compare nel
CSV perché assente da `schema.fields` nel
`datapackage.yaml`.

#### Esempio: subject-disciplines-csv.frame.yamlld

```yaml
"@type": "skos:Concept"
"@explicit": true
"@embed": "@never"
"@omitDefault": true
"@requireAll": true

"@context":
  skos: "http://www.w3.org/2004/02/skos/core#"
  clvapit: "https://w3id.org/italia/onto/CLV/"
  uri: "@id"
  id: skos:notation
  label:
    "@id": skos:prefLabel
    "@language": it
  definition:
    "@id": skos:definition
    "@language": it
  level:
    "@id": clvapit:hasRankOrder
  scheme:
    "@id": skos:inScheme
    "@container": "@set"
    "@context":
      uri: "@id"

# Seleziona solo i concetti di questo vocabolario.
# Non incluso in schema.fields → non compare nel CSV.
scheme:
  - uri: "https://w3id.org/italia/controlled-vocabulary/classifications-for-culture/subject-disciplines"
    "@explicit": true
    "@embed": "@never"

uri: {}
id: {}
label: {}
definition:
  "@default": "@null"
level: {}
```

#### Compatibilità con datapackage.yaml

Il `datapackage.yaml` è condiviso tra il flusso
con e senza SUFFIX. I campi in `schema.fields`
devono essere presenti anche nel frame CSV-specifico.
I campi assenti dal frame CSV (es. `broader`) devono
essere esclusi da `schema.fields`.

#### Eseguire il flusso manualmente con SUFFIX

```bash
schema_gov_it_tools.bin jsonld create \
  --ttl subject-disciplines.ttl \
  --frame subject-disciplines-csv.frame.yamlld \
  --vocabulary-uri self \
  --output subject-disciplines-csv.data.yaml \
  --force
```

```bash
schema_gov_it_tools.bin csv create \
  --jsonld subject-disciplines-csv.data.yaml \
  --datapackage datapackage.yaml \
  --force
```

```bash
schema_gov_it_tools.bin csv validate \
  --ttl subject-disciplines.ttl \
  --datapackage datapackage.yaml
```

Il CSV risultante con `SUFFIX: '-csv'` contiene
solo campi flat, senza `broader` o `scheme`:

```
"uri","id","label","definition","level"
"https://.../001","001","scienze matematiche","","1"
"https://.../001-001","001.001","logica matematica","...","2"
```

### Uso dello strumento di validazione {#uso-dello-strumento-di-validazione}

Il comando `csv validate` è lo strumento
principale per verificare la correttezza
semantica del CSV prodotto. Deve essere
eseguito prima di ogni pubblicazione.

Il comando `jsonld validate` verifica che
la proiezione JSON-LD sia un sottoinsieme
del grafo RDF originale; è utile per
diagnosticare problemi nel frame prima di
procedere alla generazione del CSV.

Il livello di log si configura con le opzioni
`-l` o `--log-level` a livello top-level,
prima del sottocomando. I valori supportati
sono: `critical`, `error`, `warning`,
`info`, `debug`.

```bash
schema_gov_it_tools.bin --log-level debug csv validate \
  --ttl agente_causale.ttl \
  --datapackage datapackage.yaml
```

I comandi restituiscono exit code `0`
in caso di successo e un codice non-zero
in caso di errore.

## Troubleshooting {#troubleshooting}

### Letterali non tipizzati mappati a campi interi

Il comando `csv validate` converte ogni riga del
CSV in triple RDF tramite l'`x-jsonld-context`.
Quando un campo è dichiarato di tipo `integer`
nel `datapackage.yaml`, il valore viene
serializzato come `xsd:integer`.

Se il grafo RDF originale contiene lo stesso
predicato con un letterale non tipizzato
(equivalente a `xsd:string`), le due triple
non coincidono e la validazione fallisce:

```
✗ CSV roundtrip validation failed: CSV-derived RDF graph contains N triples
  not present in original RDF graph.
```

Esempio: il TTL contiene

```turtle
agentcaus:11110101 clvapit:hasRankOrder "3" .
```

mentre il datapackage dichiara

```yaml
- name: level
  type: integer
x-jsonld-context:
  level:
    "@id": clvapit:hasRankOrder
    "@type": xsd:integer
```

Il CSV produce `clvapit:hasRankOrder "3"^^xsd:integer`,
che non corrisponde al letterale `"3"` (xsd:string)
presente nel TTL.

**Soluzione:** allineare il tipo del letterale nel
TTL sorgente oppure rimuovere `"@type": xsd:integer`
dal contesto e dichiarare il campo come `type: string`
nel datapackage.
