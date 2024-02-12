"""Pydaikin base appliance, represent a Daikin device."""
from datetime import datetime
import logging
import re
import sys

from aiohttp import ClientSession, ServerDisconnectedError
from aiohttp.web_exceptions import HTTPForbidden
import tinytuya

_LOGGER = logging.getLogger(__name__)


class Appliance:
    """Daikin main appliance class."""

    TRANSLATIONS = {
        "mode": {
            "0": "wind_dry",
            "1": "heat",
            "2": "cold",
            "3": "auto",
            "4": "dehumidification",
        },
        "f_rate": {
            "0": "auto",
            "1": "low",
            "2": "mid",
            "3": "high",
        },
    }

    REGIONS = {
        "region": {
            "cn": "China",
            "us": "US West",
            "us-e": "US East",
            "eu": "Europe Central",
            "eu-w": "Europe West",
            "in": "India",
        }
    }

    VALUES_TRANSLATION = {}

    VALUES_SUMMARY = []

    INFO_RESOURCES = []

    @classmethod
    def daikin_to_human(cls, dimension, value):
        """Return converted values from Daikin to Human."""
        return cls.TRANSLATIONS.get(dimension, {}).get(value, str(value))

    @classmethod
    def human_to_daikin(cls, dimension, value):
        """Return converted values from Human to Daikin."""
        translations_rev = {
            dim: {v: k for k, v in item.items()}
            for dim, item in cls.TRANSLATIONS.items()
        }
        return translations_rev.get(dimension, {}).get(value, value)

    @classmethod
    def daikin_values(cls, dimension):
        """Return sorted list of translated values."""
        return sorted(list(cls.TRANSLATIONS.get(dimension, {}).values()))

    @staticmethod
    def parse_response(response_body):
        """Parse response from Daikin."""
        # {"code":1108,"msg":"uri path invalid","success":false,"t":1707541799382,"tid":"a36b19c1c7d211eeb129de51143dc9c3"}'
        response = dict(
            (match.group(1), match.group(2))
            for match in re.finditer(r"(\w+)=([^=]*)(?:,|$)", response_body)
        )
        _LOGGER.info("GOT: response body=%s ", response_body)
        # if "ret" not in response:
        #     raise ValueError("missing 'ret' field in response")
        # if response.pop("ret") != "OK":
        #     return {}
        # if "name" in response:
        #     response["name"] = unquote(response["name"])

        # # Translate swing mode from 2 parameters to 1 (Special case for certain models e.g Alira X)
        # if response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "0":
        #     response["f_dir"] = "0"
        # if response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "0":
        #     response["f_dir"] = "1"
        # if response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "S":
        #     response["f_dir"] = "2"
        # if response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "S":
        #     response["f_dir"] = "3"

        return response_body

    def __init__(
        self,
        device_id,
        session=None,
        apiKey=None,
        apiSecret=None,
        apiRegion=None,
        apiRemoteID=None,
        apiDeviceID=None,
        apiIPAddr=None,
    ):
        """Init the Heatpump appliance, representing one Daikin device."""
        self.session = session
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.apiRegion = apiRegion
        self.remoteID = apiRemoteID
        self.deviceID = apiDeviceID
        self.ipaddr = apiIPAddr
        self._c = None

        self.error = None

        if session:
            self.unitname = device_id
        else:
            self.unitname = None

    async def connect(self):
        """Connect to the cloud API."""
        try:
            # async with asyncio.timeout(60):
            self._c = await tinytuya.Cloud(
                apiRegion=self.apiRegion,
                apiKey=self.apiKey,
                apiSecret=self.apiSecret,
                apiDeviceID=self.deviceID,
            )
        except Exception:
            _LOGGER.info("Error assigning auth token to the self var")
            return False
        return True

    def __getitem__(self, name):
        """Return values from self.value."""
        if name in self.values:
            return self.values[name]
        raise AttributeError("No such attribute: " + name)

    async def init(self):
        """Init status."""
        # Re-defined in all sub-classes
        raise NotImplementedError

    async def _get_resource(self, resource, retries=3):
        """Update resource."""
        try:
            if self.session and not self.session.closed:
                return await self._run_get_resource(resource)
            async with ClientSession() as self.session:
                return await self._run_get_resource(resource)
        except ServerDisconnectedError as error:
            _LOGGER.info("ServerDisconnectedError %d", retries)
            if retries == 0:
                raise error
            return await self._get_resource(resource, retries=retries - 1)

    async def _run_get_resource(self, resource):
        """Make the http request."""
        self.headers = self.createHeaders()
        if self.headers is None:
            self.headers = self.createHeaders()
        url = self.urlhost + "/" + resource
        # async with self.session.get(
        #     f"{self.urlhost}/{resource}", headers=self.headers
        # ) as resp:
        #     return await self._handle_response(resp)

        async with self.session.get(url=url, headers=self.headers) as resp:
            return await self._handle_response(resp)

    async def _handle_response(self, resp):
        """Handle the http response."""
        _LOGGER.info(
            "GET: URL=%s HEADERS=%s response code=%d text=%s token=%s",
            self.urlhost,
            self.headers,
            resp.status,
            resp.text(),
            self.token,
        )
        if resp.status == 200:
            return self.parse_response(await resp.text())
        if resp.status == 403:
            raise HTTPForbidden
        return {}

    async def update_status(self, resources=None):
        """Update status from resources."""
        if resources is None:
            resources = self.INFO_RESOURCES
        resources = [
            resource
            for resource in resources
            if self.values.should_resource_be_updated(resource)
        ]
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update_by_resource(resource, await self._get_resource(resource))

        self._register_energy_consumption_history()

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = self.VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, val) = self.represent(key)
                print("%20s: %s" % (k, val))

    def log_sensors(self, file):
        """Log sensors to a file."""
        data = [
            ("datetime", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            ("in_temp", self.inside_temperature),
        ]
        if file.tell() == 0:
            file.write(",".join(k for k, _ in data))
            file.write("\n")
        file.write(",".join(str(v) for _, v in data))
        file.write("\n")
        file.flush()

    def show_sensors(self):
        """Print sensors."""
        data = [
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            f"in_temp={int(self.inside_temperature)}°C",
        ]
        print("  ".join(data))

    def represent(self, key):
        """Return translated value from key."""
        k = self.VALUES_TRANSLATION.get(key, key)

        # adapt the value
        val = self.values.get(key)

        if key == "mode" and self.values["pow"] == "0":
            val = "off"
        else:
            val = self.daikin_to_human(key, val)

        _LOGGER.log(logging.NOTSET, "Represent: %s, %s, %s", key, k, val)
        return (k, val)

    def _parse_number(self, dimension):
        """Parse float number."""
        try:
            return float(self.values.get(dimension))
        except (TypeError, ValueError):
            return None

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return "en_hol" in self.values

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return "f_rate" in self.values

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return "f_dir" in self.values

    @property
    def support_outside_temperature(self):
        """Return True if the device is not an AirBase unit."""
        return self.outside_temperature is not None

    @property
    def support_humidity(self):
        """Return True if the device has humidity sensor."""
        return False

    @property
    def support_advanced_modes(self):
        """Return True if the device supports advanced modes."""
        return "adv" in self.values

    @property
    def support_compressor_frequency(self):
        """Return True if the device supports compressor frequency."""
        return "cmpfreq" in self.values

    @property
    def support_energy_consumption(self):
        """Return True if the device supports energy consumption monitoring."""
        return super().support_energy_consumption

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return self._parse_number("otemp")

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        return self._parse_number("htemp")

    @property
    def target_temperature(self):
        """Return current target temperature."""
        return self._parse_number("stemp")

    @property
    def compressor_frequency(self):
        """Return current compressor frequency."""
        return self._parse_number("cmpfreq")

    @property
    def humidity(self):
        """Return current humidity."""
        return self._parse_number("hhum")

    @property
    def target_humidity(self):
        """Return target humidity."""
        return self._parse_number("shum")

    @property
    def fan_rate(self):
        """Return list of supported fan rates."""
        return list(map(str.title, self.TRANSLATIONS.get("f_rate", {}).values()))

    @property
    def swing_modes(self):
        """Return list of supported swing modes."""
        return list(map(str.title, self.TRANSLATIONS.get("f_dir", {}).values()))

    async def set(self, settings):
        """Set settings on Daikin device."""
        raise NotImplementedError

    async def set_holiday(self, mode):
        """Set holiday mode."""
        raise NotImplementedError

    async def set_advanced_mode(self, mode, value):
        """Enable or disable advanced modes."""
        raise NotImplementedError

    async def set_streamer(self, mode):
        """Enable or disable the streamer."""
        raise NotImplementedError

    @property
    def zones(self):
        """Return list of zones."""
        return

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""
        raise NotImplementedError

    def _send_msg(self, message):
        """Only interface to the send the command to the connection."""
        try:
            # commands2 = {"commands": [{"code": "switch", "value": "True"}]}
            sendmsg = self._c.cloudrequest(
                "/v1.0/devices/" + self.remoteID + "/commands", "POST", message
            )
        except Exception:
            serror = "Error: "
            sys.stderr.write(serror)
        # Now wait for reply
        return sendmsg

    @property
    def get_fanRates(self):
        """Return list of supported fan rates."""
        return list(map(str.title, self.TRANSLATIONS.get("f_rate", {}).values()))

    @property
    def getstatusall(self):
        """Get all of the status of the Air Con unit."""
        url = (
            "/v2.0/infrareds/"
            + self.deviceID
            + "/remotes/"
            + self.remoteID
            + "/ac/status"
        )
        remote_list = self._c.cloudrequest(url)
        result = remote_list["result"]
        return result

    @property
    def getstatuspower(self):
        """Get the power status of the Air Con unit."""
        url2 = (
            "/v2.0/infrareds/"
            + self.deviceID
            + "/remotes/"
            + self.remoteID
            + "/ac/status"
        )
        print(url2)
        remote_list = self._c.cloudrequest(url=url2)
        result2 = remote_list["result"]["power"]
        return result2

    @property
    def getstatustemp(self):
        """Get the temperature status of the Air Con unit."""
        url2 = (
            "/v2.0/infrareds/"
            + self.deviceID
            + "/remotes/"
            + self.remoteID
            + "/ac/status"
        )
        print(url2)
        remote_list = self._c.cloudrequest(url2)
        result2 = remote_list["result"]["temp"]
        return result2

    @property
    def getstatusfan(self):
        """Get the fan status of the Air Con unit."""
        url = (
            "/v2.0/infrareds/"
            + self.deviceID
            + "/remotes/"
            + self.remoteID
            + "/ac/status"
        )
        remote_list = self._c.cloudrequest(url)
        result2 = remote_list["result"]["wind"]
        if result2 == 0:
            msg = "low"
        elif result2 == 1:
            msg = "mid"
        elif result2 == 2:
            msg = "high"
        elif result2 == 3:
            msg = "auto"
        else:
            msg = "Error Converting value "
        return msg

    @property
    def getstatusmode(self):
        """Get the mode status of the Air Con unit."""
        url = (
            "/v2.0/infrareds/"
            + self.deviceID
            + "/remotes/"
            + self.remoteID
            + "/ac/status"
        )
        remote_list = self._c.cloudrequest(url)
        result2 = remote_list["result"]["mode"]
        if result2 == 0:
            msg = "dehumidification"
        elif result2 == 1:
            msg = "cold"
        elif result2 == 2:
            msg = "auto"
        elif result2 == 3:
            msg = "fan"
        elif result2 == 4:
            msg = "heat"
        else:
            msg = "Error Converting value "
        return msg

    def set_target_temp(self, temperature):
        """Set the target temperature, to the requested int."""
        if 35 < temperature < 18:
            logging.info("Refusing to set temp outside of allowed range")
            return False
        else:
            data = {}
            data["code"] = "temp"
            data["value"] = temperature
            cmds = {}
            cmds["commands"] = [data]
            self._send_msg(cmds)
            return True

    def turnOn(self):
        """Set the unit on."""
        msgsend = {"commands": [{"code": "switch", "value": "True"}]}
        self._send_msg(msgsend)
        return True

    def turnOff(self):
        """Set the unit on."""
        msgsend = {"commands": [{"code": "switch", "value": "False"}]}
        self._send_msg(msgsend)
        return True

    def switchToCool(self):
        """Set the unit to cool mode."""
        msgsend = {"commands": [{"code": "mode", "value": "cold"}]}
        self._send_msg(msgsend)
        return True

    def switchToHeat(self):
        """Set the unit to cool mode."""
        msgsend = {"commands": [{"code": "mode", "value": "heat"}]}
        self._send_msg(msgsend)
        return True

    def switchToFan(self):
        """Set the unit to cool mode."""
        msgsend = {"commands": [{"code": "mode", "value": "wind_dry"}]}
        self._send_msg(msgsend)
        return True

    def switchToDeHumid(self):
        """Set the unit to cool mode."""
        msgsend = {"commands": [{"code": "mode", "value": "dehumidification"}]}
        self._send_msg(msgsend)
        return True

    def changeMode(self, airmode):
        """Change the fan speed."""
        if airmode == "low":
            msgsend = {"commands": [{"code": "fan", "value": "low"}]}
        elif airmode == "mid":
            msgsend = {"commands": [{"code": "fan", "value": "mid"}]}
        elif airmode == "high":
            msgsend = {"commands": [{"code": "fan", "value": "high"}]}
        elif airmode == "auto":
            msgsend = {"commands": [{"code": "fan", "value": "auto"}]}
        else:
            sys.stderr.write("Please use low, mid, high or auto as options")
            return False

        self._send_msg(msgsend)
        return True

    def changeFanSpeed(self, fanmode):
        """Change the fan speed."""
        if fanmode == "low":
            msgsend = {"commands": [{"code": "fan", "value": "low"}]}
        elif fanmode == "mid":
            msgsend = {"commands": [{"code": "fan", "value": "mid"}]}
        elif fanmode == "high":
            msgsend = {"commands": [{"code": "fan", "value": "high"}]}
        elif fanmode == "auto":
            msgsend = {"commands": [{"code": "fan", "value": "auto"}]}
        else:
            sys.stderr.write("Please use low, mid, high or auto as options")
            return False

        self._send_msg(msgsend)
        return True
