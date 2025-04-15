"""Support for Dyson cloud account."""

import logging

from custom_components.dyson_local import DOMAIN as DYSON_LOCAL_DOMAIN
from libdyson.cloud import DysonAccount
from libdyson.cloud.account import DysonAccountCN
from libdyson.exceptions import DysonNetworkError

from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_AUTH, CONF_REGION, DATA_ACCOUNT, DATA_DEVICES, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["camera"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Dyson integration."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dyson from a config entry."""
    # Get devices list
    if entry.data[CONF_REGION] == "CN":
        account = DysonAccountCN(entry.data[CONF_AUTH])
    else:
        account = DysonAccount(entry.data[CONF_AUTH])
    try:
        devices = await hass.async_add_executor_job(account.devices)
    except DysonNetworkError as err:
        _LOGGER.error("Cannot connect to Dyson cloud service")
        raise ConfigEntryNotReady from err

    for device in devices:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DYSON_LOCAL_DOMAIN,
                context={"source": SOURCE_DISCOVERY},
                data=device,
            )
        )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ACCOUNT: account,
        DATA_DEVICES: devices,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Dyson cloud."""
    # Nothing needs clean up
    return True
