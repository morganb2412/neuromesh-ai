import { chromium } from 'playwright';
import { resolve } from 'node:path';
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const errors=[]; page.on('pageerror', e=>errors.push(e.message));
  await page.goto(process.env.NEUROMESH_WEB_URL || 'http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
  await page.locator('.graph-stage canvas').waitFor();
  await page.locator('.holo-canvas canvas').waitFor();
  await page.waitForTimeout(1800);
  const output=resolve(process.env.NEUROMESH_SCREENSHOT_PATH || 'docs/screenshots/observatory-home.png');
  await page.screenshot({ path: output, fullPage: true });
  console.log(JSON.stringify({output, title:await page.title(), canvasCount:await page.locator('canvas').count(), errors}));
  if(errors.length)process.exitCode=1;
} finally { await browser.close(); }
