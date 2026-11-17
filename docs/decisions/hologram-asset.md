# Holographic head asset

The Observatory assistant uses the MakeHuman base mesh and the `caucasian-male-young` shape target, pinned to MakeHuman revision `1f508f6083b2f823dab15de924b3bde72e08d77c`. MakeHuman's core graphical assets are [CC0](https://www.makehumancommunity.org/about/license.html), so the derived mesh can be distributed in this public repository. The avatar has no texture, skin, or identifying likeness.

`scripts/build_hologram_head.py` validates the SHA-256 of both upstream files, applies the target, and exports only the upper neck, head, and helper eye surfaces to `apps/web/public/assets/hologram-head.bin`. The export retains 4,388 vertices and 8,463 **quad topology** edges. Rendering those edges avoids the triangle diagonals of a standard Three.js wireframe. The binary is 156,400 bytes; SHA-256 `0a0e8aceef23df57188c0f842506e29bea1762a22bc069e90a58185b58af8321`.

Source files:

- [`base.obj`](https://github.com/makehumancommunity/makehuman/blob/1f508f6083b2f823dab15de924b3bde72e08d77c/makehuman/data/3dobjs/base.obj), SHA-256 `8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c`
- [`caucasian-male-young.target`](https://github.com/makehumancommunity/makehuman/blob/1f508f6083b2f823dab15de924b3bde72e08d77c/makehuman/data/targets/macrodetails/caucasian-male-young.target), SHA-256 `70e228ba7164737dae664454394536fc5935fa48d333c1a97d77e2dc6eacc5f5`

Rebuild with `python3 scripts/build_hologram_head.py`. The viewer loads the checked-in binary and renders a dark surface, luminous quad edges, and integrated eye surfaces. A lower-face weight moves the jaw and grid together using the existing speech amplitude state. Cloud TTS supplies measured PCM amplitude; browser speech uses word-boundary timing. This is approximate jaw synchronization, not phoneme-level lip sync. Speech movement stops when playback stops or is interrupted.
