# Novetats — UD1 de 4t ESO Acadèmiques

Omple exactament el buit del missatge anterior: **UD1 "Nombres reals"**
(7 activitats) ja existeix i s'ha compilat. Cap altre curs canvia.

| Curs | Abans | Ara |
|---|---|---|
| 4t ESO · Acadèmiques | 9 unitats · 58 activitats | **10 unitats · 65 activitats** |

## Fitxers d'aquest paquet

```
contingut/4eso/course.json           actualitzat (10 unitats)
contingut/4eso/pdfs/manifest.json    actualitzat
contingut/4eso/pdfs/4eso-ud1-*.pdf   7 fitxers nous
index.html                           actualitzat (compte de 4t Acadèmiques)
```

Cap dels altres cursos ni pàgines HTML canvia; no cal tocar res més.

## Comprovacions fetes

- Compilació: 7/7 fitxers nous, 0 errors — amb `\mostra{4eso}{1}{N}` estàndard
  (aquesta vegada carpeta i prefix de fitxer coincideixen, sense cap dreçera).
- UD1 llegida i comparada amb la programació de `index-4eso.tex`: mateixos
  7 títols i el mateix tema (exacte/aproximat, subconjunts numèrics,
  radicals, racionalització, síntesi, dossier, prova).
- Recompte de pàgines del PDF fusionat del curs sencer = suma de pàgines
  individuals (221 = 221).
- Arbre de selecció i vista inicial (ara UD1 · Activitat 1) provats amb
  Playwright, sense errors de consola.
