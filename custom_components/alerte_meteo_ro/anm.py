"""Avertizările ANM pe județ - Alerte Meteo România.

Bazat pe alerta-anm-judet-romania, Copyright (C) 2026 dancucu
(https://github.com/dancucu/alerta-anm-judet-romania), licențiat GPL-3.0; modificat și integrat aici
(coordinator, rezervă XML, cache). Acest fișier e distribuit tot sub GPL-3.0 (vezi LICENSE).

Toate datele ANM (lista de avertizări, ID-urile hărților și culoarea județului pe hartă) se
descarcă o singură dată pe interval, în `ANMCoordinator`; senzorii doar citesc rezultatul.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .harta import parse_map

_LOGGER = logging.getLogger(__name__)

JSON_URL = "https://www.meteoromania.ro/wp-json/meteoapi/v2/avertizari-generale"
XML_URL = "https://www.meteoromania.ro/avertizari-xml.php"  # rezervă când JSON-ul nu răspunde
HTML_URL = "https://www.meteoromania.ro/avertizari/"
MAP_URL = "https://www.meteoromania.ro/wp-content/plugins/meteo/harti/harta.svg.php?id_avertizare={}"
XML_PROBE_EVERY = timedelta(minutes=10)  # cât de des verificăm XML-ul când JSON-ul merge
# Timeout pe cerere: JSON 12 s + XML 12 s (lista), pagina HTML și fiecare hartă 10 s.
REQ_TIMEOUT = aiohttp.ClientTimeout(total=12)
PROBE_TIMEOUT = aiohttp.ClientTimeout(total=8)
PAGE_TIMEOUT = aiohttp.ClientTimeout(total=10)
ALERTS_TIMEOUT = 25  # secunde, totalul pentru lista de avertizări (JSON + XML)
HEADERS = {"User-Agent": "Mozilla/5.0 (Home Assistant; alerte_meteo_ro)"}

# Ultimele avertizări primite de la ANM se păstrează pe disc, ca să rămână vizibile
# (până la expirare) dacă serverul ANM nu răspunde sau Home Assistant repornește.
CACHE_VERSION = 1
CACHE_KEY = "alerte_meteo_ro.anm_cache"
RO_TZ = ZoneInfo("Europe/Bucharest")           # ANM publică orele în ora României
CACHE_MAX_AGE_FARA_EXPIRARE = timedelta(hours=12)  # avertizare fără dată de expirare
FARA = "Nu exista avertizari"
COLOR_PRIORITY = {"rosu": 4, "portocaliu": 3, "galben": 2, "informare": 1, "verde": 0}


def _xml_to_data(text):
    """Transformă XML-ul ANM (avertizari-xml.php) în aceeași structură ca JSON-ul API-ului.

    Păstrăm doar atributele folosite (fără coordGis, care e foarte mare). Ridică ValueError
    dacă răspunsul nu e un XML <avertizari> valid.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"XML ANM invalid: {e}") from e
    if root.tag != "avertizari":
        raise ValueError(f"XML ANM neașteptat: <{root.tag}>")
    avertizari = []
    for av in root.findall("avertizare"):
        judete = [
            {"@attributes": {"cod": j.get("cod"), "culoare": j.get("culoare")}}
            for j in av.findall("judet")
        ]
        avertizari.append({"@attributes": dict(av.attrib), "judet": judete})
    return {"avertizare": avertizari} if avertizari else {}


def _parse_avertizari(data) -> list[dict]:
    """Lista plată de avertizări (una pe județ) din răspunsul ANM (JSON sau XML convertit)."""
    if not data or isinstance(data, str):
        return []
    rezultat = []
    avertizare = data.get("avertizare")
    if isinstance(avertizare, dict):
        avertizare = [avertizare]
    if not isinstance(avertizare, list):
        _LOGGER.error("Avertizare nu este un dicționar sau o listă validă, s-a primit: %s", type(avertizare))
        return []
    for item in avertizare:
        if not isinstance(item, dict):
            _LOGGER.error("Avertizare nu este un dicționar, s-a primit: %s", type(item))
            continue
        a = item.get("@attributes", {}) or {}
        for judet in item.get("judet", []) or []:
            if not isinstance(judet, dict):
                _LOGGER.error("Judet nu este un dicționar, s-a primit: %s", type(judet))
                continue
            ja = judet.get("@attributes", {}) or {}
            rezultat.append({
                "judet": ja.get("cod", "necunoscut"),
                "culoare": ja.get("culoare", "necunoscut"),
                "fenomene_vizate": a.get("fenomeneVizate", "necunoscut"),
                "data_expirarii": a.get("dataExpirarii", "necunoscut"),
                "data_aparitiei": a.get("dataAparitiei", "necunoscut"),
                "intervalul": a.get("intervalul", "necunoscut"),
                "mesaj": a.get("mesaj", "necunoscut"),
            })
    return rezultat


def _expirata(item, salvat, acum):
    """True dacă avertizarea din cache nu mai e valabilă."""
    try:
        exp = datetime.fromisoformat(str(item.get("data_expirarii")))
    except (TypeError, ValueError):
        # fără dată de expirare: o păstrăm doar o perioadă limitată
        return salvat is None or acum - salvat > CACHE_MAX_AGE_FARA_EXPIRARE
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=RO_TZ)
    return exp <= acum


class _FetchError(Exception):
    """Nicio sursă ANM (JSON/XML) n-a răspuns."""

    def __init__(self, status=None, error=None):
        super().__init__(error or f"HTTP {status}")
        self.status, self.error = status, error


class ANMCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Descarcă o dată pe interval avertizările, ID-urile hărților și culoarea județului.

    Nu ridică UpdateFailed când ANM nu răspunde: senzorii păstrează ultimele date bune
    (avertizările din cache până expiră), iar starea API-ului apare în `sensor.anm_api`.
    """

    def __init__(self, hass: HomeAssistant, judet_cod: str, interval: timedelta) -> None:
        super().__init__(hass, _LOGGER, name="alerte_meteo_ro_anm", update_interval=interval)
        self.judet_cod = judet_cod
        self._session = async_get_clientsession(hass)
        self._store = Store(hass, CACHE_VERSION, CACHE_KEY)
        self._good: list | None = None   # ultima listă primită de la ANM (poate fi goală)
        self.good_time = None            # când a fost primită
        # starea API-ului ANM (pentru senzorul „ANM API”)
        self.api_ok = None       # True / False / None (încă neîncercat)
        self.api_status = None   # cod HTTP al ultimei încercări
        self.api_error = None    # mesaj, dacă a fost excepție (timeout etc.)
        self.api_fails = 0       # încercări eșuate la rând
        self.api_fail_time = None
        self.api_source = None   # "json" sau "xml" (rezervă), ultima sursă folosită cu succes
        self.json_ok = None      # starea fiecărei surse: True / False / None (încă neverificată)
        self.xml_ok = None
        self._xml_probe_time = None
        # ultimele valori afișate (se păstrează la erori)
        self._alerts = {"state": None, "attributes": {}}
        self._ids: list[str] | None = None
        self._map: dict | None = None

    # ---------- cache ----------
    async def async_load_cache(self) -> None:
        """Încarcă ultimele date bune de pe disc (o dată, înainte de prima actualizare)."""
        try:
            data = await self._store.async_load()
        except Exception as e:  # noqa: BLE001 - fișier corupt etc.: pornim fără cache
            _LOGGER.warning("Cache ANM ilizibil, îl ignor: %s", e)
            return
        if not isinstance(data, dict) or not isinstance(data.get("avertizari"), list):
            return
        try:
            self.good_time = dt_util.parse_datetime(data.get("saved") or "")
        except (TypeError, ValueError):
            self.good_time = None
        self._good = data["avertizari"]
        self._apply_good(din_cache=True)
        _LOGGER.info("Avertizări ANM restaurate din cache (%d)", len(self._good))

    def _save_good(self) -> None:
        good, saved = self._good, self.good_time
        self._store.async_delay_save(
            lambda: {"avertizari": good, "saved": saved.isoformat() if saved else None}, 5
        )

    def _apply_good(self, din_cache=False) -> None:
        """Afișează ultimele date bune, fără avertizările expirate (doar pentru cache)."""
        lista = self._good or []
        if din_cache:
            acum = dt_util.now()
            lista = [a for a in lista if not _expirata(a, self.good_time, acum)]
        attrs: dict[str, Any] = {"avertizari": lista if lista else FARA}
        if din_cache:
            attrs["sursa"] = "cache"
            if self.good_time:
                attrs["ultima_actualizare_anm"] = self.good_time.isoformat()
        self._alerts = {"state": "active" if lista else "inactive", "attributes": attrs}

    # ---------- rețea ----------
    async def _probe_xml(self) -> None:
        """Cât timp JSON-ul merge, verifică doar starea XML-ului (cel mult o dată la XML_PROBE_EVERY)."""
        acum = dt_util.utcnow()
        if self._xml_probe_time and acum - self._xml_probe_time < XML_PROBE_EVERY:
            return
        self._xml_probe_time = acum
        try:
            async with self._session.get(XML_URL, timeout=PROBE_TIMEOUT, headers=HEADERS) as r:
                self.xml_ok = r.status == 200
        except (aiohttp.ClientError, TimeoutError):
            self.xml_ok = False

    async def _fetch_list(self):
        """JSON-ul API-ului; dacă nu răspunde (502, timeout etc.), XML-ul de pe site ca rezervă."""
        json_status, json_err, json_data = None, None, None
        try:
            async with self._session.get(JSON_URL, timeout=REQ_TIMEOUT, headers=HEADERS) as r:
                json_status = r.status
                if r.status == 200:
                    json_data = await r.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as e:
            json_err = e
        if json_status == 200 and json_err is None:
            self.api_source, self.json_ok = "json", True
            await self._probe_xml()
            return json_data

        self.json_ok = False
        xml_data = None
        try:
            async with self._session.get(XML_URL, timeout=REQ_TIMEOUT, headers=HEADERS) as r:
                if r.status == 200:
                    xml_data = _xml_to_data(await r.text())
        except (aiohttp.ClientError, TimeoutError, ValueError) as e:
            _LOGGER.debug("Rezerva XML ANM a eșuat: %s", e)
        self.xml_ok, self._xml_probe_time = xml_data is not None, dt_util.utcnow()
        if xml_data is not None:
            self.api_source = "xml"
            _LOGGER.warning("API-ul JSON ANM indisponibil (%s), folosesc XML-ul", json_status or json_err)
            return xml_data
        if json_err is not None:
            raise _FetchError(None, str(json_err) or type(json_err).__name__)
        raise _FetchError(json_status)

    async def _update_alerts(self) -> None:
        try:
            async with asyncio.timeout(ALERTS_TIMEOUT):
                data = await self._fetch_list()
        except (_FetchError, TimeoutError) as e:
            status = getattr(e, "status", None)
            err = getattr(e, "error", None) or (None if status else (str(e) or type(e).__name__))
            _LOGGER.error("Eroare la preluarea avertizărilor ANM: %s", f"HTTP {status}" if status else err)
            self.api_ok, self.api_status, self.api_error = False, status, err
            self.api_fails += 1
            self.api_fail_time = dt_util.utcnow()
            if self._good is not None:  # ANM nu răspunde: ultimele date bune, cât sunt valabile
                self._apply_good(din_cache=True)
            return
        if not data or isinstance(data, str):
            _LOGGER.debug("ANM: nu există avertizări (%s)", data)
        # date proaspete de la ANM: înlocuiesc imediat orice a ținut minte cache-ul
        self._good, self.good_time = _parse_avertizari(data), dt_util.utcnow()
        self.api_ok, self.api_status, self.api_error, self.api_fails = True, 200, None, 0
        self._save_good()
        self._apply_good()

    async def _update_ids(self) -> None:
        """ID-urile avertizărilor de pe pagina ANM (pentru hărți). La eroare rămân cele vechi."""
        try:
            async with self._session.get(HTML_URL, timeout=PAGE_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    _LOGGER.error("Eroare HTTP %s la preluarea paginii ANM", r.status)
                    return
                html = await r.text()
        except (aiohttp.ClientError, TimeoutError) as e:
            _LOGGER.error("Eroare la actualizarea ID-urilor ANM: %s", e)
            return
        ids = set(re.findall(r"id_avertizare=(\d+)", html))
        self._ids = sorted(ids, key=int, reverse=True)

    async def _check_map(self, map_id: str) -> tuple[str, dict]:
        try:
            async with self._session.get(MAP_URL.format(map_id), timeout=PAGE_TIMEOUT, headers=HEADERS) as r:
                if r.status != 200:
                    return "eroare_http", {}
                content = await r.text()
        except (aiohttp.ClientError, TimeoutError):
            return "eroare_http", {}
        try:
            return await self.hass.async_add_executor_job(parse_map, content, self.judet_cod)
        except Exception:  # noqa: BLE001 - SVG neașteptat: nu oprim actualizarea
            _LOGGER.exception("Eroare la citirea hărții ANM %s", map_id)
            return "eroare_script", {}

    async def _update_map(self) -> None:
        if not self._ids:
            self._map = None
            return
        results = await asyncio.gather(*(self._check_map(i) for i in self._ids))
        date_harti, zone = {}, {}
        for map_id, (color, zones) in zip(self._ids, results):
            date_harti[map_id] = color
            if zones:
                zone[map_id] = zones
        self._map = {"date_harti": date_harti, "zone_partiale": zone}

    async def _async_update_data(self) -> dict[str, Any]:
        await self._update_alerts()
        await self._update_ids()
        await self._update_map()
        return {"alerts": dict(self._alerts), "ids": list(self._ids or []), "map": self._map}


# ---------------------------------------------------------------- senzori
class _ANMEntity(CoordinatorEntity[ANMCoordinator], SensorEntity):
    """Bază: valorile se recalculează doar când coordinatorul are date noi."""

    def __init__(self, coordinator: ANMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_extra_state_attributes = {}
        self._refresh()

    def _refresh(self) -> None:
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return True  # datele vechi (cache) rămân vizibile; starea ANM e în sensor.anm_api


class ANMAlertSensor(_ANMEntity):
    _attr_name = "Avertizări Meteo ANM"
    _attr_unique_id = "anm_avertizari_meteo"
    _attr_icon = "mdi:weather-lightning-rainy"

    def _refresh(self) -> None:
        a = (self.coordinator.data or {}).get("alerts") or {"state": None, "attributes": {}}
        self._attr_native_value = a["state"]
        self._attr_extra_state_attributes = {**a["attributes"], "friendly_name": "Avertizări Meteo ANM"}


class ANMApiStatusSensor(_ANMEntity):
    """Arată dacă API-ul ANM răspunde (online) sau nu (offline). Istoricul lui arată când a fost căzut."""

    _attr_name = "ANM API"
    _attr_unique_id = "anm_api_status"

    def _refresh(self) -> None:
        c = self.coordinator
        self._attr_native_value = None if c.api_ok is None else ("online" if c.api_ok else "offline")
        self._attr_icon = "mdi:cloud-check" if c.api_ok else "mdi:cloud-alert"
        iso = lambda d: d.isoformat() if d else None  # noqa: E731
        st = lambda v: None if v is None else ("online" if v else "offline")  # noqa: E731
        self._attr_extra_state_attributes = {
            "sursa": c.api_source,
            "json": st(c.json_ok),
            "xml": st(c.xml_ok),
            "cod_http": c.api_status,
            "eroare": c.api_error,
            "esecuri_la_rand": c.api_fails,
            "ultima_reusita": iso(c.good_time),
            "ultimul_esec": iso(c.api_fail_time),
            "friendly_name": "ANM API",
        }


class ANMAlertIDSensor(_ANMEntity):
    """ID-urile avertizărilor ANM (de pe pagina de avertizări)."""

    _attr_name = "ANM Avertizare ID"
    _attr_unique_id = "anm_avertizare_id"
    _attr_icon = "mdi:identifier"

    def _refresh(self) -> None:
        ids = (self.coordinator.data or {}).get("ids") or []
        self._attr_native_value = ",".join(ids) if ids else "0"
        self._attr_extra_state_attributes = {
            "id_list": ids, "numar_id": len(ids), "friendly_name": "ANM Avertizare ID",
        }


def _curata_mesaj(item: dict) -> str:
    """Textul mesajului ANM fără HTML, doar partea pentru culoarea avertizării."""
    msg = str(item.get("mesaj", "") or "")
    msg = msg.replace("<br />", "\n").replace("</p>", "\n")
    msg = re.sub(r"<[^>]*>", "", msg)
    msg = msg.replace("&nbsp;", " ").replace("&ndash;", "-").strip()
    try:
        cod = int(item.get("culoare", 0))
    except (TypeError, ValueError):
        cod = 0
    alte = {1: ("PORTOCALIU", "RO[SȘ]U"), 2: ("GALBEN", "RO[SȘ]U"), 3: ("GALBEN", "PORTOCALIU")}.get(cod, ())
    for c in alte:
        msg = re.sub(rf"COD {c}[\s\S]*?(?=COD|$)", "", msg, flags=re.IGNORECASE)
    return re.sub(r"\n\s*\n", "\n\n", msg).strip()


class ANMMessageSensor(_ANMEntity):
    """Mesajul complet de avertizare pentru județul selectat."""

    _attr_icon = "mdi:alert-decagram"

    def __init__(self, coordinator, judet_cod, judet_nume) -> None:
        self._judet_cod, self._judet_nume = judet_cod, judet_nume
        self._attr_name = f"Mesaj Meteo {judet_nume}"
        self._attr_unique_id = f"anm_mesaj_meteo_{judet_cod.lower()}"
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        """Disponibil doar când lista de avertizări ANM are date (live sau din cache)."""
        return ((self.coordinator.data or {}).get("alerts") or {}).get("state") is not None

    def _refresh(self) -> None:
        alerts = ((self.coordinator.data or {}).get("alerts") or {}).get("attributes", {})
        avertizari = alerts.get("avertizari")
        verde = f"Nu sunt avertizări active pentru județul {self._judet_nume}."
        base = {"judet": self._judet_nume, "judet_cod": self._judet_cod,
                "friendly_name": f"Mesaj Meteo {self._judet_nume}"}
        lista = [a for a in avertizari if a.get("judet") == self._judet_cod] if isinstance(avertizari, list) else []
        if not lista:
            self._attr_native_value = "liniste"
            text = avertizari if isinstance(avertizari, str) and avertizari else verde
            self._attr_extra_state_attributes = {"tip_cod": "Verde", "mesaj_complet": text, **base}
            return
        coduri = []
        for a in lista:
            try:
                coduri.append(int(a.get("culoare", 0)))
            except (TypeError, ValueError):
                coduri.append(0)
        tip_cod = {3: "Rosu", 2: "Portocaliu", 1: "Galben"}.get(max(coduri), "Verde")
        mesaj = "\n\n".join(_curata_mesaj(a) for a in lista).strip()
        self._attr_native_value = "alerta"
        self._attr_extra_state_attributes = {"tip_cod": tip_cod, "mesaj_complet": mesaj or verde, **base}


class ANMMapSensor(_ANMEntity):
    """URL-ul hărții meteo active."""

    _attr_name = "Harta Meteo Activă"
    _attr_icon = "mdi:map-legend"

    def __init__(self, coordinator, judet_cod, judet_nume) -> None:
        self._judet_cod, self._judet_nume = judet_cod, judet_nume
        self._attr_unique_id = f"anm_harta_meteo_{judet_cod.lower()}"
        super().__init__(coordinator)

    def _refresh(self) -> None:
        ids = (self.coordinator.data or {}).get("ids") or []
        if ids:
            direct = MAP_URL.format(ids[0])
            self._attr_native_value = "https://images.weserv.nl/?url=" + direct.replace("https://", "")
        else:  # fără avertizări: harta generală (cu parametru anti-cache)
            direct = "https://www.meteoromania.ro/images/avertizari/harta.png"
            self._attr_native_value = (
                "https://images.weserv.nl/?url=www.meteoromania.ro/images/avertizari/harta.png"
                f"&v={int(time.time())}"
            )
        self._attr_extra_state_attributes = {
            "ids_detectate": ",".join(ids) if ids else "0",
            "url_direct_anm": direct,
            "judet_selectat": self._judet_nume,
            "judet_cod": self._judet_cod,
            "friendly_name": "Harta Meteo Activă",
        }


class ANMMapColorSensor(_ANMEntity):
    """Culoarea județului pe harta ANM (cea mai gravă dintre hărțile active)."""

    def __init__(self, coordinator, judet_cod, judet_nume) -> None:
        self._judet_cod, self._judet_nume = judet_cod, judet_nume
        self._attr_name = f"Culoare Hartă {judet_nume}"
        self._attr_unique_id = f"anm_culoare_harta_{judet_cod.lower()}"
        super().__init__(coordinator)

    @property
    def icon(self) -> str:
        return {
            "rosu": "mdi:alert-octagon", "portocaliu": "mdi:alert",
            "galben": "mdi:alert-circle", "informare": "mdi:information",
        }.get(self._attr_native_value, "mdi:check-circle")

    def _refresh(self) -> None:
        harta = (self.coordinator.data or {}).get("map")
        base = {"judet_cod": self._judet_cod, "friendly_name": f"Culoare Hartă {self._judet_nume}"}
        if not harta:
            self._attr_native_value = "verde"
            self._attr_extra_state_attributes = {"date_harti": {}, **base}
            return
        date_harti, zone_partiale = harta["date_harti"], harta["zone_partiale"]
        culoare = max(date_harti.values(), key=lambda c: COLOR_PRIORITY.get(c, 0), default="verde")
        if COLOR_PRIORITY.get(culoare, 0) == 0:
            culoare = "verde"
        # zone parțiale (munte / altitudine / litoral) colorate pe hartă, fără județul întreg
        culoare_zona = "verde"
        for zone in zone_partiale.values():
            for c in zone.values():
                if COLOR_PRIORITY.get(c, 0) > COLOR_PRIORITY.get(culoare_zona, 0):
                    culoare_zona = c
        self._attr_native_value = culoare
        self._attr_extra_state_attributes = {
            "date_harti": date_harti,
            "zone_partiale": zone_partiale,
            "culoare_zona": culoare_zona,
            "numar_harti_verificate": len(date_harti),
            **base,
        }
