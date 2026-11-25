"""Notificări push prin aplicația Home Assistant Companion (notify.mobile_app_*).

Formatul urmează exemplele din proiectele originale (dancucu): titlu cu codul și
județul, „🕒 interval” + „💨 Fenomene vizate” ca listă, sunet critic la portocaliu/roșu,
link către un dashboard și o notificare „✅ Alertă Meteo Finalizată” la încheiere.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
MAX_SEEN = 300  # câte chei de avertizări păstrăm ca să nu notificăm de două ori

LEVELS = {"galben": 1, "portocaliu": 2, "rosu": 3}
TITLES = {1: "🟡 COD GALBEN", 2: "🟠 COD PORTOCALIU", 3: "🔴 COD ROȘU"}
LEVEL_COLORS = {1: "#FFD600", 2: "#FF8C00", 3: "#E53935"}


def mobile_app_services(hass: HomeAssistant) -> list[str]:
    """Serviciile notify ale aplicației companion (mobile_app_<telefon>)."""
    return sorted(
        s for s in hass.services.async_services().get("notify", {})
        if s.startswith("mobile_app_")
    )


EXCLUDED_TEXT = {"notify", "send_message", "persistent_notification"}


def text_notify_services(hass: HomeAssistant) -> list[str]:
    """Alte servicii notify (WhatsApp/CallMeBot, Telegram, grupuri) – primesc doar text."""
    return sorted(
        s for s in hass.services.async_services().get("notify", {})
        if not s.startswith("mobile_app_") and s not in EXCLUDED_TEXT
    )


INDENT = "\u2003\u2002"  # ~ lățimea unui emoji + spațiu (WhatsApp nu taie aceste spații)


def _whatsapp_body(message: str) -> str:
    """Text compact pentru WhatsApp: sfârșitul sub început, fenomenele indentate sub titlu."""
    out = []
    for line in message.replace("\n\n", "\n").split("\n"):
        if line.startswith("🕒 ") and len(line) > 20:
            parts = re.split(r"\s+[–-]\s+", line[2:].strip(), maxsplit=1)
            if len(parts) == 2:
                out.append("🕒 Interval:")
                out.append(f"{INDENT}{parts[0]} –")
                out.append(f"{INDENT}{parts[1]}")
                continue
        if line.startswith("- "):
            line = f"{INDENT}{line}"
        out.append(line)
    return "\n".join(out)


def _level_from_name(name: str) -> int:
    n = (name or "").lower().replace("ș", "s").replace("ş", "s")
    for key, lvl in LEVELS.items():
        if key in n:
            return lvl
    return 0


def _clean(text: str, limit: int = 220) -> str:
    text = re.sub(r"<[^>]*>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _fenomene_list(text: str) -> str:
    items = [i.strip(" .") for i in _clean(text, 400).split(",") if i.strip(" .")]
    return "".join(f"\n- {i}" for i in items)


_MESE = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
         "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


def _is_vag(text: Any) -> bool:
    """ANM scrie uneori „conform textelor” în loc de interval/fenomene (sau lipsesc)."""
    t = str(text or "").strip().lower()
    return not t or t == "necunoscut" or "conform text" in t


def _interval_anm(a: dict[str, Any]) -> str:
    """Intervalul în formatul ANM („23 noiembrie, ora 10 – 24 noiembrie, ora 20”).

    Dacă ANM trimite „conform textelor”, îl refacem din data de apariție/expirare din listă,
    la fel indiferent dacă datele vin din API-ul JSON sau din fluxul XML.
    """
    iv = a.get("intervalul", "")
    if not _is_vag(iv):
        return iv
    try:
        s = datetime.fromisoformat(str(a.get("data_aparitiei")))
        e = datetime.fromisoformat(str(a.get("data_expirarii")))
    except (TypeError, ValueError):
        return iv
    if e <= s:
        return iv
    f = lambda d: f"{d.day} {_MESE[d.month - 1]}, ora {d.hour:02d}"
    return f"{f(s)} – {f(e)}"


def _fenomene_anm(a: dict[str, Any]) -> str:
    """Fenomenele; când lista spune „conform textelor”, le luăm din textul mesajului ANM."""
    fen = a.get("fenomene_vizate", "")
    if not _is_vag(fen):
        return fen
    text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", str(a.get("mesaj") or ""), flags=re.I)
    text = html.unescape(re.sub(r"<[^>]*>", "", text))
    m = re.search(r"Fenomene\s+vizate\s*:\s*([^\n]+)", text, flags=re.I)
    return m.group(1).strip() if m else fen


def format_anm(level: int, judet_nume: str, interval: str, fenomene: str) -> tuple[str, str]:
    """Titlu + mesaj pentru o avertizare ANM; județul vine mereu din configurare."""
    title = f"{TITLES.get(level, 'ℹ️ Informare Meteo')} {judet_nume.upper()}"
    msg = []
    if interval and interval != "necunoscut":
        msg.append(f"🕒 {_clean(interval, 120)}")
    fen = _fenomene_list(fenomene)
    if fen:
        msg.append(f"💨 Fenomene vizate:{fen}")
    return title, "\n\n".join(msg) or "Vezi aplicația"


def format_nowcasting(level: int, county: str, start: Any, end: Any, desc: str) -> tuple[str, str]:
    """Titlu + mesaj pentru o alertă nowcasting: interval scurt (ore) + fenomenele ca listă."""
    title = f"{TITLES.get(level, 'ℹ️ Informare')} NOWCASTING {county.upper()}"
    msg = []
    if start and end:
        msg.append(f"🕒 {start:%H:%M} – {end:%H:%M}")
    text = _clean(desc, 300)
    items = [i.strip(" .") for i in re.split(r",|;|\s+și\s+", text) if i.strip(" .")]
    if items and len(text) <= 160:
        msg.append("⚡ Fenomene:" + "".join(f"\n- {i}" for i in items))
    elif text:
        msg.append(f"⚡ {text}")
    return title, "\n\n".join(msg) or "Vezi aplicația"


def format_end(judet_nume: str) -> tuple[str, str]:
    return (
        "✅ Alertă Meteo Finalizată",
        f"Nu mai sunt avertizări meteo active pentru {judet_nume}. Vremea s-a liniștit. ☀️",
    )


class AlerteNotifier:
    """Câte o notificare pentru fiecare avertizare nouă (fără duplicate, și după restart)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        services: list[str],
        min_level: str,
        notify_anm: bool,
        notify_nowcasting: bool,
        notify_end: bool,
        url: str,
        text_services: list[str] | None = None,
    ) -> None:
        self.hass = hass
        self.services = [s.removeprefix("notify.") for s in services]
        self.min_level = LEVELS.get(min_level, 1)
        self.notify_anm = notify_anm
        self.notify_nowcasting = notify_nowcasting
        self.notify_end = notify_end
        self.url = (url or "").strip()
        self.text_services = [s.removeprefix("notify.") for s in (text_services or [])]
        self._store: Store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}.notified")
        self._seen: list[str] = []
        self._anm_active = False

    @property
    def enabled(self) -> bool:
        return bool(self.services or self.text_services)

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._seen = list(data.get("seen", []))
        self._anm_active = bool(data.get("anm_active", False))

    async def _save(self) -> None:
        self._seen = self._seen[-MAX_SEEN:]
        await self._store.async_save({"seen": self._seen, "anm_active": self._anm_active})

    async def async_send(self, title: str, message: str, level: int, tag: str) -> None:
        message = _whatsapp_body(message)  # același format compact în aplicație și pe WhatsApp
        critical = level >= 2
        data: dict[str, Any] = {
            "tag": tag,
            "group": "alerte_meteo",
            "channel": "Alerte meteo",
            "importance": "high" if critical else "default",
            "color": LEVEL_COLORS.get(level, "#4CAF50"),
            "push": {
                "interruption-level": "critical" if critical else "active",
                "sound": {"name": "default", "critical": 1, "volume": 1.0}
                if critical
                else "default",
            },
        }
        if self.url:
            data["url"] = self.url  # iOS
            data["clickAction"] = self.url  # Android
        for service in self.services:
            try:
                await self.hass.services.async_call(
                    "notify",
                    service,
                    {"title": title, "message": message, "data": data},
                    blocking=False,
                )
            except Exception as err:  # serviciu șters / telefon dezinstalat
                _LOGGER.warning("Notificare eșuată prin notify.%s: %s", service, err)
        if self.text_services:
            # WhatsApp & co.: fără titlu/date separate -> titlul îngroșat în text
            text = f"*{title}*\n\n{message}"
            for service in self.text_services:
                try:
                    await self.hass.services.async_call(
                        "notify", service, {"message": text}, blocking=False
                    )
                except Exception as err:
                    _LOGGER.warning("Mesaj eșuat prin notify.%s: %s", service, err)

    async def async_send_test(self, judet_cod: str, judet_nume: str, level: int = 2) -> None:
        """Notificare de probă (serviciul alerte_meteo_ro.test_notificare)."""
        title, message = format_anm(
            level,
            judet_nume,
            "TEST – aceasta este o notificare de probă",
            "intensificări ale vântului, ninsori",
        )
        await self.async_send(title, message, level, f"amr_test_{judet_cod.lower()}")

    async def async_send_scenario(self, scenariu: str, judet_cod: str, judet_nume: str) -> None:
        """Mesaje de probă realiste (ore reale, format identic cu avertizările ANM)."""
        from datetime import timedelta
        from homeassistant.util import dt as dt_util

        luni = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
                "august", "septembrie", "octombrie", "noiembrie", "decembrie"]

        def zi(d):
            return f"{d.day} {luni[d.month - 1]}, ora {d.hour}"

        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        tag = f"amr_test_{judet_cod.lower()}"
        warnings = []
        if scenariu in ("real", "doua"):
            s, e = now + timedelta(hours=2), now + timedelta(hours=26)
            warnings.append((1, f"{zi(s)} – {zi(e)}",
                             "intensificări ale vântului, ninsori, polei"))
        if scenariu == "doua":
            s, e = now + timedelta(hours=4), now + timedelta(hours=16)
            warnings.append((2, f"{zi(s)} – {zi(e)}",
                             "vânt puternic, viscol, vizibilitate redusă"))
        for i, (level, interval, fen) in enumerate(warnings):
            title, message = format_anm(level, judet_nume, interval, fen)
            await self.async_send(title, message, level, f"{tag}_{i}")
        if scenariu == "nowcasting":
            n = dt_util.now()
            title, message = format_nowcasting(
                2, judet_nume, n, n + timedelta(minutes=50),
                "averse torențiale, descărcări electrice și grindină",
            )
            await self.async_send(title, message, 2, f"{tag}_now")
        if scenariu == "final":
            title, message = format_end(judet_nume)
            await self.async_send(title, message, 0, tag)

    async def async_check_anm(self, avertizari: Any, judet_cod: str, judet_nume: str) -> None:
        """Avertizările ANM pentru județul configurat (început + sfârșit)."""
        if not (self.enabled and self.notify_anm):
            return
        lista = [a for a in avertizari if a.get("judet") == judet_cod] if isinstance(avertizari, list) else []
        changed = False
        relevant = False
        for a in lista:
            try:
                level = int(a.get("culoare", 0))
            except (TypeError, ValueError):
                continue
            if level < self.min_level:
                continue
            relevant = True
            key = f"anm|{judet_cod}|{level}|{a.get('data_aparitiei')}|{a.get('intervalul')}"
            if key in self._seen:
                continue
            self._seen.append(key)
            changed = True
            title, message = format_anm(
                level, judet_nume, _interval_anm(a), _fenomene_anm(a)
            )
            await self.async_send(title, message, level, f"amr_anm_{judet_cod.lower()}")

        # Sfârșit: aveam avertizare și acum nu mai e niciuna (date valide, listă goală).
        if self._anm_active and not relevant and avertizari is not None and self.notify_end:
            title, message = format_end(judet_nume)
            await self.async_send(title, message, 0, f"amr_anm_{judet_cod.lower()}")
        if self._anm_active != relevant:
            self._anm_active = relevant
            changed = True
        if changed:
            await self._save()

    async def async_check_nowcasting(self, alerts: list[dict[str, Any]], counties: list[str]) -> None:
        """Alertele nowcasting active pentru județele selectate."""
        if not (self.enabled and self.notify_nowcasting):
            return
        wanted = {c.lower() for c in counties}
        changed = False
        for a in alerts or []:
            county = (a.get("counties") or ["?"])[0]
            if county.lower() not in wanted:
                continue
            level = _level_from_name(a.get("severity", ""))
            if level < self.min_level:
                continue
            key = f"now|{a.get('id')}"
            if key in self._seen:
                continue
            self._seen.append(key)
            changed = True
            title, message = format_nowcasting(
                level, county, a.get("start_time"), a.get("end_time"), a.get("description", "")
            )
            await self.async_send(title, message, level, f"amr_now_{county.lower()}")
        if changed:
            await self._save()
