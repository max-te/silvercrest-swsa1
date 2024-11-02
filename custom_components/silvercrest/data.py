from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

type SilvercrestConfigEntry = ConfigEntry[SilvercrestData]


@dataclass
class SilvercrestData:
    host: str
    name: str
