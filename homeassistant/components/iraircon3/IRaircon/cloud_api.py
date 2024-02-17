"""Class to perform requests to Tuya Cloud APIs."""
import functools
import hashlib
import hmac
import json
import logging
import time

import requests

_LOGGER = logging.getLogger(__name__)


# Signature algorithm.
def calc_sign(msg, key):
    """Calculate signature for request."""
    sign = (
        hmac.new(
            msg=bytes(msg, "latin-1"),
            key=bytes(key, "latin-1"),
            digestmod=hashlib.sha256,
        )
        .hexdigest()
        .upper()
    )
    return sign


class TuyaCloudApi:
    """Class to send API calls."""

    TRANSLATIONS = {
        "mode": {
            "0": "cold",
            "1": "heat",
            "2": "auto",
            "3": "wind_dry",
            "4": "dehumidification",
            "5": "off",
        },
        "f_rate": {
            "0": "auto",
            "1": "low",
            "2": "mid",
            "3": "high",
        },
    }

    def __init__(
        self,
        hass,
        configdata,
    ) -> None:
        """Initialize the class."""
        region_code = configdata.get("apiregion")
        device_id = configdata.get("deviceid")
        remote_id = configdata.get("remoteid")
        if device_id is None:
            self.deviceID = None
        else:
            self.deviceID = device_id
        if remote_id is None:
            self.remoteID = None
        else:
            self.remoteID = remote_id
        self._hass = hass
        self._base_url = f"https://openapi.tuya{region_code}.com"
        self.urlcmd = f"/v1.0/devices/{remote_id}/commands"
        self._client_id = configdata.get("api_key")
        self._secret = configdata.get("apisecret")
        self._user_id = configdata.get("userid")
        self._access_token = ""
        self.timestamp = None
        self.device_list = {}
        self.hvacmode = None
        self.fanmode = None
        self.currTemp = None
        self.mintemp = configdata.get("min_temperature")
        self.maxtemp = configdata.get("max_temperature")

    def generate_payload(self, method, timestamp, url, headers, body=None):
        """Generate signed payload for requests."""
        payload = self._client_id + self._access_token + timestamp

        payload += method + "\n"
        # Content-SHA256
        if body is not None:
            data = json.dumps(body)
            dataenc = data.encode("utf-8")
            databytes = bytes(dataenc)
            sha1_hash = hashlib.sha256(databytes).hexdigest()
            payload += sha1_hash
        else:
            payload += hashlib.sha256(bytes((body or "").encode("utf-8"))).hexdigest()

        payload += (
            "\n"
            + "".join(
                [
                    "%s:%s\n" % (key, headers[key])  # Headers
                    for key in headers.get("Signature-Headers", "").split(":")
                    if key in headers
                ]
            )
            + "\n/"
            + url.split("//", 1)[-1].split("/", 1)[-1]  # Url
        )
        # _LOGGER.debug("PAYLOAD: %s", payload)
        return payload

    async def async_make_request(self, method, url, body=None, headers={}):
        """Perform requests."""
        self.timestamp = str(int(time.time() * 1000))
        payload = self.generate_payload(method, self.timestamp, url, headers, body)
        default_par = {
            "client_id": self._client_id,
            "access_token": self._access_token,
            "sign": calc_sign(payload, self._secret),
            "t": self.timestamp,
            "sign_method": "HMAC-SHA256",
        }
        full_url = self._base_url + url
        # _LOGGER.debug("\n" + method + ": [%s]", full_url)

        if method == "GET":
            func = functools.partial(
                requests.get, full_url, headers=dict(default_par, **headers)
            )
        elif method == "POST":
            func = functools.partial(
                requests.post,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
            )
            # _LOGGER.debug("BODY: [%s]", body)
        elif method == "PUT":
            func = functools.partial(
                requests.put,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
            )

        resp = await self._hass.async_add_executor_job(func)
        # r = json.dumps(r.json(), indent=2, ensure_ascii=False) # Beautify the format
        return resp

    async def async_get_access_token(self):
        """Obtain a valid access token."""
        try:
            resp = await self.async_make_request("GET", "/v1.0/token?grant_type=1")
        except requests.exceptions.ConnectionError:
            return "Request failed, status ConnectionError"

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            return f"Error {r_json['code']}: {r_json['msg']}"

        self._access_token = resp.json()["result"]["access_token"]
        return "ok"

    async def async_get_devices_list(self):
        """Obtain the list of devices associated to a user."""
        resp = await self.async_make_request(
            "GET", url=f"/v1.0/users/{self._user_id}/devices"
        )

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            # _LOGGER.debug(
            #     "Request failed, reply is %s",
            #     json.dumps(r_json, indent=2, ensure_ascii=False)
            # )
            return f"Error {r_json['code']}: {r_json['msg']}"

        self.device_list = {dev["id"]: dev for dev in r_json["result"]}
        # _LOGGER.debug("DEV_LIST: %s", self.device_list)

        return "ok"

    async def get_StatusObject(self, obj):
        """Get status of a single object."""

        timestamp = str(int(time.time() * 1000))
        if (int(timestamp) - int(self.timestamp)) > 1000:
            await self.async_get_access_token()

        resp = await self.async_make_request(
            "GET",
            url=f"/v2.0/infrareds/{self.deviceID}/remotes/{self.remoteID}/ac/status",
        )

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            # _LOGGER.debug(
            #     "Request failed, reply is %s",
            #     json.dumps(r_json, indent=2, ensure_ascii=False)
            # )
            return f"Error {r_json['code']}: {r_json['msg']}"
        result2 = None
        if obj == "power":
            result2 = r_json["result"]["power"]
        elif obj == "temperature":
            result2 = float(r_json["result"]["temp"])
        elif obj == "mode":
            result = r_json["result"]["mode"]
            result2 = self.TRANSLATIONS["mode"][result]
            self.hvacmode = result2
        elif obj == "fan":
            result = r_json["result"]["wind"]
            result2 = self.TRANSLATIONS["f_rate"][result]
            self.fanmode = result2
        else:
            result2 = "Error Getting Result"

        return result2

    def get_supported_fanRates(self):
        """Return list of supported fan rates."""
        return list(map(str.title, self.TRANSLATIONS.get("f_rate", {}).values()))

    def get_supported_modes(self):
        """Return list of supported heatpump modes."""
        return list(map(str.title, self.TRANSLATIONS.get("mode", {}).values()))

    async def turnOn(self):
        """Turn on the unit."""
        msgsend = {"commands": [{"code": "switch", "value": "True"}]}
        resp = await self.async_make_request("POST", self.urlcmd, msgsend)
        # self._send_msg(msgsend)
        r_json = resp.json()
        if r_json["success"] is not True:
            _LOGGER.debug(
                "Request failed, reply is %s",
                json.dumps(r_json, indent=2, ensure_ascii=False),
            )
            return f"Error {r_json['code']}: {r_json['msg']}"

        await self.get_StatusObject("mode")
        return r_json

    async def turnOff(self):
        """Turn off the unit."""
        msgsend = {"commands": [{"code": "switch", "value": "False"}]}
        resp = await self.async_make_request("POST", self.urlcmd, msgsend)

        r_json = resp.json()
        if r_json["success"] is not True:
            _LOGGER.debug(
                "Request failed, reply is %s",
                json.dumps(r_json, indent=2, ensure_ascii=False),
            )
            return f"Error {r_json['code']}: {r_json['msg']}"
        self.hvacmode = "off"
        return r_json

    async def async_set_temperature(self, temperature):
        """Set the temperature of the unit."""
        if int(self.maxtemp) < int(temperature) < int(self.mintemp):
            logging.info("Refusing to set temp outside of allowed range")
            return False
        else:
            data = {}
            data["code"] = "temp"
            data["value"] = temperature
            cmds = {}
            cmds["commands"] = [data]

        resp = await self.async_make_request("POST", self.urlcmd, cmds)

        r_json = resp.json()
        if r_json["success"] is not True:
            _LOGGER.debug(
                "Request failed, reply is %s",
                json.dumps(r_json, indent=2, ensure_ascii=False),
            )
            return f"Error {r_json['code']}: {r_json['msg']}"
        self.currTemp = temperature
        return r_json

    async def async_set_fan_mode(self, airmode):
        """Change the heatpump mode."""
        if airmode == "low":
            msgsend = {"commands": [{"code": "fan", "value": "low"}]}
        elif airmode == "mid":
            msgsend = {"commands": [{"code": "fan", "value": "mid"}]}
        elif airmode == "high":
            msgsend = {"commands": [{"code": "fan", "value": "high"}]}
        elif airmode == "auto":
            msgsend = {"commands": [{"code": "fan", "value": "auto"}]}
        else:
            return False

        resp = await self.async_make_request("POST", self.urlcmd, msgsend)

        r_json = resp.json()
        if r_json["success"] is not True:
            _LOGGER.debug(
                "Request failed, reply is %s",
                json.dumps(r_json, indent=2, ensure_ascii=False),
            )
            return f"Error {r_json['code']}: {r_json['msg']}"
        self.fanmode = airmode
        return r_json

    async def async_set_hvac_mode(self, airmode):
        """Change the heatpump mode."""
        if airmode == "wind_dry":
            msgsend = {"commands": [{"code": "mode", "value": "wind_dry"}]}
        elif airmode == "cold":
            msgsend = {"commands": [{"code": "mode", "value": "cold"}]}
        elif airmode == "heat":
            msgsend = {"commands": [{"code": "mode", "value": "heat"}]}
        elif airmode == "dehumidification":
            msgsend = {"commands": [{"code": "mode", "value": "dehumidification"}]}
        elif airmode == "auto":
            msgsend = {"commands": [{"code": "mode", "value": "auto"}]}
        else:
            return False

        resp = await self.async_make_request("POST", self.urlcmd, msgsend)

        r_json = resp.json()
        if r_json["success"] is not True:
            _LOGGER.debug(
                "Request failed, reply is %s",
                json.dumps(r_json, indent=2, ensure_ascii=False),
            )
            return f"Error {r_json['code']}: {r_json['msg']}"
        self.hvacmode = airmode
        return r_json

    # async def async_set_target_temp(self, temperature):
    #     """Set the target temperature, to the requested int."""
    #     if int(self.maxtemp) < int(temperature) < int(self.mintemp):
    #         logging.info("Refusing to set temp outside of allowed range")
    #         return False
    #     else:
    #         data = {}
    #         data["code"] = "temp"
    #         data["value"] = temperature
    #         cmds = {}
    #         cmds["commands"] = [data]

    #     resp = await self.async_make_request("POST", self.urlcmd, cmds)

    #     r_json = resp.json()
    #     if r_json["success"] is not True:
    #         _LOGGER.debug(
    #             "Request failed, reply is %s",
    #             json.dumps(r_json, indent=2, ensure_ascii=False),
    #         )
    #         return f"Error {r_json['code']}: {r_json['msg']}"
    #     self.currTemp = temperature
    #     return r_json
