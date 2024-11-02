"""
Platform for Silvercrest SWS A1 Wifi Switches
"""

import socket
from typing import Any, Literal
from typing_extensions import override
from Crypto.Cipher import AES

from functools import cached_property
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import (
    SwitchEntity,
    PLATFORM_SCHEMA as PLATFORM_SCHEMA_BASE,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
)

DEFAULT_NAME = "Silvercrest SWS A1"

PLATFORM_SCHEMA = PLATFORM_SCHEMA_BASE.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_devices: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # pyright: ignore[reportUnusedParameter]
):
    host: str = config[CONF_HOST]
    name: str = config[CONF_NAME]

    add_devices([SilvercrestSwitch(hass, host, name)], True)


class SilvercrestSwitch(SwitchEntity):
    _state: None | Literal["on"] | Literal["off"]
    _host: str
    _name: str

    def __init__(self, hass: HomeAssistant, host: str, name: str):
        self._state = None
        self._host = host
        self._name = name

    def _sendMsg(self, msg: str):
        mac = "FF FF FF FF FF FF"  # This works as broadcast
        preamble1 = bytes.fromhex("0140" + mac + "10")
        preamble2 = (
            "00 ff ff c1 11 71 50"  # FF FF is a package counter, if you want it.
        )
        unencmsg = bytes.fromhex(preamble2 + msg)
        encmsg = AES.new(
            b"0123456789abcdef", AES.MODE_CBC, b"0123456789abcdef"
        ).encrypt(unencmsg)

        port = 8530
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.settimeout(0.5)
        s.bind(("", port))
        try:
            s.connect((self._host, port))
            s.sendall(preamble1 + encmsg)

            response = s.recv(1024)
            return AES.new(
                b"0123456789abcdef", AES.MODE_CBC, b"0123456789abcdef"
            ).decrypt(response[9:])[7:]
        except socket.timeout:
            return None
        finally:
            s.close()

    @cached_property
    @override
    def should_poll(self):
        return True

    @cached_property
    @override
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    @override
    def is_on(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if switch is on."""
        return self._state == STATE_ON

    @property
    @override
    def state(self):
        """Return the state of the device."""
        return self._state

    @override
    def turn_on(self, **kwargs: dict[str, Any]):
        """Turn the switch on."""
        if self._sendMsg("01 00 00 ff ff 04 04 04 04"):
            self._state = STATE_ON

    @override
    def turn_off(self, **kwargs: dict[str, Any]):
        """Turn the device off."""
        if self._sendMsg("01 00 00 00 ff 04 04 04 04"):
            self._state = STATE_OFF

    def update(self):
        """Get the latest data from the smart plug and updates the states."""
        response = self._sendMsg("02 00 00 00 00 04 04 04 04")
        if response:
            self._state = STATE_ON if (response[3] == 0xFF) else STATE_OFF
        else:
            self._state = None
