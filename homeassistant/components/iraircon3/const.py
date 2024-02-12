"""Constants used in other files."""
from __future__ import annotations

from typing import Final

DOMAIN = "iraircon3"
CONF_REMOTEID: Final = "remoteid"
CONF_APIREGION: Final = "apiregion"
CONF_APISECRET: Final = "apisecret"
CONF_DEVICEID: Final = "deviceid"
CONF_USERID: Final = "userid"


ATTR_TARGET_TEMPERATURE = "target_temperature"
ATTR_INSIDE_TEMPERATURE = "inside_temperature"
ATTR_OUTSIDE_TEMPERATURE = "outside_temperature"

ATTR_TARGET_HUMIDITY = "target_humidity"
ATTR_HUMIDITY = "humidity"

ATTR_STATE_ON = "on"
ATTR_STATE_OFF = "off"


TIMEOUT = 60
