"""Options flow helpers for per-output entity types."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_RELAY_ENTITY_TYPE,
    CONF_RELAY_ENTITY_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_SSR_ENTITY_TYPE,
    CONF_SSR_ENTITY_TYPES,
    DEFAULT_OUTPUT_ENTITY_TYPE,
    DEFAULT_SCAN_INTERVAL,
    JSON_SENSOR_PATH,
)
from .parser import parse_device_payload

OPT_RELAY_PREFIX = "relay_"
OPT_SSR_PREFIX = "ssr_"


class OptionsPollError(Exception):
    """Could not read the device while building the options form."""


def option_key_relay(index: int) -> str:
    """Form field key for relay index (1-based)."""
    return f"{OPT_RELAY_PREFIX}{index}"


def option_key_ssr(index: int) -> str:
    """Form field key for SSR index (1-based)."""
    return f"{OPT_SSR_PREFIX}{index}"


async def async_fetch_output_counts(hass: HomeAssistant, entry: ConfigEntry) -> tuple[int, int]:
    """Poll device and return (relay_count, ssr_count)."""
    import aiohttp
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]
    url = f"http://{host}{JSON_SENSOR_PATH}"

    try:
        async with session.get(
            url,
            params={"psw": password},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status != 200:
                raise OptionsPollError
            payload = await response.json(content_type=None)
    except aiohttp.ClientError as err:
        raise OptionsPollError from err

    if not isinstance(payload, dict):
        raise OptionsPollError

    try:
        parsed = parse_device_payload(payload)
    except ValueError as err:
        raise OptionsPollError from err

    return len(parsed["relays"]), len(parsed["ssr_out"])


def _defaults_for_kind(
    options: dict[str, Any],
    kind: str,
    count: int,
) -> dict[str, str]:
    """Build default entity type per index from stored options."""
    if kind == "relay":
        types = options.get(CONF_RELAY_ENTITY_TYPES)
        legacy = options.get(CONF_RELAY_ENTITY_TYPE)
        prefix = OPT_RELAY_PREFIX
    else:
        types = options.get(CONF_SSR_ENTITY_TYPES)
        legacy = options.get(CONF_SSR_ENTITY_TYPE)
        prefix = OPT_SSR_PREFIX

    if not isinstance(types, dict):
        types = {}

    defaults: dict[str, str] = {}
    for index in range(1, count + 1):
        key = str(index)
        form_key = f"{prefix}{index}"
        if key in types:
            defaults[form_key] = types[key]
        elif legacy:
            defaults[form_key] = legacy
        else:
            defaults[form_key] = DEFAULT_OUTPUT_ENTITY_TYPE
    return defaults


def build_options_defaults(
    options: dict[str, Any],
    relay_count: int,
    ssr_count: int,
) -> dict[str, Any]:
    """Defaults for the options form."""
    result: dict[str, Any] = {
        CONF_SCAN_INTERVAL: options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    }
    result.update(_defaults_for_kind(options, "relay", relay_count))
    result.update(_defaults_for_kind(options, "ssr", ssr_count))
    return result


def parse_options_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert form fields into stored options."""
    relay_types: dict[str, str] = {}
    ssr_types: dict[str, str] = {}

    for key, value in user_input.items():
        if key.startswith(OPT_RELAY_PREFIX):
            index = key[len(OPT_RELAY_PREFIX) :]
            if index.isdigit():
                relay_types[index] = value
        elif key.startswith(OPT_SSR_PREFIX):
            index = key[len(OPT_SSR_PREFIX) :]
            if index.isdigit():
                ssr_types[index] = value

    return {
        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
        CONF_RELAY_ENTITY_TYPES: relay_types,
        CONF_SSR_ENTITY_TYPES: ssr_types,
    }
