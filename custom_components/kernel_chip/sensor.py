"""Sensor platform for Kernel Chip 1-Wire and ADC readings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfElectricPotential
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_PORT, ATTR_RAW_ADC, ATTR_ROM_ID, DOMAIN
from .coordinator import KernelChipCoordinator
from .entity import KernelChipEntity


class KernelChipAdcSensor(KernelChipEntity, SensorEntity):
    """Voltage reading from an ADC channel."""

    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: KernelChipCoordinator,
        entry_id: str,
        channel: int,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._channel = channel
        sn = coordinator.data["sn"] if coordinator.data else coordinator.host
        self._attr_unique_id = f"{sn}_adc_{channel}"
        self._attr_translation_key = "adc"
        self._attr_translation_placeholders = {"channel": str(channel + 1)}

    @property
    def native_value(self) -> float | None:
        adc_list = self.coordinator.data.get("adc", [])
        for item in adc_list:
            if item["index"] == self._channel:
                return item["voltage"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        adc_list = self.coordinator.data.get("adc", [])
        for item in adc_list:
            if item["index"] == self._channel:
                return {ATTR_RAW_ADC: item["raw"]}
        return None


class KernelChipOwiSensor(KernelChipEntity, SensorEntity):
    """Temperature from a 1-Wire sensor."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: KernelChipCoordinator,
        entry_id: str,
        rom_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._rom_id = rom_id
        sn = coordinator.data["sn"] if coordinator.data else coordinator.host
        self._attr_unique_id = f"{sn}_owi_{rom_id}"
        self._attr_name = name

    @property
    def native_value(self) -> float | None:
        owi = self.coordinator.data.get("owi", {})
        entry = owi.get(self._rom_id)
        if not entry:
            return None
        return entry.get("temperature")

    @property
    def available(self) -> bool:
        return super().available and self._rom_id in self.coordinator.data.get(
            "owi", {}
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        owi = self.coordinator.data.get("owi", {})
        entry = owi.get(self._rom_id)
        if not entry:
            return None
        return {
            ATTR_ROM_ID: self._rom_id,
            ATTR_PORT: entry.get("port"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kernel Chip sensors."""
    coordinator: KernelChipCoordinator = entry.runtime_data
    entry_id = entry.entry_id
    store = hass.data[DOMAIN][entry_id]

    @callback
    def _add_owi_entities() -> None:
        owi = coordinator.data.get("owi", {})
        new_entities: list[KernelChipOwiSensor] = []
        for rom_id, info in owi.items():
            if rom_id in store["known_owi"]:
                continue
            store["known_owi"].add(rom_id)
            new_entities.append(
                KernelChipOwiSensor(
                    coordinator,
                    entry_id,
                    rom_id,
                    str(info.get("name", rom_id)),
                )
            )
        if new_entities:
            async_add_entities(new_entities)

    entities: list[SensorEntity] = []
    for item in coordinator.data.get("adc", []):
        entities.append(
            KernelChipAdcSensor(coordinator, entry_id, item["index"])
        )

    owi = coordinator.data.get("owi", {})
    for rom_id, info in owi.items():
        store["known_owi"].add(rom_id)
        entities.append(
            KernelChipOwiSensor(
                coordinator,
                entry_id,
                rom_id,
                str(info.get("name", rom_id)),
            )
        )

    async_add_entities(entities)

    coordinator.async_add_listener(_add_owi_entities)
