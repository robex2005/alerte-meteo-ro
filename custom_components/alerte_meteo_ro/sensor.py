"""Platforma sensor pentru Alerte Meteo România (avertizări ANM + nowcasting)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .anm import (
    ANMAlertIDSensor,
    ANMAlertSensor,
    ANMApiStatusSensor,
    ANMCoordinator,
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

    # --- Avertizări ANM: un singur coordinator, o descărcare pe intervalul configurat ---
    anm = ANMCoordinator(hass, judet_cod, interval)
    # Ultimele avertizări ANM de pe disc: rămân vizibile (până expiră) dacă ANM nu răspunde la pornire.
    await anm.async_load_cache()
    # Prima actualizare înainte de adăugare, ca senzorii să aibă valori imediat.
    await anm.async_config_entry_first_refresh()

    async def _notify_anm() -> None:
        alerts = (anm.data or {}).get("alerts") or {}
        await notifier.async_check_anm(
            (alerts.get("attributes") or {}).get("avertizari"), judet_cod, judet_nume
        )

    if notifier.enabled:
        await _notify_anm()
        entry.async_on_unload(
            anm.async_add_listener(lambda: hass.async_create_task(_notify_anm()))
        )

    entities = [
        ANMAlertSensor(anm),
        ANMAlertIDSensor(anm),
        ANMMessageSensor(anm, judet_cod, judet_nume),
        ANMMapSensor(anm, judet_cod, judet_nume),
        ANMMapColorSensor(anm, judet_cod, judet_nume),
        ANMApiStatusSensor(anm),
    ]

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
