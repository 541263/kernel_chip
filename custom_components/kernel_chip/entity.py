"""Base entity helpers for Kernel Chip."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KernelChipCoordinator


class KernelChipEntity(CoordinatorEntity[KernelChipCoordinator]):
    """Base entity for a Kernel Chip device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KernelChipCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.device_info_data
        sn = data.get("sn", self.coordinator.host)
        return DeviceInfo(
            identifiers={(DOMAIN, sn)},
            name=self.coordinator.entry.title,
            manufacturer="Kernel Chip",
            model=data.get("fw") or "LAN Controller",
            sw_version=data.get("fw") or None,
            configuration_url=f"http://{self.coordinator.host}/",
        )
