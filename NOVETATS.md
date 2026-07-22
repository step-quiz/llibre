# Novetats — segona actualització des d'Overleaf

Fitxers nous o modificats respecte a l'última entrega. **2n ESO i 3r ESO no
apareixen aquí perquè no hi ha cap canvi.** Substitueix/afegeix aquests
fitxers al teu repositori (mateixes rutes relatives) i fes commit + push.

## Resum del que ha canviat al llibre font

| Curs | Abans | Ara | Novetat |
|---|---|---|---|
| **1r ESO** | 1 unitat · 1 activitat | 6 unitats · 57 activitats | Curs desenvolupat sencer + document "Índex del curs" |
| **4t ESO · Acadèmiques** | 9 unitats · 58 activitats | sense canvis de contingut | Només s'actualitza l'etiqueta a "4t ESO · Acadèmiques" perquè ara conviu amb Aplicades |
| **4t ESO · Aplicades** | no existia | 8 unitats · 50 activitats | **Modalitat nova**, curs sencer |

`4eso-academiques/` ha tornat a dir-se `4eso/` al teu Overleaf: el contingut
és bit a bit idèntic al que ja tenies, així que no calia recompilar ni tornar
a pujar cap PDF d'aquest curs — només s'actualitza `course.json` amb el nou
text de l'etiqueta.

## Estructura amb dues modalitats de 4t ESO

El lloc ara té **5 cursos** (2n i 3r continuen igual):

```
1r ESO  →  1eso.html       →  contingut/1eso/
2n ESO  →  2eso.html       →  contingut/2eso/       (sense canvis)
3r ESO  →  3eso.html       →  contingut/3eso/       (sense canvis)
4t ESO · Acadèmiques  →  4eso.html      →  contingut/4eso/
4t ESO · Aplicades    →  4eso-apl.html  →  contingut/4eso-apl/   (nou)
```

Cada pàgina és independent (arxiu HTML + carpeta pròpia a `contingut/`),
seguint el mateix patró d'sempre: cap registre central de cursos, tot es
descobreix per `fetch()`. El menú de navegació superior (`course-nav`) de
les 5 pàgines i de `index.html` s'ha actualitzat perquè hi apareguin els
5 enllaços ("1r ESO", "2n ESO", "3r ESO", "4t Acad.", "4t Apl.").

## ⚠️ Dos avisos sobre el teu Overleaf

**1. `1eso/ud3/` i `1eso/ud4/` estan intercanviades.** Els fitxers de dins
de la carpeta `ud3/` es diuen `1eso-ud4-*.tex` i els de dins de `ud4/` es
diuen `1eso-ud3-*.tex` — la unitat real és la que diu el nom del fitxer
(i el comentari `% UD... —`), no la carpeta que la conté. Ho he detectat i
assignat correctament (UD3 = "Com és de gran Gaza?", UD4 = "És gran l'ou
del kiwi?"), però si compiles algun d'aquests fitxers sol amb `\mostra{1eso}{3}{N}`
o `\mostra{1eso}{4}{N}` a Overleaf, la macro buscarà el fitxer a la carpeta
equivocada i fallarà. Val la pena canviar el nom de les dues carpetes
(`ud3` ↔ `ud4`) per tenir-ho consistent.

**2. `4eso/u10/` continua sense la "d"** (hauria de ser `ud10/`), igual que
ja et vaig comentar a l'entrega anterior — encara no s'ha corregit a
l'Overleaf. Segueix sense afectar els PDFs que t'entrego (ho compenso amb
un `\input` directe), però si hi tornes a treballar val la pena arreglar-ho.

Cap d'aquests dos punts afecta els PDFs d'aquest paquet: ja estan compilats
correctament, amb el número d'unitat que els correspon pel nom del fitxer.

## Fitxers d'aquest paquet

```
index.html                          actualitzat (5 targetes, comptes nous)
1eso.html                            actualitzat (nav amb 5 cursos)
2eso.html / 3eso.html / 4eso.html    actualitzats (nav amb 5 cursos)
4eso-apl.html                        nou
contingut/1eso/course.json           actualitzat (6 unitats, indexPdf)
contingut/1eso/pdfs/manifest.json    actualitzat
contingut/1eso/pdfs/*.pdf            58 fitxers (tot el curs recompilat)
contingut/4eso/course.json           actualitzat (només l'etiqueta)
contingut/4eso-apl/course.json       nou
contingut/4eso-apl/pdfs/manifest.json  nou
contingut/4eso-apl/pdfs/*.pdf        50 fitxers, nous
```

`contingut/2eso/` i `contingut/3eso/` no s'inclouen: cap fitxer ha canviat.
De `contingut/4eso/` només s'inclou `course.json`; els PDFs ja pujats la
vegada anterior continuen sent vàlids.

## Comprovacions fetes abans de lliurar-ho

- Compilació: 108/108 fitxers nous, 0 errors.
- Recompte de pàgines del PDF fusionat = suma de pàgines individuals,
  verificat per al curs sencer d'1r ESO (174=174) i 4t ESO Aplicades
  (149=149).
- Navegació i arbre de selecció provats amb Playwright a les 5 pàgines de
  curs i a `index.html` (5 targetes), sense errors de consola.
