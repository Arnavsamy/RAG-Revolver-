import { useEffect, useRef, useState } from 'react'

const TAU = Math.PI * 2
const STEP = TAU / 6
const ORANGE = '#F4A04E'
const TEAL = '#1F4E52'
const PEACH = '#F3CDA3'
const BROWN = '#4A2A22'
const CREAM = '#F7F4EC'
const BOT_NAMES = ['Mender', 'Skill Forge', 'Adversary', 'Conflict Hunter', 'Recall', 'Sentinel']

function scallopedPath(radius, depth) {
  const points = []
  for (let index = 0; index < 144; index += 1) {
    const angle = (index / 144) * TAU - Math.PI / 2
    const inset = depth * Math.max(0, Math.cos(angle * 6))
    const r = radius - inset
    points.push([450 + Math.cos(angle) * r, 250 + Math.sin(angle) * r])
  }
  return `M ${points.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(' L ')} Z`
}

function clickTone() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator(); const gain = ctx.createGain()
    osc.frequency.value = 132; gain.gain.setValueAtTime(.025, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + .05)
    osc.connect(gain); gain.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + .055)
  } catch {}
}

function cloudPath(cx, cy, sx = 1, sy = 1) {
  return `M ${cx-33*sx} ${cy+1*sy} C ${cx-36*sx} ${cy-13*sy}, ${cx-27*sx} ${cy-24*sy}, ${cx-13*sx} ${cy-25*sy} C ${cx-4*sx} ${cy-36*sy}, ${cx+12*sx} ${cy-32*sy}, ${cx+16*sx} ${cy-22*sy} C ${cx+32*sx} ${cy-22*sy}, ${cx+37*sx} ${cy-10*sy}, ${cx+31*sx} ${cy+2*sy} C ${cx+35*sx} ${cy+16*sy}, ${cx+18*sx} ${cy+25*sy}, ${cx+5*sx} ${cy+20*sy} C ${cx-9*sx} ${cy+30*sy}, ${cx-31*sx} ${cy+20*sy}, ${cx-33*sx} ${cy+1*sy} Z`
}

function Chamber({ x, y }) {
  return <g>
    <circle cx={x} cy={y} r="42" fill={PEACH} stroke={TEAL} strokeWidth="2.4" />
    <circle cx={x} cy={y} r="34" fill={CREAM} stroke={TEAL} strokeWidth="1.5" />
  </g>
}

export default function SvgCylinder({ selected, onSelect, onSettle, spinKey }) {
  const [angleState, setAngleState] = useState(0)
  const angle = useRef(0); const velocity = useRef(0); const drag = useRef(null); const current = useRef(selected)
  useEffect(() => { if (spinKey) velocity.current = Math.max(-.14, Math.min(.14, velocity.current - .12)) }, [spinKey])
  useEffect(() => {
    current.current = selected
  }, [selected])
  useEffect(() => {
    let raf; let last = performance.now(); let settling = false
    const tick = now => {
      const dt = Math.min(32, now - last) / 16; last = now
      if (!drag.current) {
        if (Math.abs(velocity.current) < .0025) {
          const target = -current.current * STEP
          const delta = ((target - angle.current + Math.PI) % TAU) - Math.PI
          angle.current += delta * .12 * dt
          if (Math.abs(delta) < .001) {
            angle.current = target
            if (!settling) { settling = true; onSettle() }
          }
        } else {
          settling = false; angle.current += velocity.current * dt; velocity.current *= Math.pow(.985, dt)
        }
      } else settling = false
      const raw = Math.round(-angle.current / STEP); const next = ((raw % 6) + 6) % 6
      if (next !== current.current) { current.current = next; onSelect(next); clickTone() }
      setAngleState(angle.current); raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf)
  }, [onSelect, onSettle])
  const down = e => { e.currentTarget.setPointerCapture(e.pointerId); drag.current = { x: e.clientX, last: performance.now() }; velocity.current = 0 }
  const move = e => { if (!drag.current) return; const now = performance.now(); const dt = Math.max(8, now - drag.current.last); const dx = e.clientX - drag.current.x; angle.current += dx * .008; velocity.current = Math.max(-.14, Math.min(.14, dx * .008 / (dt / 16))); drag.current = { x: e.clientX, last: now } }
  const up = e => { drag.current = null; e.currentTarget.releasePointerCapture?.(e.pointerId) }
  const wheel = e => { e.preventDefault(); velocity.current = Math.max(-.14, Math.min(.14, velocity.current - e.deltaY * .00065)) }
  const positions = [[450,125],[558,188],[558,312],[450,375],[342,312],[342,188]]
  const outerShape = scallopedPath(205, 25)
  const innerShape = scallopedPath(187, 19)
  return <div className="svg-cylinder-wrap" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onWheel={wheel}>
    <svg viewBox="0 0 900 500" role="img" aria-label="RAG Revolver six chamber selector">
      <g transform={`rotate(${angleState * 180 / Math.PI} 450 250)`}>
          <path d={outerShape} fill={ORANGE} stroke={TEAL} strokeWidth="4" strokeLinejoin="round" />
          <path d={innerShape} fill="none" stroke={TEAL} strokeWidth="1.8" strokeLinejoin="round" />
          <Chamber x={positions[0][0]} y={positions[0][1]} />
          <Chamber x={positions[1][0]} y={positions[1][1]} />
          <Chamber x={positions[2][0]} y={positions[2][1]} />
          <Chamber x={positions[3][0]} y={positions[3][1]} />
          <Chamber x={positions[4][0]} y={positions[4][1]} />
          <Chamber x={positions[5][0]} y={positions[5][1]} />
          <circle cx="450" cy="250" r="43" fill={ORANGE} stroke={TEAL} strokeWidth="2.4" />
          <circle cx="450" cy="250" r="15" fill={CREAM} stroke={TEAL} strokeWidth="1.4" />
        </g>
    </svg>
    <div className="active-mode"><span>ACTIVE MODE</span><b>{BOT_NAMES[selected]}</b><small>LIVE</small></div>
    <div className="bot-table">{BOT_NAMES.map((name,index)=><button key={name} className={selected===index?'active':''} onClick={()=>onSelect(index)}><span>0{index+1}</span><b>{name}</b><small>LIVE</small></button>)}</div>
  </div>
}
