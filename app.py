"""Zoom Phone Number Script

    This script utilizes the Zoom Phone API to gather all phone numbers from
    the tenant configured in ./.env. Check the attributes of the Settings class
    as a reference for what settings are required and available for the .env
    file.

    The script accepts no arguments, and will generate five (5) JSON files
    in the same folder as the script.  The files will be named:
        * user_emails.json
            * Contains user.id -> user.email
        * user_phone_numbers.json
            * Contains phone_number.assignee.id -> phone_number.number
        * user_extensions.json
            * Contains phone_number.assignee.id -> phone_number.assignee.extension_number
        * all_phone_numbers.json
            * Contains ALL phone_number.number -> phone_number.id
        * unassigned_phone_numbers.json
            * Contains UNASSIGNED phone_number.number -> phone_number.id

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
from pathlib import Path
from sys import stdout
import logging
import requests
import json


class Settings(BaseSettings):
    """A class to load strongly typed settings from ./.env"""

    model_config = SettingsConfigDict(env_file=".env")

    # Logging
    LOG_LEVEL: Union[int, str] = logging.INFO
    LOG_FILE: Optional[Path] = None

    # Zoom authentication requirements
    # https://developers.zoom.us/docs/internal-apps/s2s-oauth/
    ZOOM_AUTH_URL: HttpUrl = "https://zoom.us/oauth/token"
    ZOOM_CLIENT_ID: str
    ZOOM_CLIENT_SECRET: SecretStr
    ZOOM_ACCOUNT_ID: str
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
            "GET_ALL": {"METHOD": HTTPMethod.GET, "PATH": "/phone/users", "BODY": None},
            "GET": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/phone/users/{userId}",
                "BODY": None,
            },
            "REMOVE_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/phone/users/{userId}",
                "BODY": {"extension_number": ""},
            },
            "ASSIGN_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/phone/users/{userId}",
                "BODY": {"extension_number": "{extensionNumber}"},
            },
        },
    }


#   Load settings from ./.env
settings = Settings()

#   Configure logging
log = logging.getLogger(__name__)
log.setLevel(settings.LOG_LEVEL)
if settings.LOG_FILE:
    handler = logging.FileHandler(settings.LOG_FILE)
else:
    handler = logging.StreamHandler(stdout)
for h in log.handlers:
    log.removeHandler(h)
log.addHandler(handler)


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
    log.debug("Making auth request to %s", url)
    resp = requests.post(
        url=url,
        auth=(username, password),
        data={
            "grant_type": "account_credentials",
            "account_id": account_id,
        },
        headers=headers,
    )
    log.debug("Auth request status: %s", resp.status_code)
    log.debug("Auth request message: %s", resp.reason)
    try:
        data = resp.json()
        log.debug("Auth response has data.")
        log.debug("%s", data)
    except json.JSONDecodeError:
        log.error("Auth response has no data.")
        return None, None
    return (data.get("access_token", None), data.get("expires_in", None))


def do_get(
    url: str,
    auth: Optional[Dict[str, str]] = None,
    query: Dict = {"page_size": 100},
    headers: Dict[str, str] = {},
    next_page: Optional[str] = None,
) -> List[Dict]:
    """Get all paginated results from the URL/query.

    If a GET request to the Zoom Phone API has more results than the
    page_size in the query (max 100), then a next_page_token will be
    returned in the response.  This token is used to request the next
    page.
    """
    log.debug("Making GET request to: %s", url)
    log.debug("Query: %s", query)
    results = []
    if auth:
        log.debug("Adding auth header to headers.")
        headers.update(auth)
    elif "Authorization" not in headers:
        log.error("Did not receive an authentication form (header or parameter)!")
        raise Exception("Authorization header missing from GET request.")
    if next_page:
        log.debug("Adding next_page_token to query string")
        query["next_page_token"] = next_page
        log.debug("New query: %s", query)
    resp = requests.get(
        url=url,
        params=query,
        headers=headers,
    )
    if resp.status_code != HTTPStatus.OK:
        log.error("Non-200 response!")
        log.error("Status code: %s", resp.status_code)
        log.error("Reason: %s", resp.reason)
        return []
    try:
        results.append(resp.json())
        log.debug("GET response data size: %s", len(results[-1]))
    except json.JSONDecodeError:
        log.error("GET response has no data!")
        return []
    # Try to get a next_page_token from the new result
    next_page = results[-1].get("next_page_token", None)
    # Recursively process all subsequent pages
    if next_page:
        log.debug("Response has a next page")
        query["next_page_token"] = next_page
        results.extend(do_get(url=url, query=query, headers=headers))
    return results


if __name__ == "__main__":
    log.info(">>>   Zoom Phone Number Script    <<<")
    log.info("Retrieved settings from %s.", settings.model_config["env_file"])
    log.debug("Settings dump:\n%s", settings.model_dump())

    all_phone_numbers = {}
    unassigned_phone_numbers = {}
    user_phone_numbers = {}
    user_emails = {}
    user_extensions = {}

    # Get an access token and store the expiration time (not used)
    log.info("Attempting authentication to Zoom...")
    t_token, t_exp = auth()

    # If a token was not returned, the script cannot continue.
    if not t_token:
        log.error("Authentication failed!")
        raise Exception("Unable to authenticate to Zoom.")
    log.info("Authenticated to Zoom.")

    # Get all licensed Zoom Phone user objects
    all_user_responses = do_get(
        url=f"{settings.ZOOM_API_URL}"
        + f"{settings.ZOOM_ENDPOINTS['USERS']['GET_ALL']['PATH']}",
        auth={"Authorization": f"Bearer {t_token}"},
        query={"page_size": 100, "status": "activate"},
    )

    # Condense the paged results (list of objects) into
    # a single list of objects
    users_list: List[Dict] = []
    for response in all_user_responses:
        users_list.extend(response.get("users", []))

    # Extract the ids and emails from the responses
    # https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listPhoneUsers
    for user in users_list:
        user_emails[user["id"]] = user["email"]

    # Get all Zoom Phone phone number objects
    all_phone_responses = do_get(
        url=f"{settings.ZOOM_API_URL}"
        + f"{settings.ZOOM_ENDPOINTS['PHONES']['GET_ALL']['PATH']}",
        auth={"Authorization": f"Bearer {t_token}"},
        query={"page_size": 100, "type": "all"},
    )

    log.debug("Processing phone_number responses:\n%s", all_phone_responses)
    # Condense the paged results (lists of objects) into
    # a single list of objects
    phone_numbers_list: List[Dict] = []
    for response in all_phone_responses:
        phone_numbers_list.extend(response.get("phone_numbers", []))

    # Extract the phone numbers from the responses
    # https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listAccountPhoneNumbers
    for phone_number in phone_numbers_list:
        all_phone_numbers[phone_number["number"]] = phone_number["id"]
        if "assignee" in phone_number:
            user_phone_numbers[phone_number["assignee"]["id"]] = phone_number["number"]
            extension = phone_number["assignee"].get("extension_number", None)
            if extension:
                user_extensions[phone_number["assignee"]["id"]] = extension
        else:
            unassigned_phone_numbers[phone_number["number"]] = phone_number["id"]

    with open(file="./user_phone_numbers.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=user_phone_numbers,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )

    with open(file="./all_phone_numbers.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=all_phone_numbers,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )

    with open(file="./user_extensions.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=user_extensions,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )

    with open(file="./unassigned_phone_numbers.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=unassigned_phone_numbers,
            fp=f,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
        )

    with open(file="./user_emails.json", mode="w", encoding="utf-8") as f:
        json.dump(
            obj=user_emails, fp=f, sort_keys=True, indent=4, separators=(",", ": ")
        )
