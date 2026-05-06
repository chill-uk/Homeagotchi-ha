"""Config flow for Homeagotchi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_BIN_ENTITY,
    CONF_DRYER_ENTITY,
    CONF_ENERGY_PRICE_ENTITY,
    CONF_ENERGY_PRICE_HIGH,
    CONF_IGNORED_DELAY_MINUTES,
    CONF_LIGHT_ENTITIES,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_WASHING_MACHINE_ENTITY,
    CONF_WEATHER_ENTITY,
    DEFAULT_IGNORED_DELAY_MINUTES,
    DOMAIN,
)


class HomeagotchiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Homeagotchi config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Homeagotchi", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
        )


def _schema() -> vol.Schema:
    """Return the setup form schema."""

    entity_selector = selector.EntitySelector()

    return vol.Schema(
        {
            vol.Optional(CONF_WEATHER_ENTITY): entity_selector,
            vol.Optional(CONF_WASHING_MACHINE_ENTITY): entity_selector,
            vol.Optional(CONF_DRYER_ENTITY): entity_selector,
            vol.Optional(CONF_LIGHT_ENTITIES): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True, domain="light")
            ),
            vol.Optional(CONF_BIN_ENTITY): entity_selector,
            vol.Optional(CONF_ENERGY_PRICE_ENTITY): entity_selector,
            vol.Optional(CONF_ENERGY_PRICE_HIGH): selector.NumberSelector(
                selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_IGNORED_DELAY_MINUTES,
                default=DEFAULT_IGNORED_DELAY_MINUTES,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=240,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="minutes",
                )
            ),
            vol.Required(CONF_QUIET_HOURS_START, default="22:00"): selector.TimeSelector(),
            vol.Required(CONF_QUIET_HOURS_END, default="07:00"): selector.TimeSelector(),
        }
    )

