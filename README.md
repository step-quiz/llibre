# Llibre de Text ESO — Visor de PDFs

Lloc estàtic (HTML/CSS/JS pur, **sense build ni servidor**) que permet consultar
i descarregar el llibre de text de Matemàtiques de l'ESO (INS Miquel
Tarradell) a **qualsevol granularitat**: tot un curs, una unitat didàctica, o
qualsevol combinació d'activitats soltes.

Pensat com a lloc "germà" de `pd-main` (Programació Didàctica): reutilitza el
mateix sistema de disseny i la mateixa filosofia (`course.json` + descoberta
per `fetch()`, cap registre central, cap dependència de servidor), afegint-hi
l'única capacitat nova que calia: **selecció múltiple + fusió de PDFs al
navegador**.

## Com funciona

- Cada activitat del llibre es distribueix com un **PDF atòmic** ja compilat:
  `{curs}-ud{unitat}-{activitat}.pdf` (p. ex. `2eso-ud3-4.pdf`).
- La pàgina d'un curs (`2eso.html`, `3eso.html`, `4eso.html`) llegeix
  `contingut/{curs}/course.json` i `contingut/{curs}/pdfs/manifest.json` i
  construeix un arbre Unitat → Activitat a la barra lateral, amb una casella
  de selecció a cada nivell (activitat, unitat amb estat tri-state, i "tot el
  curs").
- Clicar el **títol** d'una activitat l'obre directament al visor (el visor
  natiu de PDF del navegador, dins un `<iframe>`) — no cal cap fusió.
- Marcar **caselles** i prémer "Veure selecció" o "Descarregar PDF" fusiona
  els PDFs marcats en un de sol, **completament al navegador**, amb la
  llibreria [pdf-lib](https://pdf-lib.js.org/) (vendoritzada localment a
  `assets/lib/pdf-lib.min.js`, sense CDN). El nom de fitxer es genera sol:
  - selecció = tot el curs → `{prefix}-complet.pdf`
  - selecció = una unitat sencera → `{prefix}-ud{N}.pdf`
  - qualsevol altra combinació → `{prefix}-seleccio.pdf`
- No hi ha cap comprovació d'existència per xarxa activitat per activitat: es
  llegeix `pdfs/manifest.json` un sol cop i es consulta com a `Set`.

## Estructura del lloc

```
llibre-pdf-viewer/
  index.html                   selector de curs (1r ESO = "properament")
  2eso.html / 3eso.html / 4eso.html   defineixen window.COURSE i carreguen l'app
  assets/
    css/  tokens.css, layout.css, components.css, index.css, responsive.css
          (portats gairebé literals de pd-main, mateixa paleta/tipografia)
          viewer.css (nou: arbre de checkboxes, unitats, barra de selecció)
    js/   utils.js        (escHtml, fetchJson — portat de pd-main)
          course-tree.js  (pinta l'arbre Unitat→Activitat i el tri-state)
          pdf-merge.js    (mergeSelected(urls) → Blob, embolcall de pdf-lib)
          app.js          (punt d'entrada de cada pàgina de curs)
    lib/  pdf-lib.min.js  (vendoritzat via npm, no CDN)
  contingut/
    2eso/{course.json, pdfs/{2eso-ud1-1.pdf … 2eso-index.pdf, manifest.json}}
    3eso/{course.json, pdfs/{…}, manifest.json}
    4eso/{course.json, pdfs/{…}, manifest.json}
```

Afegir un curs nou = crear un HTML nou (còpia d'un existent canviant
`window.COURSE`) + una carpeta `contingut/{curs}/`. Cap canvi de codi.

## Contractes de dades

**`course.json`**
```json
{
  "course": "2eso",
  "label": "2n ESO",
  "pdfPrefix": "2eso",
  "indexPdf": "2eso-index.pdf",
  "units": [
    { "num": 3, "title": "El pla cartesià: dibuixar la proporcionalitat",
      "activities": [
        { "num": 1, "title": "On apareixen gràfiques al dia a dia?",
          "subtitle": "Reconèixer les convencions dels eixos…" }
      ] }
  ]
}
```
`indexPdf` és opcional (`null` si no n'hi ha); només 2n ESO en té un, generat
a partir del document `index-2eso.tex` del repositori font.

**`pdfs/manifest.json`**
```json
{ "pdfs": ["2eso-ud1-1.pdf", "2eso-ud1-2.pdf", "…", "2eso-index.pdf"] }
```
Font de veritat sobre quins PDFs existeixen realment; es genera en temps de
compilació, mai s'escaneja per xarxa activitat per activitat.

## Contingut actual

| Curs | Unitats | Activitats |
|---|---|---|
| 2n ESO | 6 (UD1–UD6) | 53 + 1 document d'índex |
| 3r ESO | 5 (UD1–UD5) | 44 |
| 4t ESO | 2 (UD2, UD3) | 13 |
| 1r ESO | — | encara no iniciat al llibre font |

## Origen del contingut i com regenerar-lo

Els PDFs d'aquest lloc **no es generen en temps real**: són la sortida
compilada d'un repositori LaTeX separat (`llibre_text_ESO`, no inclòs aquí).
Cada activitat és un fitxer `.tex` sense preàmbul propi, inclòs mitjançant la
macro `\mostra{curs}{unitat}{activitat}` definida a `defs.tex`. Per regenerar
un PDF (des de l'arrel del repositori LaTeX):

```bash
cat > _tmp.tex <<'EOF'
\documentclass[11pt,a4paper]{article}
\input{headers.tex}
\input{defs.tex}
\begin{document}
\mostra{2eso}{3}{4}
\end{document}
EOF
pdflatex -interaction=batchmode -halt-on-error _tmp.tex
```

El PDF resultant es copia a `contingut/{curs}/pdfs/{curs}-ud{U}-{A}.pdf` i el
seu nom s'afegeix a `manifest.json`. Els títols i subtítols de `course.json`
s'extreuen automàticament dels comentaris de capçalera i de la comanda
`\horatitol{títol}{subtítol}` de cada fitxer `.tex`.

## Desplegament

Cap build, cap backend. Es pot servir des de qualsevol allotjament estàtic
(Cloudflare Pages, GitHub Pages, Netlify, un simple `python3 -m http.server`
en local…): només cal pujar el contingut d'aquesta carpeta tal qual.

## Comprovacions fetes

- Compilació de les 110 activitats + el document d'índex: 0 errors.
- Recompte de pàgines del PDF fusionat = suma exacta de pàgines dels PDFs
  individuals, comprovat per al curs sencer, per una unitat sencera i per una
  selecció personalitzada entre unitats.
- Navegació, selecció tri-state i fusió provades amb Playwright als tres
  cursos, sense errors de consola.
