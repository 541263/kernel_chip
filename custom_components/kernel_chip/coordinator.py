"""Data update coordinator for Kernel Chip devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CMD_PATH,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    JSON_SENSOR_PATH,
)
from .parser import parse_device_payload

_LOGGER = logging.getLogger(__name__)


class KernelChipCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and normalize Kernel Chip device state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.password = entry.data[CONF_PASSWORD]
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._session = async_get_clientsession(hass)
        self._io_in_override: dict[int, bool | None] = {}

    @property
    def device_info_data(self) -> dict[str, Any]:
        """Return latest device metadata."""
        if not self.data:
            return {}
        return {
            "sn": self.data["sn"],
            "fw": self.data.get("fw", ""),
            "mac": self.data.get("mac", ""),
        }

    def get_io_in_states(self) -> list[bool | None]:
        """Return io_in states with webhook overrides applied."""
        base = list(self.data.get("io_in", [])) if self.data else []
        if not self._io_in_override:
            return base
        if not base:
            max_index = max(self._io_in_override)
            base = [None] * max_index
        for index, state in self._io_in_override.items():
            while len(base) < index:
                base.append(None)
            base[index - 1] = state
        return base

    def set_io_in_state(self, index: int, state: bool | None) -> None:
        """Set a single digital input (1-based index) from webhook."""
        if index < 1:
            return
        self._io_in_override[index] = state
        if self.data:
            io_in = list(self.data.get("io_in", []))
            while len(io_in) < index:
                io_in.append(None)
            io_in[index - 1] = state
            self.data["io_in"] = io_in
        self.async_update_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        url = f"http://{self.host}{JSON_SENSOR_PATH}"
        try:
            async with self._session.get(
                url,
                params={"psw": self.password},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"HTTP {response.status} from device")
                payload = await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
        except (TypeError, ValueError) as err:
            raise UpdateFailed(f"Invalid JSON from device: {err}") from err

        if not isinstance(payload, dict):
            raise UpdateFailed("Device returned non-object JSON")

        try:
            data = parse_device_payload(payload)
        except ValueError as err:
            raise UpdateFailed(str(err)) from err

        if self._io_in_override:
            io_in = list(data.get("io_in", []))
            for index, state in list(self._io_in_override.items()):
                while len(io_in) < index:
                    io_in.append(None)
                polled = io_in[index - 1]
                if polled is not None:
                    self._io_in_override.pop(index, None)
                elif state is not None:
                    io_in[index - 1] = state
            data["io_in"] = io_in

        return data

    def set_output_state(self, data_key: str, index: int, state: bool) -> None:
        """Apply switch state locally so UI updates before the next poll."""
        if not self.data or index < 1:
            return
        updated = dict(self.data)
        states = list(updated.get(data_key, []))
        while len(states) < index:
            states.append(False)
        states[index - 1] = state
        updated[data_key] = states
        self.async_set_updated_data(updated)

    async def send_command(self, prefix: str, index: int, state: bool) -> bool:
        """Send REL or WR command; return True on #PREFIX,OK."""
        cmd = f"{prefix},{index},{1 if state else 0}"
        url = f"http://{self.host}{CMD_PATH}"
        try:
            async with self._session.get(
                url,
                params={"psw": self.password, "cmd": cmd},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                text = (await response.text()).strip()
        except aiohttp.ClientError:
            _LOGGER.exception("Command failed for %s on %s", cmd, self.host)
            return False

        expected = f"#{prefix},OK"
        if expected not in text:
            _LOGGER.warning(
                "Unexpected response for %s on %s: %s", cmd, self.host, text
            )
            return False
        return True
