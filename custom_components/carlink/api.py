"""Client for the CarLink cloud: AWS Cognito login, then api.mybrandedapp.com with the ID token.

Unofficial: worked out from the CL7 app and the account's own API answers. send_command only sends door
lock/unlock, trunk release, remote start/stop and the accessory commands set up for that car; it refuses anything else.
"""
from __future__ import annotations

import time
from typing import Any

import aiohttp

from .const import API_BASE, BASE_COMMANDS, APP_BRAND, COGNITO_CLIENT_ID, COGNITO_URL


class CarLinkAuthError(Exception):
    """Wrong email or password, or the login was refused."""


class CarLinkError(Exception):
    """The CarLink service didn't answer as expected."""


class CarLinkClient:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._tokens: dict[str, Any] = {}
        self._expires = 0.0

    # ------------------------------------------------------------------ login
    async def _cognito(self, flow: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            async with self._session.post(
                COGNITO_URL,
                json={"AuthFlow": flow, "ClientId": COGNITO_CLIENT_ID, "AuthParameters": params},
                headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
                         "Content-Type": "application/x-amz-json-1.1"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                data = await r.json(content_type=None)
                status = r.status
        except aiohttp.ClientError as err:
            raise CarLinkError(f"Login service unreachable: {err}") from err
        if status != 200:
            if status in (400, 401, 403):
                raise CarLinkAuthError(data.get("message") or data.get("__type") or str(status))
            raise CarLinkError(f"Login service answered {status}")
        result = data.get("AuthenticationResult")
        if not result:
            raise CarLinkAuthError(data.get("ChallengeName") or "No token returned")
        return result

    async def login(self) -> None:
        self._store(await self._cognito(
            "USER_PASSWORD_AUTH", {"USERNAME": self._username, "PASSWORD": self._password}))

    async def _ensure_token(self) -> None:
        if self._tokens and time.time() < self._expires - 120:
            return
        refresh = self._tokens.get("RefreshToken")
        if refresh:
            try:
                result = await self._cognito("REFRESH_TOKEN_AUTH", {"REFRESH_TOKEN": refresh})
                result.setdefault("RefreshToken", refresh)
                self._store(result)
                return
            except CarLinkAuthError:
                pass
        await self.login()

    def _store(self, result: dict[str, Any]) -> None:
        self._tokens = result
        self._expires = time.time() + int(result.get("ExpiresIn", 3600))

    # ------------------------------------------------------------------ API
    async def _request(self, method: str, path: str, json: Any = None) -> Any:
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._tokens.get('IdToken', '')}", "Accept": "application/json"}
        try:
            async with self._session.request(method, API_BASE + path, json=json, headers=headers,
                                             timeout=aiohttp.ClientTimeout(total=40)) as r:
                if r.status == 401:
                    self._tokens = {}
                    raise CarLinkError("Session expired")
                if r.status >= 300:
                    raise CarLinkError(f"{path.split('/')[0]} answered {r.status}")
                text = await r.text()
                return await r.json(content_type=None) if text else None
        except aiohttp.ClientError as err:
            raise CarLinkError(f"CarLink service unreachable: {err}") from err

    async def vehicles(self) -> list[dict[str, Any]]:
        return await self._request("GET", f"GetAllVehicles/{APP_BRAND}?lang=en") or []

    async def status(self, vehicle_id: str) -> dict[str, Any]:
        """Last status the module reported (stored in the cloud; reading it doesn't wake the car)."""
        return await self._request("GET", f"GetLastVehicleStatus/{vehicle_id}") or {}

    async def send_command(self, vehicle_id: str, command: int, aux_commands: frozenset[int] = frozenset()) -> Any:
        """Lock (0), unlock (1), trunk (2), start (3), stop (4), or one of the car's own accessory commands."""
        if command not in BASE_COMMANDS and command not in aux_commands:
            raise ValueError(f"CarLink command {command} is not allowed by this integration")
        result = await self._request("POST", "SendCarCommand", {"vehicleId": vehicle_id, "carCommand": command})
        if isinstance(result, dict) and result.get("Result") is False:
            raise CarLinkError(result.get("Reason") or "The car didn't accept the command")
        return result
