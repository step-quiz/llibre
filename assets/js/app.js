/* app.js — ENTRY POINT per a les pàgines de curs (2eso.html, 3eso.html, 4eso.html).
   Depèn de: utils.js, course-tree.js, pdf-merge.js (carregats abans) i de
   pdf-lib (assets/lib/pdf-lib.min.js).

   La pàgina HTML defineix window.COURSE abans de carregar aquest script:
     <script>window.COURSE = 'contingut/2eso';</script>

   Patró (igual que pd-main/course.js): cap registre central de cursos,
   tot es descobreix via fetch() de {COURSE}/course.json i
   {COURSE}/pdfs/manifest.json. Afegir un curs nou = crear un HTML nou +
   una carpeta de contingut nova. Cap canvi de codi en aquest fitxer. */

const coursePath = window.COURSE;
let courseMeta = null;
let pdfSet = new Set();
let currentBlobUrl = null;
let lastMergeKey = null;
let lastMergeBlob = null;

const state = {
  selected: new Set(),
  activeFile: null,
  expandedUnit: null,
};

function pdfUrl(filename) { return `${coursePath}/pdfs/${filename}`; }

/* ─── MEMÒRIA DEL NAVEGADOR (recorda on es va deixar cada llibre) ────
   Es guarda un únic registre per curs (window.COURSE) amb la unitat
   desplegada i el fitxer/activitat que s'estava consultant, perquè la
   propera vegada que s'obri el mateix llibre en aquest navegador es
   reprengui exactament al mateix lloc. */
const LAST_VIEW_KEY = `llibre:lastView:${coursePath}`;

function saveLastView() {
  try {
    localStorage.setItem(LAST_VIEW_KEY, JSON.stringify({
      expandedUnit: state.expandedUnit,
      activeFile: state.activeFile,
    }));
  } catch (_) { /* localStorage no disponible (mode privat, quota, etc.) */ }
}

function loadLastView() {
  try {
    const raw = localStorage.getItem(LAST_VIEW_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

/* ─── ORDENACIÓ CANÒNICA D'UNA SELECCIÓ (per fusionar/descarregar) ──── */
function orderedSelection() {
  const files = [];
  if (courseMeta.indexPdf && state.selected.has(courseMeta.indexPdf)) {
    files.push(courseMeta.indexPdf);
  }
  for (const u of courseMeta.units) {
    for (const a of u.activities) {
      const f = activityFilename(courseMeta.pdfPrefix, u.num, a.num);
      if (state.selected.has(f)) files.push(f);
    }
  }
  return files;
}

/* ─── VISOR ──────────────────────────────────────────────────────────── */
function showInFrame(url, title) {
  if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null; }
  const frame = document.getElementById('pdfFrame');
  const empty = document.getElementById('viewerEmpty');
  frame.src = url;
  frame.hidden = false;
  empty.hidden = true;
  document.getElementById('viewerTitle').textContent = title;
  const openBtn = document.getElementById('openNewTab');
  openBtn.href = url;
  openBtn.hidden = false;
}

function selectActivity(unit, act, filename, title) {
  state.activeFile = filename;
  state.expandedUnit = unit;
  showInFrame(pdfUrl(filename), title);
  paint();
  saveLastView();
}

function selectBonus(filename, title) {
  state.activeFile = filename;
  showInFrame(pdfUrl(filename), title);
  paint();
  saveLastView();
}

/* ─── PLEGAR / DESPLEGAR UNITATS (una de sola oberta alhora) ───────── */
function toggleExpand(unit) {
  state.expandedUnit = (state.expandedUnit === unit) ? null : unit;
  paint();
  saveLastView();
}

/* ─── SELECCIÓ (checkboxes) ─────────────────────────────────────────── */
function setSelected(filename, checked) {
  if (checked) state.selected.add(filename); else state.selected.delete(filename);
}

function toggleActivity(unit, act, filename, checked) {
  setSelected(filename, checked);
  paint();
}

function toggleUnit(unit, checked) {
  const u = courseMeta.units.find(x => x.num === unit);
  u.activities.forEach(a => {
    const f = activityFilename(courseMeta.pdfPrefix, unit, a.num);
    if (pdfSet.has(f)) setSelected(f, checked);
  });
  paint();
}

function toggleAll(checked) {
  courseMeta.units.forEach(u => u.activities.forEach(a => {
    const f = activityFilename(courseMeta.pdfPrefix, u.num, a.num);
    if (pdfSet.has(f)) setSelected(f, checked);
  }));
  if (courseMeta.indexPdf && pdfSet.has(courseMeta.indexPdf)) setSelected(courseMeta.indexPdf, checked);
  paint();
}

function toggleBonus(filename, checked) {
  setSelected(filename, checked);
  paint();
}

/* ─── BARRA DE SELECCIÓ ──────────────────────────────────────────────── */
function pluralCat(n, singular, plural) { return n === 1 ? singular : plural; }

function suggestedFilename(files) {
  const prefix = courseMeta.pdfPrefix;
  const allFiles = [];
  courseMeta.units.forEach(u => u.activities.forEach(a =>
    allFiles.push(activityFilename(prefix, u.num, a.num))));
  if (courseMeta.indexPdf) allFiles.push(courseMeta.indexPdf);

  const selSet = new Set(files);
  const isWholeCourse = allFiles.length > 0 && allFiles.every(f => selSet.has(f)) && files.length === allFiles.length;
  if (isWholeCourse) return `${prefix}-complet.pdf`;

  // una unitat sencera, i res més (sense l'índex ni altres unitats)
  for (const u of courseMeta.units) {
    const unitFiles = u.activities.map(a => activityFilename(prefix, u.num, a.num)).filter(f => pdfSet.has(f));
    const matchesUnit = unitFiles.length > 0 &&
      unitFiles.every(f => selSet.has(f)) &&
      files.length === unitFiles.length;
    if (matchesUnit) return `${prefix}-ud${u.num}.pdf`;
  }
  return `${prefix}-seleccio.pdf`;
}

function updateSelectionBar() {
  const bar = document.getElementById('selectionBar');
  const n = state.selected.size;
  bar.hidden = n === 0;
  if (n === 0) return;
  document.getElementById('selCount').textContent = String(n);
  document.getElementById('selLabel').textContent =
    pluralCat(n, 'activitat seleccionada', 'activitats seleccionades');
}

function setBusy(busy) {
  ['btnView', 'btnDownload'].forEach(id => {
    document.getElementById(id).disabled = busy;
  });
}

async function getMergedBlob() {
  const files = orderedSelection();
  const key = files.join('|');
  if (lastMergeBlob && lastMergeKey === key) return lastMergeBlob;
  const urls = files.map(pdfUrl);
  const blob = await mergeSelected(urls);
  lastMergeKey = key;
  lastMergeBlob = blob;
  return blob;
}

async function onViewSelection() {
  if (!state.selected.size) return;
  setBusy(true);
  try {
    const blob = await getMergedBlob();
    const url = URL.createObjectURL(blob);
    const n = state.selected.size;
    showInFrame(url, `Selecció (${n} ${pluralCat(n, 'activitat', 'activitats')})`);
    currentBlobUrl = url;
    state.activeFile = null;
    paint();
  } catch (err) {
    alert('No s\u2019ha pogut generar la selecció: ' + err.message);
  } finally {
    setBusy(false);
  }
}

async function onDownloadSelection() {
  if (!state.selected.size) return;
  setBusy(true);
  try {
    const blob = await getMergedBlob();
    const files = orderedSelection();
    const filename = suggestedFilename(files);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  } catch (err) {
    alert('No s\u2019ha pogut generar la descàrrega: ' + err.message);
  } finally {
    setBusy(false);
  }
}

function onClearSelection() {
  state.selected.clear();
  paint();
}

/* ─── PINTAT ─────────────────────────────────────────────────────────── */
function paint() {
  renderTree(document.getElementById('sidebar'), courseMeta, pdfSet, state, {
    onToggleActivity: toggleActivity,
    onToggleUnit: toggleUnit,
    onToggleAll: toggleAll,
    onToggleBonus: toggleBonus,
    onSelectActivity: selectActivity,
    onSelectBonus: selectBonus,
    onToggleExpand: toggleExpand,
  });
  updateSelectionBar();
}

/* ─── INIT ───────────────────────────────────────────────────────────── */
async function loadApp() {
  courseMeta = await fetchJson(`${coursePath}/course.json`, { cache: 'no-store' });
  if (!courseMeta) {
    document.getElementById('sidebar').innerHTML =
      `<div class="nav-empty">No s\u2019ha pogut llegir <code>course.json</code>.</div>`;
    return;
  }
  document.getElementById('brand').innerHTML =
    `${escHtml(courseMeta.label)} <small>Matemàtiques \u00b7 Llibre de text</small>`;

  const manifest = await fetchJson(`${coursePath}/pdfs/manifest.json`, { cache: 'no-store' });
  pdfSet = new Set(manifest && Array.isArray(manifest.pdfs) ? manifest.pdfs : []);

  document.getElementById('btnView').addEventListener('click', onViewSelection);
  document.getElementById('btnDownload').addEventListener('click', onDownloadSelection);
  document.getElementById('btnClear').addEventListener('click', onClearSelection);

  paint();
  openInitialView();
}

/* ─── VISTA INICIAL ──────────────────────────────────────────────────
   1) Si el navegador recorda on es va deixar aquest llibre (memòria
      local), es reprèn exactament allà: mateixa unitat desplegada i
      mateixa activitat (o l'Índex del curs) seleccionada.
   2) Si no hi ha res guardat (primera visita, o memòria esborrada), es
      mostra per defecte l'"Índex del curs" (si el curs en té un).
   3) Si tampoc hi ha Índex del curs, es cau a l'antic comportament:
      la primera activitat de la primera unitat disponible.
   En tots els casos, la resta d'unitats queden plegades ("collapsed"):
   només es desplega, com a molt, la unitat de l'activitat mostrada. */
/* ─── ENLLAÇ PROFUND (#ud2 · #ud2-3) ─────────────────────────────────
   Permet que un altre lloc obri una activitat concreta d'aquest llibre.
   El fa servir `repas` (repas.step-quiz.net): quan un alumne s'encalla en
   un exercici, l'enllaça amb la teoria que hi ha al darrere.

   Formats acceptats:
     #ud2      → desplega la unitat 2 i n'obre la primera activitat
     #ud2-3    → obre la unitat 2, activitat 3

   Té PRIORITAT sobre la memòria del navegador: si algú arriba amb un enllaç
   a una activitat concreta, és perquè vol aquella, no la que va deixar
   oberta l'última vegada. Si l'àncora no és vàlida (unitat inexistent, PDF
   que no hi és) s'ignora i es fa el de sempre, sense error: un enllaç trencat
   des de fora no ha de deixar el llibre en blanc. */
function objectiuDeLancora() {
  const m = /^#ud(\d+)(?:-(\d+))?$/.exec(location.hash || "");
  if (!m) return null;
  const unitNum = parseInt(m[1], 10);
  const unit = courseMeta.units.find(u => u.num === unitNum);
  if (!unit) return null;

  const actNum = m[2] ? parseInt(m[2], 10) : null;
  const candidates = actNum
    ? unit.activities.filter(a => a.num === actNum)
    : unit.activities;
  for (const a of candidates) {
    const filename = activityFilename(courseMeta.pdfPrefix, unit.num, a.num);
    if (pdfSet.has(filename)) return { unit, activity: a, filename };
  }
  /* La unitat existeix però l'activitat demanada no té PDF: val més obrir la
     unitat desplegada que no pas ignorar l'enllaç del tot. */
  return { unit, activity: null, filename: null };
}

function openInitialView() {
  const desDeFora = objectiuDeLancora();
  if (desDeFora) {
    if (desDeFora.filename) {
      selectActivity(desDeFora.unit.num, desDeFora.activity.num,
        desDeFora.filename,
        `UD${desDeFora.unit.num} \u00b7 Activitat ${desDeFora.activity.num}`
        + ` \u2014 ${desDeFora.activity.title}`);
    } else {
      state.expandedUnit = desDeFora.unit.num;
      paint();
    }
    return;
  }

  const last = loadLastView();

  if (last && last.activeFile && pdfSet.has(last.activeFile)) {
    if (last.activeFile === courseMeta.indexPdf) {
      selectBonus(last.activeFile, 'Índex del curs');
      // l'Índex no pertany a cap unitat: es respecta la unitat que
      // l'usuari tenia desplegada (si encara existeix al curs).
      state.expandedUnit = validExpandedUnit(last.expandedUnit);
      paint();
      saveLastView();
      return;
    }
    const found = findActivityByFilename(last.activeFile);
    if (found) {
      selectActivity(found.unit.num, found.activity.num, last.activeFile,
        `UD${found.unit.num} \u00b7 Activitat ${found.activity.num} \u2014 ${found.activity.title}`);
      return;
    }
  }

  // sense memòria vàlida: Índex del curs per defecte
  if (courseMeta.indexPdf && pdfSet.has(courseMeta.indexPdf)) {
    selectBonus(courseMeta.indexPdf, 'Índex del curs');
    return;
  }

  // últim recurs: primera activitat de la primera unitat disponible
  const firstUnit = courseMeta.units.find(u => u.activities.some(a =>
    pdfSet.has(activityFilename(courseMeta.pdfPrefix, u.num, a.num))));
  if (firstUnit) {
    const firstAct = firstUnit.activities.find(a =>
      pdfSet.has(activityFilename(courseMeta.pdfPrefix, firstUnit.num, a.num)));
    const filename = activityFilename(courseMeta.pdfPrefix, firstUnit.num, firstAct.num);
    selectActivity(firstUnit.num, firstAct.num, filename,
      `UD${firstUnit.num} \u00b7 Activitat ${firstAct.num} \u2014 ${firstAct.title}`);
  }
}

/* Troba unitat+activitat a partir d'un nom de fitxer (per restaurar memòria). */
function findActivityByFilename(filename) {
  for (const u of courseMeta.units) {
    for (const a of u.activities) {
      if (activityFilename(courseMeta.pdfPrefix, u.num, a.num) === filename) {
        return { unit: u, activity: a };
      }
    }
  }
  return null;
}

/* Comprova que la unitat guardada com a "desplegada" encara existeix al curs. */
function validExpandedUnit(unitNum) {
  if (unitNum == null) return null;
  return courseMeta.units.some(u => u.num === unitNum) ? unitNum : null;
}

loadApp();
