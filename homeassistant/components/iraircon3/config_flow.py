"""Config flow for IR Air Con Controller integration."""
from __future__ import annotations  # noqa: I001

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from homeassistant.const import CONF_API_KEY, CONF_IP_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

# from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_APIREGION,
    CONF_APISECRET,
    CONF_DEVICEID,
    CONF_REMOTEID,
    CONF_USERID,
)


_LOGGER = logging.getLogger(__name__)


regions = ("us", "us-e", "cn", "eu", "eu-w" "in")


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the IR Air Con config flow."""
        self.host: str | None = None

    @property
    def schema(self) -> vol.Schema:
        """Return current schema."""
        return vol.Schema(
            {
                vol.Required(CONF_APIREGION, default="us"): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_APISECRET): cv.string,
                vol.Required(CONF_DEVICEID): cv.string,
                vol.Required(CONF_REMOTEID): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_USERID): cv.string,
                vol.Optional(CONF_IP_ADDRESS): cv.string,
            }
        )

    async def _create_entry(
        self,
        apiUnitName: str,
        ipaddr: str,
        apiKey: str | None = None,
        apiSecret: str | None = None,
        apiDeviceID: str | None = None,
        apiRegion: str | None = None,
        apiRemoteID: str | None = None,
        apiUserID: str | None = None,
    ) -> FlowResult:
        """Register new entry."""
        if not self.unique_id:
            unique = apiUnitName + apiRemoteID
            await self.async_set_unique_id(unique)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=apiUnitName,
            data={
                CONF_IP_ADDRESS: ipaddr,
                CONF_API_KEY: apiKey,
                CONF_DEVICEID: apiDeviceID,
                CONF_APISECRET: apiSecret,
                CONF_APIREGION: apiRegion,
                CONF_REMOTEID: apiRemoteID,
                CONF_NAME: apiUnitName,
                CONF_USERID: apiUserID,
            },
        )

    async def _create_device(
        self,
        apiUnitName: str,
        ipaddr: str,
        apiKey: str | None = None,
        apiSecret: str | None = None,
        apiDeviceID: str | None = None,
        apiRegion: str | None = None,
        apiRemoteID: str | None = None,
        apiUserID: str | None = None,
    ) -> FlowResult:
        """Create device."""

        try:
            """ Get Device Details"""
            # host = "Test"
            ipaddr = "192.168.1.163"

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error creating device")
            return self.async_show_form(
                step_id="user",
                data_schema=self.schema,
                errors={"base": "unknown"},
            )

        return await self._create_entry(
            apiUnitName,
            ipaddr,
            apiKey,
            apiSecret,
            apiDeviceID,
            apiRegion,
            apiRemoteID,
            apiUserID=apiUserID,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """User initiated config flow."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=self.schema)
        if (
            (user_input.get(CONF_API_KEY) is None)
            or (user_input.get(CONF_APIREGION) is None)
            or (user_input.get(CONF_APISECRET) is None)
            or (user_input.get(CONF_REMOTEID) is None)
            or (user_input.get(CONF_NAME) is None)
            or (user_input.get(CONF_USERID) is None)
        ):
            self.host = user_input[CONF_NAME]
            return self.async_show_form(
                step_id="user",
                data_schema=self.schema,
                errors={"base": "Missing Configuration"},
            )
        return await self._create_device(
            user_input.get(CONF_NAME),
            user_input.get(CONF_IP_ADDRESS),
            user_input.get(CONF_API_KEY),
            user_input.get(CONF_APISECRET),
            user_input.get(CONF_DEVICEID),
            user_input.get(CONF_APIREGION),
            user_input.get(CONF_REMOTEID),
            user_input.get(CONF_USERID),
        )

    # async def async_step_zeroconf(
    #     self, discovery_info: zeroconf.ZeroconfServiceInfo
    # ) -> FlowResult:
    #     """Prepare configuration for a discovered Daikin device."""
    #     _LOGGER.debug("Zeroconf user_input: %s", discovery_info)
    #     devices = Discovery().poll(ip=discovery_info.host)
    #     if not devices:
    #         _LOGGER.debug(
    #             (
    #                 "Could not find MAC-address for %s, make sure the required UDP"
    #                 " ports are open (see integration documentation)"
    #             ),
    #             discovery_info.host,
    #         )
    #         return self.async_abort(reason="cannot_connect")
    #     await self.async_set_unique_id(next(iter(devices))[KEY_MAC])
    #     self._abort_if_unique_id_configured()
    #     self.host = discovery_info.host
    #     return await self.async_step_user()
