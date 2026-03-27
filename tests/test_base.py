"""Tests for tools.base module, specifically JsonLDFrame class."""

import contextlib
import logging

import pytest
import yaml

from tests.constants import TESTCASES, TESTDIR
from tools.base import JsonLDFrame

_TEST_BASE = yaml.safe_load(
    (TESTDIR / __file__).with_suffix(".yaml").read_text()
)
INVALID_FRAMES = _TEST_BASE["testcases"]
VALID_FRAMES = [tc for tc in TESTCASES if "invalid" not in tc]

log = logging.getLogger(__name__)


@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize(
    "testcase",
    VALID_FRAMES,
    ids=[tc["name"] for tc in VALID_FRAMES],
)
def test_jsonldframe(testcase: dict, strict):
    frame = JsonLDFrame(testcase["frame"])
    frame.validate(strict)


@pytest.mark.parametrize("strict", argvalues=[True, False])
@pytest.mark.parametrize(
    "testcase", INVALID_FRAMES, ids=[tc["id"] for tc in INVALID_FRAMES]
)
def test_invalid_jsonldframe(testcase: dict, strict):
    raises = not testcase.get("strict_only") or strict
    ctx = pytest.raises(ValueError) if raises else contextlib.nullcontext()
    with ctx:
        frame = JsonLDFrame(testcase["frame"])
        frame.validate(strict)
