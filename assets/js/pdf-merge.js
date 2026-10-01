/* pdf-merge.js — fusió de PDFs en el navegador amb pdf-lib (vendored a
   assets/lib/pdf-lib.min.js, sense CDN, seguint el mateix patró que
   pd-main vendoritza mammoth.browser.min.js).
   Exposa (global): mergeSelected(fileUrls, pageLimits) -> Promise<Blob>

   pageLimits (opcional) va en paral·lel a fileUrls: per a cada fitxer, el
   nombre de pàgines inicials que cal copiar (null/undefined = totes). Es fa
   servir per treure el full de solucions quan el botó SOL està desactivat. */

async function mergeSelected(fileUrls, pageLimits = []) {
  const { PDFDocument } = PDFLib;
  const merged = await PDFDocument.create();

  for (let i = 0; i < fileUrls.length; i++) {
    const url = fileUrls[i];
    const bytes = await fetch(url, { cache: 'force-cache' }).then(r => {
      if (!r.ok) throw new Error(`No s'ha pogut carregar ${url} (HTTP ${r.status})`);
      return r.arrayBuffer();
    });
    const src = await PDFDocument.load(bytes);
    let indices = src.getPageIndices();
    const limit = pageLimits[i];
    if (limit != null && limit > 0) indices = indices.slice(0, limit);
    const pages = await merged.copyPages(src, indices);
    pages.forEach(p => merged.addPage(p));
  }

  const mergedBytes = await merged.save();
  return new Blob([mergedBytes], { type: 'application/pdf' });
}
