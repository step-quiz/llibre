# Novetats — UD9 + Índex del curs de 4t ESO Aplicades

Un sol curs canvia respecte a l'entrega anterior.

| Curs | Abans | Ara |
|---|---|---|
| 4t ESO · Aplicades | 8 unitats · 50 activitats, sense document d'índex | **9 unitats · 57 activitats + document "Índex del curs"** |

Novetat: **UD9 — Atzar i decisions** (7 activitats: comptar amb arbre,
Laplace i experimentació, probabilitat composta, atzar i decisions
crítiques...) i el document `index-4eso-apl.tex`, que ara es tracta igual
que els altres cursos que ja en tenien un (2n ESO, 3r ESO, 4t Acadèmiques):
apareix com a "Índex del curs" seleccionable a la barra lateral.

`2eso/ud1.tex` ha desaparegut del teu Overleaf — era un fitxer solt amb
un parell de crides `\mostra` comentades, no forma part de cap activitat
compilada, així que no afecta res del lloc.

## Fitxers d'aquest paquet

```
contingut/4eso-apl/course.json           actualitzat (9 unitats, indexPdf)
contingut/4eso-apl/pdfs/manifest.json    actualitzat
contingut/4eso-apl/pdfs/4eso-apl-ud9-*.pdf   7 fitxers nous
contingut/4eso-apl/pdfs/4eso-apl-index.pdf   nou
index.html                               actualitzat (compte de 4t Aplicades)
```

Cap altre curs ni pàgina HTML canvia; no cal tocar res més.

## Comprovacions fetes

- Compilació: 8/8 fitxers nous, 0 errors (UD9 amb el mateix `\input` directe
  + capçalera manual que la resta de 4t ESO Aplicades, ja que `defs.tex`
  encara no reconeix "4eso-apl" a `\mostra`).
- Recompte de pàgines del PDF fusionat del curs sencer = suma de pàgines
  individuals (178 = 178).
- Arbre de selecció, document d'índex i vista inicial provats amb
  Playwright, sense errors de consola.
