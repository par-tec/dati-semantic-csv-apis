#!/usr/bin/env python3
import os
import sys
import requests

REPO = "par-tec/dati-semantic-csv-apis"
WORKFLOW_NAME = "Test"
ARTIFACT_NAME = "cli-binary"

token = os.environ.get("GH_TOKEN")
if not token:
    print("Missing GH_TOKEN environment variable", file=sys.stderr)
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}


def get_runs():
    url = f"https://api.github.com/repos/{REPO}/actions/runs"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return [run["id"] for run in data["workflow_runs"] if run["name"] == WORKFLOW_NAME]


def get_artifact_url(run_id):
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/artifacts"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    artifacts = r.json().get("artifacts", [])
    for a in artifacts:
        if a["name"] == ARTIFACT_NAME and not a["expired"]:
            return a["archive_download_url"]
    return None


def main():
    runs = get_runs()
    if not runs:
        print(f"No runs found for workflow '{WORKFLOW_NAME}'", file=sys.stderr)
        sys.exit(1)

    for run_id in runs:
        url = get_artifact_url(run_id)
        if url:
            print(url)
            return

    print(
        f"No valid artifact '{ARTIFACT_NAME}' found in any recent run", file=sys.stderr
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
