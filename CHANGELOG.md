# Istoric versiuni

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
