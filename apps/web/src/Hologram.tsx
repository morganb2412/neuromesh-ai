import { Canvas, useFrame } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { AvatarState } from './types';

function Head({ state, speechLevel, reducedMotion }: { state: AvatarState; speechLevel: number; reducedMotion: boolean }) {
  const group=useRef<THREE.Group>(null), jaw=useRef<THREE.Mesh>(null), halo=useRef<THREE.Mesh>(null);
  const particles=useMemo(()=>{let s=1846;const r=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296};return Array.from({length:140},()=>[(r()-.5)*2.5,(r()-.5)*3.2,(r()-.5)*1.7] as [number,number,number])},[]);
  const active=state==='thinking'||state==='retrieving'||state==='speaking'||state==='listening';
  useFrame(({clock},delta)=>{
    const t=clock.getElapsedTime();
    if(group.current&&!reducedMotion){group.current.rotation.y=THREE.MathUtils.lerp(group.current.rotation.y,state==='listening'?.02:Math.sin(t*.29)*.18,.05);group.current.rotation.z=Math.sin(t*.43)*.035;group.current.position.y=Math.sin(t*.55)*.035;}
    if(jaw.current)jaw.current.position.y=THREE.MathUtils.lerp(jaw.current.position.y,-.70-(state==='speaking'?speechLevel*.24:0),Math.min(1,delta*18));
    if(halo.current&&!reducedMotion)halo.current.rotation.z+=delta*(active?.25:.08);
  });
  const lineColor=active?'#62e2ff':'#318eae';
  return <group ref={group} position={[0,-.14,0]}>
    <mesh position={[0,-1.20,-.04]} rotation={[0,0,Math.PI]}><cylinderGeometry args={[.42,.7,.95,8]}/><meshPhysicalMaterial color="#07111b" metalness={.62} roughness={.3} emissive="#083147" emissiveIntensity={.4}/></mesh>
    <mesh position={[0,.20,0]} scale={[.88,1.09,.72]}><sphereGeometry args={[1,12,10]}/><meshPhysicalMaterial color="#08101b" metalness={.68} roughness={.22} transparent opacity={.91} side={THREE.DoubleSide}/></mesh>
    <mesh position={[0,.20,0]} scale={[.895,1.10,.735]}><sphereGeometry args={[1,14,12]}/><meshBasicMaterial color={lineColor} wireframe transparent opacity={active?.23:.13}/></mesh>
    <mesh ref={jaw} position={[0,-.7,.12]} scale={[.66,.40,.59]}><sphereGeometry args={[1,8,5,0,Math.PI*2,0,Math.PI/2]}/><meshPhysicalMaterial color="#07101a" metalness={.8} roughness={.25} emissive="#0d6886" emissiveIntensity={active?.45:.17}/></mesh>
    <Line points={[[-.65,-.2,.35],[-.47,-.51,.47],[-.27,-.84,.49],[0,-.99,.43],[.27,-.84,.49],[.47,-.51,.47],[.65,-.2,.35]]} color={lineColor} transparent opacity={.72} lineWidth={1}/>
    <Line points={[[-.67,.27,.42],[-.32,.18,.66],[-.07,.24,.72],[.08,.22,.71],[.32,.18,.66],[.67,.27,.42]]} color="#3dcdf5" transparent opacity={.50} lineWidth={1}/>
    <Line points={[[-.70,.1,.25],[-.49,.42,.51],[-.28,.73,.49],[-.08,.92,.22],[.1,.97,.1],[.38,.79,.32],[.65,.39,.36]]} color="#42bce8" transparent opacity={.46} lineWidth={1}/>
    <mesh position={[-.35,.1,.60]} scale={[.18,.023,.022]}><boxGeometry/><meshBasicMaterial color="#46d7ff" transparent opacity={active?.75:.3}/></mesh>
    <mesh position={[.35,.1,.60]} scale={[.18,.023,.022]}><boxGeometry/><meshBasicMaterial color="#46d7ff" transparent opacity={active?.75:.3}/></mesh>
    <mesh ref={halo} position={[0,.05,-.4]} rotation={[Math.PI/2,0,0]}><torusGeometry args={[1.44,.006,4,90]}/><meshBasicMaterial color="#32badd" transparent opacity={.35}/></mesh>
    <mesh position={[0,.05,-.38]} rotation={[Math.PI/2,0,0]}><torusGeometry args={[1.69,.003,4,90]}/><meshBasicMaterial color="#267394" transparent opacity={.38}/></mesh>
    {particles.map((p,i)=><mesh key={i} position={p} scale={i%6===0?.016:.008}><sphereGeometry args={[1,4,4]}/><meshBasicMaterial color={i%5===0?'#b9faff':'#3ec9f0'} transparent opacity={active?.8:.35}/></mesh>)}
  </group>;
}

export function Hologram({state,speechLevel,reducedMotion}:{state:AvatarState;speechLevel:number;reducedMotion:boolean}) {
  return <div className="hologram" data-state={state}>
    <div className="holo-top"><span>NEUROMESH // ASSISTANT</span><span className="holo-pulse">● {state.toUpperCase()}</span></div>
    <div className="holo-canvas"><Canvas camera={{position:[0,0,4.8],fov:38}} dpr={[1,1.5]} gl={{alpha:true,antialias:true}}><ambientLight intensity={.25}/><pointLight position={[1,2,3]} color="#3dbbe9" intensity={3}/><Head state={state} speechLevel={speechLevel} reducedMotion={reducedMotion}/></Canvas><div className="holo-scan"/></div>
    <div className="holo-bottom"><span className="mini-bars">▂ ▅ ▃ ▇ ▄ ▆ ▂</span><span>{state==='speaking'?'AUDIO OUTPUT ACTIVE':state==='retrieving'?'EVIDENCE TRAVERSAL':'RESEARCH INTERFACE READY'}</span></div>
  </div>;
}
