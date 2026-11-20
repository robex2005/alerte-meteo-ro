"""Integrarea Alerte Meteo România: avertizări ANM pe județ + nowcasting."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurează integrarea dintr-un config entry."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Servește și încarcă automat cardul Lovelace `alerte-meteo-card` (o singură dată)."""
    if hass.data[DOMAIN].get("card_registered"):
        return
    url = f"/{DOMAIN}_static/alerte-meteo-card.js"
    path = Path(__file__).parent / "www" / "alerte-meteo-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(url, str(path), False)])
    version = path.stat().st_mtime_ns  # URL nou la fiecare actualizare => fără cache vechi
    frontend.add_extra_js_url(hass, f"{url}?v={version}")
    hass.data[DOMAIN]["card_registered"] = True


def _async_register_services(hass: HomeAssistant) -> None:
    """Serviciul alerte_meteo_ro.test_notificare (notificare de probă pe telefoanele alese)."""
    if hass.services.has_service(DOMAIN, "test_notificare"):
        return

    async def _test(call: ServiceCall) -> None:
        level = {"galben": 1, "portocaliu": 2, "rosu": 3}.get(call.data.get("cod", "portocaliu"), 2)
        sent = False
        for data in list(hass.data.get(DOMAIN, {}).values()):
            if not isinstance(data, dict) or "notifier" not in data:
                continue
            notifier = data["notifier"]
            if not notifier.enabled:
                continue
            scen = call.data.get("scenariu", "proba")
            if scen == "proba":
                await notifier.async_send_test(data["judet_cod"], data["judet_nume"], level)
            else:
                await notifier.async_send_scenario(scen, data["judet_cod"], data["judet_nume"])
            sent = True
        if not sent:
            raise HomeAssistantError(
                "Niciun telefon / serviciu ales: Configurare integrare → Notificări."
            )

    hass.services.async_register(
        DOMAIN,
        "test_notificare",
        _test,
        schema=vol.Schema({
            vol.Optional("cod", default="portocaliu"): vol.In(["galben", "portocaliu", "rosu"]),
            vol.Optional("scenariu", default="proba"): vol.In(["proba", "real", "doua", "nowcasting", "final"]),
        }),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarcă integrarea."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reîncarcă integrarea când se schimbă opțiunile."""
    _LOGGER.info("Opțiuni modificate, reîncarc %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
