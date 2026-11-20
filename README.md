<p align="center">
  <img src="custom_components/alerte_meteo_ro/brand/icon@2x.png" width="140" alt="Alerte Meteo România">
</p>

<h1 align="center">⛈️ Alerte Meteo România</h1>

<p align="center">
  <b>Avertizările ANM și alertele nowcasting, direct în Home Assistant.</b><br>
  🟡 galben · 🟠 portocaliu · 🔴 roșu — pe județ, cu card Lovelace propriu
</p>

<p align="center">
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS"></a>
  <a href="https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml"><img src="https://github.com/robex2005/alerte-meteo-ro/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/robex2005/alerte-meteo-ro/releases"><img src="https://img.shields.io/github/v/release/robex2005/alerte-meteo-ro" alt="Release"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg" alt="Home Assistant 2024.12+">
</p>

<p align="center">
  <a href="#instalare">Instalare</a> ·
  <a href="#configurare">Configurare</a> ·
  <a href="#card">Card</a> ·
  <a href="#entități">Entități</a> ·
  <a href="CHANGELOG.md">Istoric</a>
</p>

---

Integrare Home Assistant pentru **avertizările meteo ANM** (pe județ) și **alertele nowcasting**, cu un card Lovelace propriu, care apare în lista de carduri, fără YAML.

<p align="center">
  <img src="docs/images/card-activ-acum-urmeaza.png" width="260" alt="Avertizare activă">
  <img src="docs/images/card-fara-avertizare.png" width="260" alt="Fără avertizare">
</p>

## Ce face

- **Avertizări ANM** pentru un singur județ: cod galben / portocaliu / roșu, *acum* și *urmează* (următoarele 48h), mesajele ANM complete cu harta.
- **Avertizări parțiale** (zone de munte, altitudine, litoral), citite din harta ANM: „📍 local · zone de munte".
- **Nowcasting** pentru unul sau mai multe județe.
- **Notificări pe telefon** prin aplicația Home Assistant, fără automatizări (început + încheiere avertizare).
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

## Notificări pe telefon

Integrarea trimite singură notificări prin aplicația **Home Assistant Companion** (Android / iOS) — nu e nevoie de automatizări.

1. Instalează aplicația pe telefon și conectează-o la Home Assistant (apare serviciul `notify.mobile_app_<telefon>`).
2. Pe integrare → **Configurare** → bifează telefoanele la *Notificări pe telefoanele*.

| Câmp | Descriere |
|------|-----------|
| Notificări pe telefoanele | unul sau mai multe `mobile_app_*`; gol = fără notificări |
| Notifică de la codul | galben (toate) / portocaliu și roșu / doar roșu |
| Avertizări ANM / Nowcasting | ce tipuri de alerte se trimit |
| Notificare la încheiere | „✅ Alertă Meteo Finalizată" când nu mai e avertizare ANM |
| Pagina deschisă | unde te duce apăsarea notificării, ex. `/lovelace/vreme` |

Cum arată:

```
🟠 COD PORTOCALIU MUREȘ
🕒 20 noiembrie, ora 10 – 21 noiembrie, ora 10

💨 Fenomene vizate:
- intensificări ale vântului
- ninsori
```

- câte o notificare pentru fiecare avertizare **nouă** (nu se repetă la restart sau la reîncărcare);
- portocaliu / roșu: sunet critic pe iOS, prioritate mare pe Android (canalul „Alerte meteo");
- notificările aceluiași județ se înlocuiesc una pe alta (același `tag`);
- numele județului din titlu/mesaj e mereu cel configurat (ANM) sau cel al alertei (nowcasting).

**Test:** Instrumente pentru dezvoltatori → Acțiuni → `alerte_meteo_ro.test_notificare` (opțional `cod: galben|portocaliu|rosu`) trimite o notificare de probă pentru județul tău.

<details>
<summary>Vrei control total? Automatizare manuală (exemplu)</summary>

Lasă *Notificări pe telefoanele* gol și folosește senzorul de mesaj al județului tău (`sensor.mesaj_meteo_<judet>`). Numele și codul județului se iau din atributele senzorului (`judet`, `judet_cod`), deci textul e corect pentru orice județ:

```yaml
alias: Notificare avertizare ANM
triggers:
  - trigger: state
    entity_id: sensor.mesaj_meteo_<judet>   # ex. sensor.mesaj_meteo_cluj
    to: alerta
actions:
  - action: notify.mobile_app_<telefon>     # telefonul tău
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
