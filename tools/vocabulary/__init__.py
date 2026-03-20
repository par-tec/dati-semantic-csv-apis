import json
import logging
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from rdflib import DCTERMS, OWL, SKOS, Graph, Namespace

# from rdflib.plugins.serializers.jsonld import from_rdf
from tools.base import (
    APPLICATION_LD_JSON,
    TEXT_TURTLE,
    JsonLD,
    JsonLDFrame,
    JsonLDFunction,
    JSONLDText,
    RDFText,
)
from tools.projector import framer

log = logging.getLogger(__name__)

NDC = Namespace("https://w3id.org/italia/onto/NDC/")


class UnsupportedVocabularyError(ValueError):
    """The RDF data does not contain a supported vocabulary,
    such as a ConceptScheme with NDC:keyConcept.
    """


class LangTag:
    pass


LANG_ANY = LangTag()
LANG_NONE = LangTag()


def _language_matches(obj, lang: str | LangTag):
    if lang is LANG_ANY:
        return True
    if lang is LANG_NONE:
        return not (hasattr(obj, "language") and obj.language)
    return hasattr(obj, "language") and obj.language == lang


class VocabularyMetadata(Graph):
    def language(self) -> str:
        language_uris = list(self.objects(self.identifier, DCTERMS.language))
        if not language_uris:
            raise ValueError(
                f"Vocabulary {self.identifier} is missing required DCTERMS:language"
            )

        # Infer language from URI, preferring Italian if both are present.
        if any(uri.lower().endswith(("/it", "/ita")) for uri in language_uris):
            return "it"
        if any(uri.lower().endswith(("/en", "/eng")) for uri in language_uris):
            return "en"
        raise NotImplementedError(
            f"Unsupported language '{language_uris}' for vocabulary {self.identifier}"
        )

    def get_first_value(self, predicates: list, lang: str | LangTag = LANG_ANY):
        for predicate in predicates:
            value = self.get_value(predicate, lang=lang)
            if value:
                return value
        return None

    def get_identifier(self, predicate, unique=True, required=True):
        values = {str(obj) for obj in self.objects(self.identifier, predicate)}
        if unique and len(values) > 1:
            raise ValueError(
                f"Expected exactly one value for {predicate}, found {len(values)}: {values}"
            )
        # If the identifier has a language-tagged literal,
        #  raise an error.
        if any(
            hasattr(obj, "language") and obj.language
            for obj in self.objects(self.identifier, predicate)
        ):
            raise ValueError(
                f"Expected a non-language-tagged literal for {predicate}, but found language-tagged literals: {values}"
            )
        if required and not values:
            raise ValueError(
                f"Expected a value for {predicate}, but found none"
            )
        return next(iter(values)) if values else None

    def get_value(self, predicate, lang: str | LangTag = LANG_ANY) -> Any:
        """
        Get the first value for a given predicate that matches the specified language.

        Args:
            predicate: The RDF predicate to query.
            lang: The language tag to match. Can be a string or a LangTag.

        Returns:
            The first matching value, or None if no match is found.

        """
        for obj in self.objects(self.identifier, predicate):
            if not _language_matches(obj, lang):
                continue
            return obj
        return None

    # Helper function to get all values as list
    def get_values(
        self, predicate, lang: str | LangTag = LANG_ANY
    ) -> None | list:
        values = []
        for obj in self.objects(self.identifier, predicate):
            if _language_matches(obj, lang):
                values.append(str(obj))
            else:
                log.info(
                    f"Skipping value '{obj}' for predicate '{predicate}' due to language mismatch (expected: {lang})"
                )
        return values if values else None

    @property
    def name(self) -> str:
        value = self.get_value(NDC.keyConcept, lang=LANG_NONE)
        if isinstance(value, str):
            # Note: Since rdflib.terms.Literal is a subclass of str,
            #   but yaml can't serialize it directly.
            #   We thus convert it to a plain string before returning.
            return str(value)
        raise ValueError(
            f"Vocabulary {self.identifier} is missing a string, non-language-tagged NDC:keyConcept"
        )

    @property
    def title(self) -> str:
        lang_tag: str | LangTag = self.language() or LANG_NONE
        for lang in {lang_tag, LANG_NONE}:
            value = self.get_first_value(
                [DCTERMS.title, SKOS.prefLabel], lang=lang
            )
            if isinstance(value, str):
                # Note: Since rdflib.terms.Literal is a subclass of str,
                #   but yaml can't serialize it directly.
                #   We thus convert it to a plain string before returning.
                return str(value)
        raise ValueError(
            f"Vocabulary {self.identifier} is missing required title (DCTERMS:title or SKOS:prefLabel)"
        )

    @property
    def version(self) -> str | None:
        version = self.get_value(OWL.versionInfo)
        return str(version) if version else None

    @property
    def contact_name(self) -> str | None:
        version = self.get_value("hasEmail")
        return str(version) if version else None

    @property
    def contact_email(self) -> str | None:
        hasEmail = NDC.hasEmail
        version = self.get_value(hasEmail)
        return str(version) if version else None

    @property
    def rights_holder(self) -> str | None:
        rights_holder = self.get_value(DCTERMS.rightsHolder)
        return str(rights_holder) if rights_holder else None

    @property
    def agency_id(self) -> str | None:
        """
        This property is used for backward-compatibility
        with the existing implementation of the API,
        and is derived from dcterms:rightsHolder.

        See https://github.com/teamdigitale/dati-semantic-backend/blob/9d3cb05a5fc3e41cb4a39e923a11f4312341d160/src/test/java/it/gov/innovazione/ndc/harvester/model/ControlledVocabularyModelTest.java#L232
        """
        agency_id = self.rights_holder
        return Path(agency_id).name.lower() if agency_id else None

    @property
    def description(self) -> str:
        description = self.get_first_value(
            [DCTERMS.description, SKOS.definition], lang=self.language()
        ) or self.get_first_value(
            [DCTERMS.description, SKOS.definition], lang=LANG_NONE
        )
        if description is None:
            return ""
        if isinstance(description, str):
            # Note: Since rdflib.terms.Literal is a subclass of str,
            #   but yaml can't serialize it directly.
            #   We thus convert it to a plain string before returning.
            return str(description)
        raise ValueError(
            f"Vocabulary {self.identifier} has a description that is not a string: {description}"
        )


class Vocabulary:
    """
    This class represents a vocabulary,
    that can be loaded, serialized, and projected
    in different formats.

    A vocabulary is defined by a graph.

    Functions supports both loading from a stream or a file.

    By default, uses Oxigraph.
    """

    def __init__(
        self,
        rdf_data: RDFText | JSONLDText | Path,
        format=TEXT_TURTLE,
    ) -> None:
        self.graph = Graph()
        ts: float = time.time()
        if isinstance(rdf_data, Path):
            self.graph.parse(rdf_data, format=format)
        elif isinstance(rdf_data, str):
            self.graph.parse(data=rdf_data, format=format)
        else:
            raise ValueError(
                f"Unsupported type for rdf_data: {type(rdf_data)}. Expected str or Path."
            )
        log.debug(
            f"Parsed {len(self.graph)} RDF triples in {time.time() - ts:.3f}s"
        )

        self._uri: str | None = None
        self._metadata = None
        self._jsonld: JsonLD | None = None

    def serialize(self, format=APPLICATION_LD_JSON) -> str:
        ts: float = time.time()
        serialized: str = self.graph.serialize(format=format)
        log.debug(f"Serialized RDF to {format} in {time.time() - ts:.3f}s")
        return serialized

    @property
    def json_ld(self) -> JsonLD:
        """
        Convert RDF data in Turtle format to JSON-LD.

        Args:
            rdf_data: RDF data in Turtle format
        Returns:
            JsonLD: JSON-LD representation of the RDF data
        """
        if self._jsonld is not None:
            return self._jsonld
        if self.graph:
            # data = from_rdf(self.graph, auto_compact=True) # .json_ld()
            data = json.loads(self.serialize(format=APPLICATION_LD_JSON))
            if isinstance(data, dict):
                if "@graph" not in data:
                    raise ValueError(
                        "Expected JSON-LD serialization to contain a top-level '@graph' key"
                    )
                return cast(JsonLD, data)
            if isinstance(data, list):
                return cast(JsonLD, {"@graph": data})
            raise ValueError(
                "Expected JSON-LD serialization to be a JSON object"
            )
        raise ValueError("No RDF graph loaded and no JSON-LD data available")

    @json_ld.setter
    def json_ld(self, value: JsonLD) -> None:
        self._jsonld = value

    def metadata(self) -> VocabularyMetadata:
        """
        Extract a subgraph representing a vocabulary (concept scheme) from the RDF graph.

        Args:
            uri: URI of the vocabulary (concept scheme) to extract
            key_concept: Optional URI of the key concept to filter by
        Returns:
            VocabularyMetadata: Metadata of the extracted vocabulary
        """
        query = """
                PREFIX NDC: <https://w3id.org/italia/onto/NDC/>
                PREFIX dcat: <http://www.w3.org/ns/dcat#>
                PREFIX vcard: <http://www.w3.org/2006/vcard/ns#>

                CONSTRUCT {
                    ?vocab ?p ?o .
                    ?vocab NDC:keyConcept ?keyConcept .
                    ?vocab dcat:contactPoint ?contactPoint .
                    ?contactPoint ?vcardProp ?vcardValue .
                }
                WHERE {
                    ?vocab NDC:keyConcept ?keyConcept ;
                           ?p ?o .

                    # Opzionale: include i dati vCard se presenti
                    OPTIONAL {
                        ?vocab dcat:contactPoint ?contactPoint .
                        ?contactPoint ?vcardProp ?vcardValue .
                        # Filtra solo le proprietà vCard rilevanti
                        FILTER(
                            ?vcardProp IN (
                                vcard:fn,
                                vcard:hasEmail,
                                vcard:hasTelephone,
                                vcard:hasURL,
                                rdf:type
                            )
                        )
                    }
                }
            """
        res = self.graph.query(query)
        _metadata: Graph = res.graph
        _metadata_uri = set(_metadata.subjects())
        do_i_have_just_one_vocab = len(_metadata_uri)
        if do_i_have_just_one_vocab != 1:
            raise UnsupportedVocabularyError(
                "Expected exactly one vocabulary in the RDF data",
                do_i_have_just_one_vocab,
            )
        _m2 = VocabularyMetadata(identifier=_metadata_uri.pop())
        for s, p, o in _metadata:
            _m2.add((s, p, o))
        return _m2

    def uri(self) -> str:
        """
        Get the URI of the vocabulary (concept scheme) represented by the RDF graph.

        Returns:
            str: URI of the vocabulary
        """
        if not self._uri:
            metadata = self.metadata()
            vocab_uri = next(iter(metadata.subjects()))
            self._uri = str(vocab_uri)
        return self._uri

    def project(
        self,
        frame: JsonLDFrame | dict,
        batch_size: int = 0,
        callbacks: Iterable[JsonLDFunction] = (),
    ) -> JsonLD:
        """
        Apply the frame to the RDF data and then project the result to only include fields in the frame context.

        Args:
            frame: JSON-LD frame specification
            batch_size: Number of records to process per batch. If 0, process all at once.
            callbacks: Optional list of callback functions to call after processing each batch.
        Returns:
            JsonLD: Projected JSON-LD document containing only fields in the frame context.
        """
        ld_doc: JsonLD = self.json_ld
        if isinstance(frame, dict):
            frame = JsonLDFrame(frame)
            frame.validate(strict=True)
        framed: JsonLD = framer(ld_doc, frame, batch_size)

        for callback in callbacks or []:
            log.debug(f"Applying callbacks to framed data: {callback.__name__}")
            #
            # XXX: This flexibility allows callbacks to modify the framed data in-place or return a new modified version,
            #   but might be too flexible. Consider only allowing stateless callbacks only.
            #
            result = callback(framed)
            if result is not None:
                framed = result
            log.info(f"Callback applied successfully: {callback.__name__}")
        return framed
