from __future__ import annotations

from typing import Dict, List
import json

from .config import Settings
from .api import auth, do_get


settings = Settings()
user_phone_map: Dict[str, List[str]] = {}
user_extension_map: Dict[str, str] = {}

t_token, t_exp = auth(
    url=settings.ZOOM_AUTH_URL,
    username=settings.ZOOM_CLIENT_ID,
    password=settings.ZOOM_CLIENT_SECRET,
    account_id=settings.ZOOM_ACCOUNT_ID
)

all_users_responses = do_get(
    url=f"{settings.ZOOM_API_URL}" +
        f"{settings.ZOOM_ENDPOINTS['USERS']['GET']['PATH']}",
    auth={"Authorization": f"Bearer {t_token}"},
    query="?page_size=100&status=active"
)

all_phone_responses = do_get(
    url=f"{settings.ZOOM_API_URL}" +
        f"{settings.ZOOM_ENDPOINTS['PHONES']['GET']['PATH']}",
    auth={"Authorization": f"Bearer {t_token}"},
    query="?page_size=100&type=unassigned"
)

all_phone_numbers = [
    phone_number.get("number", "ERROR")
    for phone_number
    in all_phone_responses.get('phone_numbers')
]

for user_response in all_users_responses:
    for user in user_response.get("users", []):
        if user.get("phone_numbers", None):
            user_phone_map[user["id"]] = user["phone_numbers"]
        if user.get("extension_number", None):
            user_extension_map[user["id"]] = user["extension_number"]


with open(file="./user_phone_map.json", mode="w", encoding="utf-8") as f:
    json.dump(
        obj=user_phone_map,
        fp=f,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )

with open(file="./user_extension_map.json", mode="w", encoding="utf-8") as f:
    json.dump(
        obj=user_extension_map,
        fp=f,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )

with open(file="./phone_numbers.json", mode="w", encoding="utf-8") as f:
    json.dump(
        obj=all_phone_numbers,
        fp=f,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )
