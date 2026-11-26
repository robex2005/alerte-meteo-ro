"""Culoarea județului pe harta SVG a unei avertizări ANM (fără rețea: doar parsare).

Logica provine din check_map.py din alerta-anm-judet-romania (GPL-3.0, Copyright (C) 2026 dancucu),
adaptată: harta e descărcată de coordinator (aiohttp, sesiunea Home Assistant), aici doar se citește SVG-ul.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

COD_CULOARE = {1: "galben", 2: "portocaliu", 3: "rosu"}


def normalize_color(color_str: str | None) -> str | None:
    """Transformă orice cod de culoare în standardul nostru."""
    if not color_str:
        return None
    s = color_str.lower().replace(" ", "")
    # Culori AVERTIZARE
    if "#ffff00" in s or "rgb(255,255,0)" in s:
        return "galben"
    if "#ff6600" in s or "#ff9900" in s or "#e67e22" in s or "rgb(255,102,0)" in s or "rgb(255,127,0)" in s:
        return "portocaliu"
    if "#ff0000" in s or "rgb(255,0,0)" in s:
        return "rosu"
    # Culori INFORMARE (gri-uri folosite de ANM)
    if "#b4b4b4" in s or "#cccccc" in s or "#999999" in s or "rgb(180,180,180)" in s:
        return "informare"
    # 'none' sau alb = verde (fără nimic)
    if "none" in s or "#ffffff" in s or "rgb(255,255,255)" in s:
        return "verde"
    return None


def check_zones(content: str, judet_cod: str) -> dict[str, str]:
    """Zone parțiale ale județului (munte, altitudine, litoral) colorate pe hartă.

    ANM desenează avertizările „local la munte” / „peste X m” ca zone separate
    (id `conturMuntiJudet<COD><COD>_...`, `conturAlt1400Judet<COD><COD>_...`) cu clasa `codN`.
    Returnează {zona: culoare} doar pentru zonele cu avertizare (cod1..cod3).
    """
    zones: dict[str, str] = {}
    rank = {"galben": 1, "portocaliu": 2, "rosu": 3}
    code = re.escape(judet_cod)
    pat = re.compile(
        r'<[a-zA-Z]+\s[^>]*?id="contur(?:Munti|Alt\d+|Litoral)Judet' + code + code + r'_[^"]*"[^>]*>'
    )
    for tag in pat.findall(content):
        cl = re.search(r'class="([^"]*)"', tag)
        if not cl:
            continue
        classes = cl.group(1).split()
        m = next((re.fullmatch(r"cod([123])", c) for c in classes if re.fullmatch(r"cod([123])", c)), None)
        if not m:
            continue
        kind = classes[0]  # munte / alt1400 / alt400 / litoral ...
        color = COD_CULOARE[int(m.group(1))]
        if rank[color] > rank.get(zones.get(kind), 0):
            zones[kind] = color
    return zones


def parse_map(content: str, judet_cod: str) -> tuple[str, dict[str, str]]:
    """Culoarea județului (verde/informare/galben/portocaliu/rosu sau eroare_xml) + zonele parțiale."""
    zones = check_zones(content, judet_cod)

    # 1. clase CSS -> culoare
    css_map = {}
    for cls, color in re.findall(r"\.([a-zA-Z0-9_\-]+)[^{]*\{[^}]*fill:\s*([^;}]+)", content):
        css_map[cls] = color.strip()

    # 2. fără namespace, ca id-urile să se caute simplu
    content = re.sub(r'\sxmlns="[^"]+"', "", content, count=1)
    content = re.sub(r'\sxmlns:xlink="[^"]+"', "", content, count=1)
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return "eroare_xml", zones

    # 3. conturul județului
    target_id = f"conturJudet{judet_cod}"
    found = next((el for el in root.iter() if el.get("id") == target_id), None)
    if found is None:
        return "verde", zones

    # 4. culoarea: întâi style inline, apoi clasele
    style = found.get("style", "")
    m = re.search(r"fill:\s*([^;]+)", style)
    if m:
        detected = normalize_color(m.group(1))
        if detected:
            return detected, zones
    for cls in found.get("class", "").split():
        if cls in css_map:
            detected = normalize_color(css_map[cls])
            if detected:
                return detected, zones
    return "verde", zones
