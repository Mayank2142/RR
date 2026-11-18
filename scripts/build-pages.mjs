import { mkdir, copyFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

// Build the self-contained React dashboard with the current snapshot and downloads.
await import('./build_offline_shortlist.mjs');

const root = fileURLToPath(new URL('..', import.meta.url));
const site = resolve(root, 'site');
await mkdir(site, { recursive: true });
await Promise.all([
  copyFile(resolve(root, 'output/shortlist/SupeRR_Shortlist_Dashboard.html'), resolve(site, 'index.html')),
  copyFile(resolve(root, 'output/pdf/SupeRR_Screenshot_Shortlist_Report.pdf'), resolve(site, 'report.pdf')),
  copyFile(resolve(root, 'output/shortlist/Shortlist_Form_Selections.csv'), resolve(site, 'selections.csv')),
  writeFile(resolve(site, '.nojekyll'), ''),
]);
console.log(`GitHub Pages files prepared in ${site}`);
