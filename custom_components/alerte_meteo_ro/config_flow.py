"""Config flow pentru Alerte Meteo România."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_COUNTIES,
    CONF_JUDET_COD,
    CONF_NOWCASTING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ANM_INTERVAL,
    DOMAIN,
    JUDETE,
    NAME,
    ROMANIAN_COUNTIES,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema comună pentru configurare inițială și opțiuni."""
    return vol.Schema(
        {
            vol.Required(
                CONF_JUDET_COD, default=defaults.get(CONF_JUDET_COD, "B")
            ): vol.In(
                {cod: nume for cod, nume in sorted(JUDETE.items(), key=lambda i: i[1])}
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_ANM_INTERVAL),
            ): cv.positive_int,
            vol.Required(
                CONF_NOWCASTING, default=defaults.get(CONF_NOWCASTING, True)
            ): bool,
            vol.Optional(
                CONF_COUNTIES, default=defaults.get(CONF_COUNTIES, [])
            ): cv.multi_select({c: c for c in sorted(ROMANIAN_COUNTIES)}),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configurare inițială: județ ANM + județe nowcasting."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Modificarea setărilor. self.config_entry este furnizat de Home Assistant."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
