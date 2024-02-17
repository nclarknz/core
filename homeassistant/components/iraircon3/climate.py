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
from homeassistant.components.climate.const import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.components.template.const import CONF_AVAILABILITY_TEMPLATE
from homeassistant.components.template.template_entity import TemplateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    CONF_UNIQUE_ID,
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
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_TEMPERATURE_STEP,
    CONF_TEMPUNIT,
)
from .IRaircon import cloud_api

CONF_FAN_MODE_LIST = "fan_modes"
CONF_MODE_LIST = "modes"
CONF_SWING_MODE_LIST = "swing_modes"
CONF_PRECISION = "precision"
CONF_CURRENT_TEMP_TEMPLATE = "current_temperature_template"

CONF_CURRENT_HUMIDITY_TEMPLATE = "current_humidity_template"
CONF_TARGET_TEMPERATURE_TEMPLATE = "target_temperature_template"
CONF_TARGET_TEMPERATURE_HIGH_TEMPLATE = "target_temperature_high_template"
CONF_TARGET_TEMPERATURE_LOW_TEMPLATE = "target_temperature_low_template"
CONF_HVAC_MODE_TEMPLATE = "hvac_mode_template"
CONF_FAN_MODE_TEMPLATE = "fan_mode_template"
CONF_SWING_MODE_TEMPLATE = "swing_mode_template"
CONF_HVAC_ACTION_TEMPLATE = "hvac_action_template"

CONF_SET_TEMPERATURE_ACTION = "set_temperature"
CONF_SET_HVAC_MODE_ACTION = "set_hvac_mode"
CONF_SET_FAN_MODE_ACTION = "set_fan_mode"
CONF_SET_SWING_MODE_ACTION = "set_swing_mode"

CONF_CLIMATES = "climates"

DEFAULT_NAME = "Heatpump"
DEFAULT_PRECISION = 1.0
_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
        vol.Optional(CONF_CURRENT_TEMP_TEMPLATE): cv.template,
        vol.Optional(CONF_CURRENT_HUMIDITY_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMPERATURE_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMPERATURE_HIGH_TEMPLATE): cv.template,
        vol.Optional(CONF_TARGET_TEMPERATURE_LOW_TEMPLATE): cv.template,
        vol.Optional(CONF_HVAC_MODE_TEMPLATE): cv.template,
        vol.Optional(CONF_FAN_MODE_TEMPLATE): cv.template,
        vol.Optional(CONF_SWING_MODE_TEMPLATE): cv.template,
        vol.Optional(CONF_HVAC_ACTION_TEMPLATE): cv.template,
        vol.Optional(CONF_SET_TEMPERATURE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_HVAC_MODE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_FAN_MODE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_SWING_MODE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(
            CONF_MODE_LIST,
            default=[
                HVACMode.AUTO,
                HVACMode.OFF,
                HVACMode.COOL,
                HVACMode.HEAT,
                HVACMode.DRY,
                HVACMode.FAN_ONLY,
            ],
        ): cv.ensure_list,
        vol.Optional(
            CONF_FAN_MODE_LIST,
            default=[FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH],
        ): cv.ensure_list,
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMPUNIT, default="Celsius"): cv.string,
        vol.Optional(CONF_TEMPERATURE_STEP, default=DEFAULT_PRECISION): vol.Coerce(
            float
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
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

HA_FANSTATE_TO_DAIKIN = {
    FAN_AUTO: "auto",
    FAN_HIGH: "high",
    FAN_LOW: "low",
    FAN_MEDIUM: "mid",
}

DAIKIN_TO_HA_FANSTATE = {
    "auto": FAN_AUTO,
    "high": FAN_HIGH,
    "low": FAN_LOW,
    "mid": FAN_MEDIUM,
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Daikin climate based on config_entry."""
    # confApiRegion = entry.data["apiregion"]
    # confDeviceID = entry.data["deviceid"]
    # confRemoteID = entry.data["remoteid"]
    # confUserId = entry.data["userid"]
    # confApiKey = entry.data["api_key"]
    # confApiSecret = entry.data["apisecret"]
    # daikin_api = entry.entry_id

    irapi = cloud_api.TuyaCloudApi(hass, entry.data)

    await irapi.async_get_access_token()

    entities = []
    entities.append(DaikinIRClimate(hass, irapi, entry))
    async_add_entities(entities)


def format_target_temperature(target_temperature: float) -> str:
    """Format target temperature to be sent to the Daikin unit, rounding to nearest half degree."""
    return str(round(float(target_temperature) * 2, 0) / 2).rstrip("0").rstrip(".")


class DaikinIRClimate(TemplateEntity, ClimateEntity):
    """Representation of a Daikin HVAC."""

    _attr_name = None
    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = list(HA_STATE_TO_DAIKIN)
    _attr_target_temperature_step = 1
    # _attr_fan_modes: list[str]
    # _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, hass, irapi: cloud_api.TuyaCloudApi, config: ConfigType) -> None:
        """Initialize the climate device."""
        super().__init__(
            hass,
            availability_template=config.data.get(CONF_AVAILABILITY_TEMPLATE),
            icon_template=config.data.get(CONF_ICON_TEMPLATE),
            entity_picture_template=config.data.get(CONF_ENTITY_PICTURE_TEMPLATE),
        )
        self._config = config
        self._attr_unique_id = config.data.get(CONF_UNIQUE_ID, None)
        self._attr_name = config.data[CONF_NAME]
        self._attr_min_temp = config.data[CONF_MIN_TEMP]
        self._attr_max_temp = config.data[CONF_MAX_TEMP]
        self._attr_target_temperature_step = config.data[CONF_TEMPERATURE_STEP]
        self._attr_precision = config.data.get("target_precision")
        self._attr_current_temp = None
        self._attr_target_temperature = None
        self._attr_current_humidity = None
        self._remoteID = irapi.remoteID
        self._irapi = irapi

        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = list(HA_STATE_TO_DAIKIN)
        self._attr_fan_mode = None
        self._attr_fan_modes = list(HA_FANSTATE_TO_DAIKIN)

        self._list: dict[str, list[Any]] = {
            ATTR_HVAC_MODE: self._attr_hvac_modes,
            ATTR_FAN_MODE: self._attr_fan_modes,
        }
        # self._current_temp_template = config.data.get(CONF_CURRENT_TEMP_TEMPLATE)
        # self._current_humidity_template = config.data.get(
        #     CONF_CURRENT_HUMIDITY_TEMPLATE
        # )
        self._target_temperature_template = config.data.get(
            CONF_TARGET_TEMPERATURE_TEMPLATE
        )
        self._target_temperature_high_template = config.data.get(
            CONF_TARGET_TEMPERATURE_HIGH_TEMPLATE
        )
        self._target_temperature_low_template = config.data.get(
            CONF_TARGET_TEMPERATURE_LOW_TEMPLATE
        )
        self._hvac_mode_template = config.data.get(CONF_HVAC_MODE_TEMPLATE)
        self._fan_mode_template = config.data.get(CONF_FAN_MODE_TEMPLATE)
        self._hvac_action_template = config.data.get(CONF_HVAC_ACTION_TEMPLATE)
        self._attr_available = True
        self._available = True
        self._unit_of_measurement = hass.config.units.temperature_unit
        # self._unit_of_measurement = config.data.get(CONF_TEMPUNIT)
        # self._attr_hvac_modes = config.data[CONF_MODE_LIST]
        # self._attr_fan_modes = config.data[CONF_FAN_MODE_LIST]

        self._current_temp = None

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
        )

        # self._attr_supported_features |= ClimateEntityFeature.FAN_MODE

    async def getPowerStatus(self):
        """Get the current powersttaus of heatpump."""

        res = await self._irapi.get_StatusObject("power")
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
            elif attr == ATTR_TEMPERATURE:
                # temperature
                try:
                    values[
                        HA_ATTR_TO_DAIKIN[ATTR_TARGET_TEMPERATURE]
                    ] = format_target_temperature(value)
                    await self._irapi.async_set_temperature(value)
                except ValueError:
                    _LOGGER.error("Invalid temperature %s", value)
            elif value in self._list[attr]:
                # values[daikin_attr] = value.lower()
                if attr == ATTR_HVAC_MODE:
                    if (daikin_attr := HA_ATTR_TO_DAIKIN.get(attr)) is not None:
                        values[daikin_attr] = HA_STATE_TO_DAIKIN[value]
                        hvacmode = values[daikin_attr]
                        self._attr_hvac_mode = value
                        await self._irapi.async_set_hvac_mode(hvacmode)
                # fan speed
                elif attr == ATTR_FAN_MODE:
                    try:
                        fanmode = HA_FANSTATE_TO_DAIKIN[value]
                        values[HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE]] = value
                        await self._irapi.async_set_fan_mode(fanmode)
                    except ValueError:
                        _LOGGER.error("Invalid fan speed %s", value)
            else:
                _LOGGER.error("Invalid value %s for %s", attr, value)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._remoteID

    @property
    def current_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return None

    # @property
    # async def async_current_temperature(self) -> float | None:
    #     """Return the current temperature."""
    #     res = await self._irapi.get_StatusObject("temperature")
    #     _LOGGER.info("Current temp returned : %s ", res)
    #     if res != "ok":
    #         _LOGGER.error("Cloud API connection failed: %s", res)
    #         return cloud_api, {"reason": "authentication_failed", "msg": res}
    #     # return float(res)
    #     return int(res)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._attr_target_temperature

    @property
    async def async_target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        res = await self._irapi.get_StatusObject("temperature")
        if res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
            return cloud_api, {"reason": "authentication_failed", "msg": res}
        return res, {}

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self._set(kwargs)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current state."""
        ret = HA_STATE_TO_CURRENT_HVAC.get(self._attr_hvac_mode)
        if ret in (HVACAction.COOLING, HVACAction.HEATING):
            return HVACAction.IDLE
        return ret

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation ie. heat, cool, idle."""
        # daikin_mode = self._api.device.represent(HA_ATTR_TO_DAIKIN[ATTR_HVAC_MODE])[1]
        # daikin_mode = await self._irapi.get_StatusObject("mode")
        return self._attr_hvac_mode
        # return DAIKIN_TO_HA_STATE.get(daikin_mode, HVACMode.HEAT_COOL)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        await self._set({ATTR_HVAC_MODE: hvac_mode})

    @property
    async def async_get_fan_mode(self) -> str:
        """Return the fan setting."""
        res = await self._irapi.get_StatusObject("fan")
        if res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
            return cloud_api, {"reason": "authentication_failed", "msg": res}
        return res, {}
        # return self._api.device.represent(HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE])[1].title()
        # return self._irapi.getstatusfan(HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE])[1].title()

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
        # await self._irapi.get_StatusObject("power")
        temp = await self._irapi.get_StatusObject("temperature")
        self._attr_target_temperature = float(temp)
        hvacmode = await self._irapi.get_StatusObject("mode")
        hvacmodeha = DAIKIN_TO_HA_STATE[hvacmode]
        self._attr_hvac_mode = hvacmodeha
        return True

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._irapi.turnOn()
        return True

    async def async_turn_off(self) -> None:
        """Turn device off."""
        # await self._api.device.set(
        #     {HA_ATTR_TO_DAIKIN[ATTR_HVAC_MODE]: HA_STATE_TO_DAIKIN[HVACMode.OFF]}
        # )
        await self._irapi.turnOff()
        return True
