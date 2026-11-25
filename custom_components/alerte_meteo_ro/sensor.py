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
    ANMApiStatusSensor,
    ANMMapColorSensor,
    ANMMapSensor,
    ANMMessageSensor,
)
from .const import (
    CONF_API_URL,
    CONF_COUNTIES,
    CONF_JUDET_COD,
    CONF_NOTIFY_ANM,
    CONF_NOTIFY_END,
    CONF_NOTIFY_MIN_LEVEL,
    CONF_NOTIFY_NOWCASTING,
    CONF_NOTIFY_SERVICES,
    CONF_NOTIFY_TEXT,
    CONF_NOTIFY_URL,
    CONF_NOWCASTING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ANM_INTERVAL,
    DEFAULT_API_URL,
    DOMAIN,
    JUDETE,
)
from .notify import AlerteNotifier
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
    api_sensor = ANMApiStatusSensor(alert_sensor)
    anm_entities = [alert_sensor, id_sensor, message_sensor, map_sensor, color_sensor, api_sensor]

    async def update_anm(now=None) -> None:
        _LOGGER.debug("Actualizare senzori ANM")
        # Ordinea contează: ceilalți senzori se bazează pe primii doi.
        await alert_sensor.async_update()
        await id_sensor.async_update()
        await message_sensor.async_update()
        await map_sensor.async_update()
        await color_sensor.async_update()

        await notifier.async_check_anm(
            alert_sensor._attributes.get("avertizari"), judet_cod, judet_nume
        )

    # --- Notificări aplicație companion ---
    notifier = AlerteNotifier(
        hass,
        entry.entry_id,
        cfg.get(CONF_NOTIFY_SERVICES) or [],
        cfg.get(CONF_NOTIFY_MIN_LEVEL, "galben"),
        cfg.get(CONF_NOTIFY_ANM, True),
        cfg.get(CONF_NOTIFY_NOWCASTING, True),
        cfg.get(CONF_NOTIFY_END, True),
        cfg.get(CONF_NOTIFY_URL, ""),
        cfg.get(CONF_NOTIFY_TEXT) or [],
    )
    await notifier.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "notifier": notifier,
        "judet_cod": judet_cod,
        "judet_nume": judet_nume,
    }

    # Ultimele avertizări ANM de pe disc: rămân vizibile (până expiră) dacă ANM nu răspunde la pornire.
    await alert_sensor.async_load_cache()

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

        async def _notify_nowcasting() -> None:
            data = coordinator.data or {}
            await notifier.async_check_nowcasting(data.get("active_alerts", []), counties)

        def _on_nowcasting_update() -> None:
            hass.async_create_task(_notify_nowcasting())

        if notifier.enabled:
            await _notify_nowcasting()
            entry.async_on_unload(coordinator.async_add_listener(_on_nowcasting_update))
        entities.extend(
            AlerteNowcastingSensor(coordinator, entry, county) for county in counties
        )

    async_add_entities(entities)
