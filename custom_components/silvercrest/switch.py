"""
Platform for Silvercrest SWS A1 Wifi Switches

Reference https://wiki.fhem.de/wiki/Silvercrest_SWS_A1_Wifi for protocol details.
"""

import socket
from typing import Any, Literal
from typing_extensions import override
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

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


SILVERCREST_AES_KEY = b"0123456789abcdef"
SILVERCREST_AES_IV = b"0123456789abcdef"
SILVERCREST_UDP_PORT = 8530


class SilvercrestSwitch(SwitchEntity):
    _state: None | Literal["on"] | Literal["off"]
    _host: str
    _name: str
    _aes: Cipher[modes.CBC]

    def __init__(self, hass: HomeAssistant, host: str, name: str):
        self._state = None
        self._host = host
        self._name = name
        self._aes = Cipher(
            algorithms.AES(SILVERCREST_AES_KEY),
            modes.CBC(SILVERCREST_AES_IV),
            backend=default_backend(),
        )

    def _sendMsg(self, msg: bytes):
        mac = b"\xff\xff\xff\xff\xff\xff"  # This works as broadcast
        envelope = b"\x01\x40" + mac + b"\x10"

        preamble = b"\x00\xff\xff\xc1\x11\x71\x50"  # FF FF is a package counter, if you want it.
        unencmsg = preamble + msg
        encryptor = self._aes.encryptor()
        encmsg = encryptor.update(unencmsg) + encryptor.finalize()

        port = SILVERCREST_UDP_PORT
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.settimeout(0.5)
        s.bind(("", port))
        try:
            s.connect((self._host, port))
            s.sendall(envelope + encmsg)

            response = s.recv(1024)
            decryptor = self._aes.decryptor()
            response = decryptor.update(response[9:]) + decryptor.finalize()
            response = response[7:]
            return response
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
        if self._sendMsg(b"\x01\x00\x00\xff\xff\x04\x04\x04\x04"):
            self._state = STATE_ON

    @override
    def turn_off(self, **kwargs: dict[str, Any]):
        """Turn the device off."""
        if self._sendMsg(b"\x01\x00\x00\x00\xff\x04\x04\x04\x04"):
            self._state = STATE_OFF

    def update(self):
        """Get the latest data from the smart plug and updates the states."""
        response = self._sendMsg(b"\x02\x00\x00\x00\x00\x04\x04\x04\x04")
        if response:
            self._state = STATE_ON if (response[3] == 0xFF) else STATE_OFF
        else:
            self._state = None
