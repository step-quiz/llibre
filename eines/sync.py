#!/usr/bin/env python3
# =====================================================================
#  sync.py — Sincronitza el repositori LaTeX amb el lloc web de PDFs
#
#  Quatre ordres, en l'ordre en què les faràs servir:
#
#    python3 sync.py 1eso --main
#        Escriu "main-1eso.tex". El copies a Overleaf i el compiles:
#        et dona UN PDF amb totes les activitats del curs.
#
#    python3 sync.py 1eso --split ~/Descarregues/main-1eso.pdf
#        Parteix aquell PDF en un fitxer per activitat, els posa al lloc
#        web i regenera course.json, manifest.json i index.html.
#        NO cal tenir LaTeX instal·lat.
#
#    python3 sync.py 1eso --check
#        No toca res. Només diu quines activitats falten al web.
#
#    python3 sync.py 1eso --compile
#        Alternativa a --main + --split si TENS LaTeX instal·lat:
#        compila cada activitat aquí mateix.
#
#  El .tex és sempre l'única font de veritat: els títols del web es
#  llegeixen de \horatitol i no es poden desincronitzar.
#
#  Ús a GitHub Codespaces (sense instal·lar res al portàtil):
#    l'script viu al repo del web (p. ex. eines/sync.py) i el font
#    d'Overleaf es descomprimeix a _font/ (ignorat per git):
#        python3 eines/sync.py 1eso --compile --ud 3 --font _font
#    El repo del web es detecta sol (la carpeta que conté contingut/).
# =====================================================================
import argparse, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

TEX = Path(__file__).resolve().parent           # font LaTeX (per defecte, aquesta carpeta)
WEB = None                                      # repo del web (es detecta a main())


def troba_web(tex: Path):
    """Busca el repo del web: la carpeta que conté contingut/."""
    candidats = [Path.cwd(), Path(__file__).resolve().parent.parent,
                 tex.parent, tex.parent / "llibre-main"]
    for c in candidats:
        if (c / "contingut").is_dir():
            return c.resolve()
    return (tex.parent / "llibre-main").resolve()

ETIQUETES = {"1eso": "1r ESO", "2eso": "2n ESO", "3eso": "3r ESO",
             "4eso": "4t ESO", "4eso-apl": "4t ESO Aplicades"}


# ---------------------------------------------------------------------
#  Lectura dels títols des del .tex
# ---------------------------------------------------------------------
def _mates(m):
    """Normalitza el contingut d'un $...$ perquè s'assembli al PDF."""
    t = m.group(1)
    t = t.replace("^2", "\u00b2").replace("^3", "\u00b3")
    t = re.sub(r"\s*([=+])\s*", r" \1 ", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    return " ".join(t.split())


def tex_a_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\\(?:textbf|emph|textit)\{(.+?)\}", r"\1", s)
    s = re.sub(r"\$(.+?)\$", _mates, s)
    s = s.replace("\\%", "%").replace("\\&", "&")
    s = re.sub(r"\\,|\\ |~", " ", s)
    s = s.replace("{", "").replace("}", "")
    return " ".join(s.split())


def llegeix_activitat(f: Path):
    """Retorna (titol, subtitol, titol_de_la_unitat) o None."""
    s = f.read_text(encoding="utf-8")
    m = re.search(r"\\horatitol\{(.+?)\}%?\s*\n?\{(.+?)\}", s, re.S)
    if not m:
        return None
    titol = re.sub(r"^Activitat\s+\d+\s+\u2014\s*", "", tex_a_text(m.group(1)))
    subtitol = tex_a_text(m.group(2))
    mu = re.search(r"^%\s+UD\d+\s+\u2014\s*(.+?)\s*$", s, re.M)
    titol_ud = None
    if mu:
        titol_ud = mu.group(1)
        # Les capçaleres porten qualificadors que el web no té:
        #   "... (via A · Aplicades)"  ·  "... · activitat inicial (1 sessio)"
        # Cal treure PRIMER el parentesi (pot contenir un "·" a dins).
        titol_ud = re.sub(r"\s*\([^()]*\)\s*$", "", titol_ud)
        titol_ud = titol_ud.split(" \u00b7 ")[0].strip()
    return titol, subtitol, titol_ud


def inventari(curs: str):
    """Llista ordenada de (unitat, activitat, titol, subtitol, titol_unitat)."""
    fitxers = sorted(
        (TEX / curs).glob(f"ud*/{curs}-ud*-*.tex"),
        key=lambda p: tuple(int(x) for x in
                            re.search(r"ud(\d+)-(\d+)\.tex$", p.name).groups()))
    out = []
    for f in fitxers:
        ud, act = (int(x) for x in re.search(r"ud(\d+)-(\d+)\.tex$", f.name).groups())
        d = llegeix_activitat(f)
        if d is None:
            print(f"  !  {f.name}: no hi trobo \\horatitol, l'ometo")
            continue
        out.append((ud, act) + d)
    return out


# ---------------------------------------------------------------------
#  Escriptura dels fitxers del web
# ---------------------------------------------------------------------
def escriu_metadades(curs, inv):
    base = WEB / "contingut" / curs
    (base / "pdfs").mkdir(parents=True, exist_ok=True)

    # Només es publica el que té PDF: així una activitat o una unitat encara no
    # compilada (p. ex. 4t Aplicades UD10-UD11) no surt ni al manifest, ni a
    # course.json, ni al recompte de l'index.html.
    falten = [f"{curs}-ud{ud}-{act}.pdf" for ud, act, *_ in inv
              if not (base / "pdfs" / f"{curs}-ud{ud}-{act}.pdf").exists()]
    if falten:
        print(f"  !  {len(falten)} activitats del .tex encara no tenen PDF; "
              f"no es publiquen: {', '.join(falten)}")
    inv = [x for x in inv if f"{curs}-ud{x[0]}-{x[1]}.pdf" not in falten]

    unitats = {}
    for ud, act, titol, subtitol, titol_ud in inv:
        nova = ud not in unitats
        u = unitats.setdefault(ud, {"num": ud, "title": titol_ud or f"UD{ud}",
                                    "activities": []})
        # El titol d'unitat es pren NOMES de la primera activitat: les altres
        # sovint porten variants ("UD1 - Sentit numeric · BLOC B").
        if nova and titol_ud:
            u["title"] = titol_ud
        u["activities"].append({"num": act, "title": titol, "subtitle": subtitol})

    index_pdf = f"{curs}-index.pdf"
    te_index = (base / "pdfs" / index_pdf).exists()
    noms = [f"{curs}-ud{ud}-{act}.pdf" for ud, act, *_ in inv]

    (base / "pdfs" / "manifest.json").write_text(
        json.dumps({"pdfs": ([index_pdf] if te_index else []) + noms},   # mateix ordre que ara
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (base / "course.json").write_text(json.dumps({
        "course": curs, "label": ETIQUETES.get(curs, curs),
        "pdfPrefix": curs, "indexPdf": index_pdf if te_index else None,
        "units": [unitats[k] for k in sorted(unitats)],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idx = WEB / "index.html"
    if idx.exists():
        html = idx.read_text(encoding="utf-8")
        nou = re.sub(
            rf'(href="{re.escape(curs)}\.html".*?<span class="cc-sub">)[^<]*(</span>)',
            '\\g<1>' + f'{len(unitats)} unitats \u00b7 {len(inv)} activitats' + '\\g<2>',
            html, flags=re.S)
        if nou != html:
            idx.write_text(nou, encoding="utf-8")

    return len(unitats), len(inv)


# ---------------------------------------------------------------------
#  MODE --main : genera el fitxer per compilar a Overleaf
# ---------------------------------------------------------------------
def fes_main(curs, inv):
    linies = ["\\documentclass[11pt,a4paper]{article}",
              "\\input{headers.tex}", "\\input{defs.tex}",
              "\\begin{document}", ""]
    ud_ant = None
    for ud, act, titol, *_ in inv:
        if ud != ud_ant:
            linies.append(f"% ---------- UD{ud} ----------")
            ud_ant = ud
        linies.append(f"\\mostra{{{curs}}}{{{ud}}}{{{act}}}  % {titol}")
    linies += ["", "\\end{document}", ""]
    f = TEX / f"main-{curs}.tex"
    f.write_text("\n".join(linies), encoding="utf-8")
    print(f"Escrit {f.name} amb {len(inv)} activitats.")
    print("Copia'l a Overleaf, compila'l i descarrega el PDF resultant.")


# ---------------------------------------------------------------------
#  MODE --split : parteix el PDF gran (no cal LaTeX)
# ---------------------------------------------------------------------
def parteix(curs, inv, pdf_gran: Path):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        sys.exit("Falta la llibreria pypdf. Instal\u00b7la-la amb:\n"
                 "    pip install pypdf")

    lector = PdfReader(str(pdf_gran))
    print(f"Llegint {pdf_gran.name}: {len(lector.pages)} pagines.")

    # Cada pagina porta "Unitat N · Activitat M" a la capcalera. L'extractor
    # de text hi cola espais pel mig ("A ctivitat"), aixi que els traiem tots
    # abans de comparar.
    trams, actual, inici = [], None, 0
    for i, pagina in enumerate(lector.pages):
        text = re.sub(r"\s+", "", (pagina.extract_text() or "")[:200])
        m = re.search(r"Unitat(\d+)\u00b7Activitat(\d+)", text)
        if not m:
            print(f"  !  pagina {i+1}: sense capcalera reconeixible.")
            continue
        clau = (int(m.group(1)), int(m.group(2)))
        if clau != actual:
            if actual is not None:
                trams.append((actual, inici, i))
            actual, inici = clau, i
    if actual is not None:
        trams.append((actual, inici, len(lector.pages)))

    esperades = {(ud, act) for ud, act, *_ in inv}
    trobades = {c for c, _, _ in trams}
    if esperades - trobades:
        print(f"  !  no surten al PDF: {sorted(esperades - trobades)}")
    if trobades - esperades:
        print(f"  !  al PDF pero no al .tex: {sorted(trobades - esperades)}")

    desti = WEB / "contingut" / curs / "pdfs"
    desti.mkdir(parents=True, exist_ok=True)
    for (ud, act), a, b in trams:
        w = PdfWriter()
        for p in range(a, b):
            w.add_page(lector.pages[p])
        nom = f"{curs}-ud{ud}-{act}.pdf"
        with open(desti / nom, "wb") as fh:
            w.write(fh)
        print(f"  {nom}  ({b - a} pag.)")
    return len(trams)


# ---------------------------------------------------------------------
#  MODE --compile : compila localment (nomes si tens LaTeX)
# ---------------------------------------------------------------------
def compila(curs, ud, act, desti: Path) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        aux = Path(tmp) / "a.tex"
        aux.write_text("\\documentclass[11pt,a4paper]{article}\n"
                       "\\input{headers.tex}\n\\input{defs.tex}\n"
                       "\\begin{document}\n"
                       f"\\mostra{{{curs}}}{{{ud}}}{{{act}}}\n"
                       "\\end{document}\n", encoding="utf-8")
        for _ in range(2):
            subprocess.run(["pdflatex", "-interaction=batchmode",
                            f"-output-directory={tmp}", str(aux)],
                           cwd=TEX, capture_output=True)
        pdf = Path(tmp) / "a.pdf"
        log = Path(tmp) / "a.log"
        errors = []
        if log.exists():
            errors = [l for l in log.read_text(errors="replace").splitlines()
                      if l.startswith("!")]
        if errors or not pdf.exists():
            # Amb errors, pdflatex a vegades escup igualment un PDF trencat:
            # no el copiem, perquè no substitueixi el que ja està publicat.
            print(f"\n      {errors[0] if errors else 'no ha sortit cap PDF'}", end=" ")
            return False
        desti.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, desti)
        return True


# ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Sincronitza el LaTeX amb el lloc web.")
    ap.add_argument("curs", help="1eso, 2eso, 3eso, 4eso o 4eso-apl")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--main", action="store_true", help="genera main-{curs}.tex per a Overleaf")
    g.add_argument("--split", metavar="PDF", help="parteix el PDF gran d'Overleaf")
    g.add_argument("--check", action="store_true", help="informa; no toca res")
    g.add_argument("--compile", action="store_true", help="compila localment (cal LaTeX)")
    ap.add_argument("--ud", type=int, help="amb --compile: nomes aquesta unitat")
    ap.add_argument("--web", metavar="CARPETA",
                    help="ruta del repo del web (per defecte, es detecta sol)")
    ap.add_argument("--font", metavar="CARPETA",
                    help="ruta del font LaTeX (per defecte, la carpeta de l'script)")
    args = ap.parse_args()

    global WEB, TEX
    if args.font:
        TEX = Path(args.font).expanduser().resolve()
    WEB = Path(args.web).expanduser().resolve() if args.web else troba_web(TEX)

    curs = args.curs
    if not (TEX / curs).is_dir():
        sys.exit(f"No trobo la carpeta {TEX / curs}")
    inv = inventari(curs)
    if not inv:
        sys.exit(f"Cap activitat a {TEX / curs}")

    if args.main:
        fes_main(curs, inv)
        return

    if not WEB.is_dir():
        sys.exit(f"No trobo el repo del web (cap carpeta amb contingut/).\n"
                 f"Indica-la amb --web, per exemple:  --web /workspaces/llibre")

    if args.check:
        falten = 0
        for ud, act, titol, *_ in inv:
            p = WEB / "contingut" / curs / "pdfs" / f"{curs}-ud{ud}-{act}.pdf"
            if not p.exists():
                falten += 1
                print(f"  x FALTA  {curs}-ud{ud}-{act}.pdf   {titol}")
        print(f"\n{curs}: {len(inv)} activitats al .tex, {falten} sense publicar.")
        return

    if args.split:
        pdf = Path(args.split).expanduser()
        if not pdf.exists():
            sys.exit(f"No trobo {pdf}")
        n = parteix(curs, inv, pdf)
        print(f"\n{n} activitats partides.")
    else:
        fallides = []
        for ud, act, *_ in inv:
            if args.ud and ud != args.ud:
                continue
            nom = f"{curs}-ud{ud}-{act}.pdf"
            print(f"  compilant {nom} ... ", end="", flush=True)
            desti = WEB / "contingut" / curs / "pdfs" / nom
            if compila(curs, ud, act, desti):
                try:
                    from pypdf import PdfReader
                    print(f"ok ({len(PdfReader(str(desti)).pages)} pag.)")
                except Exception:
                    print("ok")
            else:
                print("ERROR"); fallides.append(nom)
        if fallides:
            print(f"\n  !  {len(fallides)} fallides: {', '.join(fallides)}")

    n_ud, n_act = escriu_metadades(curs, inv)
    print(f"\nMetadades actualitzades: {n_ud} unitats, {n_act} activitats.")
    print("Ara ves al repo del web, mira 'git diff' i fes commit.")


if __name__ == "__main__":
    main()
