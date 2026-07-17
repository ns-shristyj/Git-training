"""The agent's source-fetch boundary: reads exactly one file from GitHub at a
pinned commit SHA, authenticated with a PAT pulled from Secrets Manager.

No filesystem access, no S3. The two external calls this module makes —
one Secrets Manager read, one GitHub Contents API GET — are the agent's
entire permitted network surface for fetching source.
"""
import os

import boto3
import requests

REGION = "ap-southeast-2"
GITHUB_API_BASE = "https://api.github.com"

_cached_pat = None


def _get_github_pat() -> str:
    global _cached_pat
    if _cached_pat is not None:
        return _cached_pat

    secret_arn = os.environ.get("GITHUB_PAT_SECRET_ARN")
    if not secret_arn:
        raise ValueError("GITHUB_PAT_SECRET_ARN environment variable is not set")

    client = boto3.client("secretsmanager", region_name=REGION)
    response = client.get_secret_value(SecretId=secret_arn)
    _cached_pat = response["SecretString"]
    return _cached_pat


def fetch_source_from_github(repo: str, file_path: str, ref: str) -> str:
    pat = _get_github_pat()

    response = requests.get(
        f"{GITHUB_API_BASE}/repos/{repo}/contents/{file_path}",
        params={"ref": ref},
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github.raw+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.text


def fetch_multiple_from_github(repo: str, file_paths: list[str], ref: str) -> dict[str, str]:
    """Fetch multiple files from GitHub at once. Returns {file_path: content}."""
    pat = _get_github_pat()
    result = {}

    for file_path in file_paths:
        response = requests.get(
            f"{GITHUB_API_BASE}/repos/{repo}/contents/{file_path}",
            params={"ref": ref},
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github.raw+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        response.raise_for_status()
        result[file_path] = response.text

    return result
