"""Switch platform for Kernel Chip relays and solid-state outputs."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ENTITY_TYPE_SWITCH
from .output_entity import KernelChipOutputEntity
from .output_setup import iter_output_entities


class KernelChipOutputSwitch(KernelChipOutputEntity, SwitchEntity):
    """Switch mapped to a relay or SSR output."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kernel Chip switches when configured in options."""
    coordinator = entry.runtime_data
    entities = iter_output_entities(
        coordinator, entry, ENTITY_TYPE_SWITCH, KernelChipOutputSwitch
    )
    async_add_entities(entities)
