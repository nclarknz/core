"""Platform for the Daikin AC."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientConnectionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

# from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.util import Throttle

from .const import DOMAIN
from .IRaircon.cloud_api import TuyaCloudApi

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

PLATFORMS = [Platform.CLIMATE]

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Establish connection with Daikin."""
    conf = entry.data
    # For backwards compat, set unique ID
    if entry.unique_id is None or ".local" in entry.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=conf[CONF_API_KEY])

    cloud_api, res = await attempt_cloud_connection(hass, entry.data)

    if not cloud_api:
        return False

    # await async_migrate_unique_id(hass, entry, cloud_api)

    hass.data.setdefault(DOMAIN, {}).update({entry.entry_id: cloud_api})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok


async def attempt_cloud_connection(hass, entrydata):
    """Create device."""
    cloud_api = TuyaCloudApi(hass, entrydata)

    res = await cloud_api.async_get_access_token()
    if res != "ok":
        _LOGGER.error("Cloud API connection failed: %s", res)
        return cloud_api, {"reason": "authentication_failed", "msg": res}

    res = await cloud_api.async_get_devices_list()
    if res != "ok":
        _LOGGER.error("Cloud API get_devices_list failed: %s", res)
        return cloud_api, {"reason": "device_list_failed", "msg": res}
    _LOGGER.info("Cloud API connection succeeded")

    return cloud_api, {}


class DaikinApi:
    """Keep the Daikin instance in one place and centralize the update."""

    def __init__(self, init_token) -> None:
        """Initialize the Daikin Handle."""
        # self.device = device
        self.name = "DAIKIN HEATPUMP"
        self.ip_address = "192.168.1.163"
        self._available = True
        self.token = init_token

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs: Any) -> None:
        """Pull the latest data from Daikin."""
        try:
            # await self.device.update_status()
            self._available = True
        except ClientConnectionError:
            _LOGGER.warning("Connection failed for %s", self.ip_address)
            self._available = False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        # info = self.device.values
        return DeviceInfo(
            connections=None,
            manufacturer="Daikin",
            model="model",
            name="name",
            sw_version="1.1",
        )


async def async_migrate_unique_id(
    hass: HomeAssistant, config_entry: ConfigEntry, api: TuyaCloudApi
) -> None:
    """Migrate old entry."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    old_unique_id = config_entry.unique_id
    new_unique_id = "DFSDFSDFSDAFSADFSDFSDFS"
    new_mac = "FF:FF:FF:FF:FF"
    # new_mac = dr.format_mac(new_unique_id)
    # new_name = api.name
    new_name = "Lounge Daikin"

    @callback
    def _update_unique_id(entity_entry: er.RegistryEntry) -> dict[str, str] | None:
        """Update unique ID of entity entry."""
        return update_unique_id(entity_entry, new_unique_id)

    if new_unique_id == old_unique_id:
        return
    duplicate = None
    # duplicate = dev_reg.async_get_device(
    #     connections={(CONNECTION_NETWORK_MAC, new_mac)}, identifiers=None
    # )

    # Remove duplicated device
    if duplicate is not None:
        if config_entry.entry_id in duplicate.config_entries:
            _LOGGER.debug(
                "Removing duplicated device %s",
                duplicate.name,
            )

            # The automatic cleanup in entity registry is scheduled as a task, remove
            # the entities manually to avoid unique_id collision when the entities
            # are migrated.
            duplicate_entities = er.async_entries_for_device(
                ent_reg, duplicate.id, True
            )
            for entity in duplicate_entities:
                if entity.config_entry_id == config_entry.entry_id:
                    ent_reg.async_remove(entity.entity_id)

            dev_reg.async_update_device(
                duplicate.id, remove_config_entry_id=config_entry.entry_id
            )

    # Migrate devices
    for device_entry in dr.async_entries_for_config_entry(
        dev_reg, config_entry.entry_id
    ):
        for connection in device_entry.connections:
            if connection[1] == old_unique_id:
                new_connections = {(CONNECTION_NETWORK_MAC, new_mac)}

                _LOGGER.debug(
                    "Migrating device %s connections to %s",
                    device_entry.name,
                    new_connections,
                )
                dev_reg.async_update_device(
                    device_entry.id,
                    merge_connections=new_connections,
                )

        if device_entry.name is None:
            _LOGGER.debug(
                "Migrating device name to %s",
                new_name,
            )
            dev_reg.async_update_device(
                device_entry.id,
                name=new_name,
            )

        # Migrate entities
        await er.async_migrate_entries(hass, config_entry.entry_id, _update_unique_id)

        new_data = {**config_entry.data}

        hass.config_entries.async_update_entry(
            config_entry, unique_id=new_unique_id, data=new_data
        )


@callback
def update_unique_id(
    entity_entry: er.RegistryEntry, unique_id: str
) -> dict[str, str] | None:
    """Update unique ID of entity entry."""
    if entity_entry.unique_id.startswith(unique_id):
        # Already correct, nothing to do
        return None

    unique_id_parts = entity_entry.unique_id.split("-")
    unique_id_parts[0] = unique_id
    entity_new_unique_id = "-".join(unique_id_parts)

    _LOGGER.debug(
        "Migrating entity %s from %s to new id %s",
        entity_entry.entity_id,
        entity_entry.unique_id,
        entity_new_unique_id,
    )
    return {"new_unique_id": entity_new_unique_id}
