"""Light platform for Kernel Chip relays and solid-state outputs."""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ENTITY_TYPE_LIGHT
from .output_entity import KernelChipOutputEntity
from .output_setup import iter_output_entities


class KernelChipOutputLight(KernelChipOutputEntity, LightEntity):
    """On/off light mapped to a relay or SSR output."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kernel Chip lights when configured in options."""
    coordinator = entry.runtime_data
    entities = iter_output_entities(
        coordinator, entry, ENTITY_TYPE_LIGHT, KernelChipOutputLight
    )
    async_add_entities(entities)
