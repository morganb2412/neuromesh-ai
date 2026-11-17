import { afterEach, expect, test, vi } from 'vitest';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { loadHologramMesh } from '../src/hologramMesh';

afterEach(() => vi.unstubAllGlobals());

test('the redistributable head asset retains dense anatomical quad topology', async () => {
  const path = fileURLToPath(new URL('../public/assets/hologram-head.bin', import.meta.url));
  const bytes = await readFile(path);
  vi.stubGlobal('fetch', async () => ({ ok: true, arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) }));
  const mesh = await loadHologramMesh();
  expect(mesh.vertexCount).toBe(4388);
  expect(mesh.edgeCount).toBe(8463);
  expect(mesh.eyes.index?.count).toBe(840);
  const weights = mesh.surface.getAttribute('jawWeight');
  expect(Array.from({ length: weights.count }, (_, i) => weights.getX(i)).some(weight => weight > 0.9)).toBe(true);
  for (const geometry of [mesh.surface, mesh.grid, mesh.eyes]) geometry.dispose();
});

test('rejects a truncated mesh before handing it to WebGL', async () => {
  vi.stubGlobal('fetch', async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(20) }));
  await expect(loadHologramMesh()).rejects.toThrow('Invalid hologram asset');
});
