from tools.harvest.catalog import Catalog


def test_catalog():
    catalog = Catalog("https://schema.gov.it/sparql")
    vocabularies = catalog.vocabularies()
    assert "@context" in vocabularies
    assert "@graph" in vocabularies


def test_catalog_items():
    catalog = Catalog("https://schema.gov.it/sparql")
    items = catalog.items()
    assert len(items) == 106
