"""Constants for the Kernel Chip integration."""

DOMAIN = "kernel_chip"

CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_WEBHOOK_ID = "webhook_id"
CONF_RELAY_ENTITY_TYPE = "relay_entity_type"
CONF_SSR_ENTITY_TYPE = "ssr_entity_type"
CONF_RELAY_ENTITY_TYPES = "relay_entity_types"
CONF_SSR_ENTITY_TYPES = "ssr_entity_types"

ENTITY_TYPE_SWITCH = "switch"
ENTITY_TYPE_LIGHT = "light"
DEFAULT_OUTPUT_ENTITY_TYPE = ENTITY_TYPE_LIGHT

DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NAME = "Kernel Chip"

JSON_SENSOR_PATH = "/json_sensor.cgi"
CMD_PATH = "/cmd.cgi"

CMD_REL = "REL"
CMD_WR = "WR"

PLATFORMS = ["binary_sensor", "light", "sensor", "switch"]

ATTR_PORT = "owi_port"
ATTR_ROM_ID = "rom_id"
ATTR_RAW_ADC = "raw_adc"
