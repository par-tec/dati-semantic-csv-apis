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
