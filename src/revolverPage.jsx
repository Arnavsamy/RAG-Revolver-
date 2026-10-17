import React, { useCallback, useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import './revolver.css'

const bots = [
  { id:'mender', name:'Mender', line:'fixes bad answers by tuning the model' },
  { id:'skill-forge', name:'Skill Forge', line:'saves what worked as a reusable skill' },
  { id:'adversary', name:'Adversary', line:'tries to break the RAG' },
  { id:'conflict-hunter', name:'Conflict Hunter', line:'finds where documents disagree' },
  { id:'recall', name:'Recall', line:'remembers notes with dates' },
  { id:'sentinel', name:'Sentinel', line:'watches pages for changes' },
]
const TAU=Math.PI*2, STEP=TAU/6, clamp=(n,a,b)=>Math.max(a,Math.min(b,n))
function clickTone(){try{const c=new(window.AudioContext||window.webkitAudioContext)(),o=c.createOscillator(),g=c.createGain();o.frequency.value=125;g.gain.setValueAtTime(.035,c.currentTime);g.gain.exponentialRampToValueAtTime(.001,c.currentTime+.055);o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+.06)}catch{}}

function Revolver({selected,onSelect,onSettle,spinSignal}){
  const mount=useRef(null), angle=useRef(Math.PI/2), velocity=useRef(0), drag=useRef(null), current=useRef(selected), signal=useRef(spinSignal)
  useEffect(()=>{signal.current=spinSignal; if(spinSignal) velocity.current=clamp(velocity.current-.12,-.14,.14)},[spinSignal])
  useEffect(()=>{
    const el=mount.current, scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(28,1,.1,100); camera.position.z=8
    const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(el.clientWidth,el.clientHeight); renderer.outputColorSpace=THREE.SRGBColorSpace; el.appendChild(renderer.domElement)
    scene.add(new THREE.HemisphereLight(0xfff7e8,0x6d2810,2.5)); const key=new THREE.DirectionalLight(0xffffff,4); key.position.set(-4,5,7); scene.add(key); const fill=new THREE.PointLight(0xff9b43,18,12); fill.position.set(4,-2,4); scene.add(fill)
    const group=new THREE.Group(); scene.add(group); const orange=new THREE.MeshStandardMaterial({color:0xd96512,metalness:.82,roughness:.22}), rim=new THREE.MeshStandardMaterial({color:0xff9c45,metalness:.9,roughness:.17}), dark=new THREE.MeshStandardMaterial({color:0x3d170d,metalness:.55,roughness:.34})
    const body=new THREE.Mesh(new THREE.CylinderGeometry(2.28,2.28,.72,96),orange); body.rotation.x=Math.PI/2; group.add(body)
    const rear=new THREE.Mesh(new THREE.CylinderGeometry(2.12,2.12,.84,96),new THREE.MeshStandardMaterial({color:0x913d0c,metalness:.8,roughness:.29})); rear.rotation.x=Math.PI/2; rear.position.z=-.08; group.add(rear)
    const edge=new THREE.Mesh(new THREE.TorusGeometry(2.26,.055,12,96),rim); edge.position.z=.39; group.add(edge); const inner=new THREE.Mesh(new THREE.TorusGeometry(2.05,.025,8,96),dark); inner.position.z=.42; group.add(inner)
    bots.forEach((_,i)=>{const a=i*STEP,x=Math.cos(a)*1.3,y=Math.sin(a)*1.3; const hole=new THREE.Mesh(new THREE.CylinderGeometry(.51,.51,.84,48),dark); hole.rotation.x=Math.PI/2; hole.position.set(x,y,.08); group.add(hole); const ring=new THREE.Mesh(new THREE.TorusGeometry(.54,.04,10,48),rim); ring.position.set(x,y,.49); group.add(ring)})
    const hub=new THREE.Mesh(new THREE.CylinderGeometry(.48,.48,.9,64),rim); hub.rotation.x=Math.PI/2; hub.position.z=.13; group.add(hub); const hubHole=new THREE.Mesh(new THREE.CylinderGeometry(.19,.19,.94,40),dark); hubHole.rotation.x=Math.PI/2; hubHole.position.z=.57; group.add(hubHole)
    const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const selectFromAngle=()=>{const raw=Math.round((Math.PI/2-angle.current)/STEP),next=((raw%6)+6)%6;if(next!==current.current){current.current=next;onSelect(next);clickTone()}}
    const down=e=>{el.setPointerCapture(e.pointerId);drag.current={x:e.clientX,last:performance.now()};velocity.current=0}, move=e=>{if(!drag.current)return;const t=performance.now(),dt=Math.max(8,t-drag.current.last),dx=e.clientX-drag.current.x,f=reduced?.35:1;angle.current+=dx*.008*f;velocity.current=clamp(dx*.008/(dt/16),-.14,.14);drag.current={x:e.clientX,last:t};selectFromAngle()}, up=e=>{drag.current=null;el.releasePointerCapture?.(e.pointerId)}, wheel=e=>{e.preventDefault();velocity.current=clamp(velocity.current-e.deltaY*.00065,-.14,.14)}
    el.addEventListener('pointerdown',down);el.addEventListener('pointermove',move);el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);el.addEventListener('wheel',wheel,{passive:false})
    let raf,last=performance.now(),settling=false; const frame=now=>{const dt=Math.min(32,now-last)/16;last=now;if(!drag.current){if(Math.abs(velocity.current)<.0025){const target=Math.PI/2-current.current*STEP,delta=((target-angle.current+Math.PI)%TAU)-Math.PI;angle.current+=delta*.12*dt;if(Math.abs(delta)<.001){angle.current=target;if(!settling){settling=true;onSettle()}}}else{settling=false;angle.current+=velocity.current*dt;velocity.current*=Math.pow(.985,dt)}}else settling=false;group.rotation.z=angle.current;selectFromAngle();renderer.render(scene,camera);raf=requestAnimationFrame(frame)};raf=requestAnimationFrame(frame)
    const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};window.addEventListener('resize',resize)
    return()=>{cancelAnimationFrame(raf);window.removeEventListener('resize',resize);el.removeEventListener('pointerdown',down);el.removeEventListener('pointermove',move);el.removeEventListener('pointerup',up);el.removeEventListener('pointercancel',up);el.removeEventListener('wheel',wheel);renderer.dispose();el.removeChild(renderer.domElement)}
  },[onSelect,onSettle])
  useEffect(()=>{current.current=selected},[selected])
  return <div className="revolver-stage"><div className="marker"/><div ref={mount} className="revolver-canvas"/><div className="drag-note">DRAG / SCROLL TO SPIN</div></div>
}

export default function RevolverPage(){const[selected,setSelected]=useState(0),[settled,setSettled]=useState(true),[open,setOpen]=useState(false),[spinSignal,setSpinSignal]=useState(0),bot=bots[selected];const choose=useCallback(i=>{setSelected(i);setSettled(false);setOpen(false)},[]);const settle=useCallback(()=>{setSettled(true);setTimeout(()=>setOpen(true),450)},[]);return <main className="revolver-page"><header><div className="logo">RAG <span>REVOLVER</span></div><nav><a>BOTS</a><a>EVALS</a><a>MODELS</a><a>ABOUT</a></nav><button className="black-button" onClick={()=>setOpen(true)}>OPEN A BOT <b>↗</b></button></header><section className="hero"><div className="pill"><i/> SIX BOTS — RUNS ON LOCALHOST</div><h1>Spin to pick<br/><em>your bot.</em></h1><p>Each bot fixes one way RAG goes wrong.</p><button className="spin-cta" onClick={()=>setSpinSignal(x=>x+1)}>SPIN THE BARREL <span>↗</span></button></section><section className="selector"><div className="labels">{bots.map((b,i)=><button key={b.id} className={i===selected?'active':''} onClick={()=>choose(i)}><span className="label-dot"/>{b.name}<small>LIVE</small></button>)}</div><Revolver selected={selected} onSelect={choose} onSettle={settle} spinSignal={spinSignal}/></section><section className={'selected-card '+(settled?'show':'')}><div><div className="card-kicker">CHAMBER 0{selected+1} / SELECTED</div><h2>{bot.name}</h2><p>{bot.line}.</p></div><button className="black-button" onClick={()=>setOpen(true)}>OPEN {bot.name.toUpperCase()} <b>↗</b></button></section>{open&&<div className="toast"><span><i/> {bot.name} is ready</span><button onClick={()=>setOpen(false)}>CLOSE ×</button></div>}<footer><span>BOTS 6 <b>—</b> ALL LIVE</span><span>RAG / REVOLVER <b>·</b> LOCAL EXPERIMENTAL SYSTEM</span></footer></main>}
