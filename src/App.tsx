import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Bell, ChevronDown, CircleHelp, Command, Search } from 'lucide-react'
import { MobileNav, Sidebar, type ScreenId } from './components/Sidebar'
import { useFarmData } from './hooks/useFarmData'
import { defaultDecisionInputs, scoreRotations } from './services/decisionModel'
import type { DecisionInputs } from './types/domain'
import './App.css'
import 'leaflet/dist/leaflet.css'

const FarmPage = lazy(async () => ({ default: (await import('./pages/FarmPage')).FarmPage }))
const ComparePage = lazy(async () => ({ default: (await import('./pages/ComparePage')).ComparePage }))
const BoundaryPage = lazy(async () => ({ default: (await import('./pages/BoundaryPage')).BoundaryPage }))
const HistoryPage = lazy(async () => ({ default: (await import('./pages/HistoryPage')).HistoryPage }))
const EvidencePage = lazy(async () => ({ default: (await import('./pages/EvidencePage')).EvidencePage }))

const pageTitles: Record<ScreenId, string> = {
  farm: 'Farm intelligence',
  compare: 'Rotation comparison',
  boundary: 'Decision explorer',
  history: 'Climate replay',
  evidence: 'Evidence & uncertainty',
}

function App() {
  const [activeScreen, setActiveScreen] = useState<ScreenId>('farm')
  const [selectedFarmId, setSelectedFarmId] = useState('demo-farm-east')
  const [inputs, setInputs] = useState<DecisionInputs>(defaultDecisionInputs)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { dashboard, history, loading, error } = useFarmData(selectedFarmId)
  const baselineRainMm = dashboard?.climate.reduce((sum, month) => sum + month.precipitationMm, 0) ?? 281
  const comparison = useMemo(
    () => dashboard ? scoreRotations(dashboard.rotations, inputs, baselineRainMm) : null,
    [dashboard, inputs, baselineRainMm],
  )

  useEffect(() => {
    const handler = (event: Event) => {
      const screen = (event as CustomEvent<ScreenId>).detail
      if (screen in pageTitles) setActiveScreen(screen)
    }
    document.addEventListener('hinge:navigate', handler)
    return () => document.removeEventListener('hinge:navigate', handler)
  }, [])

  const navigate = (screen: ScreenId) => {
    setActiveScreen(screen)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'shell-collapsed' : ''}`}>
      <Sidebar active={activeScreen} onNavigate={navigate} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} />
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left"><div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>{pageTitles[activeScreen]}</strong></div></div>
          <div className="topbar-actions"><div className="global-search"><Search size={15} /><span>Search workspace</span><kbd><Command size={11} /> K</kbd></div><button className="top-icon" aria-label="Help"><CircleHelp size={17} /></button><button className="top-icon has-notification" aria-label="Notifications"><Bell size={17} /><i /></button><div className="top-divider" /><button className="profile-button"><span className="profile-avatar">PV</span><ChevronDown size={14} /></button></div>
        </header>
        <main className="page-content">
          {loading && <div className="loading-state"><div className="loading-spinner" /> Loading farm scenario…</div>}
          {error && <div className="error-state" role="alert">Could not load farm data: {error}</div>}
          {!loading && dashboard && comparison && (
            <Suspense fallback={<div className="loading-state"><div className="loading-spinner" /> Preparing analysis view…</div>}>
              {activeScreen === 'farm' && <FarmPage dashboard={dashboard} comparison={comparison} onFarmChange={setSelectedFarmId} />}
              {activeScreen === 'compare' && <ComparePage dashboard={dashboard} comparison={comparison} />}
              {activeScreen === 'boundary' && <BoundaryPage rotations={dashboard.rotations} inputs={inputs} comparison={comparison} baselineRainMm={baselineRainMm} onChange={setInputs} />}
              {activeScreen === 'history' && <HistoryPage scenarios={history} />}
              {activeScreen === 'evidence' && <EvidencePage evidence={dashboard.evidence} decisionState={comparison.decisionState} />}
            </Suspense>
          )}
          <footer className="page-footer"><span>HINGE · LAND SYSTEMS DECISION SUPPORT</span><span>DEMONSTRATION BUILD · 2026</span></footer>
        </main>
      </div>
      <MobileNav active={activeScreen} onNavigate={navigate} />
    </div>
  )
}

export default App
