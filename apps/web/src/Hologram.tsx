import { Canvas, useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { loadHologramMesh, type HologramMesh } from './hologramMesh';
import type { AvatarState } from './types';

type Props = { state: AvatarState; speechLevel: number; reducedMotion: boolean };

const vertex = /* glsl */ `
  attribute float jawWeight;
  uniform float uJaw;
  uniform float uTime;
  uniform float uEnergy;
  varying vec3 vPosition;
  varying vec3 vNormal;
  varying float vPulse;
  void main() {
    vec3 p = position;
    p.y -= jawWeight * uJaw * 0.21;
    p.z += jawWeight * uJaw * 0.055;
    vPosition = p;
    vNormal = normalize(normalMatrix * normal);
    vPulse = pow(max(0.0, sin(p.y * 10.0 - uTime * 2.3)), 22.0) * uEnergy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`;

const lineVertex = /* glsl */ `
  attribute float jawWeight;
  uniform float uJaw;
  uniform float uTime;
  uniform float uEnergy;
  varying float vPulse;
  varying float vFront;
  void main() {
    vec3 p = position;
    p.y -= jawWeight * uJaw * 0.21;
    p.z += jawWeight * uJaw * 0.055;
    vFront = smoothstep(-0.42, 0.48, p.z);
    vPulse = pow(max(0.0, sin(p.y * 13.0 - uTime * 2.4)), 25.0) * uEnergy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }
`;

function makeSurfaceMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uJaw: { value: 0 }, uTime: { value: 0 }, uEnergy: { value: 0.2 } },
    vertexShader: vertex,
    fragmentShader: /* glsl */ `
      uniform float uEnergy;
      varying vec3 vPosition;
      varying vec3 vNormal;
      varying float vPulse;
      void main() {
        float facing = abs(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)));
        float rim = pow(1.0 - facing, 2.5);
        float front = smoothstep(-0.50, 0.55, vPosition.z);
        float scan = pow(max(0.0, sin(vPosition.y * 58.0)), 28.0) * 0.045;
        vec3 color = vec3(0.009, 0.035, 0.063) + vec3(0.06, 0.27, 0.39) * rim +
          vec3(0.09, 0.29, 0.43) * (vPulse + scan) * front * (0.4 + uEnergy);
        gl_FragColor = vec4(color, 0.97);
      }
    `,
    side: THREE.DoubleSide, transparent: true, depthWrite: true,
  });
}

function makeGridMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uJaw: { value: 0 }, uTime: { value: 0 }, uEnergy: { value: 0.2 } },
    vertexShader: lineVertex,
    fragmentShader: /* glsl */ `
      varying float vPulse;
      varying float vFront;
      void main() {
        vec3 silver = vec3(0.61, 0.79, 0.85);
        vec3 cyan = vec3(0.23, 0.72, 0.99);
        gl_FragColor = vec4(mix(silver, cyan, min(1.0, vPulse * 1.5)),
          0.43 + vFront * 0.48 + vPulse * 0.08);
      }
    `,
    transparent: true, depthWrite: false, depthTest: true,
  });
}

function makeEyeMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uJaw: { value: 0 }, uTime: { value: 0 }, uEnergy: { value: 0.2 }, uGaze: { value: new THREE.Vector2() } },
    vertexShader: vertex,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform float uEnergy;
      uniform vec2 uGaze;
      varying vec3 vPosition;
      varying vec3 vNormal;
      varying float vPulse;
      void main() {
        float side = sign(vPosition.x);
        vec2 eye = vec2((abs(vPosition.x) - 0.24 - uGaze.x * side) / 0.112,
                        (vPosition.y - 0.16 - uGaze.y) / 0.106);
        float r = length(eye);
        float iris = 1.0 - smoothstep(0.52, 0.85, r);
        float pupil = 1.0 - smoothstep(0.17, 0.31, r);
        float halo = 1.0 - smoothstep(0.78, 1.32, r);
        float glint = exp(-length(eye - vec2(-0.22, 0.24)) * 13.0);
        float flicker = 0.92 + 0.05 * sin(uTime * 2.2);
        vec3 color = vec3(0.012, 0.07, 0.12) + vec3(0.05, 0.25, 0.48) * halo +
          vec3(0.16, 0.68, 1.0) * iris * (0.62 + 0.33 * uEnergy) * flicker;
        color *= 1.0 - pupil * 0.78;
        color += vec3(0.5, 0.9, 1.0) * glint * 0.7;
        gl_FragColor = vec4(color, 1.0);
      }
    `,
    side: THREE.DoubleSide, depthWrite: true,
  });
}

function Head({ state, speechLevel, reducedMotion }: Props) {
  const [asset, setAsset] = useState<HologramMesh | null>(null);
  const head = useRef<THREE.Group>(null);
  const jaw = useRef(0);
  const energy = useRef(0.2);
  const surfaceMaterial = useMemo(makeSurfaceMaterial, []);
  const gridMaterial = useMemo(makeGridMaterial, []);
  const eyeMaterial = useMemo(makeEyeMaterial, []);

  useEffect(() => {
    let mounted = true;
    let loaded: HologramMesh | null = null;
    loadHologramMesh().then(mesh => {
      if (mounted) { loaded = mesh; setAsset(mesh); }
      else for (const geometry of [mesh.surface, mesh.grid, mesh.eyes]) geometry.dispose();
    }).catch(error => console.error('Hologram mesh failed to load', error));
    return () => {
      mounted = false;
      if (loaded) for (const geometry of [loaded.surface, loaded.grid, loaded.eyes]) geometry.dispose();
    };
  }, []);
  useEffect(() => () => {
    surfaceMaterial.dispose(); gridMaterial.dispose(); eyeMaterial.dispose();
  }, [surfaceMaterial, gridMaterial, eyeMaterial]);

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();
    const active = state === 'listening' || state === 'thinking' || state === 'retrieving' || state === 'speaking';
    energy.current = THREE.MathUtils.damp(energy.current, state === 'retrieving' ? 1 : active ? 0.72 : 0.25, 3.5, delta);
    // Cloud playback supplies measured PCM amplitude; browser speech supplies word-boundary timing.
    jaw.current = THREE.MathUtils.damp(jaw.current,
      state === 'speaking' ? THREE.MathUtils.clamp(speechLevel * 1.3, 0, 1) : 0, 17, delta);
    for (const material of [surfaceMaterial, gridMaterial, eyeMaterial]) {
      material.uniforms.uJaw.value = jaw.current;
      material.uniforms.uTime.value = reducedMotion ? 0 : t;
      material.uniforms.uEnergy.value = energy.current;
    }
    eyeMaterial.uniforms.uGaze.value.set(
      reducedMotion ? 0 : Math.sin(t * 0.39) * 0.007,
      reducedMotion ? 0 : Math.sin(t * 0.31) * 0.004,
    );
    if (head.current) {
      const yaw = reducedMotion ? 0 : state === 'listening' ? 0.015 : Math.sin(t * 0.31) * 0.085;
      const tilt = reducedMotion ? 0 : state === 'thinking' ? -0.045 : Math.sin(t * 0.23) * 0.018;
      const nod = reducedMotion ? 0 : state === 'speaking' ? Math.sin(t * 1.8) * 0.014 * jaw.current : Math.sin(t * 0.27) * 0.01;
      head.current.rotation.y = THREE.MathUtils.damp(head.current.rotation.y, yaw, 2, delta);
      head.current.rotation.z = THREE.MathUtils.damp(head.current.rotation.z, tilt, 2, delta);
      head.current.rotation.x = THREE.MathUtils.damp(head.current.rotation.x, nod, 2, delta);
    }
  });

  return asset ? <group ref={head} position={[0, -0.02, 0]}>
    <mesh geometry={asset.surface} material={surfaceMaterial} renderOrder={0} />
    <mesh geometry={asset.eyes} material={eyeMaterial} renderOrder={1} />
    <lineSegments geometry={asset.grid} material={gridMaterial} renderOrder={2} />
  </group> : null;
}

export function Hologram({ state, speechLevel, reducedMotion }: Props) {
  return <div className="hologram" data-state={state}>
    <div className="holo-top"><span>NEUROMESH // ASSISTANT</span><span className="holo-pulse">● {state.toUpperCase()}</span></div>
    <div className="holo-canvas">
      <Canvas camera={{ position: [0, 0.04, 3.95], fov: 37 }} dpr={[1, 1.5]} gl={{ alpha: true, antialias: true, powerPreference: 'low-power' }}>
        <Head state={state} speechLevel={speechLevel} reducedMotion={reducedMotion} />
      </Canvas>
      <div className="holo-scan" />
    </div>
    <div className="holo-bottom"><span className="mini-bars">▂ ▅ ▃ ▇ ▄ ▆ ▂</span><span>{state === 'speaking' ? 'AUDIO OUTPUT ACTIVE' : state === 'retrieving' ? 'EVIDENCE TRAVERSAL' : 'RESEARCH INTERFACE READY'}</span></div>
  </div>;
}
