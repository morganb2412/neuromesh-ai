/** Run browser tests against Cloud Run without printing the private operator token. */
import { execFileSync, spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const terraformDir = resolve(root, 'infrastructure/terraform');
const terraform = resolve(root, '.local/bin/terraform');
const output = name => execFileSync(terraform, ['output', '-raw', name], {
  cwd: terraformDir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
}).trim();
const url = output('app_url');
const token = output('operator_token');
if (!url.startsWith('https://') || !token) throw new Error('Live app URL or operator token unavailable');
const result = spawnSync('npm', ['run', 'test:e2e', '-w', 'apps/web'], {
  cwd: root, stdio: 'inherit', env: {
    ...process.env,
    NEUROMESH_WEB_URL: url,
    NEUROMESH_TEST_ADMIN_TOKEN: token,
    NEUROMESH_LIVE_INTEGRATION: '1',
  },
});
process.exit(result.status ?? 1);
