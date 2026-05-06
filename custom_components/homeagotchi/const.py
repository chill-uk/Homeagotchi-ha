"""Constants for the Homeagotchi integration."""

from __future__ import annotations

from datetime import time

DOMAIN = "homeagotchi"
PLATFORMS = ["sensor"]

CONF_WEATHER_ENTITY = "weather_entity"
CONF_WASHING_MACHINE_ENTITY = "washing_machine_entity"
CONF_DRYER_ENTITY = "dryer_entity"
CONF_LIGHT_ENTITIES = "light_entities"
CONF_BIN_ENTITY = "bin_entity"
CONF_ENERGY_PRICE_ENTITY = "energy_price_entity"
CONF_ENERGY_PRICE_HIGH = "energy_price_high"
CONF_IGNORED_DELAY_MINUTES = "ignored_delay_minutes"
CONF_QUIET_HOURS_START = "quiet_hours_start"
CONF_QUIET_HOURS_END = "quiet_hours_end"

DEFAULT_IGNORED_DELAY_MINUTES = 30
DEFAULT_LED_BRIGHTNESS = 0.15
DEFAULT_ATTENTION_LED_BRIGHTNESS = 0.2
DEFAULT_URGENT_LED_BRIGHTNESS = 0.25
DEFAULT_QUIET_HOURS_START = time(22, 0)
DEFAULT_QUIET_HOURS_END = time(7, 0)

ACK_SUPPRESS_MINUTES = 30

