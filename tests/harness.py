import logging
from pathlib import Path
from typing import Any, cast

import yaml
from deepdiff import DeepDiff
from git import Repo

from tests.constants import TESTDIR

# from rdflib.plugins.serializers.jsonld import from_rdf
# from rdflib.plugins.parsers.jsonld import to_rdf
from tools.base import JsonLDFrame
from tools.openapi import (
    OpenAPI,
)
from tools.utils import SafeQuotedStringDumper


def assert_file(fileinfo: dict):
    path = Path(fileinfo["path"])
    assert path.exists() == fileinfo.get("exists", True), (
        f"Expected file not found: {path}"
    )

    assert_snapshot(fileinfo)


def assert_snapshot(fileinfo: dict):
    snapshot_path = fileinfo.get("snapshot")
    if not snapshot_path:
        return
    path = Path(fileinfo["path"])
    snapshot_file: Path = Path(snapshot_path)

    match fileinfo.get("compare"):
        case "data":
            assert_snapshot_matches_data(snapshot_file, path)
            return
        case _:
            assert_snapshot_matches_content(snapshot_file, path)
            return
    raise NotImplementedError("Unreachable code.")


def assert_snapshot_matches_data(
    snapshot_file: Path,
    current_file: Path | None = None,
    current_data: Any = None,
    update=False,
):
    """
    Compare the data content of two files,
    eventually retrieving the last committed version
    from git.
    """
    assert not (current_data and current_file), (
        "Either current_data or current_file must be provided"
    )
    current_source: Path | str
    if current_file is not None:
        current_data = yaml.safe_load(current_file.read_text())
        current_source = current_file
    else:
        current_source = "provided data"

    # If can't get info from current_file, get data from git.
    if current_data or (snapshot_file == current_file):
        snapshot_raw: str = git_show_head(snapshot_file)
        snapshot_data = yaml.safe_load(snapshot_raw)
    else:
        snapshot_data = yaml.safe_load(snapshot_file.read_text())

    delta = DeepDiff(snapshot_data, current_data, ignore_order=True)

    if update:
        snapshot_file.write_text(
            yaml.dump(
                current_data, sort_keys=True, Dumper=SafeQuotedStringDumper
            ),
            encoding="utf-8",
        )
        logging.warning(f"Updated snapshot file: {snapshot_file}")
    if delta:
        assert not delta, (
            f"{current_source} differs from {snapshot_file}."
            f" Either {current_source} is wrong,"
            f" or {snapshot_file} has uncommitted changes."
            f"\ndiff:\n{delta}"  # limit diff output to 500 chars
        )


def assert_snapshot_matches_content(snapshot_file: Path, current_file: Path):
    if snapshot_file == current_file:
        # compare the current_file to its git commited version.
        delta = git_diff(snapshot_file)
        assert not delta, (
            f"File {snapshot_file} has uncommitted changes. Please commit the file or update the snapshot reference."
            f"\nGit diff:\n{delta.decode('utf-8')[:500]}"  # limit diff output to 500 chars
        )
    else:
        assert snapshot_file.exists(), (
            f"Expected snapshot file not found: {snapshot_file}"
        )
        assert snapshot_file.read_bytes() == current_file.read_bytes()


def git_show_head(path: Path) -> str:
    """
    Get the git show of a file at HEAD as a string.

    :param path: Path to the file to get the show for
    :return: The git show as a string
    """
    repo = Repo(TESTDIR.parent, search_parent_directories=True)

    relative_path = (
        path.relative_to(repo.working_tree_dir)
        if path.is_relative_to(repo.working_tree_dir)
        else path
    )

    show: str = repo.git.show(
        f"HEAD:{relative_path.as_posix()}",
    )
    return cast(str, show)


def git_diff(path: Path) -> bytes:
    """
    Get the git diff of a file as bytes.

    :param path: Path to the file to get the diff for
    :return: The git diff as bytes
    """

    repo = Repo(TESTDIR.parent, search_parent_directories=True)
    diff: str = repo.git.diff("HEAD", path.as_posix(), ignore_cr_at_eol=True)
    return diff.encode("utf-8")


def assert_schema(schema_copy: OpenAPI, frame: JsonLDFrame) -> None:
    """ """
    validation = schema_copy.pop("x-validation", None)
    x_jsonld_type = schema_copy.pop("x-jsonld-type", None)
    assert x_jsonld_type
    x_jsonld_context = schema_copy.pop("x-jsonld-context", None)
    assert x_jsonld_context
    # Check that schema was generated
    assert validation is not None, "Schema should include x-validation results"

    # Log validation results for inspection
    logging.info("Validation results for %s:", frame.get("@type"))
    logging.info("  Valid: %s", validation["valid"])
    logging.info("  Errors: %d", validation["error_count"])

    if validation["errors"]:
        for error in validation["errors"][:5]:  # Log first 5 errors
            logging.warning(
                "  - %s at path %s", error["message"], error["path"]
            )

    # Check that constraints were added where expected
    properties = schema_copy.get("properties", {})
    assert properties, "Schema should have properties"

    # Check for integer constraints (e.g., level field with xsd:integer)
    for field_name, prop_schema in properties.items():
        if prop_schema.get("type") in ["integer", "number"]:
            # Should have minimum constraint from xsd:integer
            if field_name == "level":
                assert "minimum" in prop_schema, (
                    f"Integer field '{field_name}' should have minimum constraint"
                )
                assert "maximum" in prop_schema, (
                    "Level field should have maximum constraint"
                )
                logging.info(
                    "Field '%s' has constraints: minimum=%s, maximum=%s",
                    field_name,
                    prop_schema.get("minimum"),
                    prop_schema.get("maximum"),
                )

    # Check for string constraints (e.g., SKOS notation)
    context = frame.context
    for field_name, field_def in context.items():
        if isinstance(field_def, dict) and "@id" in field_def:
            predicate = field_def["@id"]
            if "notation" in predicate and field_name in properties:
                prop_schema = properties[field_name]
                if prop_schema.get("type") == "string":
                    assert "pattern" in prop_schema, (
                        f"Notation field '{field_name}' should have pattern constraint"
                    )
                    assert "minLength" in prop_schema, (
                        f"Notation field '{field_name}' should have minLength constraint"
                    )
                    logging.info(
                        "Field '%s' (notation) has pattern: %s",
                        field_name,
                        prop_schema.get("pattern"),
                    )

    # The validation should ideally pass, but if there are errors,
    # they should be specific and actionable
    if not validation["valid"]:
        logging.warning(
            "Validation failed with %d errors", validation["error_count"]
        )
        assert validation["error_count"] > 0, "If not valid, should have errors"
        # Errors should have proper structure
        for error in validation["errors"]:
            assert "message" in error, "Error should have message"
            assert "path" in error, "Error should have path"
    else:
        logging.info(
            "✓ All framed vocabulary data validates against the enhanced schema"
        )
