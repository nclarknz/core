"""Config flow for IR Air Con Controller Daikin integration."""
from __future__ import annotations  # noqa: I001

import logging
from typing import Any, Optional

import voluptuous as vol

from homeassistant import config_entries

from homeassistant.const import CONF_API_KEY, CONF_IP_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

# from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_APIREGION,
    CONF_APISECRET,
    CONF_DEVICEID,
    CONF_REMOTEID,
)


_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APIREGION, default="us"): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_APISECRET): cv.string,
        vol.Required(CONF_DEVICEID): cv.string,
        vol.Required(CONF_REMOTEID): cv.string,
        vol.Optional(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)

OPT_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APIREGION, default="us"): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_APISECRET): cv.string,
        vol.Required(CONF_DEVICEID): cv.string,
        vol.Required(CONF_REMOTEID): cv.string,
        vol.Optional(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)

regions = ("us", "us-e", "cn", "eu", "eu-w" "in")

# class PlaceholderHub:
#     """Placeholder class to make tests pass."""

#     def __init__(self, host: str) -> None:
#         """Initialize."""
#         self.host = host

#     async def authenticate(self, username: str, password: str) -> bool:
#         """Test if we can authenticate with the host."""
#         return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    regioncode = data[CONF_APIREGION]
    if regioncode not in regions:
        raise NoRegion

    # hub = PlaceholderHub(data[CONF_HOST])

    # if not await hub.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD]):
    #    raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_NAME]}


class NoRegion(Exception):
    """Error code if no region is entered that matches the list."""


class IRAIRCONConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IR Air Con Controller Daikin."""

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self.async_set_unique_id(unique_id=user_input[CONF_REMOTEID])

                info = await validate_input(self.hass, user_input)
            except NoRegion:
                errors["base"] = "Region not in List"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # If checked the data from the form is correct
                # then create an entry in HA
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    # async def async_create_entry(self, user_input, data) -> FlowResult:
    #     errors: dict[str, str] = {}
    #     if user_input is not None:
    #         if not errors:
    #             # Input is valid, set data.
    #             # If user ticked the box show this form again so they can add an
    #             # additional repo.

    #             # User is done adding repos, create the config entry.
    #             return self.async_create_entry(title=user_input, data=self.data)

    #     return self.async_show_form(
    #         step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
    #     )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """handles alowing editing the entity in HA."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=OPT_USER_DATA_SCHEMA)
