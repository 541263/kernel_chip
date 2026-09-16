"""Config flow for Kernel Chip."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_WEBHOOK_ID,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTITY_TYPE_LIGHT,
    ENTITY_TYPE_SWITCH,
    JSON_SENSOR_PATH,
)
from .options_util import (
    OptionsPollError,
    async_fetch_output_counts,
    build_options_defaults,
    option_key_relay,
    option_key_ssr,
    parse_options_user_input,
)
from .parser import parse_device_payload

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate host/password by polling json_sensor.cgi."""
    session = async_get_clientsession(hass)
    host = data[CONF_HOST].strip().removeprefix("http://").removeprefix("https://")
    host = host.rstrip("/")
    url = f"http://{host}{JSON_SENSOR_PATH}"

    try:
        async with session.get(
            url,
            params={"psw": data[CONF_PASSWORD]},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status != 200:
                raise CannotConnect
            payload = await response.json(content_type=None)
    except aiohttp.ClientError as err:
        raise CannotConnect from err
    except (TypeError, ValueError) as err:
        raise CannotConnect from err

    if not isinstance(payload, dict):
        raise InvalidAuth

    try:
        parsed = parse_device_payload(payload)
    except ValueError as err:
        raise InvalidAuth from err

    return {"host": host, "sn": parsed["sn"], "fw": parsed.get("fw", "")}


class KernelChipConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kernel Chip."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["sn"])
                self._abort_if_unique_id_configured()

                title = user_input.get(CONF_NAME) or f"{DEFAULT_NAME} {info['sn'][-8:]}"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: info["host"],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_NAME: title,
                        CONF_WEBHOOK_ID: secrets.token_hex(16),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> KernelChipOptionsFlow:
        """Get the options flow."""
        return KernelChipOptionsFlow()


def _entity_type_selector() -> selector.SelectSelector:
    """Dropdown for switch vs light output entities."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[ENTITY_TYPE_SWITCH, ENTITY_TYPE_LIGHT],
            translation_key="output_entity_type",
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


class KernelChipOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Kernel Chip."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage polling interval and per-output entity types."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=parse_options_user_input(user_input),
            )

        try:
            relay_count, ssr_count = await async_fetch_output_counts(
                self.hass, self.config_entry
            )
        except OptionsPollError:
            errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        options = dict(self.config_entry.options)
        defaults = build_options_defaults(options, relay_count, ssr_count)

        schema_fields: dict[vol.Marker, Any] = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults[CONF_SCAN_INTERVAL],
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
        }

        for index in range(1, relay_count + 1):
            key = option_key_relay(index)
            schema_fields[
                vol.Optional(key, default=defaults[key])
            ] = _entity_type_selector()

        for index in range(1, ssr_count + 1):
            key = option_key_ssr(index)
            schema_fields[
                vol.Optional(key, default=defaults[key])
            ] = _entity_type_selector()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
            description_placeholders={
                "relay_count": str(relay_count),
                "ssr_count": str(ssr_count),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


def get_webhook_url(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> str:
    """Return the full webhook URL for this device."""
    webhook_id = entry.data[CONF_WEBHOOK_ID]
    return webhook.async_generate_url(hass, webhook_id)
