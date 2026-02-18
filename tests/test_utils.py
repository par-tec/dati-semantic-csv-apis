from tools.utils import expand_context_to_absolute_uris


def test_expand_simple_context():
    """Test expanding a simple context with prefixes and @vocab."""
    context = {
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "@vocab": "https://w3id.org/italia/onto/CPV/",
        "p": "Person",
        "id": "skos:notation",
    }

    result = expand_context_to_absolute_uris(context)

    assert result["p"] == "https://w3id.org/italia/onto/CPV/Person"
    assert result["id"] == "http://www.w3.org/2004/02/skos/core#notation"
    # Ensure prefix declarations are not in output
    assert "skos" not in result
    assert "@vocab" not in result


def test_expand_complex_context():
    """Test expanding a complex context with nested definitions."""
    context = {
        "@vocab": "https://w3id.org/italia/work-accident/controlled-vocabulary/adm_serv/",
        "dct": "http://purl.org/dc/terms/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "xkos": "http://rdf-vocabulary.ddialliance.org/xkos#",
        "url": "@id",
        "id": {"@id": "skos:notation"},
        "label": {"@id": "skos:prefLabel", "@language": "it"},
        "parent": {"@id": "skos:broader", "@container": "@set"},
    }

    result = expand_context_to_absolute_uris(context)

    # Check that compact IRIs are expanded
    assert result["id"] == "http://www.w3.org/2004/02/skos/core#notation"
    assert result["label"] == "http://www.w3.org/2004/02/skos/core#prefLabel"
    assert result["parent"] == "http://www.w3.org/2004/02/skos/core#broader"

    # @id mappings should not appear in output
    assert "url" not in result

    # Prefix declarations should not appear
    assert "dct" not in result
    assert "skos" not in result
    assert "xkos" not in result


def test_expand_with_vocab_only():
    """Test expanding when only @vocab is defined."""
    context = {
        "@vocab": "https://example.org/vocab/",
        "name": "fullName",
        "age": "personAge",
    }

    result = expand_context_to_absolute_uris(context)

    assert result["name"] == "https://example.org/vocab/fullName"
    assert result["age"] == "https://example.org/vocab/personAge"
    assert "@vocab" not in result


def test_expand_with_base_uri():
    """Test expanding with @base defined."""
    context = {
        "@base": "https://example.org/base/",
        "@vocab": "https://example.org/vocab/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "concept": "Concept",
        "notation": "skos:notation",
    }

    result = expand_context_to_absolute_uris(context)

    assert result["concept"] == "https://example.org/vocab/Concept"
    assert result["notation"] == "http://www.w3.org/2004/02/skos/core#notation"
    assert "@base" not in result


def test_expand_empty_context():
    """Test expanding an empty context."""
    context = {}

    result = expand_context_to_absolute_uris(context)

    assert result == {}


def test_expand_only_prefixes():
    """Test that prefix declarations themselves are not included in output."""
    context = {
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dct": "http://purl.org/dc/terms/",
        "@vocab": "https://example.org/",
    }

    result = expand_context_to_absolute_uris(context)

    # Only keywords starting with @ should be filtered, and no actual properties defined
    assert result == {}
