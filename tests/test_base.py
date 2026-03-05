"""Tests for tools.base module, specifically JsonLDFrame class."""

import logging

import pytest

from tests.constants import TESTCASES
from tools.base import JsonLDFrame

log = logging.getLogger(__name__)


@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("testcase", TESTCASES)
def test_jsonldframe(testcase: dict, strict):
    frame = JsonLDFrame(testcase["frame"])
    assert frame.validate(strict)
