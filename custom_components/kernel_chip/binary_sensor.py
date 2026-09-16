"""Binary sensor platform for Kernel Chip digital inputs."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import KernelChipEntity


class KernelChipInputBinarySensor(KernelChipEntity, BinarySensorEntity):
    """Binary sensor for one io_in line."""

    def __init__(
        self,
        coordinator,
        entry_id: str,
        index: int,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._index = index
        sn = coordinator.data["sn"] if coordinator.data else coordinator.host
        self._attr_unique_id = f"{sn}_io_in_{index}"
        self._attr_translation_key = "io_input"
        self._attr_translation_placeholders = {"index": str(index)}

    @property
    def is_on(self) -> bool | None:
        states = self.coordinator.get_io_in_states()
        if len(states) < self._index:
            return None
        return states[self._index - 1]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kernel Chip binary sensors."""
    coordinator = entry.runtime_data
    if not coordinator.data:
        return

    count = len(coordinator.data.get("io_in", []))
    entities = [
        KernelChipInputBinarySensor(coordinator, entry.entry_id, index)
        for index in range(1, count + 1)
    ]
    async_add_entities(entities)
