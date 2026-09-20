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

REFS_SENSE = 0
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
#  MODE --import-zip : porta un .zip baixat d'Overleaf cap al repo font
# ---------------------------------------------------------------------
def importa_zip(zip_path: Path):
    import zipfile, shutil as sh

    if not zip_path.exists():
        sys.exit(f"No trobo {zip_path}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        # Overleaf sol exportar pla (defs.tex a l'arrel del zip), però per si
        # algun dia ve dins d'una carpeta, cerquem on és defs.tex de debò.
        trobats = list(tmp.rglob("defs.tex"))
        if not trobats:
            sys.exit("Al zip no hi ha cap defs.tex enlloc. Segur que és "
                     "el 'Download > Source' d'Overleaf?")
        arrel = trobats[0].parent

        canviats, nous, del_zip = [], [], set()
        for origen in arrel.rglob("*"):
            if origen.is_dir():
                continue
            relatiu = origen.relative_to(arrel)
            if origen.suffix == ".tex":
                del_zip.add(str(relatiu))
            desti = TEX / relatiu
            contingut_nou = origen.read_bytes()
            if desti.exists():
                if desti.read_bytes() == contingut_nou:
                    continue
                canviats.append(str(relatiu))
            else:
                nous.append(str(relatiu))
            desti.parent.mkdir(parents=True, exist_ok=True)
            sh.copy2(origen, desti)

    # Fitxers .tex que hi ha al font i NO al zip. No els esborrem: un zip
    # parcial buidaria el font sense avisar. Pero cal dir-ho, perque si no
    # una activitat esborrada a Overleaf es continua compilant i publicant
    # des d'una carpeta que ningu no mira.
    sobrants = sorted(
        str(f.relative_to(TEX)) for f in TEX.rglob("*.tex")
        if str(f.relative_to(TEX)) not in del_zip
        and not f.name.startswith("main-")
    )

    print(f"Importat des de {zip_path.name}.")
    if nous:
        print(f"  {len(nous)} fitxer(s) nou(s):")
        for n in nous[:15]:
            print(f"    + {n}")
        if len(nous) > 15:
            print(f"    ... i {len(nous) - 15} més")
    if canviats:
        print(f"  {len(canviats)} fitxer(s) modificat(s):")
        for c in canviats[:15]:
            print(f"    * {c}")
        if len(canviats) > 15:
            print(f"    ... i {len(canviats) - 15} més")
    if not nous and not canviats:
        print("  Cap canvi: ja tenies aquesta versió importada.")
    if sobrants:
        print(f"\n  !  {len(sobrants)} fitxer(s) .tex al font que NO són al zip:")
        for x in sobrants[:15]:
            print(f"    ? {x}")
        if len(sobrants) > 15:
            print(f"    ... i {len(sobrants) - 15} més")
        print("     Si els has esborrat o reanomenat a Overleaf, esborra'ls també")
        print("     aquí; si no, es continuaran compilant i publicant.")
    tocats = nous + canviats
    compartits = [f for f in tocats if f in ("headers.tex", "defs.tex", "quadern.tex", "numeracio.tex")]
    per_curs, indexs = {}, set()
    for f in tocats:
        m = re.fullmatch(r"([^/\\]+)[/\\]ud(\d+)[/\\]\1-ud\2-(\d+)\.tex", f)
        if m:
            per_curs.setdefault(m.group(1), set()).add((int(m.group(2)), int(m.group(3))))
        m = re.fullmatch(r"([^/\\]+)[/\\]index-\1\.tex", f)
        if m:
            indexs.add(m.group(1))
    try:
        font = str(TEX.relative_to(Path.cwd()))
    except ValueError:
        font = str(TEX)
    if compartits:
        print(f"\n  !  Han canviat fitxers compartits ({', '.join(compartits)}):")
        print("     cal compilar els cursos sencers (sense --act).")
    elif per_curs or indexs:
        print("\nPer compilar només el que ha canviat:")
        for c in sorted(per_curs):
            llista = " ".join(f"{u}.{a}" for u, a in sorted(per_curs[c]))
            print(f"  python3 eines/sync.py {c} --compile --act {llista} --font {font}")
        for c in sorted(indexs):
            print(f"  python3 eines/sync.py {c} --index --font {font}")
    print("\nRepassa'ls amb 'git status' i 'git diff' dins del repo font "
          "abans de fer commit.")


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
def compila(curs, ud, act, desti: Path, inici=None, taula=(), einici=None):
    """Compila una activitat. Torna (ok, fi, q): fi és l'últim número d'exercici
    de la unitat fins a aquesta activitat; q, el nombre de preguntes Q (proves)."""
    with tempfile.TemporaryDirectory() as tmp:
        aux = Path(tmp) / "a.tex"
        aux.write_text("\\documentclass[11pt,a4paper]{article}\n"
                       "\\input{headers.tex}\n\\input{defs.tex}\n"
                       "\\begin{document}\n"
                       + ("\\providecommand{\\numeraciodesde}[3]{}\n"
                          f"\\numeraciodesde{{{curs}}}{{{ud}}}{{{inici}}}\n" if inici is not None else "")
                       + ("\\providecommand{\\numeracioexemples}[1]{}\n"
                          f"\\numeracioexemples{{{einici}}}\n" if einici is not None else "")
                       + "".join("\\providecommand{\\numeracioact}[4]{}\n" if i == 0 else ""
                                 for i in range(1 if taula else 0))
                       + "".join(f"\\numeracioact{{{curs}}}{{{k}}}{{{ini}}}{{{q}}}\n" for k, ini, q in taula)
                       + f"\\mostra{{{curs}}}{{{ud}}}{{{act}}}\n"
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
            return False, None
        desti.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, desti)
        text = log.read_text(errors="replace")
        m = re.search(rf"NUMERACIO {re.escape(curs)} {ud}\.{act} fi=(\d+) q=(\d+) e=(\d+) l=(\d+) x=(\d+)", text)
        global REFS_SENSE
        REFS_SENSE = text.count("NUMERACIO-REF-UNDEF")
        return True, (dict(zip(("fi", "q", "e_fi", "llistes", "x"), map(int, m.groups()))) if m else None)


# ---------------------------------------------------------------------
#  MODE --index : compila l'index del curs (index-{curs}.tex)
# ---------------------------------------------------------------------
def compila_index(curs) -> bool:
    """Compila {curs}/index-{curs}.tex i el publica com a {curs}-index.pdf."""
    font = TEX / curs / f"index-{curs}.tex"
    if not font.is_file():
        print(f"  !  no hi ha {font.relative_to(TEX)}: res a fer.")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        aux = Path(tmp) / "i.tex"
        aux.write_text("\\documentclass[11pt,a4paper]{article}\n"
                       "\\input{headers.tex}\n\\input{defs.tex}\n"
                       "\\begin{document}\n"
                       f"\\input{{{curs}/index-{curs}}}\n"
                       "\\end{document}\n", encoding="utf-8")
        for _ in range(2):
            subprocess.run(["pdflatex", "-interaction=batchmode",
                            f"-output-directory={tmp}", str(aux)],
                           cwd=TEX, capture_output=True)
        pdf = Path(tmp) / "i.pdf"
        log = Path(tmp) / "i.log"
        errors = [l for l in log.read_text(errors="replace").splitlines()
                  if l.startswith("!")] if log.exists() else []
        if errors or not pdf.exists():
            print(f"      {errors[0] if errors else 'no ha sortit cap PDF'}")
            return False
        desti = WEB / "contingut" / curs / "pdfs" / f"{curs}-index.pdf"
        desti.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, desti)
        from pypdf import PdfReader
        print(f"  {desti.name}: ok ({len(PdfReader(str(desti)).pages)} pag.)")
        return True


# ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Sincronitza el LaTeX amb el lloc web.")
    ap.add_argument("curs", nargs="?",
                    help="1eso, 2eso, 3eso, 4eso o 4eso-apl (no cal amb --import-zip)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--import-zip", metavar="ZIP",
                   help="porta el .zip exportat d'Overleaf cap al repo font "
                        "i diu quins fitxers han canviat")
    g.add_argument("--main", action="store_true", help="genera main-{curs}.tex per a Overleaf")
    g.add_argument("--split", metavar="PDF", help="parteix el PDF gran d'Overleaf")
    g.add_argument("--index", action="store_true",
                   help="compila index-{curs}.tex i el publica com a {curs}-index.pdf")
    g.add_argument("--check", action="store_true", help="informa; no toca res")
    g.add_argument("--compile", action="store_true", help="compila localment (cal LaTeX)")
    ap.add_argument("--ud", type=int, help="amb --compile: nomes aquesta unitat")
    ap.add_argument("--act", nargs="+", metavar="U.A",
                    help="amb --compile: nomes aquestes activitats (p. ex. --act 1.4 9.5)")
    ap.add_argument("--web", metavar="CARPETA",
                    help="ruta del repo del web (per defecte, es detecta sol)")
    ap.add_argument("--font", metavar="CARPETA",
                    help="ruta del font LaTeX (per defecte, la carpeta de l'script)")
    args = ap.parse_args()

    global WEB, TEX
    if args.font:
        TEX = Path(args.font).expanduser().resolve()
    WEB = Path(args.web).expanduser().resolve() if args.web else troba_web(TEX)

    if args.import_zip:
        importa_zip(Path(args.import_zip).expanduser())
        return

    if not args.curs:
        sys.exit("Falta dir quin curs (1eso, 2eso, 3eso, 4eso o 4eso-apl).")
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

    if args.index:
        compila_index(curs)
        escriu_metadades(curs, inv)
        return

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
        seleccio = None
        if args.act:
            seleccio = set()
            for tros in args.act:
                for x in re.split(r"[,\s]+", tros.strip()):
                    m = re.fullmatch(r"(\d+)\.(\d+)", x)
                    if not m:
                        sys.exit(f"--act: '{x}' no té la forma U.A (p. ex. 1.4)")
                    seleccio.add((int(m.group(1)), int(m.group(2))))
            falten = sorted(seleccio - {(u, a) for u, a, *_ in inv})
            if falten:
                sys.exit(f"--act: no existeixen a {curs}: "
                         + ", ".join(f"{u}.{a}" for u, a in falten))
        # Numeració: 1, 2, 3... per unitat. numeracio.json guarda on comença i on
        # acaba cada activitat; si una activitat canvia de nombre d'exercicis, les
        # següents de la unitat es recompilen soles (les proves, amb Q, no cal).
        num_path = WEB / "contingut" / curs / "numeracio.json"
        try:
            num = json.loads(num_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            num = {}
        per_ud = {}
        for ud, act, *_ in inv:
            per_ud.setdefault(ud, []).append(act)
        sense_marca = False
        for ud in sorted(per_ud):
            if args.ud and ud != args.ud:
                continue
            esperat, eesperat = 0, 0
            for act in per_ud[ud]:
                clau, ant = f"{ud}.{act}", num.get(f"{ud}.{act}")
                if ant is not None and not all(k in ant for k in ("inici", "fi", "q", "e_inici", "e_fi", "llistes", "x")):
                    ant = None                      # dades d'una versió anterior: cal recompilar
                triada = seleccio is None or (ud, act) in seleccio
                if ant is None:
                    motiu = "" if triada else "  <- calia per a la numeració"
                elif triada:
                    motiu = ""
                elif ((ant["inici"] != esperat and (ant["fi"] != ant["inici"] or ant["x"]))
                      or (ant["e_inici"] != eesperat and ant["e_fi"] != ant["e_inici"])):
                    motiu = "  <- renumerada"
                else:
                    # res del que surt al PDF depèn del desplaçament: només s'actualitzen les dades
                    if ant["inici"] != esperat:
                        ant = dict(ant, inici=esperat, fi=esperat, llistes=esperat)
                    if ant["e_inici"] != eesperat:
                        ant = dict(ant, e_inici=eesperat, e_fi=eesperat)
                    num[clau] = ant
                    esperat, eesperat = ant["fi"], ant["e_fi"]
                    continue
                nom = f"{curs}-ud{ud}-{act}.pdf"
                print(f"  compilant {nom} ... ", end="", flush=True)
                desti = WEB / "contingut" / curs / "pdfs" / nom
                taula = [(k, v.get("llistes", v["inici"]), v["q"]) for k, v in num.items()
                         if k.split(".")[0] == str(ud)]
                ok, dades = compila(curs, ud, act, desti, esperat, taula, eesperat)
                if not ok:
                    print("ERROR"); fallides.append(nom)
                    if ant:
                        esperat, eesperat = ant["fi"], ant["e_fi"]
                    continue
                try:
                    from pypdf import PdfReader
                    pags = f"{len(PdfReader(str(desti)).pages)} pag., "
                except Exception:
                    pags = ""
                if dades is None:
                    sense_marca = True
                    print(f"ok ({pags}sense numeració){motiu}")
                    continue
                fi, q = dades["fi"], dades["q"]
                rang = (f"Q1-Q{q}" if q else
                        f"{esperat + 1}-{fi}" if fi > esperat else "sense exercicis")
                avis = (f"  !! {REFS_SENSE} referència(es) \\exref sense resoldre" if REFS_SENSE else "")
                print(f"ok ({pags}{rang}){motiu}{avis}")
                num[clau] = dict(dades, inici=esperat, e_inici=eesperat)
                esperat, eesperat = fi, dades["e_fi"]
        if sense_marca:
            print("\n  !  El font no escriu la numeració: falta \\input{numeracio.tex} a defs.tex.")
        else:
            existents = {f"{u}.{a}" for u, a, *_ in inv}
            num = {k: v for k, v in sorted(num.items(),
                   key=lambda kv: tuple(int(x) for x in kv[0].split(".")))
                   if k in existents}
            num_path.write_text(json.dumps(num, ensure_ascii=False) .replace("}, ", "},\n ")
                                + "\n", encoding="utf-8")
        if fallides:
            print(f"\n  !  {len(fallides)} fallides: {', '.join(fallides)}")

    n_ud, n_act = escriu_metadades(curs, inv)
    print(f"\nMetadades actualitzades: {n_ud} unitats, {n_act} activitats.")
    print("Ara ves al repo del web, mira 'git diff' i fes commit.")


if __name__ == "__main__":
    main()
