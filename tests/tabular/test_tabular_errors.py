from operator import itemgetter

import pytest

from tests.constants import TESTCASES
from tools.base import JsonLDFrame
from tools.tabular import Tabular


@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES],
    ids=[x["name"] for x in TESTCASES],
)
def test_datapackage_setter_invalid(data: str, frame: JsonLDFrame):
    # Crea un'istanza di Tabular con dati di test
    tabular = Tabular(rdf_data=data, frame=frame)

    # Prova a impostare un datapackage invalido
    invalid_datapackage = {
        "invalid": "data"
    }  # Questo non passerà la validazione
    with pytest.raises(ValueError, match="Invalid datapackage"):
        tabular.datapackage = invalid_datapackage


@pytest.mark.parametrize(
    "invalid_resource_path",
    argvalues=[
        {
            "resource_name": "name",
            "resource_path": None,
            "resource_error": "resource_path is required",
        },
        {
            "resource_name": None,
            "resource_path": "file.csv",
            "resource_error": "resource_name is required",
        },
    ],
)
@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASES[:1]],
    ids=[x["name"] for x in TESTCASES[:1]],
)
def test_dataresource_setter_invalid(
    data: str, frame: JsonLDFrame, invalid_resource_path: dict
):
    # Crea un'istanza di Tabular con dati di test
    tabular = Tabular(rdf_data=data, frame=frame)

    error = invalid_resource_path.pop("resource_error")

    # Prova a impostare un datapackage invalido
    with pytest.raises(ValueError, match=error):
        tabular.dataresource_stub(**invalid_resource_path)
