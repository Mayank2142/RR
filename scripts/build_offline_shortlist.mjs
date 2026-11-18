import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const root = fileURLToPath(new URL('..', import.meta.url));
const { outputFiles } = await build({
  absWorkingDir: root,
  entryPoints: ['frontend/src/shortlist-standalone.tsx'],
  outfile: 'shortlist.js',
  bundle: true, format: 'iife', minify: true, write: false,
  define: {'process.env.NODE_ENV': '"production"'},
  jsx: 'automatic', target: ['chrome110', 'firefox115', 'safari16'],
});
const contents = ext => {
  const item = outputFiles.find(f => f.path.endsWith(ext));
  if (!item) throw new Error(`Missing bundled ${ext} asset`);
  return item.text;
};
const [json, csv, pdf] = await Promise.all([
  readFile(resolve(root, 'output/shortlist/shortlist.json'), 'utf8'),
  readFile(resolve(root, 'output/shortlist/Shortlist_Form_Selections.csv')),
  readFile(resolve(root, 'output/pdf/SupeRR_Screenshot_Shortlist_Report.pdf')),
]);
const snapshot = json.replaceAll('<', '\\u003c');
const photos = await Promise.all(['team', 'royals-palace', 'celebration', 'squad'].map(async name => {
  const bytes = await readFile(resolve(root, `frontend/public/rr/${name}.png`));
  return `<script id="sl-photo-${name}" type="text/plain">data:image/png;base64,${bytes.toString('base64')}</script>`;
}));
const bundle = contents('.js').replace(/<\/script/gi, '<\\/script');
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Local Rajasthan Royals pressure shortlist from the supplied data">
<title>SupeRR | Pressure shortlist</title>
<style>*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit}button,a,input,select{-webkit-tap-highlight-color:transparent}${contents('.css')}</style>
</head><body><div id="root"></div>
<script id="sl-snapshot" type="application/json">${snapshot}</script>
<script id="sl-report" type="application/octet-stream">${pdf.toString('base64')}</script>
<script id="sl-selections" type="application/octet-stream">${csv.toString('base64')}</script>
${photos.join('\n')}
<script>${bundle}</script>
</body></html>`;
const dest = resolve(root, 'output/shortlist/SupeRR_Shortlist_Dashboard.html');
await writeFile(dest, html);
console.log(dest);
