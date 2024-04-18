from typing import Dict, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Url
from http import HTTPMethod


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env'
    )

    ZOOM_CLIENT_ID: str
    ZOOM_CLIENT_SECRET: SecretStr
    ZOOM_ACCOUNT_ID: int
    ZOOM_GRANT_TYPE: str = "account_credentials"
    ZOOM_API_URL: Url = "https://api.zoom.us/v2"
    ZOOM_AUTH_URL: Url = "https://zoom.us/oauth/token"

    ZOOM_ENDPOINTS: Dict[
        str, Dict[
            str, Dict[
                str, Union[
                    str, List, None, Dict, HTTPMethod
                ]
            ]
        ]
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
                "BODY": [
                    {
                        "id": "{phoneNumberId}"
                    }
                ]
            },
        },
        "USERS": {
            "GET_ALL": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/users",
                "BODY": None
            },
            "GET": {
                "METHOD": HTTPMethod.GET,
                "PATH": "/users/{userId}",
                "BODY": None,
            },
            "REMOVE_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/users/{userId}",
                "BODY": {
                    "extension_number": ""
                }
            },
            "ASSIGN_EXTENSION": {
                "METHOD": HTTPMethod.PATCH,
                "PATH": "/users/{userId}",
                "BODY": {
                    "extension_number": "{extensionNumber}"
                },
            },
        },
    }
