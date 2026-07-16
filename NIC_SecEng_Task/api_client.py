import requests


def fetch_user_profile(base_url, user_id, api_key):
    """Fetches a user profile from a remote API and returns the parsed JSON body."""
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")

    response = requests.get(
        f"{base_url}/users/{user_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=5,
    )
    response.raise_for_status()

    data = response.json()
    if "id" not in data:
        raise ValueError("Malformed API response: missing 'id' field")

    return data
