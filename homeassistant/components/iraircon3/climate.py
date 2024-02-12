"""The IR Air Con Controller Daikin integration.

Support for the Daikin HVAC.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    PLATFORM_SCHEMA,
    PRESET_AWAY,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_API_KEY,
    CONF_IP_ADDRESS,
    CONF_NAME,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

# from . import DOMAIN as DAIKIN_DOMAIN, DaikinApi
from .const import (
    ATTR_INSIDE_TEMPERATURE,
    ATTR_OUTSIDE_TEMPERATURE,
    ATTR_TARGET_TEMPERATURE,
    CONF_APIREGION,
    CONF_APISECRET,
    CONF_DEVICEID,
    CONF_REMOTEID,
)
from .IRaircon import cloud_api

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_APIREGION): cv.string,
        vol.Required(CONF_APISECRET): cv.string,
        vol.Required(CONF_DEVICEID): cv.string,
        vol.Required(CONF_REMOTEID): cv.string,
        vol.Optional(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)

HA_STATE_TO_DAIKIN = {
    HVACMode.FAN_ONLY: "wind_dry",
    HVACMode.DRY: "dehumidification",
    HVACMode.COOL: "cold",
    HVACMode.HEAT: "heat",
    HVACMode.HEAT_COOL: "auto",
    HVACMode.OFF: "off",
}

DAIKIN_TO_HA_STATE = {
    "wind_dry": HVACMode.FAN_ONLY,
    "dehumidification": HVACMode.DRY,
    "cold": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "auto": HVACMode.HEAT_COOL,
    "off": HVACMode.OFF,
}

HA_STATE_TO_CURRENT_HVAC = {
    HVACMode.COOL: HVACAction.COOLING,
    HVACMode.HEAT: HVACAction.HEATING,
    HVACMode.OFF: HVACAction.OFF,
}

HA_PRESET_TO_DAIKIN = {
    PRESET_AWAY: "on",
    PRESET_NONE: "off",
}

HA_ATTR_TO_DAIKIN = {
    ATTR_PRESET_MODE: "en_hol",
    ATTR_HVAC_MODE: "mode",
    ATTR_FAN_MODE: "f_rate",
    ATTR_INSIDE_TEMPERATURE: "htemp",
    ATTR_OUTSIDE_TEMPERATURE: "otemp",
    ATTR_TARGET_TEMPERATURE: "stemp",
}

DAIKIN_ATTR_ADVANCED = "adv"


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Old way of setting up the Daikin IR HVAC platform.

    Can only be called when a user accidentally mentions the platform in their
    config. But even in that case it would have been ignored.
    """


def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Daikin climate based on config_entry."""
    confApiRegion = entry.data["apiregion"]
    confDeviceID = entry.data["deviceid"]
    confRemoteID = entry.data["remoteid"]
    confipaddr = entry.data["ip_address"]
    confUserId = entry.data["userid"]
    confApiKey = entry.data["api_key"]
    confApiSecret = entry.data["apisecret"]
    daikin_api = entry.entry_id

    irapi = cloud_api.TuyaCloudApi(
        hass,
        confApiRegion,
        confApiKey,
        confApiSecret,
        confUserId,
        confDeviceID,
        confRemoteID,
    )
    # ({'ip_address': '192.168.1.163', 'api_key': 'p57d8pmf7gn45ym3pkmr', 'deviceid': 'ebc38472469be5057cinaw', 'apisecret': 'c5f6362caf8a40c9ba99872de8a2fcac', 'apiregion': 'us', 'remoteid': '40723017ecfabc481772', 'name': 'HEatPumpLounge', 'userid': 'az1566194334126gGaQI'})

    # dataapi = hass.data[DOMAIN].get(entry.data)
    async_add_entities(
        [
            DaikinIRClimate(
                daikin_api,
                irapi,
                confRemoteID,
            )
        ],
        update_before_add=False,
    )


def format_target_temperature(target_temperature: float) -> str:
    """Format target temperature to be sent to the Daikin unit, rounding to nearest half degree."""
    return str(round(float(target_temperature) * 2, 0) / 2).rstrip("0").rstrip(".")


class DaikinIRClimate(ClimateEntity):
    """Representation of a Daikin HVAC."""

    _attr_name = None
    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = list(HA_STATE_TO_DAIKIN)
    _attr_target_temperature_step = 1
    # _attr_fan_modes: list[str]
    # _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, entryid, irapi: cloud_api.TuyaCloudApi, remoteID) -> None:
        """Initialize the climate device."""
        self._remoteID = remoteID
        self._irapi = irapi
        self._attr_current_temperature = None
        # self._irapi._connect()
        # self._attr_current_temperature = self._irapi.get_statusPower()
        self._attr_hvac_modes = None
        self._attr_fan_modes = None
        self._attr_device_info = "Hello"
        self._list: dict[str, list[Any]] = {
            ATTR_HVAC_MODE: self._attr_hvac_modes,
            ATTR_FAN_MODE: self._attr_fan_modes,
        }

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
        )

        self._attr_supported_features |= ClimateEntityFeature.FAN_MODE

    async def getPowerStatus(self):
        """Get the current powersttaus of heatpump."""

        res = await self._irapi.get_statusPower()
        if res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
            return cloud_api, {"reason": "authentication_failed", "msg": res}
        return res, {}

    async def _set(self, settings: dict[str, Any]) -> None:
        """Set device settings using API."""
        values: dict[str, Any] = {}

        for attr in (ATTR_TEMPERATURE, ATTR_FAN_MODE, ATTR_HVAC_MODE):
            if (value := settings.get(attr)) is None:
                continue

            if (daikin_attr := HA_ATTR_TO_DAIKIN.get(attr)) is not None:
                if attr == ATTR_HVAC_MODE:
                    values[daikin_attr] = HA_STATE_TO_DAIKIN[value]
                    self._irapi.changeMode(value)
                elif value in self._list[attr]:
                    values[daikin_attr] = value.lower()
                else:
                    _LOGGER.error("Invalid value %s for %s", attr, value)

            # temperature
            elif attr == ATTR_TEMPERATURE:
                try:
                    values[
                        HA_ATTR_TO_DAIKIN[ATTR_TARGET_TEMPERATURE]
                    ] = format_target_temperature(value)
                    self._irapi.set_target_temp(value)
                except ValueError:
                    _LOGGER.error("Invalid temperature %s", value)

            # fan speed
            elif attr == ATTR_FAN_MODE:
                try:
                    values[
                        HA_ATTR_TO_DAIKIN[ATTR_TARGET_TEMPERATURE]
                    ] = format_target_temperature(value)
                    self._irapi.async_set_fan_mode(value)
                except ValueError:
                    _LOGGER.error("Invalid temperature %s", value)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._remoteID

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._irapi.getstatustemp()

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._irapi.getstatustemp()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self._set(kwargs)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current state."""
        ret = HA_STATE_TO_CURRENT_HVAC.get(self.hvac_mode)
        if ret in (HVACAction.COOLING, HVACAction.HEATING):
            return HVACAction.IDLE
        return ret

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation ie. heat, cool, idle."""
        # daikin_mode = self._api.device.represent(HA_ATTR_TO_DAIKIN[ATTR_HVAC_MODE])[1]
        daikin_mode = self._irapi.getstatusmode
        return DAIKIN_TO_HA_STATE.get(daikin_mode, HVACMode.HEAT_COOL)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        await self._set({ATTR_HVAC_MODE: hvac_mode})

    @property
    def fan_mode(self) -> str:
        """Return the fan setting."""
        # return self._api.device.represent(HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE])[1].title()
        return self._irapi.getstatusfan(HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE])[1].title()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        await self._set({ATTR_FAN_MODE: fan_mode})

    # @property
    # def preset_mode(self) -> str:
    #     """Return the preset_mode."""
    #     if (
    #         self._api.device.represent(HA_ATTR_TO_DAIKIN[ATTR_PRESET_MODE])[1]
    #         == HA_PRESET_TO_DAIKIN[PRESET_AWAY]
    #     ):
    #         return PRESET_AWAY
    #     if (
    #         HA_PRESET_TO_DAIKIN[PRESET_BOOST]
    #         in self._api.device.represent(DAIKIN_ATTR_ADVANCED)[1]
    #     ):
    #         return PRESET_BOOST
    #     if (
    #         HA_PRESET_TO_DAIKIN[PRESET_ECO]
    #         in self._api.device.represent(DAIKIN_ATTR_ADVANCED)[1]
    #     ):
    #         return PRESET_ECO
    #     return PRESET_NONE

    # async def async_set_preset_mode(self, preset_mode: str) -> None:
    #     """Set preset mode."""
    #     if preset_mode == PRESET_AWAY:
    #         await self._api.device.set_holiday(ATTR_STATE_ON)
    #     elif preset_mode == PRESET_BOOST:
    #         await self._api.device.set_advanced_mode(
    #             HA_PRESET_TO_DAIKIN[PRESET_BOOST], ATTR_STATE_ON
    #         )
    #     elif preset_mode == PRESET_ECO:
    #         await self._api.device.set_advanced_mode(
    #             HA_PRESET_TO_DAIKIN[PRESET_ECO], ATTR_STATE_ON
    #         )
    #     elif self.preset_mode == PRESET_AWAY:
    #         await self._api.device.set_holiday(ATTR_STATE_OFF)
    #     elif self.preset_mode == PRESET_BOOST:
    #         await self._api.device.set_advanced_mode(
    #             HA_PRESET_TO_DAIKIN[PRESET_BOOST], ATTR_STATE_OFF
    #         )
    #     elif self.preset_mode == PRESET_ECO:
    #         await self._api.device.set_advanced_mode(
    #             HA_PRESET_TO_DAIKIN[PRESET_ECO], ATTR_STATE_OFF
    #         )

    # @property
    # def preset_modes(self) -> list[str]:
    #     """List of available preset modes."""
    #     ret = [PRESET_NONE]
    #     if self._api.device.support_away_mode:
    #         ret.append(PRESET_AWAY)
    #     if self._api.device.support_advanced_modes:
    #         ret += [PRESET_ECO, PRESET_BOOST]
    #     return ret

    async def async_update(self) -> None:
        """Retrieve latest state."""
        # await self._irapi.getstatusall()

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._irapi.turnOn()

    async def async_turn_off(self) -> None:
        """Turn device off."""
        # await self._api.device.set(
        #     {HA_ATTR_TO_DAIKIN[ATTR_HVAC_MODE]: HA_STATE_TO_DAIKIN[HVACMode.OFF]}
        # )
        await self._irapi.turnOff()
