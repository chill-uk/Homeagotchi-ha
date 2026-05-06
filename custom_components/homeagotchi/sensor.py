"""Debug sensors for Homeagotchi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomeagotchiCoordinator


@dataclass(frozen=True, kw_only=True)
class HomeagotchiSensorEntityDescription(SensorEntityDescription):
    """Describes a Homeagotchi debug sensor."""

    value_path: tuple[str, ...]


SENSORS: tuple[HomeagotchiSensorEntityDescription, ...] = (
    HomeagotchiSensorEntityDescription(
        key="scene",
        translation_key="scene",
        value_path=("scene",),
    ),
    HomeagotchiSensorEntityDescription(
        key="emotion",
        translation_key="emotion",
        value_path=("emotion",),
    ),
    HomeagotchiSensorEntityDescription(
        key="message",
        translation_key="message",
        value_path=("message",),
    ),
    HomeagotchiSensorEntityDescription(
        key="led_color",
        translation_key="led_color",
        value_path=("led", "color"),
    ),
    HomeagotchiSensorEntityDescription(
        key="led_mode",
        translation_key="led_mode",
        value_path=("led", "mode"),
    ),
    HomeagotchiSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        value_path=("updated_at",),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homeagotchi debug sensors."""

    coordinator: HomeagotchiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HomeagotchiSensor(coordinator, entry, description) for description in SENSORS
    )


class HomeagotchiSensor(SensorEntity):
    """A sensor exposing one field from the current Homeagotchi state."""

    entity_description: HomeagotchiSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomeagotchiCoordinator,
        entry: ConfigEntry,
        description: HomeagotchiSensorEntityDescription,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Homeagotchi",
            "manufacturer": "Homeagotchi",
        }
        self._unsub_listener = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""

        self._unsub_listener = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from coordinator updates."""

        if self._unsub_listener is not None:
            self._unsub_listener()
            self._unsub_listener = None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return the configured field from the current Homeagotchi state."""

        value: Any = self.coordinator.state
        for key in self.entity_description.value_path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

