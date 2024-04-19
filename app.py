"""Zoom Phone Number Script

    This script utilizes the Zoom Phone API to gather all phone numbers from
    the tenant configured in ./.env. Check the attributes of the Settings class
    as a reference for what settings are required and available for the .env
    file.

    The script accepts no arguments, and will generate three (3) JSON files
    in the same folder as the script.  The files will be named:
        * user_phone_map.json
            * Contains a map of user id to list of assigned phone numbers.
        * user_extension_map.json
            * Contains a map of user id to assigned extension number.
        * phone_numbers.json
            * Contains a list of all unassigned phone numbers

    Required Non-Standard Modules:
        * pydantic
            * pip install pydantic
        * pydantic-settings
            * pip install pydantic-settings
        * requests
            * pip install requests
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
from http import HTTPStatus, HTTPMethod
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, HttpUrl
import requests
import json


class Settings(BaseSettings):
    """A class to load strongly typed settings from ./.env"""

    model_config = SettingsConfigDict(env_file=".env")

    # Zoom authentication requirements
    # https://developers.zoom.us/docs/internal-apps/s2s-oauth/
    ZOOM_AUTH_URL: HttpUrl = "https://zoom.us/oauth/token"
    ZOOM_CLIENT_ID: str
    ZOOM_CLIENT_SECRET: SecretStr
    ZOOM_ACCOUNT_ID: int
    ZOOM_GRANT_TYPE: str = "account_credentials"

    # Zoom API information
    # https://developers.zoom.us/docs/api/rest/reference/phone/methods
    ZOOM_API_URL: HttpUrl = "https://api.zoom.us/v2"
    ZOOM_ENDPOINTS: Dict[
        str, Dict[str, Dict[str, Union[str, List, None, Dict, HTTPMethod]]]
    ] = {
        "PHONES": {
            "GET_ALL": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/phone/numbers",
                "BODY": None,
            },
            "GET": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/phone/numbers/{phoneNumberId}",
                "BODY": None,
            },
            "UNASSIGN": {
                "METHOD": HTTPMethod.DELETE,
                "PATH": "/phone/users/{userId}/phone_numbers/{phoneNumberId}",
                "BODY": None,
            },
            "ASSIGN": {
                "METHOD": HTTPMethod.POST,
                "PATH": "/phone/users/{userId}/phone_numbers",
                "BODY": [{"id": "{phoneNumberId}"}],
            },
        },
        "USERS": {
            "GET_ALL": {"METHOD": HTTPMethod.GET, "PATH": "/users", "BODY": None},
            "GET": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/users/{userId}",
                "BODY": None,
            },
            "REMOVE_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/users/{userId}",
                "BODY": {"extension_number": ""},
            },
            "ASSIGN_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/users/{userId}",
                "BODY": {"extension_number": "{extensionNumber}"},
            },
        },
    }


#   Load settings from ./.env
settings = Settings()


def auth(
    url: str = str(settings.ZOOM_AUTH_URL),
    username: str = settings.ZOOM_CLIENT_ID,
    password: str = settings.ZOOM_CLIENT_SECRET.get_secret_value(),
    account_id: str = settings.ZOOM_ACCOUNT_ID,
    headers: Dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"},
) -> Tuple[Optional[str], Optional[int]]:
    """Retrieve an auth token from Zoom

    Reference: https://developers.zoom.us/docs/internal-apps/s2s-oauth/

    Uses `ZOOM_CLIENT_ID` and `ZOOM_CLIENT_SECRET` for basic auth against
    `ZOOM_AUTH_URL` with the headers:
        - 'Content-Type': 'application/x-www-form-urlencoded'
    The request body contains:
        - 'grant_type': 'account_credentials'
        - 'account_id': '`ZOOM_ACCOUNT_ID`'
    """
    resp = requests.post(
        url=url,
        auth=(username, password),
        data={
            "grant_type": "account_credentials",
            "account_id": account_id,
        },
        headers=headers,
    )
    data = resp.json()
    return (data.get("access_token", None), data.get("expires_in", None))


def do_get(
    url: str,
    auth: Optional[Dict[str, str]] = None,
    query: str = "?page_size=100",
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
    },
    next_page: Optional[str] = None,
) -> List[Dict]:
    """Get all paginated results from the URL/query.

    If a GET request to the Zoom Phone API has more results than the
    page_size in the query (max 100), then a next_page_token will be
    returned in the response.  This token is used to request the next
    page.
    """
    results = []
    if auth:
        headers.update(auth)
    elif "Authorization" not in headers:
        raise Exception("Authorization header missing from GET request.")
    if next_page:
        query += f"&next_page_token={next_page}"
    resp = requests.get(
        url=f"{url}{query}",
        headers=headers,
    )
    if resp.status_code != HTTPStatus.OK:
        return results
    results.append(resp.json())
    # Try to get a next_page_token from the new result
    next_page = results[-1].get("next_page_token", None)
    # Recursively process all subsequent pages
    if next_page:
        return results.extend(
            do_get(
                url=url,
                # Remove the next_page_token that was just used from the query
                query="".join(query.split("&")[:-1]),
                headers=headers,
                # Pass the new next_page_token
                next_page=next_page,
            )
        )
    return results


if __name__ == "__main__":
    # Holds userID -> phone_numbers
    user_phone_map: Dict[str, List[str]] = {}
    # Holds userID -> extension
    user_extension_map: Dict[str, str] = {}

    # Get an access token and store the expiration time (not used)
    t_token, t_exp = auth()

    # If a token was not returned, the script cannot continue.
    if not t_token:
        raise Exception("Unable to authenticate to Zoom.")

    # Get all active Zoom Phone user objects.
    all_users_responses = do_get(
        url=f"{settings.ZOOM_API_URL}"
        + f"{settings.ZOOM_ENDPOINTS['USERS']['GET']['PATH']}",
        auth={"Authorization": f"Bearer {t_token}"},
        query="?page_size=100&status=active",
    )

    # Get all unassigned Zoom Phone phone number objects
    all_phone_responses = do_get(
        url=f"{settings.ZOOM_API_URL}"
        + f"{settings.ZOOM_ENDPOINTS['PHONES']['GET']['PATH']}",
        auth={"Authorization": f"Bearer {t_token}"},
        query="?page_size=100&type=unassigned",
    )

    # Condense the paged results (lists of objects) into a single list of objects
    phone_numbers_list: List[Dict] = []
    for response in all_phone_responses:
        phone_numbers_list.extend(response.get("phone_numbers", []))

    # Extract the phone numbers from the responses
    # https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listAccountPhoneNumbers
    all_phone_numbers = [
        phone_number.get("number", "ERROR")
        for phone_number in phone_numbers_list
    ]

    # Extract the phone numbers and extension from the responses
    # https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listPhoneUsers
    for user_response in all_users_responses:
        for user in user_response.get("users", []):
            if user.get("phone_numbers", None):
                user_phone_map[user["id"]] = user["phone_numbers"]
            if user.get("extension_number", None):
                user_extension_map[user["id"]] = user["extension_number"]

    with open(file="./user_phone_map.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=user_phone_map, fp=f, sort_keys=True, indent=4, separators=(",", ": ")
        )

    with open(file="./user_extension_map.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=user_extension_map,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )

    with open(file="./phone_numbers.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=all_phone_numbers,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )
