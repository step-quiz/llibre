# Novetats — 1r d'ESO complet i canvis de format a tots els cursos

Aquesta entrega és la més gran fins ara: **1r d'ESO passa d'estar sense
començar a estar complet**, i, de retruc, **els PDFs dels cinc cursos canvien de
format**.

| Curs | Abans | Ara |
|---|---|---|
| 1r ESO | no publicat | **8 unitats · 76 activitats + document d'índex** |
| 2n ESO | 6 unitats · 53 activitats | igual, amb el format nou |
| 3r ESO | 6 unitats · 54 activitats | igual, amb el format nou |
| 4t ESO · Acadèmiques | 10 unitats · 65 activitats | igual, amb el format nou |
| 4t ESO · Aplicades | 9 unitats · 57 activitats | igual, amb el format nou |

> **Què vol dir «igual, amb el format nou».** Els canvis de format afecten els
> cinc cursos, perquè `defs.tex` és compartit. En canvi, **el contingut només
> s'ha revisat a 1r d'ESO** (unitats 1 a 8) **i a 4t Aplicades** (figures i
> errades). A 2n, 3r i 4t Acadèmiques només s'hi ha fet una recompilació: no
> s'han revisat, i encara hi ha referències del tipus «exercici 7» que amb la
> numeració nova haurien de dir «3.7.7».

## 1. Canvis de format (afecten els cinc cursos)

Són canvis a `defs.tex`, que és compartit. **El contingut no canvia.**

- **Els exercicis es numeren `unitat.activitat.exercici`.** Abans totes les
  activitats numeraven des d'1.1, de manera que en un PDF d'unitat fusionat hi
  havia vuit exercicis amb el mateix número. Ara `3.7.5` és únic a tot el llibre.
  **Les fotocòpies fetes amb la numeració antiga no coincideixen.**
- **Els títols d'activitat perden el «1.»** del davant: «Activitat 4 — Polígons».
- **Les capçaleres dels quadres es llegeixen en fotocòpia:** abans eren text
  marí sobre fons blau mitjà i en blanc i negre desapareixien.
- **S'ha tret el salt de pàgina forçat** abans dels exercicis, que era
  redundant: **119 pàgines menys** en total, sense perdre res.
- **Cap exercici no queda partit** entre dues pàgines.

## 2. 1r d'ESO

Vuit unitats, 76 activitats i 89 sessions, alineades amb el Repartiment de
continguts del centre i amb les set situacions d'aprenentatge.

| UD | Títol | Activitats |
|---|---|---|
| 1 | Nombres naturals | 8 |
| 2 | Divisibilitat: l'ADN dels nombres | 10 |
| 3 | Com és de gran Gaza? Fraccions i àrea | 11 |
| 4 | És gran l'ou del kiwi? Fracció i percentatge | 11 |
| 5 | Decimals i arrel quadrada | 8 |
| 6 | Sentit espacial: el món en formes | 10 |
| 7 | El sentit de la mesura | 11 |
| 8 | Patrons i llenguatge algebraic | 7 |

Novetats respecte de la versió de treball anterior:

- **UD7 i UD8 són noves.** La UD7 tanca el projecte de Fotomàtiques obert a la
  UD6 (es mesura la forma fotografiada a partir d'un objecte de mida coneguda) i
  acaba amb un projecte de camp: mesurar el pati i dibuixar-ne el plànol a
  escala. La UD8 porta els patrons fins al llenguatge algebraic i inclou l'única
  activitat de sentit estocàstic del curs, de lectura crítica de gràfics.
- **Fitxes imprimibles** a dotze activitats: taulers i cartes d'Enfonsar la
  flota, graelles del garbell, triangles de Tartaglia, tires de fraccions,
  models quadriculats, graelles de percentatges, construccions de GeoGebra,
  l'experiment de π i els fulls de camp dels projectes. Algunes s'imprimeixen a
  una sola cara: cada fitxa ho indica.
- **Espai per respondre als exàmens**, amb barems que sumen 10, i ítems que no
  repeteixen els exercicis de la unitat.
- **Errades corregides** a totes les unitats, incloses dues figures que estaven
  mal dibuixades (el garbell d'Eratòstenes i l'espiral de Fibonacci).

## 3. Eines

- **`eines/sync.py`**: genera `course.json`, `manifest.json` i el recompte de
  l'`index.html` a partir del `.tex`, i compila les activitats. Només publica el
  que té PDF, i no substitueix un PDF publicat si la compilació falla.
- **`.devcontainer/devcontainer.json`**: Codespace amb LaTeX (inclosos els
  patrons de partició del català), `poppler-utils`, `pypdf` i `git-lfs`.
