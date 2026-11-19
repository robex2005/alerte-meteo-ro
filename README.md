# Alerte Meteo România

Integrare Home Assistant care reunește, într-o singură integrare, două surse oficiale ANM (Meteo România):

- **Avertizări meteo ANM** pe județ: mesajul complet, codul (galben / portocaliu / roșu), harta activă și culoarea județului pe hartă.
- **Alerte nowcasting** (următoarele ore), câte un senzor pentru fiecare județ ales.

Provine din unificarea integrărilor [`alerta-anm-judet-romania`](https://github.com/dancucu/alerta-anm-judet-romania) (GPL-3.0) și [`alerta-nowcasting`](https://github.com/dancucu/alerta-nowcasting) (MIT), de `dancucu`.

## Instalare

1. Adaugă acest repository ca *custom repository* în Marketplace/HACS, cu categoria **Integration**, folosind linkul complet:

   ```
   https://github.com/robex2005/alerte-meteo-ro
   ```

   (Marketplace/HACS → meniul ⋮ → *Custom repositories* → lipești linkul → alegi *Integration* → *Add*.)
2. Instalează **Alerte Meteo România** și repornește Home Assistant.
3. **Setări → Dispozitive și servicii → Adaugă integrare → Alerte Meteo România**.

La configurare alegi:

| Câmp | Descriere |
|------|-----------|
| Județ (avertizări ANM) | județul pentru care se afișează mesajul ANM |
| Interval actualizare ANM | în minute (implicit 10) |
| Activează alertele nowcasting | pornește senzorii nowcasting |
| Județe nowcasting | unul sau mai multe județe; gol = județul ales pentru ANM |

Setările se pot schimba ulterior din **Configurare** pe integrare.

## Entități

Pentru județul ales (exemplu: Mureș):

| Entitate | Descriere |
|----------|-----------|
| `sensor.avertizari_meteo_anm` | toate avertizările ANM (atributul `avertizari`) |
| `sensor.anm_avertizare_id` | ID-urile avertizărilor active |
| `sensor.mesaj_meteo_mures` | `alerta` / `liniste`; atribute `tip_cod`, `mesaj_complet` |
| `sensor.harta_meteo_activa` | URL-ul hărții active |
| `sensor.culoare_harta_mures` | culoarea județului pe hartă; atribut `date_harti` |
| `sensor.alerta_nowcasting_mures` | `alerta` / `liniste`; atribute `Alerte active`, `Culoare`, `Început`, `Sfârșit`, `semnalare`, `Zone`, `Fenomene`, `Titlu`, `Ultima actualizare` |

Atributele nowcasting sunt în limba română, cu diacritice; într-un template folosește ghilimele, de exemplu
`state_attr('sensor.alerta_nowcasting_mures', 'Alerte active') | int(0)`.

## Carduri Lovelace (universale)

Cardurile din [`examples/`](examples/) nu conțin niciun județ scris de mână: își găsesc singure entitățile integrării și iau numele județului din atributul `judet` al lui `sensor.mesaj_meteo_<județ>`. Funcționează pentru orice județ ales la configurare; copiezi YAML-ul în dashboard, fără editări.

| Fișier | Conținut | Necesită |
|--------|----------|----------|
| [`lovelace_card_alerte_meteo.yaml`](examples/lovelace_card_alerte_meteo.yaml) | **cardul principal**: ANM + nowcasting într-un singur card pliabil; *acum* / *urmează* (≤48h), mesajele ANM complete cu hartă | `button-card` |
| [`lovelace_card_markdown.yaml`](examples/lovelace_card_markdown.yaml) | variantă simplă, doar text | cardul Markdown standard |

### Cum arată cardul (telefon)

| Avertizare activă acum + următoarele | Nowcasting activ | Nicio avertizare |
|:---:|:---:|:---:|
| ![Avertizare activă acum și următoarele](docs/images/card-activ-acum-urmeaza.png) | ![Nowcasting activ](docs/images/card-activ-nowcasting.png) | ![Nicio avertizare](docs/images/card-fara-avertizare.png) |

Mesajele complete ANM, cu harta fiecărui mesaj, apar sub secțiunile *Acum* / *Urmează*:

<p align="center"><img src="docs/images/card-detalii-anm.png" alt="Mesaje ANM cu hartă" width="320"></p>

Antetul cardului principal se schimbă singur:

- **fără avertizare**: antet neutru „NICIO AVERTIZARE METEO”, card colapsat;
- **cu avertizare** (activă acum, nowcasting sau în următoarele 48h): antet colorat după cea mai gravă avertizare (galben / portocaliu / roșu), „AVERTIZARE METEO ACTIVĂ” și card expandat.

Dacă îl pliezi sau îl expandezi manual, alegerea se păstrează până când starea (avertizare / fără avertizare) se schimbă.

## Licență

GPL-3.0 (vezi `LICENSE`). Partea de nowcasting provine din `alerta-nowcasting`, publicat sub licența MIT, Copyright (c) 2026 Dan.
