from pathlib import Path

import yaml

TESTDIR = Path(__file__).parent
DATADIR = TESTDIR / "data"
ASSETS = TESTDIR.parent / "assets" / "controlled-vocabularies"
SNAPSHOTS = DATADIR / "snapshots"
TESTCASES_YAML = TESTDIR / "testcases.yaml"


def _resolve_yaml_path(path_like: str) -> Path:
    """Resolve testcase YAML references from common test data locations."""
    candidate = Path(path_like)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    candidates = (
        TESTDIR / path_like,
        DATADIR / path_like,
        SNAPSHOTS / path_like,
        SNAPSHOTS / "base" / path_like,
    )
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Cannot resolve testcase payload path: {path_like}"
    )


def _normalize_testcases(testcases: list[dict]) -> list[dict]:
    """Load file-based expected payloads while keeping inline payloads unchanged."""
    normalized: list[dict] = []
    for case in testcases:
        case = dict(case)
        payload = case.get("expected_payload")
        if isinstance(payload, str):
            if payload.endswith((".yaml", ".yamlld", ".jsonld", ".json")):
                payload_path = _resolve_yaml_path(payload)
                case["expected_payload"] = yaml.safe_load(
                    payload_path.read_text()
                )
            elif payload == "ValueError":
                case["expected_payload"] = ValueError
            else:
                raise NotImplementedError(
                    f"Unsupported expected_payload format: {payload}"
                )
        normalized.append(case)
    return normalized


TESTCASES = _normalize_testcases(
    yaml.safe_load(TESTCASES_YAML.read_text())["testcases"]
)
