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
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_TEMPUNIT,
    CONF_TEMPERATURE_STEP,
    CONF_TARGET_PRECISION,
)

OPT_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MAX_TEMP, default="30"): cv.string,
        vol.Optional(CONF_MIN_TEMP, default="16"): cv.string,
        vol.Optional(CONF_TEMPUNIT, default="celsius"): vol.In(
            ["celsius", "fahrenheit"]
        ),
        vol.Optional(CONF_TEMPERATURE_STEP, default="1"): vol.In(["0.1", "0.5", "1"]),
        vol.Optional(CONF_TARGET_PRECISION): cv.string,
    }
)


_LOGGER = logging.getLogger(__name__)
regions = ("us", "us-e", "cn", "eu", "eu-w" "in")


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the IR Air Con config flow."""
        self.host: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=OPT_USER_DATA_SCHEMA)

    @property
    def schema(self) -> vol.Schema:
        """Return current schema."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_APIREGION, default="us"): vol.In(
                    ["us", "us-e", "cn", "eu", "eu-w" "in"]
                ),
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_APISECRET): cv.string,
                vol.Required(CONF_USERID): cv.string,
                vol.Required(CONF_DEVICEID): cv.string,
                vol.Required(CONF_REMOTEID): cv.string,
                vol.Optional(CONF_IP_ADDRESS): cv.string,
                vol.Optional(CONF_MAX_TEMP, default=30): cv.positive_float,
                vol.Optional(CONF_MIN_TEMP, default=16): cv.positive_float,
                vol.Optional(CONF_TEMPUNIT, default="celsius"): vol.In(
                    ["celsius", "fahrenheit"]
                ),
                vol.Optional(CONF_TEMPERATURE_STEP, default="1"): vol.In(
                    ["0.1", "0.5", "1"]
                ),
                vol.Optional(CONF_TARGET_PRECISION, default=1): cv.string,
            }
        )

    async def _create_entry(
        self,
        userinput,
    ) -> FlowResult:
        """Register new entry."""
        if not self.unique_id:
            unique = userinput[CONF_NAME] + userinput[CONF_REMOTEID]
            await self.async_set_unique_id(unique)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=userinput[CONF_NAME],
            data={
                CONF_IP_ADDRESS: userinput[CONF_IP_ADDRESS],
                CONF_API_KEY: userinput[CONF_API_KEY],
                CONF_DEVICEID: userinput[CONF_DEVICEID],
                CONF_APISECRET: userinput[CONF_APISECRET],
                CONF_APIREGION: userinput[CONF_APIREGION],
                CONF_REMOTEID: userinput[CONF_REMOTEID],
                CONF_NAME: userinput[CONF_NAME],
                CONF_USERID: userinput[CONF_USERID],
                CONF_MAX_TEMP: userinput[CONF_MAX_TEMP],
                CONF_MIN_TEMP: userinput[CONF_MIN_TEMP],
                CONF_TEMPUNIT: userinput[CONF_TEMPUNIT],
                CONF_TEMPERATURE_STEP: userinput[CONF_TEMPERATURE_STEP],
                CONF_TARGET_PRECISION: userinput[CONF_TARGET_PRECISION],
            },
        )

    async def _create_device(
        self,
        userinput,
    ) -> FlowResult:
        """Create device."""

        try:
            host = "Test"
            # ipaddr = "192.168.1.163"

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error creating device")
            return self.async_show_form(
                step_id="user",
                data_schema=self.schema,
                errors={"base": "unknown"},
            )

        return await self._create_entry(userinput)

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
        return await self._create_device(user_input)

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
