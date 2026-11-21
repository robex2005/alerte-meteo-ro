<p align="center">
  <img src="custom_components/alerte_meteo_ro/brand/icon@2x.png" width="140" alt="Alerte Meteo România">
</p>

<h1 align="center">⛈️ Alerte Meteo România</h1>

<p align="center">
  <b>Romanian ANM weather warnings and nowcasting alerts, right in Home Assistant.</b><br>
  🟡 yellow · 🟠 orange · 🔴 red — per county, with its own Lovelace card and notifications
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/Marketplace-Custom-orange.svg" alt="Marketplace"></a>
  <a href="https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml"><img src="https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/robex2005/alerte-meteo-ro/releases"><img src="https://img.shields.io/github/v/release/robex2005/alerte-meteo-ro" alt="Release"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg" alt="Home Assistant 2024.12+">
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#notifications">Notifications</a> ·
  <a href="#card">Card</a> ·
  <a href="#manual-cards-examples">Manual cards</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="README.md"><img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f1f7-1f1f4.svg" width="16" alt="RO"> Română</a>
</p>

---

Home Assistant integration for **ANM weather warnings** (per county; ANM is Romania's National Meteorological Administration) and **nowcasting alerts**, with its own Lovelace card that shows up in the card picker, no YAML needed.

> The data comes from ANM in Romanian, so warning texts, phenomena and notifications are in Romanian.

<p align="center">
  <img src="docs/images/galerie-card.png" width="640" alt="Warnings now / next, nowcasting and full ANM message">
</p>

## What it does

- **ANM warnings** for a single county: yellow / orange / red level, *now* and *next* (the next 48h), full ANM messages with the map.
- **Partial warnings** (mountain areas, altitude, seaside), read from the ANM map: "📍 Your area".
- **Nowcasting** for one or more counties.
- **Notifications** in the Home Assistant app and on WhatsApp / Telegram (any text service), no automations needed: warning start + end.
- **Card** `custom:alerte-meteo-card`, compact on mobile: level, area, time and phenomena one below the other; colored, expanded header when there is a warning, "Nicio avertizare meteo" (no weather warning) and collapsed when there isn't.

## Installation

1. **Marketplace → Add via link** (or ⋮ → **Custom repositories** → **Add via link**) → `https://github.com/robex2005/alerte-meteo-ro` → **Add**.
2. Install **Alerte Meteo România** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Alerte Meteo România.**

Requirements: Home Assistant **2024.12** or newer, internet access (data from `meteoromania.ro`). If you have the old `alerta_anm_judet_romania` / `alerta_nowcasting` integrations, remove them first (the entities would be duplicated).

## Configuration

| Field | Description |
|-------|-------------|
| ANM warnings county | **a single county** |
| ANM update interval | minutes (default 10) |
| Enable nowcasting alerts | turns on the nowcasting sensors |
| Nowcasting counties | **one or more**; empty = the ANM county |

You can change them at any time from **Configure** on the integration.

## Notifications

The integration sends notifications on its own — no automations needed. On the integration → **Configure**:

| Field | Description |
|-------|-------------|
| Notify these phones | one or more `mobile_app_*` (Home Assistant Companion app); empty = none |
| Also send text messages to | any `notify.*` service that only sends text: WhatsApp, Telegram, notify groups |
| Notify from level | yellow (all) / orange and red / red only |
| Notify ANM warnings / nowcasting alerts | which alert types are sent |
| Notify when the ANM warning ends | "✅ Alertă Meteo Finalizată" (weather alert ended) |
| Page opened when tapping the notification | e.g. `/lovelace/vreme` |

For phones: install the Home Assistant app (Android / iOS) and connect it — the `notify.mobile_app_<phone>` service appears. For WhatsApp / Telegram: first set up the matching `notify` service in Home Assistant, then pick it under *Also send text messages to*.

What they look like (same text in the app and on WhatsApp):

<p align="center">
  <img src="docs/images/galerie-notificari.png" width="640" alt="Notifications: ANM warning and nowcasting">
</p>

- one notification for each **new** warning (not repeated on restart or reload);
- orange / red: critical sound on iOS, high priority on Android (channel "Alerte meteo");
- notifications for the same county replace each other in the app (same `tag`);
- the county name in the title/message is always the configured one (ANM) or the alert's own (nowcasting).

**Test:** Developer tools → Actions → `alerte_meteo_ro.test_notificare` — optional `cod: galben|portocaliu|rosu` (yellow|orange|red) and `scenariu: proba|real|doua|nowcasting|final` (sample|real|two|nowcasting|end).

<details>
<summary>Want full control? Manual automation (example)</summary>

Leave the notification fields empty and use your county's message sensor (`sensor.mesaj_meteo_<county>`). The county name and code come from the sensor attributes (`judet`, `judet_cod`), so the text is right for any county:

```yaml
alias: ANM warning notification
triggers:
  - trigger: state
    entity_id: sensor.mesaj_meteo_<county>   # e.g. sensor.mesaj_meteo_cluj
    to: alerta
actions:
  - action: notify.mobile_app_<phone>        # your phone
    data:
      title: >-
        ⚠️ Cod {{ trigger.to_state.attributes.tip_cod }}
        {{ trigger.to_state.attributes.judet | upper }}
      message: "{{ trigger.to_state.attributes.mesaj_complet[:250] }}"
      data:
        url: /lovelace/vreme
        tag: "alerta-meteo-{{ trigger.to_state.attributes.judet_cod | lower }}"
```

</details>

## Card

Dashboard → **Edit** → **Add card** → **Alerte Meteo România**. It loads automatically with the integration; in the editor you tick which nowcasting counties to show. ANM warnings always follow the integration's county.

In YAML:

```yaml
type: custom:alerte-meteo-card
judete:            # optional: nowcasting counties to show (name or code, with/without diacritics)
  - Mureș
  - HR
collapsed: true    # optional: the card starts collapsed even when there is a warning
```

| Option | Default | Description |
|--------|---------|-------------|
| `judete` | all nowcasting counties in the integration | list of counties (name or code) |
| `collapsed` | `false` | `true` = starts collapsed; manual open/close is remembered in the browser |

## Manual cards (`examples/`)

If you'd rather build the card yourself, [`examples/`](examples/) has two ready-to-copy versions (Dashboard → Add card → Manual):

| File | Requires | Shows |
|------|----------|-------|
| [`lovelace_card_alerte_meteo.yaml`](examples/lovelace_card_alerte_meteo.yaml) | `custom:button-card` | same as the integration's card (screenshots above), but as YAML you can edit |
| [`lovelace_card_markdown.yaml`](examples/lovelace_card_markdown.yaml) | nothing (Markdown card) | simple list: active / upcoming ANM warnings + nowcasting |

Both find the integration's county on their own — no editing needed. In the `button-card` version, the `judete` and `collapsed` options are in the first lines of `label` (`const cfg = …`).

> **Hand-written cards, templates or automations:** if you use hard-coded entities or county codes (e.g. `sensor.mesaj_meteo_mures`, `sensor.alerta_nowcasting_mures`, `judet == 'MS'`), change **the county code and name everywhere** they appear, otherwise you will see the old county's data.

## Limitations

- Partial warnings are only detected while they are active; ANM gives no per-area data for upcoming ones.
- Maps are shown through `images.weserv.nl`.
- Text services (WhatsApp etc.) only get text: no critical sound, no tap link.

## Changelog and license

Versions in [CHANGELOG.md](CHANGELOG.md) (in Romanian). License **GPL-3.0**; it merges and improves the [`alerta-anm-judet-romania`](https://github.com/dancucu/alerta-anm-judet-romania) (GPL-3.0) and [`alerta-nowcasting`](https://github.com/dancucu/alerta-nowcasting) (MIT) integrations by `dancucu`. Data: Administrația Națională de Meteorologie (ANM).
