"""Shared relay and SSR output entity logic."""

from __future__ import annotations

from typing import Any, Literal

from .const import CMD_REL, CMD_WR
from .entity import KernelChipEntity

OutputKind = Literal["relay", "ssr"]


class KernelChipOutputEntity(KernelChipEntity):
    """Base for relay (REL) and solid-state (WR) outputs."""

    def __init__(
        self,
        coordinator,
        entry_id: str,
        kind: OutputKind,
        index: int,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._kind = kind
        self._index = index
        sn = coordinator.data["sn"] if coordinator.data else coordinator.host

        if kind == "relay":
            self._cmd_prefix = CMD_REL
            self._data_key = "relays"
            self._attr_translation_key = "relay"
            self._attr_unique_id = f"{sn}_relay_{index}"
        else:
            self._cmd_prefix = CMD_WR
            self._data_key = "ssr_out"
            self._attr_translation_key = "ssr_output"
            self._attr_unique_id = f"{sn}_ssr_{index}"

        self._attr_translation_placeholders = {"index": str(index)}

    @property
    def is_on(self) -> bool | None:
        states: list[bool] = self.coordinator.data.get(self._data_key, [])
        if len(states) < self._index:
            return None
        return states[self._index - 1]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        if not await self.coordinator.send_command(
            self._cmd_prefix, self._index, state
        ):
            return
        self.coordinator.set_output_state(self._data_key, self._index, state)
        self.hass.async_create_task(self.coordinator.async_request_refresh())
