#!/usr/bin/env python3
# =====================================================================
#  test_sync.py — Proves de sync.py
#
#      python3 eines/test_sync.py          (des de l'arrel del repositori)
#
#  Només fa servir la biblioteca estàndard de Python; pypdf, si hi és,
#  s'aprofita (sync.py el fa servir per comptar pàgines i trobar les
#  solucions), però les proves passen igual sense.
#
#  Dues parts:
#
#  1. sync.py contra un curs de mentida (un font LaTeX i un web en una
#     carpeta temporal). No cal LaTeX: la compilació es substitueix per una
#     funció que escriu un PDF d'una pàgina i diu quants exercicis té cada
#     activitat. Així es prova de debò la lògica de la numeració
#     (què es recompila, què es renumera, què es deixa estar), el manifest,
#     course.json i el recompte de l'index.html.
#
#  2. Les dades publicades de debò (contingut/*): que course.json, el
#     manifest, els PDFs, numeracio.json i l'index.html diguin el mateix.
# =====================================================================
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

EINES = Path(__file__).resolve().parent
ARREL = EINES.parent
sys.path.insert(0, str(EINES))
import sync  # noqa: E402

CURSOS = ["1eso", "2eso", "3eso", "4eso", "4eso-apl"]

try:
    from pypdf import PdfReader
except ImportError:          # les proves que en depenen se salten
    PdfReader = None


def pdf_minim(text="Unitat 1 · Activitat 1"):
    """Un PDF vàlid d'una pàgina, fet a mà (sense cap biblioteca)."""
    contingut = ("BT /F1 12 Tf 72 720 Td (%s) Tj ET" % text.encode("latin-1", "replace")
                 .decode("latin-1")).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(contingut) + contingut + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def activitat_tex(ud, act, titol, subtitol, titol_ud):
    return ("%% UD%d \u2014 %s\n" % (ud, titol_ud)
            + "\\horatitol{Activitat %d \u2014 %s}{%s}\n" % (act, titol, subtitol)
            + "Text de l'activitat.\n")


class CursDeMentida(unittest.TestCase):
    """Un font amb dues unitats (UD1: tres activitats; UD2: dues) i un web
    buit amb un index.html que té la targeta del curs."""

    CURS = "1eso"
    # Exercicis i exemples de cada activitat. La compilació de mentida els
    # suma a l'inici que li passa sync.py, com fa numeracio.tex de debò.
    EXERCICIS = {(1, 1): (5, 1), (1, 2): (3, 2), (1, 3): (4, 0),
                 (2, 1): (6, 1), (2, 2): (2, 1)}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.font = base / "font"
        self.web = base / "web"
        for (ud, act) in self.EXERCICIS:
            f = self.font / self.CURS / f"ud{ud}" / f"{self.CURS}-ud{ud}-{act}.tex"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(activitat_tex(ud, act, f"Títol {ud}.{act}", f"Subtítol {ud}.{act}",
                                       f"Unitat {ud}"), encoding="utf-8")
        (self.web / "contingut" / self.CURS / "pdfs").mkdir(parents=True)
        (self.web / "index.html").write_text(
            '<a href="1eso.html" class="cc"><span class="cc-sub">0 unitats · 0 activitats</span></a>\n'
            '<a href="2eso.html" class="cc"><span class="cc-sub">6 unitats · 53 activitats</span></a>\n',
            encoding="utf-8")
        self.crides = []
        self.falla = set()
        self._compila_original = sync.compila
        sync.compila = self._compila

    def tearDown(self):
        sync.compila = self._compila_original
        self._tmp.cleanup()

    # --- substituts -------------------------------------------------------
    def _compila(self, curs, ud, act, desti, inici=None, taula=(), einici=None):
        self.crides.append((ud, act))
        if (ud, act) in self.falla:
            return False, None
        n, e = self.EXERCICIS[(ud, act)]
        desti.parent.mkdir(parents=True, exist_ok=True)
        desti.write_bytes(pdf_minim(f"Unitat {ud} · Activitat {act}"))
        return True, {"fi": inici + n, "q": 0, "e_fi": einici + e,
                      "llistes": inici + 1, "x": 0}

    def sync(self, *args):
        """Executa sync.py amb aquests arguments; torna el que escriu."""
        sortida = io.StringIO()
        vell = sys.argv
        sys.argv = ["sync.py", self.CURS, *args, "--font", str(self.font), "--web", str(self.web)]
        try:
            with contextlib.redirect_stdout(sortida):
                sync.main()
        finally:
            sys.argv = vell
        return sortida.getvalue()

    def llegeix(self, nom):
        return json.loads((self.web / "contingut" / self.CURS / nom).read_text(encoding="utf-8"))


class Inventari(CursDeMentida):
    def test_ordre_numeric_no_alfabetic(self):
        """ud10 va després d'ud2, i l'activitat 10 després de la 2."""
        for ud, act in [(10, 1), (1, 10)]:
            f = self.font / self.CURS / f"ud{ud}" / f"{self.CURS}-ud{ud}-{act}.tex"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(activitat_tex(ud, act, "x", "y", "z"), encoding="utf-8")
        sync.TEX = self.font
        claus = [(u, a) for u, a, *_ in sync.inventari(self.CURS)]
        self.assertEqual(claus, [(1, 1), (1, 2), (1, 3), (1, 10), (2, 1), (2, 2), (10, 1)])

    def test_sense_horatitol_s_omet_i_s_avisa(self):
        f = self.font / self.CURS / "ud1" / f"{self.CURS}-ud1-4.tex"
        f.write_text("% UD1 — Unitat 1\nSense títol.\n", encoding="utf-8")
        sync.TEX = self.font
        sortida = io.StringIO()
        with contextlib.redirect_stdout(sortida):
            claus = [(u, a) for u, a, *_ in sync.inventari(self.CURS)]
        self.assertNotIn((1, 4), claus)
        self.assertIn("1eso-ud1-4.tex", sortida.getvalue())

    def test_un_nom_que_no_encaixa_s_ignora_i_s_avisa_sense_petar(self):
        """Un 1eso-ud1-7bis.tex (o similar) no ha de fer petar l'inventari."""
        f = self.font / self.CURS / "ud1" / f"{self.CURS}-ud1-7bis.tex"
        f.write_text(activitat_tex(1, 7, "x", "y", "z"), encoding="utf-8")
        sync.TEX = self.font
        sortida = io.StringIO()
        with contextlib.redirect_stdout(sortida):
            claus = [(u, a) for u, a, *_ in sync.inventari(self.CURS)]
        self.assertNotIn((1, 7), claus)
        self.assertIn("ud1-7bis.tex", sortida.getvalue())

    def test_titols_net(self):
        f = self.font / self.CURS / "ud1" / f"{self.CURS}-ud1-1.tex"
        f.write_text("% UD1 \u2014 Sentit numèric · activitat inicial (1 sessió · 55 min)\n"
                     "\\horatitol{Activitat 1 \u2014 \\textbf{Fraccions} i $x^2 = 4$}%\n"
                     "{El 50\\,\\% d'un \\emph{tot}}\n", encoding="utf-8")
        titol, subtitol, titol_ud = sync.llegeix_activitat(f)
        self.assertEqual(titol, "Fraccions i x\u00b2 = 4")
        self.assertEqual(subtitol, "El 50 % d'un tot")
        self.assertEqual(titol_ud, "Sentit numèric")

    def test_claus_niades_al_titol(self):
        """El subtítol de la 4eso 1.2 sortia al web tallat al primer «}»:
        «Classificar nombres pels subconjunts $\\mathbbN»."""
        f = self.font / self.CURS / "ud1" / f"{self.CURS}-ud1-1.tex"
        f.write_text("% UD1 \u2014 Nombres reals\n"
                     "\\horatitol{Activitat 2 \u2014 El mapa dels reals i la recta}\n"
                     "{Classificar nombres pels subconjunts "
                     "$\\mathbb{N}\\subset\\mathbb{Z}\\subset\\mathbb{Q}\\subset\\mathbb{R}$ "
                     "justificant-ho, entendre per què $\\sqrt{2}$ és irracional}\n",
                     encoding="utf-8")
        titol, subtitol, _ = sync.llegeix_activitat(f)
        self.assertEqual(titol, "El mapa dels reals i la recta")
        self.assertEqual(subtitol, "Classificar nombres pels subconjunts "
                         "\u2115 \u2282 \u2124 \u2282 \u211a \u2282 \u211d justificant-ho, "
                         "entendre per què \u221a2 és irracional")

    def test_comentari_entre_els_dos_arguments(self):
        f = self.font / self.CURS / "ud1" / f"{self.CURS}-ud1-1.tex"
        f.write_text("\\horatitol{Activitat 1 \u2014 A}% el subtítol, a sota\n  {B \\textbf{C} D}\n",
                     encoding="utf-8")
        self.assertEqual(sync.llegeix_activitat(f)[:2], ("A", "B C D"))

    def test_cap_titol_publicat_no_porta_restes_de_latex(self):
        for curs in CURSOS:
            course = json.loads((ARREL / "contingut" / curs / "course.json").read_text(encoding="utf-8"))
            for u in course["units"]:
                for a in u["activities"]:
                    for camp in ("title", "subtitle"):
                        with self.subTest(curs=curs, act=f"{u['num']}.{a['num']}", camp=camp):
                            self.assertNotRegex(a[camp], r"[\\{}$]")


class Compilacio(CursDeMentida):
    def test_primera_compilacio_encadena_la_numeracio_per_unitat(self):
        self.sync("--compile")
        self.assertEqual(self.crides, list(self.EXERCICIS))
        num = self.llegeix("numeracio.json")
        self.assertEqual(list(num), ["1.1", "1.2", "1.3", "2.1", "2.2"])
        # Cada unitat torna a començar a 0; dins de la unitat, cada activitat
        # comença on acaba l'anterior (exercicis i exemples per separat).
        esperat = {"1.1": (0, 5, 0, 1), "1.2": (5, 8, 1, 3), "1.3": (8, 12, 3, 3),
                   "2.1": (0, 6, 0, 1), "2.2": (6, 8, 1, 2)}
        for k, (ini, fi, eini, efi) in esperat.items():
            self.assertEqual((num[k]["inici"], num[k]["fi"], num[k]["e_inici"], num[k]["e_fi"]),
                             (ini, fi, eini, efi), k)

    def test_recompilar_una_activitat_que_no_canvia_no_toca_les_altres(self):
        self.sync("--compile")
        self.crides.clear()
        self.sync("--compile", "--act", "1.2")
        self.assertEqual(self.crides, [(1, 2)])

    def test_si_una_activitat_creix_es_renumeren_les_seguents_de_la_unitat(self):
        self.sync("--compile")
        self.crides.clear()
        self.EXERCICIS = {**self.EXERCICIS, (1, 1): (7, 1)}
        sortida = self.sync("--compile", "--act", "1.1")
        # 1.2 i 1.3 porten els números d'exercici al PDF: s'han de refer.
        # La UD2 té la seva pròpia numeració: no es toca.
        self.assertEqual(self.crides, [(1, 1), (1, 2), (1, 3)])
        self.assertEqual(sortida.count("<- renumerada"), 2)
        num = self.llegeix("numeracio.json")
        self.assertEqual((num["1.2"]["inici"], num["1.3"]["inici"], num["1.3"]["fi"]), (7, 10, 14))
        self.assertEqual(num["2.1"]["inici"], 0)

    def test_una_activitat_sense_exercicis_no_es_recompila_nomes_es_desplaca(self):
        """Si una activitat no té exercicis ni referències (fi == inici, x == 0),
        el seu PDF no depèn d'on comença: només s'actualitzen les dades."""
        self.EXERCICIS = {**self.EXERCICIS, (1, 3): (0, 0)}
        self.sync("--compile")
        self.crides.clear()
        self.EXERCICIS = {**self.EXERCICIS, (1, 2): (5, 2)}
        self.sync("--compile", "--act", "1.2")
        self.assertEqual(self.crides, [(1, 2)])
        num = self.llegeix("numeracio.json")
        self.assertEqual((num["1.3"]["inici"], num["1.3"]["fi"]), (10, 10))

    def test_ud_compila_nomes_aquella_unitat(self):
        self.sync("--compile")
        self.crides.clear()
        self.sync("--compile", "--ud", "2")
        self.assertEqual(self.crides, [(2, 1), (2, 2)])

    def test_sense_numeracio_l_act_ho_compila_tot(self):
        """--act 1.3 sense numeracio.json: per saber on comença la 1.3 cal
        compilar abans la 1.1 i la 1.2, i de passada es compila la resta per
        tornar a tenir numeracio.json sencer."""
        sortida = self.sync("--compile", "--act", "1.3")
        self.assertEqual(self.crides, list(self.EXERCICIS))
        self.assertEqual(sortida.count("<- calia per a la numeració"), 4)
        self.assertEqual(len(self.llegeix("numeracio.json")), 5)

    def test_un_error_de_latex_no_esborra_res_i_la_numeracio_segueix(self):
        self.sync("--compile")
        pdf = self.web / "contingut" / self.CURS / "pdfs" / f"{self.CURS}-ud1-2.pdf"
        abans = pdf.read_bytes()
        self.crides.clear()
        self.falla = {(1, 2)}
        sortida = self.sync("--compile", "--act", "1.2")
        self.assertIn("1 fallides", sortida)
        self.assertEqual(pdf.read_bytes(), abans, "el PDF publicat s'ha de conservar")
        self.assertEqual(self.llegeix("numeracio.json")["1.2"]["fi"], 8)

    def test_act_que_no_existeix_s_atura(self):
        with self.assertRaises(SystemExit):
            self.sync("--compile", "--act", "1.9")
        with self.assertRaises(SystemExit):
            self.sync("--compile", "--act", "1-2")
        self.assertEqual(self.crides, [])

    def test_numeracio_d_una_versio_antiga_es_recompila(self):
        self.sync("--compile")
        num = self.llegeix("numeracio.json")
        num["1.2"] = {"inici": 5, "fi": 8}                 # sense e_inici, e_fi...
        (self.web / "contingut" / self.CURS / "numeracio.json").write_text(json.dumps(num))
        self.crides.clear()
        self.sync("--compile", "--act", "1.1")
        self.assertIn((1, 2), self.crides)

    def test_activitats_esborrades_surten_de_numeracio(self):
        self.sync("--compile")
        (self.font / self.CURS / "ud2" / f"{self.CURS}-ud2-2.tex").unlink()
        self.sync("--compile", "--ud", "1")
        self.assertNotIn("2.2", self.llegeix("numeracio.json"))


class Metadades(CursDeMentida):
    def test_course_json(self):
        self.sync("--compile")
        c = self.llegeix("course.json")
        self.assertEqual((c["course"], c["label"], c["pdfPrefix"], c["indexPdf"]),
                         ("1eso", "1r ESO", "1eso", None))
        self.assertEqual([u["num"] for u in c["units"]], [1, 2])
        self.assertEqual(c["units"][0]["title"], "Unitat 1")
        self.assertEqual(c["units"][0]["activities"][1],
                         {"num": 2, "title": "Títol 1.2", "subtitle": "Subtítol 1.2"})

    def test_manifest_en_ordre_amb_l_index_primer(self):
        (self.web / "contingut" / self.CURS / "pdfs" / "1eso-index.pdf").write_bytes(pdf_minim())
        self.sync("--compile")
        m = self.llegeix("pdfs/manifest.json")
        self.assertEqual(m["pdfs"], ["1eso-index.pdf", "1eso-ud1-1.pdf", "1eso-ud1-2.pdf",
                                     "1eso-ud1-3.pdf", "1eso-ud2-1.pdf", "1eso-ud2-2.pdf"])
        self.assertEqual(self.llegeix("course.json")["indexPdf"], "1eso-index.pdf")

    def test_una_activitat_sense_pdf_no_es_publica(self):
        self.falla = {(2, 2)}                   # no arriba a tenir PDF
        self.sync("--compile")
        m = self.llegeix("pdfs/manifest.json")
        self.assertNotIn("1eso-ud2-2.pdf", m["pdfs"])
        acts = [a["num"] for u in self.llegeix("course.json")["units"] for a in u["activities"]]
        self.assertEqual(len(acts), 4)
        html = (self.web / "index.html").read_text(encoding="utf-8")
        self.assertIn("2 unitats · 4 activitats", html)

    def test_index_html_nomes_canvia_la_targeta_del_curs(self):
        self.sync("--compile")
        html = (self.web / "index.html").read_text(encoding="utf-8")
        self.assertIn("2 unitats · 5 activitats", html)
        self.assertIn("6 unitats · 53 activitats", html, "la targeta de 2n no s'ha de tocar")

    @unittest.skipIf(PdfReader is None, "cal pypdf")
    def test_pagina_de_solucions(self):
        self.sync("--compile")
        self.assertEqual(self.llegeix("pdfs/manifest.json")["solucions"], {},
                         "cap PDF de mentida té «Full del professorat»")
        pdf = self.web / "contingut" / self.CURS / "pdfs" / f"{self.CURS}-ud1-1.pdf"
        pdf.write_bytes(pdf_minim("Full del professorat - Solucions"))
        sync.WEB = self.web
        self.assertEqual(sync.pagines_solucions(pdf.parent, [pdf.name]), {pdf.name: 1})

    def test_check_no_escriu_res(self):
        sortida = self.sync("--check")
        self.assertIn("5 activitats al .tex, 5 sense publicar", sortida)
        self.assertFalse((self.web / "contingut" / self.CURS / "course.json").exists())


class AltresOrdres(CursDeMentida):
    def test_main_llista_les_activitats_en_ordre(self):
        self.sync("--main")
        s = (self.font / f"main-{self.CURS}.tex").read_text(encoding="utf-8")
        mostres = re.findall(r"\\mostra\{1eso\}\{(\d+)\}\{(\d+)\}", s)
        self.assertEqual([(int(u), int(a)) for u, a in mostres], list(self.EXERCICIS))
        self.assertIn("\\begin{document}", s)

    def test_import_zip_diu_que_es_nou_que_ha_canviat_i_que_sobra(self):
        (self.font / "defs.tex").write_text("% defs\n", encoding="utf-8")
        zpath = Path(self._tmp.name) / "overleaf.zip"
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("defs.tex", "% defs\n")                                   # igual
            z.writestr("1eso/ud1/1eso-ud1-1.tex",
                       activitat_tex(1, 1, "Nou títol", "s", "Unitat 1"))         # canviat
            z.writestr("1eso/ud3/1eso-ud3-1.tex",
                       activitat_tex(3, 1, "t", "s", "Unitat 3"))                 # nou
            for ud, act in self.EXERCICIS:                                       # la resta, iguals
                if (ud, act) not in [(1, 1), (2, 2)]:
                    rel = f"1eso/ud{ud}/1eso-ud{ud}-{act}.tex"
                    z.writestr(rel, (self.font / rel).read_text(encoding="utf-8"))
        sortida = io.StringIO()
        vell = sys.argv
        sys.argv = ["sync.py", "--import-zip", str(zpath), "--font", str(self.font),
                    "--web", str(self.web)]
        try:
            with contextlib.redirect_stdout(sortida):
                sync.main()
        finally:
            sys.argv = vell
        s = sortida.getvalue()
        self.assertIn("+ 1eso/ud3/1eso-ud3-1.tex", s)
        self.assertIn("* 1eso/ud1/1eso-ud1-1.tex", s)
        self.assertIn("? 1eso/ud2/1eso-ud2-2.tex", s, "un .tex que ja no és a Overleaf s'ha d'avisar")
        self.assertIn("--compile --act 1.1 3.1", s)
        self.assertTrue((self.font / "1eso" / "ud2" / "1eso-ud2-2.tex").exists(),
                        "un zip parcial no pot esborrar res del font")


class DadesPublicades(unittest.TestCase):
    """El que hi ha ara mateix a contingut/: tot ha de dir el mateix."""

    def _curs(self, curs):
        base = ARREL / "contingut" / curs
        course = json.loads((base / "course.json").read_text(encoding="utf-8"))
        manifest = json.loads((base / "pdfs" / "manifest.json").read_text(encoding="utf-8"))
        return base, course, manifest

    def test_course_manifest_i_pdfs_coincideixen(self):
        for curs in CURSOS:
            with self.subTest(curs=curs):
                base, course, manifest = self._curs(curs)
                acts = [f"{curs}-ud{u['num']}-{a['num']}.pdf"
                        for u in course["units"] for a in u["activities"]]
                index = [course["indexPdf"]] if course["indexPdf"] else []
                self.assertEqual(manifest["pdfs"], index + acts)
                for nom in manifest["pdfs"]:
                    self.assertTrue((base / "pdfs" / nom).is_file(), nom)
                self.assertLessEqual(set(manifest["solucions"]), set(acts))
                self.assertEqual(course["course"], curs)
                self.assertEqual(course["label"], sync.ETIQUETES[curs])

    def test_no_hi_ha_pdfs_orfes(self):
        for curs in CURSOS:
            with self.subTest(curs=curs):
                base, _, manifest = self._curs(curs)
                al_disc = {p.name for p in (base / "pdfs").glob("*.pdf")}
                self.assertEqual(al_disc - set(manifest["pdfs"]), set())

    def test_numeracio_encadenada(self):
        for curs in CURSOS:
            with self.subTest(curs=curs):
                base, course, _ = self._curs(curs)
                num = json.loads((base / "numeracio.json").read_text(encoding="utf-8"))
                claus = [f"{u['num']}.{a['num']}" for u in course["units"] for a in u["activities"]]
                self.assertEqual(sorted(num, key=lambda k: tuple(map(int, k.split(".")))), claus)
                for u in course["units"]:
                    fi = efi = 0
                    for a in u["activities"]:
                        d = num[f"{u['num']}.{a['num']}"]
                        k = f"{u['num']}.{a['num']}"
                        self.assertEqual((d["inici"], d["e_inici"]), (fi, efi), k)
                        self.assertGreaterEqual(d["fi"], d["inici"], k)
                        self.assertGreaterEqual(d["e_fi"], d["e_inici"], k)
                        fi, efi = d["fi"], d["e_fi"]

    def test_index_html_dona_els_recomptes_bons(self):
        html = (ARREL / "index.html").read_text(encoding="utf-8")
        for curs in CURSOS:
            with self.subTest(curs=curs):
                _, course, _ = self._curs(curs)
                m = re.search(rf'href="{re.escape(curs)}\.html".*?<span class="cc-sub">([^<]*)</span>',
                              html, re.S)
                self.assertIsNotNone(m)
                n_act = sum(len(u["activities"]) for u in course["units"])
                self.assertEqual(m.group(1), f"{len(course['units'])} unitats · {n_act} activitats")

    def test_cada_curs_te_la_seva_pagina(self):
        for curs in CURSOS:
            with self.subTest(curs=curs):
                html = (ARREL / f"{curs}.html").read_text(encoding="utf-8")
                self.assertIn(curs, html)

    @unittest.skipIf(PdfReader is None, "cal pypdf")
    def test_la_pagina_de_solucions_existeix(self):
        for curs in CURSOS:
            with self.subTest(curs=curs):
                base, _, manifest = self._curs(curs)
                for nom, pag in manifest["solucions"].items():
                    n = len(PdfReader(str(base / "pdfs" / nom)).pages)
                    self.assertTrue(1 <= pag <= n, f"{nom}: pàgina {pag} de {n}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
