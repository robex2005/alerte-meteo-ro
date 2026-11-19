"""Platforma sensor pentru Alerte Meteo România (avertizări ANM + nowcasting)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .anm import (
    ANMAlertIDSensor,
    ANMAlertSensor,
    ANMMapColorSensor,
    ANMMapSensor,
    ANMMessageSensor,
)
from .const import (
    CONF_API_URL,
    CONF_COUNTIES,
    CONF_JUDET_COD,
    CONF_NOWCASTING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ANM_INTERVAL,
    DEFAULT_API_URL,
    JUDETE,
)
from .nowcasting import AlerteNowcastingCoordinator, AlerteNowcastingSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creează senzorii ANM și, opțional, cei de nowcasting."""
    cfg = {**entry.data, **entry.options}

    judet_cod = cfg.get(CONF_JUDET_COD, "B")
    judet_nume = JUDETE.get(judet_cod, judet_cod)
    interval = timedelta(minutes=cfg.get(CONF_UPDATE_INTERVAL, DEFAULT_ANM_INTERVAL))

    # --- Avertizări ANM ---
    alert_sensor = ANMAlertSensor(hass)
    id_sensor = ANMAlertIDSensor(hass)
    message_sensor = ANMMessageSensor(hass, judet_cod, judet_nume, alert_sensor)
    map_sensor = ANMMapSensor(hass, judet_cod, judet_nume, id_sensor)
    color_sensor = ANMMapColorSensor(hass, judet_cod, judet_nume, id_sensor)
    anm_entities = [alert_sensor, id_sensor, message_sensor, map_sensor, color_sensor]

    async def update_anm(now=None) -> None:
        _LOGGER.debug("Actualizare senzori ANM")
        # Ordinea contează: ceilalți senzori se bazează pe primii doi.
        await alert_sensor.async_update()
        await id_sensor.async_update()
        await message_sensor.async_update()
        await map_sensor.async_update()
        await color_sensor.async_update()

    # Prima actualizare înainte de adăugare, ca senzorii să aibă valori imediat.
    await update_anm()
    entry.async_on_unload(async_track_time_interval(hass, update_anm, interval))

    entities = list(anm_entities)

    # --- Nowcasting ---
    if cfg.get(CONF_NOWCASTING, True):
        counties = cfg.get(CONF_COUNTIES) or [judet_nume]
        coordinator = AlerteNowcastingCoordinator(
            hass, cfg.get(CONF_API_URL, DEFAULT_API_URL), counties
        )
        await coordinator.async_config_entry_first_refresh()
        entities.extend(
            AlerteNowcastingSensor(coordinator, entry, county) for county in counties
        )

    async_add_entities(entities)
