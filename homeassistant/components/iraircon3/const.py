"""Constants used in other files."""
from __future__ import annotations

from typing import Final

DOMAIN = "iraircon3"
CONF_REMOTEID: Final = "remoteid"
CONF_APIREGION: Final = "apiregion"
CONF_APISECRET: Final = "apisecret"
CONF_DEVICEID: Final = "deviceid"
CONF_USERID: Final = "userid"


# climate
CONF_TARGET_TEMPERATURE = "target_temperature"
CONF_CURRENT_TEMPERATURE = "current_temperature"
CONF_TEMPERATURE_STEP = "temperature_step"
CONF_TEMPUNIT: Final = "TemperatureUnit"
CONF_MAX_TEMP = "max_temperature"
CONF_MIN_TEMP = "min_temperature"
CONF_PRECISION = "precision"
CONF_TARGET_PRECISION = "target_precision"
CONF_HVAC_MODE_DP = "hvac_mode_dp"
CONF_HVAC_MODE_SET = "hvac_mode_set"
CONF_PRESET_DP = "preset_dp"
CONF_PRESET_SET = "preset_set"
CONF_HEURISTIC_ACTION = "heuristic_action"
CONF_HVAC_ACTION_DP = "hvac_action_dp"
CONF_HVAC_ACTION_SET = "hvac_action_set"

ATTR_TARGET_TEMPERATURE = "target_temperature"
ATTR_INSIDE_TEMPERATURE = "inside_temperature"
ATTR_OUTSIDE_TEMPERATURE = "outside_temperature"

ATTR_TARGET_HUMIDITY = "target_humidity"
ATTR_HUMIDITY = "humidity"

ATTR_STATE_ON = "on"
ATTR_STATE_OFF = "off"


TIMEOUT = 60
