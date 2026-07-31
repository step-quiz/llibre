/* course-tree.js — construeix l'arbre de selecció de la sidebar
   (tot el curs → unitat → activitat) amb caselles de selecció tri-state.
   Sense estat propi: llegeix `state` i escriu al DOM cada vegada que es
   crida renderTree(), igual que el patró stateless de sidebar.js a pd-main.

   Exposa (global): renderTree(root, courseMeta, pdfSet, state, handlers)

   state = {
     selected: Set<string>     // noms de fitxer PDF seleccionats (checkbox)
     activeFile: string|null   // fitxer mostrat actualment al visor
     expandedUnit: number|null // unitat actualment desplegada (o null = cap)
   }
   handlers = {
     onToggleActivity(unit, act, filename, checked)
     onToggleUnit(unit, checked)
     onToggleAll(checked)
     onToggleBonus(filename, checked)
     onSelectActivity(unit, act, filename, title)
     onSelectBonus(filename, title)
     onToggleExpand(unit)   // l'usuari ha clicat la capçalera d'una unitat
   } */

function activityFilename(pdfPrefix, unit, act) {
  return `${pdfPrefix}-ud${unit}-${act}.pdf`;
}

function renderTree(root, courseMeta, pdfSet, state, handlers) {
  const { pdfPrefix, units } = courseMeta;
  const selected = state.selected;

  // ── comptes totals per al checkbox "Seleccionar-ho tot" ──────────
  let totalCount = 0, selCount = 0;
  units.forEach(u => u.activities.forEach(a => {
    totalCount++;
    if (selected.has(activityFilename(pdfPrefix, u.num, a.num))) selCount++;
  }));
  if (courseMeta.indexPdf) {
    totalCount++;
    if (selected.has(courseMeta.indexPdf)) selCount++;
  }

  let html = '';

  html += `<div class="tree-master">
    <label>
      <input type="checkbox" id="selectAllCourse">
      <span>Seleccionar tot el curs</span>
    </label>
  </div>`;

  if (courseMeta.indexPdf && pdfSet.has(courseMeta.indexPdf)) {
    const isActive = state.activeFile === courseMeta.indexPdf;
    html += `<div class="side-group">
      <h3>Document del curs</h3>
      <div class="activity-item bonus-item">
        <span class="act-check-wrap">
          <input type="checkbox" class="bonus-check" ${selected.has(courseMeta.indexPdf) ? 'checked' : ''}>
        </span>
        <button class="activity-row bonus-row${isActive ? ' active' : ''}" data-file="${escHtml(courseMeta.indexPdf)}">
          <span class="act-ico">IX</span>
          <span class="act-body">
            <span class="act-title">Índex del curs</span>
            <span class="act-sub">Continguts i coherència curricular</span>
          </span>
        </button>
      </div>
    </div>`;
  }

  html += `<div class="side-group"><h3>Unitats didàctiques</h3>`;
  for (const u of units) {
    const uSelCount = u.activities.filter(a => selected.has(activityFilename(pdfPrefix, u.num, a.num))).length;
    const uTotal = u.activities.length;
    const badgeCls = uSelCount === uTotal ? ' all' : '';
    const isExpanded = state.expandedUnit === u.num;
    html += `<div class="unit-block${isExpanded ? '' : ' collapsed'}" data-unit="${u.num}">
      <div class="unit-header" data-unit-header="${u.num}">
        <span class="unit-collapse">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>
        </span>
        <input type="checkbox" class="unit-check" data-unit="${u.num}" ${uSelCount === uTotal ? 'checked' : ''}>
        <span class="unit-label">
          <span class="unit-num">UD${u.num}</span>
          <span class="unit-title-text">${escHtml(u.title)}</span>
        </span>
        <span class="unit-badge${badgeCls}">${uSelCount}/${uTotal}</span>
      </div>
      <div class="unit-activities">`;
    for (const a of u.activities) {
      const filename = activityFilename(pdfPrefix, u.num, a.num);
      const exists = pdfSet.has(filename);
      const isActive = state.activeFile === filename;
      html += `<div class="activity-item">
        <span class="act-check-wrap">
          <input type="checkbox" class="act-check" data-unit="${u.num}" data-act="${a.num}" ${selected.has(filename) ? 'checked' : ''} ${exists ? '' : 'disabled'}>
        </span>
        <button class="activity-row${isActive ? ' active' : ''}" data-unit="${u.num}" data-act="${a.num}" data-file="${escHtml(filename)}" ${exists ? '' : 'disabled'}>
          <span class="act-ico">${a.num}</span>
          <span class="act-body">
            <span class="act-title">${escHtml(a.title)}</span>
            <span class="act-sub">${escHtml(a.subtitle)}</span>
          </span>
        </button>
      </div>`;
    }
    html += `</div></div>`;
  }
  html += `</div>`;

  root.innerHTML = html;

  // ── tri-state per als checkboxes d'unitat i el de "tot el curs" ──
  root.querySelectorAll('.unit-check').forEach(cb => {
    const unit = cb.dataset.unit;
    const u = units.find(x => String(x.num) === unit);
    const sel = u.activities.filter(a => selected.has(activityFilename(pdfPrefix, u.num, a.num))).length;
    cb.indeterminate = sel > 0 && sel < u.activities.length;
  });
  const masterCb = root.querySelector('#selectAllCourse');
  if (masterCb) {
    masterCb.checked = selCount === totalCount && totalCount > 0;
    masterCb.indeterminate = selCount > 0 && selCount < totalCount;
  }

  // ── esdeveniments ──────────────────────────────────────────────
  root.querySelectorAll('.act-check').forEach(cb => {
    cb.addEventListener('change', () => {
      const unit = Number(cb.dataset.unit), act = Number(cb.dataset.act);
      const filename = activityFilename(pdfPrefix, unit, act);
      handlers.onToggleActivity(unit, act, filename, cb.checked);
    });
  });
  root.querySelectorAll('.unit-check').forEach(cb => {
    cb.addEventListener('change', () => handlers.onToggleUnit(Number(cb.dataset.unit), cb.checked));
  });
  if (masterCb) masterCb.addEventListener('change', () => handlers.onToggleAll(masterCb.checked));

  const bonusCheck = root.querySelector('.bonus-check');
  if (bonusCheck) {
    bonusCheck.addEventListener('change', () => handlers.onToggleBonus(courseMeta.indexPdf, bonusCheck.checked));
  }
  const bonusRow = root.querySelector('.bonus-row');
  if (bonusRow) {
    bonusRow.addEventListener('click', () => handlers.onSelectBonus(courseMeta.indexPdf, 'Índex del curs'));
  }

  root.querySelectorAll('.activity-row:not(.bonus-row)').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      const unit = Number(btn.dataset.unit), act = Number(btn.dataset.act);
      const u = units.find(x => x.num === unit);
      const a = u.activities.find(x => x.num === act);
      handlers.onSelectActivity(unit, act, btn.dataset.file, `UD${unit} · Activitat ${act} — ${a.title}`);
    });
  });

  root.querySelectorAll('.unit-header').forEach(header => {
    header.addEventListener('click', (e) => {
      if (e.target.closest('.unit-check')) return; // el checkbox té la seva pròpia lògica
      const unit = Number(header.dataset.unitHeader);
      handlers.onToggleExpand(unit);
    });
  });
}
