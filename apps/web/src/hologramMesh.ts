import * as THREE from 'three';

export type HologramMesh = {
  surface: THREE.BufferGeometry;
  grid: THREE.BufferGeometry;
  eyes: THREE.BufferGeometry;
  vertexCount: number;
  edgeCount: number;
};

/** The compact, pinned CC0 MakeHuman asset is documented in docs/decisions/hologram-asset.md. */
export async function loadHologramMesh(url = '/assets/hologram-head.bin'): Promise<HologramMesh> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Hologram asset HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  const view = new DataView(bytes);
  if (bytes.byteLength < 20 || String.fromCharCode(...new Uint8Array(bytes, 0, 4)) !== 'NMH1') {
    throw new Error('Invalid hologram asset header');
  }
  const vertexCount = view.getUint32(4, true);
  const triangleCount = view.getUint32(8, true);
  const edgeIndexCount = view.getUint32(12, true);
  const eyeTriangleCount = view.getUint32(16, true);
  const expected = 20 + vertexCount * 16 + (triangleCount + edgeIndexCount + eyeTriangleCount) * 2;
  if (!vertexCount || vertexCount > 65535 || !triangleCount || !edgeIndexCount ||
      edgeIndexCount % 2 || triangleCount % 3 || eyeTriangleCount % 3 || expected !== bytes.byteLength) {
    throw new Error('Invalid hologram asset dimensions');
  }
  let offset = 20;
  const positions = new Float32Array(bytes.slice(offset, offset += vertexCount * 12));
  const jawWeights = new Float32Array(bytes.slice(offset, offset += vertexCount * 4));
  const triangles = new Uint16Array(bytes.slice(offset, offset += triangleCount * 2));
  const edges = new Uint16Array(bytes.slice(offset, offset += edgeIndexCount * 2));
  const eyeTriangles = new Uint16Array(bytes.slice(offset, offset + eyeTriangleCount * 2));
  for (const indices of [triangles, edges, eyeTriangles]) {
    if (indices.some(index => index >= vertexCount)) throw new Error('Invalid hologram asset index');
  }

  const attributes = () => ({
    position: new THREE.BufferAttribute(positions, 3),
    jawWeight: new THREE.BufferAttribute(jawWeights, 1),
  });
  const surface = new THREE.BufferGeometry();
  const grid = new THREE.BufferGeometry();
  const eyes = new THREE.BufferGeometry();
  for (const geometry of [surface, grid, eyes]) {
    const { position, jawWeight } = attributes();
    geometry.setAttribute('position', position);
    geometry.setAttribute('jawWeight', jawWeight);
  }
  surface.setIndex(new THREE.BufferAttribute(triangles, 1));
  grid.setIndex(new THREE.BufferAttribute(edges, 1));
  eyes.setIndex(new THREE.BufferAttribute(eyeTriangles, 1));
  surface.computeVertexNormals();
  eyes.computeVertexNormals();
  for (const geometry of [surface, grid, eyes]) geometry.computeBoundingSphere();
  return { surface, grid, eyes, vertexCount, edgeCount: edgeIndexCount / 2 };
}
