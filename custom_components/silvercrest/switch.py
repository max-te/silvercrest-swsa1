"""
Platform for Silvercrest SWS A1 Wifi Switches
"""

import socket
from Crypto.Cipher import AES

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
    STATE_UNAVAILABLE,
)

DEFAULT_NAME = "Silvercrest SWS A1"

PLATFORM_SCHEMA = PLATFORM_SCHEMA_BASE.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)

    add_devices([SilvercrestSwitch(hass, host, name)], True)


class SilvercrestSwitch(SwitchEntity):
    def __init__(self, hass, host, name):
        self._state = ""
        self._host = host
        self._name = name

    def _sendMsg(self, msg):
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

    @property
    def should_poll(self):
        return True

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state == STATE_ON

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        if self._sendMsg("01 00 00 ff ff 04 04 04 04"):
            self._state = STATE_ON

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self._sendMsg("01 00 00 00 ff 04 04 04 04"):
            self._state = STATE_OFF

    def update(self):
        """Get the latest data from the smart plug and updates the states."""
        response = self._sendMsg("02 00 00 00 00 04 04 04 04")
        if response:
            self._state = STATE_ON if (response[3] == 0xFF) else STATE_OFF
        else:
            self._state = STATE_UNAVAILABLE
