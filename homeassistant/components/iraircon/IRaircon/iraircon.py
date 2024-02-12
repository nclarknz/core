"""Control the IR Air Con unit."""

import asyncio
import logging
import sys

# from . import constants
# import importlib_resources
import tinytuya

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class IRAirCon:
    """Initialises a IR Air Con, by taking a device ID and ip addr and other setup Info."""

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

    def __init__(
        self, deviceID, ipaddr, apiregion, apikey, apisecret, remoteID
    ) -> None:
        """Start the init of the unit."""
        self.deviceID = deviceID
        self._ipaddr = ipaddr
        self._apiRegion = apiregion
        self._apiKey = apikey
        self._apiSecret = apisecret
        self.remoteID = remoteID
        self._c = None

    async def _connect(self):
        """Connect to the cloud API."""
        try:
            async with asyncio.timeout(10):
                self._c = await tinytuya.Cloud(
                    self._apiRegion, self._apiKey, self._apiSecret, self.remoteID
                )
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout calling IRAiRCon TUYA Api to get auth token")
            return False
        except Exception:
            _LOGGER.error("Error assigning auth token to the self var")
            return False
        return True

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

    def get_fanRates(self):
        """Return list of supported fan rates."""
        return list(map(str.title, self.TRANSLATIONS.get("f_rate", {}).values()))

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
