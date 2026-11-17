import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line, Stars } from '@react-three/drei';
import { useEffect, useMemo, useRef, type ComponentRef, type RefObject } from 'react';
import * as THREE from 'three';
import type { Edge, Entity, GraphData } from './types';

const COLORS: Record<string, string> = { PAPER: '#498df8', GRANT: '#f1b465', MODEL: '#a48cff', ALGORITHM: '#8cecff', INDUSTRY: '#46d4bc', REPOSITORY: '#84adfb', SCIENTIFIC_TOPIC: '#e3f4ff', RESEARCHER: '#78c8fc', ORGANIZATION: '#73bbd6' };
const KIND_ORDER = ['PAPER','GRANT','MODEL','ALGORITHM','INDUSTRY','REPOSITORY','RESEARCHER','ORGANIZATION','SCIENTIFIC_TOPIC'];
const clusterCenters = [[-9,3,0],[-4,-4,0],[3,4,-1],[9,-1,-2],[2,-6,1],[-10,-5,-1],[-5,2,1],[-1,-2,-1],[5,1,0]];
function hash(input: string) { let h=2166136261; for (let i=0;i<input.length;i++) h=Math.imul(h ^ input.charCodeAt(i),16777619); return (h>>>0)/4294967295; }
function initialPosition(node: Entity, i: number): THREE.Vector3 {
  const k = KIND_ORDER.indexOf(node.kind);
  const c = clusterCenters[k < 0 ? 2 : k];
  const a = hash(node.id + 'a') * Math.PI * 2, r = 1.2 + Math.sqrt(hash(node.id + 'r')) * 5;
  return new THREE.Vector3(c[0]+Math.cos(a)*r,c[1]+Math.sin(a)*r,c[2]+(hash(node.id+'z')-.5)*7);
}

function CameraActions({ focus, data, positions, controls, resetSignal, focusSignal, mode2d }: { focus: string | null; data: GraphData; positions: THREE.Vector3[]; controls: RefObject<ComponentRef<typeof OrbitControls> | null>; resetSignal: number; focusSignal: number; mode2d: boolean }) {
  const { camera } = useThree();
  useEffect(() => { camera.position.set(0,0,mode2d ? 38 : 31); controls.current?.target.set(0,0,0); controls.current?.update(); }, [mode2d, resetSignal, camera, controls]);
  useEffect(() => { if (!focus) return; const index=data.nodes.findIndex(n=>n.id===focus);if(index<0)return;const p=positions[index].clone().multiplyScalar(1.5);camera.position.set(p.x,p.y,p.z+15);controls.current?.target.copy(p);controls.current?.update(); }, [focus,focusSignal,data,positions,camera,controls]);
  return null;
}

function LivingNetwork({ data, positions, selected, onSelect, query, visibleKinds, visibleEdges, highlighted, highlightedEdges, paused, reducedMotion, mode2d }: {
 data: GraphData; positions: THREE.Vector3[]; selected: string | null; onSelect: (id: string) => void; query: string; visibleKinds: Set<string>; visibleEdges: Set<string>; highlighted: Set<string>; highlightedEdges: Set<string>; paused: boolean; reducedMotion: boolean; mode2d: boolean;
}) {
  const velocities = useMemo(() => data.nodes.map(() => new THREE.Vector3()), [data]);
  const nodeIndex = useMemo(() => new Map(data.nodes.map((n,i)=>[n.id,i])), [data]);
  const edgePairs = useMemo(() => data.edges.map(e=>[nodeIndex.get(e.source_id),nodeIndex.get(e.target_id),e] as const).filter(x=>x[0]!==undefined && x[1]!==undefined),[data,nodeIndex]);
  const pointRef = useRef<THREE.Points>(null);
  const edgeRef = useRef<THREE.LineSegments>(null);
  const pulseRef = useRef<THREE.Points>(null);
  const particlePositions = useMemo(()=>new Float32Array(data.nodes.length*3),[data]);
  const particleColors = useMemo(()=>new Float32Array(data.nodes.length*3),[data]);
  const linePositions = useMemo(()=>new Float32Array(edgePairs.length*6),[edgePairs]);
  const lineColors = useMemo(()=>new Float32Array(edgePairs.length*6),[edgePairs]);
  const pulsePositions = useMemo(()=>new Float32Array(Math.min(160,edgePairs.length)*3),[edgePairs]);
  const pickRef = useRef<THREE.InstancedMesh>(null);
  const pickDummy = useMemo(()=>new THREE.Object3D(),[]);
  const elapsed = useRef(0);
  const queryLower = query.toLowerCase();
  useFrame((_, delta) => {
    if (document.hidden) return;
    elapsed.current += Math.min(delta,.05);
    if (!paused && !reducedMotion) {
      const dt=Math.min(delta,.05)*32;
      for (let i=0;i<positions.length;i++) {
        const p=positions[i],v=velocities[i], n=data.nodes[i];
        const c=clusterCenters[Math.max(0,KIND_ORDER.indexOf(n.kind))];
        v.x+=(c[0]-p.x)*.0007*dt; v.y+=(c[1]-p.y)*.0007*dt; v.z+=((mode2d?0:c[2])-p.z)*.0006*dt;
        v.x+=Math.sin(elapsed.current*.25+i*2.2)*.0007*dt; v.y+=Math.cos(elapsed.current*.28+i)*.0007*dt;
      }
      for (const [ai,bi] of edgePairs) {
        const a=positions[ai!],b=positions[bi!], d=a.distanceTo(b), f=(d-3.4)*.00010*dt;
        velocities[ai!].addScaledVector(b.clone().sub(a).normalize(),f);
        velocities[bi!].addScaledVector(a.clone().sub(b).normalize(),f);
      }
      positions.forEach((p,i)=>{velocities[i].multiplyScalar(.97);p.add(velocities[i]);});
    }
    for(let i=0;i<data.nodes.length;i++) {
      const n=data.nodes[i],p=positions[i], shown=visibleKinds.has(n.kind),match=!queryLower || n.label.toLowerCase().includes(queryLower), active=selected===n.id || highlighted.has(n.id);
      particlePositions.set([p.x,p.y,mode2d?0:p.z],i*3);
      const color=new THREE.Color(COLORS[n.kind]||'#a8dfff').multiplyScalar(!shown?.02:active?2.5:match?1.2:.13);
      particleColors.set(color.toArray(),i*3);
      pickDummy.position.set(p.x,p.y,mode2d?0:p.z);pickDummy.scale.setScalar(shown?active?2.1:1.25:.001);pickDummy.updateMatrix();pickRef.current?.setMatrixAt(i,pickDummy.matrix);
    }
    if(pickRef.current) pickRef.current.instanceMatrix.needsUpdate=true;
    if(pointRef.current) { const g=pointRef.current.geometry;g.attributes.position.needsUpdate=true;g.attributes.color.needsUpdate=true; }
    edgePairs.forEach(([ai,bi,e],i)=>{
      const a=positions[ai!],b=positions[bi!], shown=visibleEdges.has(e.kind)&&visibleKinds.has(data.nodes[ai!].kind)&&visibleKinds.has(data.nodes[bi!].kind),active=highlightedEdges.has(e.id);
      linePositions.set([a.x,a.y,mode2d?0:a.z,b.x,b.y,mode2d?0:b.z],i*6);
      const color=new THREE.Color(active?'#8eefff':e.confidence==='inferred'?'#df9a68':e.demo?'#31658a':'#82c9ef').multiplyScalar(shown?active?1.5:.45:0);
      lineColors.set([...color.toArray(),...color.toArray()],i*6);
    });
    if(edgeRef.current){edgeRef.current.geometry.attributes.position.needsUpdate=true;edgeRef.current.geometry.attributes.color.needsUpdate=true;}
    for(let i=0;i<pulsePositions.length/3;i++){
      const pair=edgePairs[(i*7)%edgePairs.length]; if(!pair)continue;
      if(!visibleEdges.has(pair[2].kind)){pulsePositions.set([1000,1000,1000],i*3);continue;}
      const a=positions[pair[0]!],b=positions[pair[1]!],t=(elapsed.current*.12+i*.097)%1;
      pulsePositions.set([a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,mode2d?0:a.z+(b.z-a.z)*t],i*3);
    }
    if(pulseRef.current)pulseRef.current.geometry.attributes.position.needsUpdate=true;
  });
  return <group scale={1.5}>
    <lineSegments ref={edgeRef}><bufferGeometry><bufferAttribute attach="attributes-position" args={[linePositions,3]}/><bufferAttribute attach="attributes-color" args={[lineColors,3]}/></bufferGeometry><lineBasicMaterial vertexColors transparent opacity={.36} blending={THREE.AdditiveBlending} depthWrite={false}/></lineSegments>
    <points ref={pointRef}><bufferGeometry><bufferAttribute attach="attributes-position" args={[particlePositions,3]}/><bufferAttribute attach="attributes-color" args={[particleColors,3]}/></bufferGeometry><pointsMaterial size={.19} vertexColors sizeAttenuation transparent opacity={1} blending={THREE.AdditiveBlending} depthWrite={false}/></points>
    <points ref={pulseRef}><bufferGeometry><bufferAttribute attach="attributes-position" args={[pulsePositions,3]}/></bufferGeometry><pointsMaterial size={.055} color="#c9faff" transparent opacity={.8} blending={THREE.AdditiveBlending} depthWrite={false}/></points>
    <instancedMesh ref={pickRef} args={[undefined,undefined,data.nodes.length]} onClick={e=>{e.stopPropagation();const id=e.instanceId; if(id!==undefined)onSelect(data.nodes[id].id)}}><sphereGeometry args={[.14,6,6]}/><meshBasicMaterial transparent opacity={0} depthWrite={false}/></instancedMesh>
    {selected && (()=>{const i=nodeIndex.get(selected);if(i===undefined)return null;const p=positions[i];return <mesh position={p}><sphereGeometry args={[.36,16,16]}/><meshBasicMaterial color="#bdfaff" wireframe transparent opacity={.8}/></mesh>})()}
  </group>;
}

function AmbientField({ reducedMotion }: { reducedMotion: boolean }) {
  const ref=useRef<THREE.Points>(null);
  const vertices=useMemo(()=>{let s=789123;const rand=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296};const a=new Float32Array(2200*3);for(let i=0;i<2200;i++)a.set([(rand()-.5)*70,(rand()-.5)*40,(rand()-.5)*28],i*3);return a},[]);
  useFrame((_,d)=>{if(ref.current&&!reducedMotion&&!document.hidden)ref.current.rotation.y+=d*.002});
  return <points ref={ref}><bufferGeometry><bufferAttribute attach="attributes-position" args={[vertices,3]}/></bufferGeometry><pointsMaterial size={.026} color="#326b91" transparent opacity={.54} depthWrite={false}/></points>;
}

export function GraphScene(props: {data:GraphData;selected:string|null;onSelect:(id:string)=>void;query:string;visibleKinds:Set<string>;visibleEdges:Set<string>;highlighted:Set<string>;highlightedEdges:Set<string>;paused:boolean;reducedMotion:boolean;mode2d:boolean;resetSignal:number;focusSignal:number}) {
  const controls=useRef<ComponentRef<typeof OrbitControls>>(null);
  const positions=useMemo(()=>props.data.nodes.map(initialPosition),[props.data]);
  return <Canvas aria-label="Interactive neural knowledge graph" camera={{position:[0,0,31],fov:58}} dpr={[1,1.6]} gl={{antialias:true,alpha:true,powerPreference:'high-performance'}} onPointerMissed={()=>props.onSelect('')}>
    <color attach="background" args={['#050d19']}/><fog attach="fog" args={['#050d19',35,80]}/>
    <AmbientField reducedMotion={props.reducedMotion}/><LivingNetwork {...props} positions={positions}/><OrbitControls ref={controls} enableDamping dampingFactor={.08} minDistance={8} maxDistance={65} enablePan/>
    <CameraActions focus={props.selected} data={props.data} positions={positions} controls={controls} resetSignal={props.resetSignal} focusSignal={props.focusSignal} mode2d={props.mode2d}/>
  </Canvas>;
}
