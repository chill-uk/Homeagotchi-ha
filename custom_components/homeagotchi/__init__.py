"""Homeagotchi custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .api import async_register_views
from .const import (
    CONF_BIN_ENTITY,
    CONF_DRYER_ENTITY,
    CONF_ENERGY_PRICE_ENTITY,
    CONF_LIGHT_ENTITIES,
    CONF_WASHING_MACHINE_ENTITY,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)
from .coordinator import HomeagotchiCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homeagotchi from a config entry."""

    coordinator = HomeagotchiCoordinator(hass, entry)
    await coordinator.async_update()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.data[DOMAIN]["coordinator"] = coordinator
    async_register_views(hass)

    @callback
    def _handle_source_entity_change(event) -> None:
        """Refresh Homeagotchi state when a configured source entity changes."""
        hass.async_create_task(coordinator.async_update())

    entity_ids = _configured_entity_ids(entry)
    if entity_ids:
        unsub = async_track_state_change_event(
            hass,
            entity_ids,
            _handle_source_entity_change,
        )
        entry.async_on_unload(unsub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Homeagotchi config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if hass.data[DOMAIN].get("coordinator") is not None:
            hass.data[DOMAIN].pop("coordinator", None)

    return unload_ok


def _configured_entity_ids(entry: ConfigEntry) -> list[str]:
    """Return entity IDs that should trigger Homeagotchi recomputation."""

    data = {**entry.data, **entry.options}
    entity_ids = [
        data.get(CONF_WEATHER_ENTITY),
        data.get(CONF_WASHING_MACHINE_ENTITY),
        data.get(CONF_DRYER_ENTITY),
        data.get(CONF_BIN_ENTITY),
        data.get(CONF_ENERGY_PRICE_ENTITY),
    ]
    entity_ids.extend(data.get(CONF_LIGHT_ENTITIES) or [])
    return [entity_id for entity_id in entity_ids if entity_id]
