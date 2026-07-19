/* utils.js — utilitats sense estat (portat de pd-main).
   Exposa (globals): escHtml(s), fetchJson(url, opts). */

/* Escapa text per inserir-lo de manera segura dins de HTML. */
function escHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

/* Llegeix un JSON. `opts` es passa tal qual a fetch (p. ex. { cache: 'no-store' }).
   Retorna l'objecte parsejat o null si falla. */
async function fetchJson(url, opts) {
  try {
    const r = await fetch(url, opts);
    if (!r.ok) return null;
    return await r.json();
  } catch (_) {
    return null;
  }
}
