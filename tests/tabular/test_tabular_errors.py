from operator import itemgetter

import pytest

from tests.constants import TESTCASES
from tools.base import JsonLDFrame
from tools.tabular import Tabular

TESTCASE = [TESTCASES[0]]


@pytest.mark.parametrize(
    "data,frame",
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASE],
    ids=[x["name"] for x in TESTCASE],
)
def test_datapackage_setter_invalid(data: str, frame: JsonLDFrame):
    # Given a Tabular instance with valid data and frame ...
    tabular = Tabular(rdf_data=data, frame=frame)

    # When I try to set an invalid datapackage
    invalid_datapackage = {"invalid": "data"}
    # Then the setter fails.
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
    argvalues=[itemgetter("data", "frame")(x) for x in TESTCASE],
    ids=[x["name"] for x in TESTCASE],
)
def test_dataresource_setter_invalid(
    data: str, frame: JsonLDFrame, invalid_resource_path: dict
):
    # Given a Tabular instance with valid data and frame ...
    tabular = Tabular(rdf_data=data, frame=frame)

    error = invalid_resource_path.pop("resource_error")

    # When I try to set an invalid datapackage resource
    # Then the stub creation fails.
    with pytest.raises(ValueError, match=error):
        tabular.dataresource_stub(**invalid_resource_path)
