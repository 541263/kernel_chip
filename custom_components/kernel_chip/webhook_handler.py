"""Webhook handling for Kernel Chip digital inputs."""

from __future__ import annotations

import logging
import re

from aiohttp import web
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_WEBHOOK_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

_IN_PATTERN = re.compile(r"IN(\d+)", re.IGNORECASE)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return True
    lowered = value.strip().lower()
    if lowered in {"1", "on", "true", "high", "h"}:
        return True
    if lowered in {"0", "off", "false", "low", "l"}:
        return False
    return None


def parse_webhook_input(request: web.Request) -> tuple[int, bool | None] | None:
    """Parse input index and state from a device webhook GET request."""
    query = request.query

    if "input" in query:
        try:
            index = int(query["input"])
        except (TypeError, ValueError):
            return None
        return index, _parse_bool(query.get("state"))

    for key, value in query.items():
        match = _IN_PATTERN.fullmatch(key)
        if match:
            return int(match.group(1)), _parse_bool(value if value != "" else "1")
        match = _IN_PATTERN.search(key)
        if match:
            return int(match.group(1)), _parse_bool(value if value != "" else "1")

    path = request.path
    match = _IN_PATTERN.search(path)
    if match:
        return int(match.group(1)), _parse_bool(query.get("state"))

    url = str(request.url)
    match = _IN_PATTERN.search(url)
    if match:
        return int(match.group(1)), _parse_bool(query.get("state"))

    return None


@callback
def async_register_webhook(
    hass: HomeAssistant, entry: ConfigEntry, handler
) -> None:
    """Register the device webhook."""
    from homeassistant.components import webhook as webhook_component

    name = entry.data.get("name", entry.title)
    webhook_component.async_register(
        hass,
        domain=DOMAIN,
        name=name,
        webhook_id=entry.data[CONF_WEBHOOK_ID],
        handler=handler,
        allowed_methods=["GET"],
    )


@callback
def async_unregister_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unregister the device webhook."""
    from homeassistant.components import webhook as webhook_component

    webhook_component.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])


async def async_handle_webhook(
    hass: HomeAssistant,
    entry_id: str,
    request: web.Request,
) -> web.Response:
    """Handle incoming webhook from device."""
    parsed = parse_webhook_input(request)
    if parsed is None:
        _LOGGER.debug("Webhook without recognizable input: %s", request.url)
        return web.Response(status=400, text="Missing input identifier")

    input_index, state = parsed
    entry_data = hass.data.get(DOMAIN, {}).get(entry_id)
    if not entry_data:
        return web.Response(status=404, text="Device not found")

    coordinator = entry_data["coordinator"]
    coordinator.set_io_in_state(input_index, state)
    _LOGGER.debug(
        "Webhook set io_in %s to %s for entry %s",
        input_index,
        state,
        entry_id,
    )
    return web.Response(text="OK")
