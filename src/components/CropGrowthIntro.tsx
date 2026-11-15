import { Component, useEffect, useRef, useState } from 'react'
import type { ReactNode, RefObject } from 'react'
import './CropGrowthIntro.css'

const sessionKey = 'hinge:crop-intro-seen'
const durationMs = 3800
const motionPreference = '(prefers-reduced-motion: reduce)'

function shouldPlay() {
  if (window.matchMedia?.(motionPreference).matches) return false
  try {
    return sessionStorage.getItem(sessionKey) !== '1'
  } catch {
    return true
  }
}

function CropRow() {
  return (
    <svg className="crop-intro-row" viewBox="0 0 680 222" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="intro-furrow">
          <stop stopColor="#81664b" stopOpacity="0" />
          <stop offset=".18" stopColor="#81664b" />
          <stop offset=".82" stopColor="#81664b" />
          <stop offset="1" stopColor="#81664b" stopOpacity="0" />
        </linearGradient>
        <g id="intro-rye">
          <path d="M0 0Q-3-36-27-56Q-8-52 0-25Q1-62 15-82Q11-46 4-23Q18-52 36-57Q17-39 5 0Z" fill="#5b7541" />
          <path d="M1-21Q-12-74-19-86Q-5-82 3-37M6-17Q20-28 25-42" fill="none" stroke="#8c985c" strokeWidth="1.6" strokeLinecap="round" />
        </g>
        <g id="intro-wheat">
          <path d="M0 0Q-1-51 4-107M-1-39Q-7-63-24-70M0-51Q9-79 23-83" fill="none" stroke="#666f39" strokeWidth="2.5" strokeLinecap="round" />
          <g className="crop-intro-leaf">
            <path d="M4-102Q-13-111-8-125Q2-122 5-111Q3-128 11-140Q17-128 9-116Q16-129 24-127Q23-112 8-107Q19-116 22-111Q17-103 4-102Z" fill="#a98b48" />
            <path d="M9-116 14-151M8-110-5-136M11-111 28-136" fill="none" stroke="#a98b48" strokeWidth="1.1" strokeLinecap="round" />
          </g>
        </g>
        <g id="intro-soy">
          <path d="M0 0Q6-30-2-70M2-25Q-8-38-21-41M1-37Q11-48 23-54" fill="none" stroke="#416c47" strokeWidth="3" strokeLinecap="round" />
          <g className="crop-intro-leaf">
            <path d="M-2-61Q-25-68-21-88Q-4-87-2-69Q-4-89 11-101Q23-79-2-61Z" fill="#75925b" />
            <path d="M19-52Q18-72 39-76Q42-57 19-52ZM-17-40Q-39-40-43-58Q-24-63-17-40ZM3-27Q18-43 32-37Q23-20 3-27Z" fill="#497b52" />
            <path d="M-6-49Q-13-43-9-36Q-5-33-4-39Z" fill="#9b9e58" />
          </g>
        </g>
        <g id="intro-corn">
          <path d="M0 0Q5-72 0-150" fill="none" stroke="#3f6a48" strokeWidth="4" />
          <g className="crop-intro-leaf">
            <path d="M1-28Q-13-61-57-58Q-25-48-1-14ZM3-48Q26-90 64-85Q31-70 3-34ZM2-71Q-19-109-49-107Q-20-91 2-61ZM2-101Q16-133 45-135Q23-119 2-90Z" fill="#528356" />
            <path d="M1-28Q-23-56-48-56M6-48Q27-75 51-80M4-102Q20-124 35-130" fill="none" stroke="#a3a968" strokeWidth="1.1" />
            <path d="M13-79Q12-108 24-114Q33-104 22-83Z" fill="#bc9a50" />
            <path d="M10-68Q4-91 15-105Q23-95 20-84Q25-98 33-102Q32-83 10-68Z" fill="#719260" />
            <path d="M1-145Q-8-157-14-161M1-151 2-175M1-149Q7-164 17-168M1-144Q11-153 21-154" fill="none" stroke="#9f824c" strokeWidth="1.8" strokeLinecap="round" />
          </g>
        </g>
      </defs>
      <g className="crop-intro-soil">
        <path d="M14 185H666" stroke="url(#intro-furrow)" strokeWidth="1.5" />
        <path d="M64 186Q340 210 616 186" fill="#a78a68" opacity=".13" />
        <path d="M90 195Q340 214 590 195M160 207Q340 220 520 207" fill="none" stroke="#aa9075" opacity=".24" />
      </g>
      <g transform="translate(92 185) scale(.81)"><use className="crop-intro-plant" href="#intro-rye" /></g>
      <g transform="translate(160 185) scale(.83)"><use className="crop-intro-plant crop-intro-plant-2" href="#intro-soy" /></g>
      <g transform="translate(235 185) scale(.88)"><use className="crop-intro-plant crop-intro-plant-3" href="#intro-wheat" /></g>
      <g transform="translate(326 185)"><use className="crop-intro-plant crop-intro-plant-4" href="#intro-corn" /></g>
      <g transform="translate(415 185) scale(-.89 .89)"><use className="crop-intro-plant crop-intro-plant-5" href="#intro-soy" /></g>
      <g transform="translate(486 185) scale(-.75 .75)"><use className="crop-intro-plant crop-intro-plant-6" href="#intro-wheat" /></g>
      <g transform="translate(575 185) scale(-.85 .85)"><use className="crop-intro-plant crop-intro-plant-7" href="#intro-rye" /></g>
    </svg>
  )
}

// Keep a failure in the decorative overlay from affecting the application tree.
export class IntroBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? null : this.props.children
  }
}

export function CropGrowthIntro({ dashboard }: { dashboard: RefObject<HTMLElement | null> }) {
  const [playing, setPlaying] = useState(shouldPlay)
  const skip = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!playing) return
    try {
      sessionStorage.setItem(sessionKey, '1')
    } catch {
      // The in-page animation still dismisses when storage is blocked.
    }

    const finish = () => {
      if (document.activeElement === skip.current) dashboard.current?.focus({ preventScroll: true })
      setPlaying(false)
    }

    const preference = window.matchMedia?.(motionPreference)
    const onPreferenceChange = (event: MediaQueryListEvent) => { if (event.matches) finish() }
    preference?.addEventListener?.('change', onPreferenceChange)
    const timeout = window.setTimeout(finish, durationMs)
    return () => {
      window.clearTimeout(timeout)
      preference?.removeEventListener?.('change', onPreferenceChange)
    }
  }, [dashboard, playing])

  if (!playing) return null

  return (
    <div className="crop-intro" onBlur={event => {
      if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setPlaying(false)
    }}>
      <button
        ref={skip}
        type="button"
        className="crop-intro-skip"
        onClick={() => {
          setPlaying(false)
          dashboard.current?.focus({ preventScroll: true })
        }}
      >
        Skip intro
      </button>
      <div className="crop-intro-scene" aria-hidden="true">
        <div className="crop-intro-brand">
          <div className="crop-intro-wordmark">HINGE</div>
          <div className="crop-intro-subtitle">Land Systems Intelligence</div>
        </div>
        <CropRow />
      </div>
    </div>
  )
}
