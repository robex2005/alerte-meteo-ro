"""Senzori pentru avertizările ANM pe județ - Alerte Meteo România.

Provine din integrarea alerta-anm-judet-romania (GPL-3.0), integrată aici.
"""
import logging
import re
import json
import asyncio
import os
import aiohttp
import async_timeout
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

JSON_URL = "https://www.meteoromania.ro/wp-json/meteoapi/v2/avertizari-generale"
XML_URL = "https://www.meteoromania.ro/avertizari-xml.php"  # rezervă când JSON-ul nu răspunde
XML_PROBE_EVERY = timedelta(minutes=10)  # cât de des verificăm XML-ul când JSON-ul merge
# Timeout pe cerere (totalul unei actualizări rămâne limitat la 25 s): JSON 12 s + XML 12 s.
REQ_TIMEOUT = aiohttp.ClientTimeout(total=12)
PROBE_TIMEOUT = aiohttp.ClientTimeout(total=8)
HTML_URL = "https://www.meteoromania.ro/avertizari/"

# Ultimele avertizări primite de la ANM se păstrează pe disc, ca să rămână vizibile
# (până la expirare) dacă serverul ANM nu răspunde sau Home Assistant repornește.
CACHE_VERSION = 1
CACHE_KEY = "alerte_meteo_ro.anm_cache"
RO_TZ = ZoneInfo("Europe/Bucharest")           # ANM publică orele în ora României
CACHE_MAX_AGE_FARA_EXPIRARE = timedelta(hours=12)  # avertizare fără dată de expirare


def _xml_to_data(text):
    """Transformă XML-ul ANM (avertizari-xml.php) în aceeași structură ca JSON-ul API-ului.

    Păstrăm doar atributele folosite (fără coordGis, care e foarte mare). Ridică ValueError
    dacă răspunsul nu e un XML <avertizari> valid.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"XML ANM invalid: {e}")
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


class _Resp:
    """Răspuns ANM unificat (JSON sau XML), cu aceeași interfață folosită în async_update."""

    def __init__(self, status, data=None):
        self.status, self._data = status, data

    async def json(self):
        return self._data


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


class ANMAlertSensor(Entity):
    def __init__(self, hass):
        self._hass = hass
        self._state = None
        self._attributes = {}
        self._store = Store(hass, CACHE_VERSION, CACHE_KEY)
        self._good = None        # ultima listă primită de la ANM (poate fi goală)
        self._good_time = None   # când a fost primită
        # starea API-ului ANM (pentru senzorul „ANM API”)
        self._api_ok = None      # True / False / None (încă neîncercat)
        self._api_status = None  # cod HTTP al ultimei încercări
        self._api_error = None   # mesaj, dacă a fost excepție (timeout etc.)
        self._api_fails = 0      # încercări eșuate la rând
        self._api_fail_time = None
        self._api_source = None  # "json" sau "xml" (rezervă), ultima sursă folosită cu succes
        self._json_ok = None     # starea fiecărei surse: True / False / None (încă neverificată)
        self._xml_ok = None
        self._xml_probe_time = None

    def _api_up(self):
        self._api_ok, self._api_status, self._api_error, self._api_fails = True, 200, None, 0

    def _api_down(self, status, error=None):
        self._api_ok, self._api_status, self._api_error = False, status, error
        self._api_fails += 1
        self._api_fail_time = dt_util.utcnow()

    async def async_load_cache(self):
        """Încarcă ultimele date bune de pe disc (apelat o dată, înainte de prima actualizare)."""
        try:
            data = await self._store.async_load()
        except Exception as e:  # fișier corupt etc.: pornim fără cache
            _LOGGER.warning(f"Cache ANM ilizibil, îl ignor: {e}")
            return
        if not isinstance(data, dict) or not isinstance(data.get("avertizari"), list):
            return
        try:
            self._good_time = dt_util.parse_datetime(data.get("saved") or "")
        except Exception:
            self._good_time = None
        self._good = data["avertizari"]
        self._apply_good(din_cache=True)
        _LOGGER.info("Avertizări ANM restaurate din cache (%d)", len(self._good))

    def _save_good(self):
        good, saved = self._good, self._good_time
        self._store.async_delay_save(
            lambda: {"avertizari": good, "saved": saved.isoformat() if saved else None}, 5
        )

    def _apply_good(self, din_cache=False):
        """Afișează ultimele date bune, fără avertizările expirate."""
        acum = dt_util.now()
        alive = [a for a in (self._good or []) if not _expirata(a, self._good_time, acum)]
        attrs = {"friendly_name": "Avertizări Meteo ANM"}
        if alive:
            self._state = "active"
            attrs["avertizari"] = alive
        else:
            self._state = "inactive"
            attrs["avertizari"] = "Nu exista avertizari"
        if din_cache:
            attrs["sursa"] = "cache"
            if self._good_time:
                attrs["ultima_actualizare_anm"] = self._good_time.isoformat()
        self._attributes = attrs

    def _serve_cache_on_failure(self):
        """ANM nu răspunde: păstrăm ultimele date bune cât sunt valabile."""
        if self._good is not None:
            self._apply_good(din_cache=True)

    @property
    def name(self):
        return "Avertizări Meteo ANM"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        return "mdi:weather-lightning-rainy"

    @property
    def unique_id(self):
        return "anm_avertizari_meteo"

    @asynccontextmanager
    async def _fetch_anm(self, session):
        """JSON-ul API-ului; dacă nu răspunde (502, timeout etc.), XML-ul de pe site ca rezervă.

        O singură încercare pe sursă la fiecare actualizare (fără reîncercări). Fiecare cerere are
        timeout propriu, ca un API care nu răspunde deloc să lase timp și pentru XML.
        Cererile sunt făcute înainte de `yield`, ca o eroare la procesarea datelor să nu
        declanșeze din greșeală rezerva XML.
        """
        json_status, json_err, json_data, json_ok = None, None, None, False
        try:
            async with session.get(JSON_URL, timeout=REQ_TIMEOUT) as r:
                json_status = r.status
                if r.status == 200:
                    json_data, json_ok = await r.json(), True
        except Exception as e:  # timeout, JSON invalid etc.: încercăm XML-ul
            json_err = e
        if json_ok:
            self._api_source, self._json_ok = "json", True
            # JSON ok: verificăm din când în când și XML-ul, ca să știm dacă rezerva e disponibilă
            await self._probe_xml(session)
            yield _Resp(200, json_data)
            return

        self._json_ok = False
        xml_data = None
        try:
            async with session.get(XML_URL, timeout=REQ_TIMEOUT) as r:
                if r.status == 200:
                    xml_data = _xml_to_data(await r.text())
        except Exception as e:
            _LOGGER.debug("Rezerva XML ANM a eșuat: %s", e)
        self._xml_ok, self._xml_probe_time = xml_data is not None, dt_util.utcnow()
        if xml_data is not None:
            self._api_source = "xml"
            _LOGGER.warning("API-ul JSON ANM indisponibil (%s), folosesc XML-ul", json_status or json_err)
            yield _Resp(200, xml_data)
            return
        if json_err is not None:
            raise json_err
        yield _Resp(json_status)

    async def _probe_xml(self, session):
        """Cât timp JSON-ul merge, verifică doar starea XML-ului (cel mult o dată la XML_PROBE_EVERY)."""
        acum = dt_util.utcnow()
        if self._xml_probe_time and acum - self._xml_probe_time < XML_PROBE_EVERY:
            return
        self._xml_probe_time = acum
        try:
            async with session.get(XML_URL, timeout=PROBE_TIMEOUT) as r:
                self._xml_ok = r.status == 200
        except Exception:
            self._xml_ok = False

    async def async_update(self, now=None):
        _LOGGER.debug("Actualizare date Avertizări Meteo ANM")
        try:
            async with async_timeout.timeout(25):
                session = async_get_clientsession(self._hass)
                async with self._fetch_anm(session) as response:
                    if response.status == 200:
                        data = await response.json()
                        if not data or isinstance(data, str):
                            _LOGGER.warning(f"Nu există date disponibile: {data}")
                            self._state = "inactive"
                            self._attributes = {
                                "avertizari": "Nu exista avertizari",
                                "friendly_name": "Avertizări Meteo ANM"
                            }
                            # răspuns valid de la ANM („nu sunt avertizări”): înlocuiește cache-ul
                            self._good, self._good_time = [], dt_util.utcnow()
                            self._api_up()
                            self._save_good()
                            return

                        toate_avertizarile = []

                        avertizare = data.get('avertizare', None)
                        if isinstance(avertizare, dict):
                            avertizare = [avertizare]

                        if isinstance(avertizare, list):
                            for avertizare_item in avertizare:
                                if isinstance(avertizare_item, dict):
                                    for judet in avertizare_item.get('judet', []):
                                        if isinstance(judet, dict):
                                            try:
                                                avertizare_judet = {
                                                    "judet": judet.get('@attributes', {}).get('cod', 'necunoscut'),
                                                    "culoare": judet.get('@attributes', {}).get('culoare', 'necunoscut'),
                                                    "fenomene_vizate": avertizare_item.get('@attributes', {}).get('fenomeneVizate', 'necunoscut'),
                                                    "data_expirarii": avertizare_item.get('@attributes', {}).get('dataExpirarii', 'necunoscut'),
                                                    "data_aparitiei": avertizare_item.get('@attributes', {}).get('dataAparitiei', 'necunoscut'),
                                                    "intervalul": avertizare_item.get('@attributes', {}).get('intervalul', 'necunoscut'),
                                                    "mesaj": avertizare_item.get('@attributes', {}).get('mesaj', 'necunoscut')
                                                }
                                                toate_avertizarile.append(avertizare_judet)
                                            except KeyError as e:
                                                _LOGGER.error(f"Eroare la procesarea datelor pentru județ: {e}")
                                        else:
                                            _LOGGER.error("Judete nu este un dicționar, s-a primit: %s", type(judet))
                                else:
                                    _LOGGER.error("Avertizare nu este un dicționar, s-a primit: %s", type(avertizare_item))
                        else:
                            _LOGGER.error("Avertizare nu este un dicționar sau o listă validă, s-a primit: %s", type(avertizare))
                        
                        if toate_avertizarile:
                            self._state = "active"
                            self._attributes = {
                                "avertizari": toate_avertizarile,
                                "friendly_name": "Avertizări Meteo ANM"
                            }
                        else:
                            self._state = "inactive"
                            self._attributes = {
                                "avertizari": "Nu exista avertizari",
                                "friendly_name": "Avertizări Meteo ANM"
                            }
                        # date proaspete de la ANM: înlocuiesc imediat orice a ținut minte cache-ul
                        self._good, self._good_time = toate_avertizarile, dt_util.utcnow()
                        self._api_up()
                        self._save_good()
                        _LOGGER.info("Senzor ANM actualizat cu succes.")
                    else:
                        _LOGGER.error(f"Eroare HTTP {response.status} la preluarea datelor ANM")
                        self._api_down(response.status)
                        self._serve_cache_on_failure()
        except Exception as e:
            _LOGGER.error(f"Eroare la actualizarea datelor ANM: {e}")
            self._api_down(None, str(e) or type(e).__name__)
            self._serve_cache_on_failure()


class ANMApiStatusSensor(Entity):
    """Arată dacă API-ul ANM răspunde (online) sau nu (offline). Istoricul lui arată când a fost căzut."""

    def __init__(self, alert_sensor):
        self._alert = alert_sensor

    @property
    def name(self):
        return "ANM API"

    @property
    def unique_id(self):
        return "anm_api_status"

    @property
    def icon(self):
        return "mdi:cloud-check" if self._alert._api_ok else "mdi:cloud-alert"

    @property
    def state(self):
        if self._alert._api_ok is None:
            return None
        return "online" if self._alert._api_ok else "offline"

    @property
    def extra_state_attributes(self):
        a = self._alert
        iso = lambda d: d.isoformat() if d else None
        return {
            "sursa": a._api_source,
            "json": None if a._json_ok is None else ("online" if a._json_ok else "offline"),
            "xml": None if a._xml_ok is None else ("online" if a._xml_ok else "offline"),
            "cod_http": a._api_status,
            "eroare": a._api_error,
            "esecuri_la_rand": a._api_fails,
            "ultima_reusita": iso(a._good_time),
            "ultimul_esec": iso(a._api_fail_time),
            "friendly_name": "ANM API",
        }


class ANMAlertIDSensor(Entity):
    """Senzor pentru ID-urile alertelor ANM."""

    def __init__(self, hass):
        self._hass = hass
        self._state = "0"
        self._attributes = {}

    @property
    def name(self):
        return "ANM Avertizare ID"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        return "mdi:identifier"

    @property
    def unique_id(self):
        return "anm_avertizare_id"

    async def async_update(self, now=None):
        _LOGGER.debug("Actualizare ID-uri Avertizări ANM")
        try:
            async with async_timeout.timeout(10):
                session = async_get_clientsession(self._hass, verify_ssl=False)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                async with session.get(HTML_URL, headers=headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Extrage toate ID-urile de tipul id_avertizare=XXXX
                        pattern = r'id_avertizare=(\d+)'
                        ids = list(set(re.findall(pattern, html_content)))
                        
                        if ids:
                            # Sortează ID-urile și le unește cu virgulă
                            ids_sorted = sorted(ids, key=int, reverse=True)
                            self._state = ','.join(ids_sorted)
                            self._attributes = {
                                "id_list": ids_sorted,
                                "numar_id": len(ids_sorted),
                                "friendly_name": "ANM Avertizare ID"
                            }
                            _LOGGER.info(f"ID-uri ANM găsite: {self._state}")
                        else:
                            self._state = "0"
                            self._attributes = {
                                "id_list": [],
                                "numar_id": 0,
                                "friendly_name": "ANM Avertizare ID"
                            }
                            _LOGGER.info("Nu s-au găsit ID-uri ANM active")
                    else:
                        _LOGGER.error(f"Eroare HTTP {response.status} la preluarea paginii ANM")
        except Exception as e:
            _LOGGER.error(f"Eroare la actualizarea ID-urilor ANM: {e}")


class ANMMessageSensor(Entity):
    """Senzor pentru mesajul complet de avertizare pentru județul selectat."""

    def __init__(self, hass, judet_cod, judet_nume, alert_sensor):
        self._hass = hass
        self._judet_cod = judet_cod
        self._judet_nume = judet_nume
        self._alert_sensor = alert_sensor
        self._state = "liniste"
        self._attributes = {}

    @property
    def name(self):
        return f"Mesaj Meteo {self._judet_nume}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        # Județul e expus ca atribut, ca un card să nu depindă de numele lui.
        return {
            **self._attributes,
            "judet": self._judet_nume,
            "judet_cod": self._judet_cod,
        }

    @property
    def icon(self):
        return "mdi:alert-decagram"

    @property
    def unique_id(self):
        return f"anm_mesaj_meteo_{self._judet_cod.lower()}"

    @property
    def available(self):
        """Sensor is available only if alert sensor has valid data."""
        return self._alert_sensor.state not in [None, "unknown", "unavailable"]

    async def async_update(self, now=None):
        """Update se face automat când alert_sensor are date noi."""
        await self._process_alerts()

    async def _process_alerts(self):
        """Procesează alertele pentru județul selectat."""
        if not self._alert_sensor._attributes.get('avertizari'):
            self._state = "liniste"
            self._attributes = {
                "tip_cod": "Verde",
                "mesaj_complet": f"Nu sunt avertizări active pentru județul {self._judet_nume}.",
                "friendly_name": f"Mesaj Meteo {self._judet_nume}"
            }
            return

        avertizari = self._alert_sensor._attributes.get('avertizari', [])
        
        # Filtrăm alertele pentru județul curent
        if isinstance(avertizari, str):
            self._state = "liniste"
            self._attributes = {
                "tip_cod": "Verde",
                "mesaj_complet": avertizari,
                "friendly_name": f"Mesaj Meteo {self._judet_nume}"
            }
            return
        
        gl_list = [a for a in avertizari if a.get('judet') == self._judet_cod]
        
        if not gl_list:
            self._state = "liniste"
            self._attributes = {
                "tip_cod": "Verde",
                "mesaj_complet": f"Nu sunt avertizări active pentru județul {self._judet_nume}.",
                "friendly_name": f"Mesaj Meteo {self._judet_nume}"
            }
            return
        
        self._state = "alerta"
        
        # Calculăm cel mai grav cod
        max_code = max([int(a.get('culoare', 0)) for a in gl_list])
        tip_cod_map = {3: "Rosu", 2: "Portocaliu", 1: "Galben", 0: "Verde"}
        tip_cod = tip_cod_map.get(max_code, "Verde")
        
        # Construim mesajul complet
        mesaje = []
        for item in gl_list:
            msg_raw = item.get('mesaj', '')
            
            # Curățăm HTML-ul
            msg_raw = msg_raw.replace('<br />', '\n').replace('</p>', '\n')
            msg_raw = re.sub(r'<[^>]*>', '', msg_raw)
            msg_raw = msg_raw.replace('&nbsp;', ' ').replace('&ndash;', '-').strip()
            
            # Filtrăm mesajul pe baza culorii
            cod = int(item.get('culoare', 0))
            
            if cod == 1:  # Galben
                msg_raw = re.sub(r'COD PORTOCALIU[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
                msg_raw = re.sub(r'COD RO[SȘ]U[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
            elif cod == 2:  # Portocaliu
                msg_raw = re.sub(r'COD GALBEN[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
                msg_raw = re.sub(r'COD RO[SȘ]U[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
            elif cod == 3:  # Roșu
                msg_raw = re.sub(r'COD GALBEN[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
                msg_raw = re.sub(r'COD PORTOCALIU[\s\S]*?(?=COD|$)', '', msg_raw, flags=re.IGNORECASE)
            
            # Curățăm rânduri goale duble
            msg_final = re.sub(r'\n\s*\n', '\n\n', msg_raw).strip()
            mesaje.append(msg_final)
        
        mesaj_complet = '\n\n'.join(mesaje).strip()
        
        self._attributes = {
            "tip_cod": tip_cod,
            "mesaj_complet": mesaj_complet if mesaj_complet else f"Nu sunt avertizări active pentru județul {self._judet_nume}.",
            "friendly_name": f"Mesaj Meteo {self._judet_nume}"
        }
        
        _LOGGER.info(f"Mesaj meteo actualizat pentru {self._judet_nume}: {self._state} ({tip_cod})")


class ANMMapSensor(Entity):
    """Senzor pentru URL-ul hărții meteo active."""

    def __init__(self, hass, judet_cod, judet_nume, id_sensor):
        self._hass = hass
        self._judet_cod = judet_cod
        self._judet_nume = judet_nume
        self._id_sensor = id_sensor
        self._state = None
        self._attributes = {}
        
        import time
        self._timestamp = int(time.time())

    @property
    def name(self):
        return "Harta Meteo Activă"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        return "mdi:map-legend"

    @property
    def unique_id(self):
        return f"anm_harta_meteo_{self._judet_cod.lower()}"

    async def async_update(self, now=None):
        """Actualizare URL hartă în funcție de ID-urile active."""
        sensor_ids = self._id_sensor.state
        
        # Actualizăm timestamp-ul pentru cache busting
        import time
        self._timestamp = int(time.time())
        
        if sensor_ids and sensor_ids not in ['unknown', 'unavailable', '0', '']:
            # Preluăm primul ID din listă
            first_id = sensor_ids.split(',')[0]
            self._state = f"https://images.weserv.nl/?url=www.meteoromania.ro/wp-content/plugins/meteo/harti/harta.svg.php?id_avertizare={first_id}"
            url_direct = f"https://www.meteoromania.ro/wp-content/plugins/meteo/harti/harta.svg.php?id_avertizare={first_id}"
        else:
            # Fallback la harta generală
            self._state = f"https://images.weserv.nl/?url=www.meteoromania.ro/images/avertizari/harta.png&v={self._timestamp}"
            url_direct = "https://www.meteoromania.ro/images/avertizari/harta.png"
        
        self._attributes = {
            "ids_detectate": sensor_ids if sensor_ids else "0",
            "url_direct_anm": url_direct,
            "judet_selectat": self._judet_nume,
            "judet_cod": self._judet_cod,
            "friendly_name": "Harta Meteo Activă"
        }
        
        _LOGGER.debug(f"Hartă meteo actualizată pentru {self._judet_nume}: {self._state}")


class ANMMapColorSensor(Entity):
    """Senzor pentru culoarea județului pe hartă."""

    def __init__(self, hass, judet_cod, judet_nume, id_sensor):
        self._hass = hass
        self._judet_cod = judet_cod
        self._judet_nume = judet_nume
        self._id_sensor = id_sensor
        self._state = "verde"
        self._attributes = {}

    @property
    def name(self):
        return f"Culoare Hartă {self._judet_nume}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        if self._state == "rosu":
            return "mdi:alert-octagon"
        elif self._state == "portocaliu":
            return "mdi:alert"
        elif self._state == "galben":
            return "mdi:alert-circle"
        elif self._state == "informare":
            return "mdi:information"
        return "mdi:check-circle"

    @property
    def unique_id(self):
        return f"anm_culoare_harta_{self._judet_cod.lower()}"

    async def async_update(self, now=None):
        """Actualizare culoare prin apelarea scriptului check_map.py."""
        sensor_ids = self._id_sensor.state
        
        if not sensor_ids or sensor_ids in ['unknown', 'unavailable', '0', '']:
            self._state = "verde"
            self._attributes = {
                "date_harti": {},
                "judet_cod": self._judet_cod,
                "friendly_name": f"Culoare Hartă {self._judet_nume}"
            }
            return
        
        # Calea către script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "check_map.py")
        
        try:
            # Apelăm scriptul check_map.py
            process = await asyncio.create_subprocess_exec(
                "python3", script_path, sensor_ids, self._judet_cod,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result = json.loads(stdout.decode())
                date_harti = result.get("date_harti", {})
                zone_partiale = result.get("zone_partiale", {})
                
                # Determinăm cea mai gravă culoare
                priority = {"rosu": 4, "portocaliu": 3, "galben": 2, "informare": 1, "verde": 0}
                max_color = "verde"
                max_priority = 0
                
                for map_id, color in date_harti.items():
                    if priority.get(color, 0) > max_priority:
                        max_priority = priority.get(color, 0)
                        max_color = color
                
                # zone parțiale (munte / altitudine / litoral) colorate pe hartă, fără județul întreg
                culoare_zona = "verde"
                for zone in zone_partiale.values():
                    for color in zone.values():
                        if priority.get(color, 0) > priority.get(culoare_zona, 0):
                            culoare_zona = color

                self._state = max_color
                self._attributes = {
                    "date_harti": date_harti,
                    "zone_partiale": zone_partiale,
                    "culoare_zona": culoare_zona,
                    "numar_harti_verificate": len(date_harti),
                    "judet_cod": self._judet_cod,
                    "friendly_name": f"Culoare Hartă {self._judet_nume}"
                }
                
                _LOGGER.info(f"Culoare hartă pentru {self._judet_nume}: {self._state}")
            else:
                _LOGGER.error(f"Eroare la rularea check_map.py: {stderr.decode()}")
                self._state = "necunoscut"
                
        except Exception as e:
            _LOGGER.error(f"Eroare la verificarea culorii hărții: {e}")
            self._state = "necunoscut"
