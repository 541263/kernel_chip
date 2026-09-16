"""Parse JSON payloads from Kernel Chip devices."""

from __future__ import annotations

from typing import Any


def _parse_bitstring(value: str | None) -> list[bool]:
    if not value:
        return []
    return [char == "1" for char in value]


def _parse_tristate_string(value: str | None) -> list[bool | None]:
    if not value:
        return []
    states: list[bool | None] = []
    for char in value.lower():
        if char == "1":
            states.append(True)
        elif char == "0":
            states.append(False)
        else:
            states.append(None)
    return states


def _parse_adc(adc: list[Any] | None) -> list[dict[str, float]]:
    if not adc:
        return []
    parsed: list[dict[str, float]] = []
    for index, item in enumerate(adc):
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            parsed.append(
                {
                    "index": index,
                    "raw": float(item[0]),
                    "voltage": float(item[1]),
                }
            )
        except (TypeError, ValueError):
            continue
    return parsed


def _parse_owi_temp(owi_temp: list[Any] | None) -> dict[str, dict[str, Any]]:
    if not owi_temp:
        return {}
    sensors: dict[str, dict[str, Any]] = {}
    for item in owi_temp:
        if not isinstance(item, (list, tuple)) or len(item) < 4:
            continue
        port, rom_id, name, temperature = item[0], item[1], item[2], item[3]
        rom_key = str(rom_id)
        try:
            temp_value = float(temperature)
        except (TypeError, ValueError):
            continue
        sensors[rom_key] = {
            "port": str(port),
            "name": str(name) if name else rom_key,
            "temperature": temp_value,
        }
    return sensors


def parse_device_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a json_sensor.cgi payload for coordinator consumers."""
    sn = str(payload.get("sn", "")).strip()
    if not sn:
        raise ValueError("Missing device serial number (sn)")

    return {
        "sn": sn,
        "fw": str(payload.get("fw", "")),
        "mac": str(payload.get("mac", "")),
        "sys_time": payload.get("sys_time"),
        "rtc": payload.get("rtc"),
        "relays": _parse_bitstring(payload.get("rele")),
        "io_in": _parse_tristate_string(payload.get("io_in")),
        "io_out": _parse_bitstring(payload.get("io_out")),
        "ssr_out": _parse_bitstring(payload.get("out")),
        "adc": _parse_adc(payload.get("adc")),
        "owi": _parse_owi_temp(payload.get("owi_temp")),
    }
