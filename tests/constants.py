from pathlib import Path

import yaml

TESTDIR = Path(__file__).parent
DATADIR = TESTDIR / "data"
ASSETS = TESTDIR.parent / "assets" / "controlled-vocabularies"

TESTCASES_YAML = TESTDIR / "testcases.yaml"

TESTCASES = yaml.safe_load(TESTCASES_YAML.read_text())["testcases"]
