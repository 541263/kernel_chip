"""Helpers for creating relay/SSR output entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_RELAY_ENTITY_TYPE,
    CONF_RELAY_ENTITY_TYPES,
    CONF_SSR_ENTITY_TYPE,
    CONF_SSR_ENTITY_TYPES,
    DEFAULT_OUTPUT_ENTITY_TYPE,
)
from .coordinator import KernelChipCoordinator
from .output_entity import KernelChipOutputEntity, OutputKind


def output_entity_type(entry: ConfigEntry, kind: OutputKind, index: int) -> str:
    """Return switch or light for one relay or SSR output."""
    if kind == "relay":
        types = entry.options.get(CONF_RELAY_ENTITY_TYPES)
        legacy = entry.options.get(CONF_RELAY_ENTITY_TYPE)
    else:
        types = entry.options.get(CONF_SSR_ENTITY_TYPES)
        legacy = entry.options.get(CONF_SSR_ENTITY_TYPE)

    if isinstance(types, dict):
        stored = types.get(str(index))
        if stored:
            return stored
    if legacy:
        return legacy
    return DEFAULT_OUTPUT_ENTITY_TYPE


def iter_output_entities(
    coordinator: KernelChipCoordinator,
    entry: ConfigEntry,
    platform: str,
    entity_class: type[KernelChipOutputEntity],
) -> list[KernelChipOutputEntity]:
    """Build output entities matching the requested platform (switch or light)."""
    if not coordinator.data:
        return []

    entry_id = entry.entry_id
    entities: list[KernelChipOutputEntity] = []

    for index in range(1, len(coordinator.data.get("relays", [])) + 1):
        if output_entity_type(entry, "relay", index) == platform:
            entities.append(entity_class(coordinator, entry_id, "relay", index))

    for index in range(1, len(coordinator.data.get("ssr_out", [])) + 1):
        if output_entity_type(entry, "ssr", index) == platform:
            entities.append(entity_class(coordinator, entry_id, "ssr", index))

    return entities
