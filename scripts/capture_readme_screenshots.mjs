/** Capture real Cloud Run screens for the public README without exposing the operator token. */
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { chromium } from 'playwright';

const root = resolve(import.meta.dirname, '..');
const terraform = resolve(root, '.local/bin/terraform');
const terraformDir = resolve(root, 'infrastructure/terraform');
const output = name => {
  try {
    return execFileSync(terraform, ['output', '-raw', name], {
      cwd: terraformDir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
  } catch {
    return '';
  }
};
const base = process.env.NEUROMESH_APP_URL || output('app_url');
const token = process.env.NEUROMESH_ADMIN_TOKEN || output('operator_token');
if (!base.startsWith('https://')) throw new Error('Set NEUROMESH_APP_URL to the HTTPS deployment URL');

const browser = await chromium.launch({ headless: true, channel: 'chrome' });
const screenshots = [];
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  page.on('pageerror', error => errors.push(error.message));
  const capture = async name => {
    const path = resolve(root, 'docs/screenshots', `${name}.png`);
    await page.screenshot({ path, fullPage: true, animations: 'disabled' });
    screenshots.push(name);
  };
  const pageShot = async (name, tab) => {
    const endpoints = tab === 'Analytics' ? ['/api/analytics', '/api/clusters']
      : tab === 'Agents' ? ['/api/agent-executions']
      : ['LLM Lab', 'Experiments', 'Reports'].includes(tab) ? ['/api/laboratory'] : [];
    const responses = endpoints.map(endpoint => page.waitForResponse(response =>
      response.url().endsWith(endpoint) && response.status() === 200));
    await page.getByRole('button', { name: tab, exact: true }).click();
    await Promise.all(responses);
    if (tab === 'Analytics') await page.waitForFunction(() => {
      const value = document.querySelector('.analysis-grid .workspace-card b')?.textContent?.trim();
      return Boolean(value && value !== '—');
    });
    if (['LLM Lab', 'Experiments', 'Reports'].includes(tab)) await page.waitForFunction(() =>
      !document.body.innerText.includes('Loading recorded laboratory state'));
    await page.waitForTimeout(350);
    await capture(name);
  };

  await page.goto(base, { waitUntil: 'networkidle' });
  await page.locator('.graph-stage canvas').waitFor();
  await page.locator('.holo-canvas canvas').waitFor();
  await page.waitForTimeout(1600);
  await page.locator('.guest-access').waitFor();
  await capture('observatory-home');
  await pageShot('research', 'Research');
  await pageShot('pipelines', 'Pipelines');
  await pageShot('analytics', 'Analytics');

  if (token) {
    await page.getByRole('button', { name: 'Admin', exact: true }).click();
    await page.getByLabel('OPERATOR TOKEN').fill(token);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByRole('button', { name: 'Admin active' }).waitFor();
    await page.getByRole('button', { name: 'Observatory', exact: true }).click();
    await page.getByRole('textbox', { name: 'Research question' }).fill('Find continual learning research');
    await page.getByTitle('Send question').click();
    await page.locator('.investigation-state').getByText(/cited records/).waitFor({ timeout: 30000 });
    await page.locator('.message.assistant a').first().waitFor();
    await page.waitForTimeout(700);
    await capture('observatory-admin');

    await page.getByRole('button', { name: 'Admin active' }).click();
    await page.locator('.admin-panel').waitFor();
    await capture('admin-controls');
    await page.getByRole('button', { name: 'Close admin panel' }).click();
    await pageShot('llm-lab', 'LLM Lab');
    await pageShot('experiments', 'Experiments');
    await pageShot('agents', 'Agents');
    await pageShot('reports', 'Reports');
  }
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  console.log(JSON.stringify({ url: base, screenshots, browserErrors: 0 }));
} finally {
  await browser.close();
}
