/* pdf-merge.js — fusió de PDFs en el navegador amb pdf-lib (vendored a
   assets/lib/pdf-lib.min.js, sense CDN, seguint el mateix patró que
   pd-main vendoritza mammoth.browser.min.js).
   Exposa (global): mergeSelected(fileUrls) -> Promise<Blob> */

async function mergeSelected(fileUrls) {
  const { PDFDocument } = PDFLib;
  const merged = await PDFDocument.create();

  for (const url of fileUrls) {
    const bytes = await fetch(url, { cache: 'force-cache' }).then(r => {
      if (!r.ok) throw new Error(`No s'ha pogut carregar ${url} (HTTP ${r.status})`);
      return r.arrayBuffer();
    });
    const src = await PDFDocument.load(bytes);
    const pages = await merged.copyPages(src, src.getPageIndices());
    pages.forEach(p => merged.addPage(p));
  }

  const mergedBytes = await merged.save();
  return new Blob([mergedBytes], { type: 'application/pdf' });
}
