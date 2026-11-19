// Captura headless: chama SIM.render(ação, frame, n, vista) para cada frame e salva PNG.
import {chromium} from 'playwright';
import fs from 'node:fs';

const molde = JSON.parse(fs.readFileSync('molde_referencia.json', 'utf8'));
const VIEWS = ['S', 'SW', 'W', 'NW', 'N'];
fs.mkdirSync('frames3d', {recursive: true});

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM || undefined,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage();
page.on('console', (m) => console.log('[page]', m.text()));
page.on('pageerror', (e) => console.log('[err]', e.message));
await page.goto('http://127.0.0.1:8765/scene.html');
await page.waitForFunction(() => window.READY === true, null, {timeout: 30000});

let count = 0;
for (const [action, info] of Object.entries(molde.acoes)) {
  const n = info.frames;
  for (const view of VIEWS) {
    for (let k = 0; k < n; k++) {
      const url = await page.evaluate(([a, k, n, v]) => window.SIM.render(a, k, n, v), [action, k, n, view]);
      fs.writeFileSync(`frames3d/${action}_${view}_${String(k).padStart(2, '0')}.png`, Buffer.from(url.split(',')[1], 'base64'));
      count++;
    }
  }
}
console.log('frames:', count);
await browser.close();
