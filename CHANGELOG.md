# Istoric versiuni

## 1.11
- Notificări și pe WhatsApp, Telegram sau orice serviciu de notificare text, pe lângă aplicația Home Assistant.
- Mesaje mai ușor de citit: bulină cu culoarea codului, intervalul pe rânduri separate, fenomenele ca listă.
- Alertele nowcasting au același format.
- Card redesenat, compact pe mobil: codul, zona, ora și fenomenele, câte unul pe rând.
- Mesajele ANM complete se văd direct, cu textul și harta.
- Opțiune nouă `collapsed: true`: cardul pornește închis.
- Exemplul `button-card` din `examples/` arată ca noul card.

## 1.10
- Notificări pe telefon prin aplicația Home Assistant Companion, direct din integrare (fără automatizări): alegi telefoanele, codul minim, ANM / nowcasting, notificare la încheiere și pagina deschisă la apăsare.
- Format ca în proiectele originale: titlu cu codul și județul, 🕒 interval, 💨 fenomene ca listă; sunet critic la portocaliu/roșu.
- Fără duplicate: avertizările deja trimise sunt ținute minte și după restart.

## 1.9
- README rescris, succint.
- Validări automate (HACS, hassfest, sintaxă card) pentru adăugarea în HACS.
- Manifest conform hassfest (chei sortate, fără `requests` în requirements).

## 1.8
- Card: textul fenomenului din mesajele ANM se decodează (entități HTML) și pictograma potrivită (💨 etc.) apare corect.

## 1.7
- Card: pictograma fenomenului se potrivește și cu diacritice diferite.
- Card: fenomenul se ia din mesajul ANM complet când lista scrie „conform textelor".

## 1.6
- Detectare avertizări parțiale pe județ (zone de munte, altitudine, litoral) din harta ANM.
- Senzorul `culoare_harta_<județ>` are atribute noi: `zone_partiale` și `culoare_zona`.
- Card: dacă județul e verde dar zona de munte e colorată, arată „📍 local · zone de munte".

## 1.5
- Remediere: editorul cardului dădea eroarea „Cannot read properties of undefined (reading 'judete')".

## 1.4
- Avertizările ANM: un singur județ (cel ales în integrare); nowcasting: mai multe județe.
- Card: casetele din editor se aplică doar nowcasting-ului; ANM rămâne pe județul integrării.
- Formularul integrării: etichete clare (ANM = un județ, nowcasting = mai multe).

## 1.3
- Editor card: casete cu bifă doar pentru județele adăugate în integrare (nu o listă cu toate).
- Cardul afișează avertizările ANM și nowcasting pentru toate județele bifate; cu mai multe județe, fiecare bloc are eticheta județului.
- Configurare YAML: `judete: [MS, AB]` (nume sau cod); implicit, toate județele din integrare.

## 1.2
- Iconiță integrare: harta României (tricolor).
- Cardul `custom:alerte-meteo-card`: județ ales după nume sau cod, cu editor vizual (listă de județe).
- Alegere automată a județului: ignoră senzorii vechi „indisponibili".
- Dacă ANM trimite culoarea 0 pe intervalul activ, se folosește culoarea de pe hartă.

## 1.1
- Card Lovelace propriu `custom:alerte-meteo-card`, încărcat automat de integrare (fără YAML, fără button-card).
- Tap pe un bloc „Acum / Urmează" sare la mesajul ANM complet (și pe touch).
- Card exemplu (YAML) cu antet colorat / „Nicio avertizare", compact pe telefon, link ANM funcțional.
- README: link complet pentru repository personalizat, capturi, cerințe.

## 1.0
- Prima versiune: avertizări ANM pe județ + nowcasting într-o singură integrare (unificare `alerta-anm-judet-romania` + `alerta-nowcasting`).
