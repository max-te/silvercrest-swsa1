"""
Platform for Silvercrest SWS A1 Wifi Switches
"""

import asyncio
from asyncio.transports import DatagramTransport
from typing_extensions import override
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.silvercrest.switch import UDP_PORT

from .const import PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    _ = await async_unload_entry(hass, entry)
    _ = await async_setup_entry(hass, entry)


SEARCH_ALL_DATAGRAM = b"\x25\xff\xff\xff\xff\xff\xff\x02\x02"
BROADCAST = ("255.255.255.255", UDP_PORT)


class SilvercrestDiscoveryProtocol(asyncio.DatagramProtocol):
    transport: DatagramTransport | None = None

    def __init__(self):
        pass

    @override
    def connection_made(self, transport: DatagramTransport):
        self.transport = transport
        self.transport.sendto()


async def async_discover_devices(hass: HomeAssistant):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint()
