# Novetats — actualització des d'Overleaf

Fitxers nous o modificats respecte a l'última versió publicada. **2n ESO no
apareix aquí perquè no hi ha cap canvi.** Substitueix/afegeix aquests
fitxers al teu repositori (mateixes rutes relatives que ja tens) i fes
commit + push.

## Resum del que ha canviat al llibre font

| Curs | Abans | Ara | Novetat |
|---|---|---|---|
| **1r ESO** | no existia | 1 unitat (UD1) · 1 activitat | Curs nou, acabat de començar |
| **3r ESO** | 5 unitats · 44 activitats | 6 unitats · 54 activitats | +UD6 "La funció més recta" (10 activitats) + document "Índex del curs" |
| **4t ESO** | 2 unitats · 13 activitats | 9 unitats · 58 activitats | +UD4–UD10 (45 activitats noves) + document "Índex del curs" |

UD2 i UD3 de 4t ESO són contingut idèntic al que ja tenies (bit a bit); no
calia recompilar-los ni tornar-los a pujar.

## ⚠️ Un avís sobre el teu Overleaf: la carpeta `4eso-academiques`

Al teu projecte, la unitat de 4t ESO ara viu a la carpeta
`4eso-academiques/` (abans `4eso/`), però els fitxers interns i els propis
comentaris de capçalera (`% ... via \mostra{4eso}{4}{1}`) continuen fent
servir el prefix `4eso`. La macro `\mostra` de `defs.tex` lliga el nom de
carpeta i el prefix de fitxer amb el **mateix** paràmetre
(`\input{#1/ud#2/#1-ud#2-#3}`), així que amb la carpeta reanomenada
**`\mostra{4eso-academiques}{...}` ja no compila** (busca un fitxer que no
existeix) i **`\mostra{4eso}{...}` tampoc** (la carpeta `4eso` ja no hi és).

Per generar aquests PDFs he hagut de saltar-me `\mostra` per a les unitats
de `4eso-academiques` i reproduir manualment la capçalera + un `\input`
directe a la ruta real. Funciona, però si continues afegint unitats a
aquesta carpeta amb aquest mateix desajust, hauràs de seguir fent-ho fitxer
a fitxer. Dues maneres de resoldre-ho de soca-rel al teu Overleaf, si vols:

1. Reanomena la carpeta de tornada a `4eso/` (més senzill, cap canvi de codi), o
2. Actualitza `defs.tex` perquè `\mostra` accepti la carpeta i el prefix per
   separat, p. ex. `\newcommand{\mostra}[4]{...\input{#1/ud#3/#2-ud#3-#4}...}`
   i crida `\mostra{4eso-academiques}{4eso}{4}{1}`.

També hi havia un caràcter Unicode (★) al document
`index-4eso-academiques.tex` que `pdflatex` no reconeix per defecte; l'he
mapejat a `\bigstar` només al meu embolcall de compilació, sense tocar el
teu fitxer font. Si compiles aquest document directament a Overleaf,
probablement et donarà el mateix error tret que hi afegeixis
`\DeclareUnicodeCharacter{2605}{\ensuremath{\bigstar}}` al preàmbul, o
canviïs l'estrella per un altre símbol.

Cap d'aquests dos punts afecta els PDFs que t'entrego: ja estan compilats
correctament.

## Fitxers d'aquest paquet

```
index.html                          actualitzat (targeta 1r ESO activa + comptes)
1eso.html                           nou
2eso.html / 3eso.html / 4eso.html   actualitzats (nav amb enllaç a 1r ESO)
contingut/1eso/course.json          nou
contingut/1eso/pdfs/manifest.json   nou
contingut/1eso/pdfs/1eso-ud1-1.pdf  nou
contingut/3eso/course.json          actualitzat (6 unitats, indexPdf)
contingut/3eso/pdfs/manifest.json   actualitzat
contingut/3eso/pdfs/3eso-ud6-*.pdf  nous (10 fitxers)
contingut/3eso/pdfs/3eso-index.pdf  nou
contingut/4eso/course.json          actualitzat (9 unitats, indexPdf)
contingut/4eso/pdfs/manifest.json   actualitzat
contingut/4eso/pdfs/4eso-ud{4..10}-*.pdf   nous (45 fitxers)
contingut/4eso/pdfs/4eso-index.pdf  nou
```

`contingut/2eso/` no s'inclou: cap fitxer ha canviat.

## Comprovacions fetes abans de lliurar-ho

- Compilació: 58/58 fitxers nous, 0 errors.
- Recompte de pàgines del PDF fusionat = suma de pàgines individuals,
  verificat per al curs sencer de 1r, 3r i 4t ESO (4=4, 172=172, 193=193).
- Navegació i arbre de selecció provats amb Playwright a les quatre
  pàgines de curs, sense errors de consola.
