"""Build the compact CC0 MakeHuman head used by the Observatory avatar.

The checked-in binary has a quad-edge grid, surface triangles, eye triangles,
and a smooth lower-face weight for audio-driven jaw motion. It contains no
textures or identifying likeness. Rebuild with Python 3 and network access.
"""
from __future__ import annotations

import hashlib
import argparse
import struct
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'apps/web/public/assets/hologram-head.bin'
REVISION = '1f508f6083b2f823dab15de924b3bde72e08d77c'
SOURCE = f'https://raw.githubusercontent.com/makehumancommunity/makehuman/{REVISION}/makehuman/data'
FILES = {
    'base.obj': ('3dobjs/base.obj', '8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c'),
    'male.target': ('targets/macrodetails/caucasian-male-young.target', '70e228ba7164737dae664454394536fc5935fa48d333c1a97d77e2dc6eacc5f5'),
}


def source_bytes(name: str, local_path: Path | None = None) -> bytes:
    path, expected = FILES[name]
    if local_path is not None:
        data = local_path.read_bytes()
    else:
        with urllib.request.urlopen(f'{SOURCE}/{path}', timeout=30) as response:
            data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise RuntimeError(f'{name} hash mismatch: {actual}')
    return data


def smoothstep(low: float, high: float, value: float) -> float:
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def build(obj: bytes, target: bytes) -> bytes:
    original: list[tuple[float, float, float]] = []
    groups: dict[str, list[list[int]]] = {}
    group = ''
    for line in obj.decode().splitlines():
        if line.startswith('v '):
            original.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith('g '):
            group = line[2:]
        elif line.startswith('f '):
            groups.setdefault(group, []).append([int(token.split('/')[0]) - 1 for token in line.split()[1:]])

    positions = [list(vertex) for vertex in original]
    for line in target.decode().splitlines():
        if not line or line.startswith('#'):
            continue
        index, dx, dy, dz = line.split()
        vertex = positions[int(index)]
        vertex[0] += float(dx)
        vertex[1] += float(dy)
        vertex[2] += float(dz)

    # The body group is continuous; retain complete quads above the upper neck.
    surface = [face for face in groups['body'] if all(original[index][1] >= 6.0 for index in face)]
    body_indices = {index for face in surface for index in face}
    eyes = groups['helper-l-eye'] + groups['helper-r-eye']
    selected = sorted({index for face in surface + eyes for index in face})
    remap = {source: output for output, source in enumerate(selected)}
    head_y = [positions[index][1] for face in surface for index in face]
    center_y = (min(head_y) + max(head_y)) / 2.0
    scale, center_z = 0.82, 0.64

    coordinates: list[float] = []
    jaw_weights: list[float] = []
    for index in selected:
        x, y, z = positions[index]
        coordinates.extend((x * scale, (y - center_y) * scale, (z - center_z) * scale))
        old_x, old_y, old_z = original[index]
        jaw_weights.append(smoothstep(7.08, 6.42, old_y) * smoothstep(0.12, 0.65, old_z) if index in body_indices else 0.0)

    triangles: list[int] = []
    edges: set[tuple[int, int]] = set()
    for face in surface:
        mapped = [remap[index] for index in face]
        for i in range(1, len(mapped) - 1):
            triangles.extend((mapped[0], mapped[i], mapped[i + 1]))
        for a, b in zip(mapped, mapped[1:] + mapped[:1]):
            edges.add((min(a, b), max(a, b)))
    eye_triangles: list[int] = []
    for face in eyes:
        mapped = [remap[index] for index in face]
        for i in range(1, len(mapped) - 1):
            eye_triangles.extend((mapped[0], mapped[i], mapped[i + 1]))
    edge_indices = [index for edge in sorted(edges) for index in edge]
    if len(selected) >= 65536:
        raise RuntimeError('Head exceeds 16-bit index range')
    header = struct.pack('<4sIIII', b'NMH1', len(selected), len(triangles), len(edge_indices), len(eye_triangles))
    return b''.join((
        header,
        struct.pack(f'<{len(coordinates)}f', *coordinates),
        struct.pack(f'<{len(jaw_weights)}f', *jaw_weights),
        struct.pack(f'<{len(triangles)}H', *triangles),
        struct.pack(f'<{len(edge_indices)}H', *edge_indices),
        struct.pack(f'<{len(eye_triangles)}H', *eye_triangles),
    ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-obj', type=Path)
    parser.add_argument('--male-target', type=Path)
    args = parser.parse_args()
    obj = source_bytes('base.obj', args.base_obj)
    target = source_bytes('male.target', args.male_target)
    binary = build(obj, target)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(binary)
    print(f'{OUTPUT.relative_to(ROOT)}: {len(binary)} bytes, SHA-256 {hashlib.sha256(binary).hexdigest()}')
