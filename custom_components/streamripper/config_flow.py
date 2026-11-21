"""Config flow: discovery first, typing only as a fallback.

The coordinator announces itself as _streamripper._tcp; when
Home Assistant sees the announcement this flow is offered with
the address already filled in, and only the API token is asked
for — discovery never carries a credential. A manual flow
(host, port, token) covers networks where mDNS does not reach.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.service_info.zeroconf import (
    ZeroconfServiceInfo,
)

from .api import (
    StreamRipperApiError,
    StreamRipperAuthError,
    StreamRipperClient,
)
from .const import CONF_API_TOKEN, DEFAULT_PORT, DOMAIN


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


class StreamRipperConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup for one coordinator."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: dict | None = None

    async def _async_validate(self, host: str, port: int,
                              token: str) -> dict:
        client = StreamRipperClient(
            aiohttp_client.async_get_clientsession(self.hass),
            _base_url(host, port), token)
        return await client.async_validate()

    async def _async_finish(self, host: str, port: int, token: str,
                            instance_id: str | None) -> ConfigFlowResult:
        await self.async_set_unique_id(instance_id or _base_url(host, port))
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_PORT: port})
        return self.async_create_entry(
            title="StreamRipper",
            data={CONF_HOST: host, CONF_PORT: port,
                  CONF_API_TOKEN: token},
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        properties = discovery_info.properties or {}
        instance_id = properties.get("id")
        if isinstance(instance_id, bytes):
            instance_id = instance_id.decode("utf-8", "replace")
        await self.async_set_unique_id(instance_id or _base_url(host, port))
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_PORT: port})
        self._discovery = {
            CONF_HOST: host, CONF_PORT: port, "instance_id": instance_id,
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        host = self._discovery[CONF_HOST]
        port = self._discovery[CONF_PORT]
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            try:
                status = await self._async_validate(host, port, token)
            except StreamRipperAuthError:
                errors["base"] = "invalid_auth"
            except StreamRipperApiError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_finish(
                    host, port, token,
                    status.get("instance_id")
                    or self._discovery.get("instance_id"))
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_API_TOKEN): str}),
            description_placeholders={"host": host, "port": str(port)},
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            token = user_input[CONF_API_TOKEN].strip()
            try:
                status = await self._async_validate(host, port, token)
            except StreamRipperAuthError:
                errors["base"] = "invalid_auth"
            except StreamRipperApiError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_finish(
                    host, port, token, status.get("instance_id"))
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_API_TOKEN): str,
            }),
            errors=errors,
        )
