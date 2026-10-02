'use strict';
// Trusted local runtime paths are supplied by the operator, never by the PDF.
const fs = require('node:fs');
const path = require('node:path');
async function main() {
  const [source, destination, modulePath, chromium] = process.argv.slice(2);
  if (!source || !destination || !modulePath || !chromium) throw new Error('Expected HTML, PDF, Playwright module, Chromium executable');
  const { chromium: browserType } = require(path.resolve(modulePath));
  const browser = await browserType.launch({ executablePath: path.resolve(chromium), headless: true });
  try {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1000, height: 1400 } });
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    await page.setContent(fs.readFileSync(source, 'utf8'), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.emulateMedia({ media: 'print' });
    await page.pdf({ path: destination, format: 'A4', printBackground: true, preferCSSPageSize: true,
      displayHeaderFooter: true, headerTemplate: '<span></span>',
      footerTemplate: '<div style="font:9px sans-serif;width:100%;padding:0 18mm;color:#687b76;display:flex;justify-content:space-between"><span>Caplin Learning Pack · local study copy</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>' });
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
