from typing import Dict, List, Optional, Tuple
from http import HTTPStatus
import requests


def auth(
    url: str,
    username: str,
    password: str,
    account_id: str,
    headers: Dict[str, str] = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
) -> Tuple[Optional[str], Optional[int]]:
    resp = requests.post(
        url=url,
        auth=(username, password),
        data={
            "grant_type": "account_credentials",
            "account_id": account_id,
        },
        headers=headers
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
    next_page: Optional[str] = None
) -> List[Dict]:
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
    next_page = results[-1].get("next_page_token", None)
    if next_page:
        return results.extend(
            do_get(
                url=url,
                query="".join(query.split('&')[:-1]),
                headers=headers,
                next_page=next_page
            )
        )
    return results
