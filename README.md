# Alerte Meteo România

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml/badge.svg)](https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/robex2005/alerte-meteo-ro)](https://github.com/robex2005/alerte-meteo-ro/releases)

Integrare Home Assistant pentru **avertizările meteo ANM** (pe județ) și **alertele nowcasting**, cu un card Lovelace propriu, care apare în lista de carduri, fără YAML.

<p align="center">
  <img src="docs/images/card-activ-acum-urmeaza.png" width="260" alt="Avertizare activă">
  <img src="docs/images/card-fara-avertizare.png" width="260" alt="Fără avertizare">
</p>

## Ce face

- **Avertizări ANM** pentru un singur județ: cod galben / portocaliu / roșu, *acum* și *urmează* (următoarele 48h), mesajele ANM complete cu harta.
- **Avertizări parțiale** (zone de munte, altitudine, litoral), citite din harta ANM: „📍 local · zone de munte".
- **Nowcasting** pentru unul sau mai multe județe.
- **Card** `custom:alerte-meteo-card`: antet colorat și deschis când e avertizare, „Nicio avertizare meteo" și închis când nu e; atingi un bloc din rezumat și sare la mesajul complet.

## Instalare

1. HACS → ⋮ → **Custom repositories** → `https://github.com/robex2005/alerte-meteo-ro` → categoria **Integration** → *Add*.
2. Instalează **Alerte Meteo România** și repornește Home Assistant.
3. **Setări → Dispozitive și servicii → Adaugă integrare → Alerte Meteo România.**

Cerințe: Home Assistant **2024.12** sau mai nou, acces la internet (date de la `meteoromania.ro`). Dacă ai integrările vechi `alerta_anm_judet_romania` / `alerta_nowcasting`, șterge-le întâi (entitățile s-ar dubla).

## Configurare

| Câmp | Descriere |
|------|-----------|
| Județ avertizări ANM | **un singur județ** |
| Interval actualizare | minute (implicit 10) |
| Nowcasting | pornește senzorii nowcasting |
| Județe nowcasting | **unul sau mai multe**; gol = județul ANM |

Se pot schimba oricând din **Configurare** pe integrare.

## Card

Dashboard → **Editează** → **Adaugă card** → **Alerte Meteo România** (sau în YAML: `type: custom:alerte-meteo-card`). Se încarcă singur odată cu integrarea.

În editor bifezi județele de nowcasting afișate; în YAML: `judete: [Mureș, Alba]` (nume sau cod, cu/fără diacritice). Avertizările ANM rămân pe județul integrării.

Varianta cu `button-card` și una Markdown simplă sunt în [`examples/`](examples/).

> **Carduri, template-uri sau automatizări scrise manual:** dacă folosești entități sau coduri de județ scrise de mână (ex. `sensor.mesaj_meteo_mures`, `sensor.alerta_nowcasting_mures`, `judet == 'MS'`), schimbă **codul și numele județului peste tot** unde apar, altfel vei vedea datele județului vechi. Cardul `custom:alerte-meteo-card` și exemplele din `examples/` își iau județul singure.

## Entități

Pentru județul ales (ex. Mureș):

| Entitate | Descriere |
|----------|-----------|
| `sensor.avertizari_meteo_anm` | toate avertizările ANM (atribut `avertizari`) |
| `sensor.anm_avertizare_id` | ID-urile avertizărilor active |
| `sensor.mesaj_meteo_mures` | `alerta` / `liniste`; atribute `tip_cod`, `mesaj_complet` |
| `sensor.harta_meteo_activa` | URL-ul hărții active |
| `sensor.culoare_harta_mures` | culoarea județului; atribute `date_harti`, `zone_partiale`, `culoare_zona` |
| `sensor.alerta_nowcasting_mures` | `alerta` / `liniste`; atribute `Alerte active`, `Culoare`, `Început`, `Sfârșit`, `semnalare`, `Zone`, `Fenomene` |

Atributele nowcasting sunt în română, cu diacritice: `state_attr('sensor.alerta_nowcasting_mures', 'Alerte active') | int(0)`.

## Limite

- Avertizările parțiale se detectează doar cât timp sunt active; pentru cele viitoare ANM nu dă date pe zone.
- Hărțile sunt afișate prin `images.weserv.nl`.

## Istoric și licență

Versiuni în [CHANGELOG.md](CHANGELOG.md). Licență **GPL-3.0**; provine din unificarea [`alerta-anm-judet-romania`](https://github.com/dancucu/alerta-anm-judet-romania) (GPL-3.0) și [`alerta-nowcasting`](https://github.com/dancucu/alerta-nowcasting) (MIT) de `dancucu`. Date: Administrația Națională de Meteorologie.
