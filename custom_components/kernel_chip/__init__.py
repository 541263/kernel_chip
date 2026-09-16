"""The Kernel Chip integration."""

from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN, PLATFORMS
from .coordinator import KernelChipCoordinator
from .webhook_handler import (
    async_handle_webhook,
    async_register_webhook,
    async_unregister_webhook,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kernel Chip from a config entry."""
    coordinator = KernelChipCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry_id = entry.entry_id

    async def _webhook_handler(hass: HomeAssistant, webhook_id: str, request: web.Request) -> web.Response:
        if webhook_id != entry.data.get(CONF_WEBHOOK_ID):
            return web.Response(status=404)
        return await async_handle_webhook(hass, entry_id, request)

    async_register_webhook(hass, entry, _webhook_handler)

    hass.data[DOMAIN][entry_id] = {
        "coordinator": coordinator,
        "known_owi": set(),
    }
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    from .config_flow import get_webhook_url

    _LOGGER.info(
        "Kernel Chip %s configured. Webhook URL: %s",
        coordinator.data["sn"],
        get_webhook_url(hass, entry),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unregister_webhook(hass, entry)
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await async_reload_entry(hass, entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
