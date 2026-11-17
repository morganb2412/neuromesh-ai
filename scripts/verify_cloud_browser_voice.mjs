/** Real deployed Cloud TTS playback and PCM-driven face smoke check. */
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { chromium } from 'playwright';

const repo = resolve(import.meta.dirname, '..');
const terraformDir = resolve(repo, 'infrastructure/terraform');
const terraform = resolve(repo, '.local/bin/terraform');
const output = name => execFileSync(terraform, ['output', '-raw', name], {
  cwd: terraformDir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
}).trim();
const url = output('app_url');
const token = output('operator_token');
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.addInitScript(() => {
    const original = AnalyserNode.prototype.getByteTimeDomainData;
    window.__neuromeshPcmFrames = 0;
    AnalyserNode.prototype.getByteTimeDomainData = function (array) {
      original.call(this, array);
      if (Array.from(array).some(value => Math.abs(value - 128) > 3))
        window.__neuromeshPcmFrames++;
    };
  });
  let speechStatus = 0;
  page.on('response', response => {
    if (response.url().endsWith('/api/speech')) speechStatus = response.status();
  });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.locator('.holo-canvas canvas').waitFor();
  await page.getByTitle('Settings').click();
  await page.locator('.settings-token input[type="password"]').fill(token);
  await page.getByRole('button', { name: 'Close settings' }).click();
  await page.getByTitle('Toggle voice mode').click();
  await page.getByTitle('Unmute assistant').click();
  await page.getByRole('textbox', { name: 'Research question' }).fill('Find recent continual learning research');
  await page.getByTitle('Send question').click();
  await page.locator('.hologram[data-state="speaking"]').waitFor({ timeout: 90000 });
  await page.waitForFunction(() => window.__neuromeshPcmFrames > 5, undefined, { timeout: 15000 });
  const frames = await page.evaluate(() => window.__neuromeshPcmFrames);
  await page.getByTitle('Stop speaking or investigating').click();
  await page.locator('.hologram[data-state="interrupted"]').waitFor();
  if (speechStatus !== 200 || frames <= 5) throw Error('Cloud speech did not drive PCM animation');
  console.log(JSON.stringify({ url, speechStatus, nonzeroPcmFrames: frames, interruption: true }));
} finally {
  await browser.close();
}
