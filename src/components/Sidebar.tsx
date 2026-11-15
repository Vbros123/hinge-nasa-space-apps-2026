import {
  Activity,
  BookOpenCheck,
  CircleHelp,
  GitCompareArrows,
  Globe2,
  Leaf,
  PanelLeftClose,
  PanelLeftOpen,
  Sprout,
} from 'lucide-react'

export type ScreenId = 'farm' | 'compare' | 'boundary' | 'history' | 'evidence'

const navigation: Array<{ id: ScreenId; label: string; icon: typeof Sprout }> = [
  { id: 'farm', label: 'Farm intelligence', icon: Sprout },
  { id: 'compare', label: 'Rotation comparison', icon: GitCompareArrows },
  { id: 'boundary', label: 'Decision explorer', icon: Activity },
  { id: 'history', label: 'Climate replay', icon: Globe2 },
  { id: 'evidence', label: 'Evidence & uncertainty', icon: BookOpenCheck },
]

export function Sidebar({
  active,
  demo = true,
  onNavigate,
  collapsed,
  onToggle,
}: {
  active: ScreenId
  demo?: boolean
  onNavigate: (screen: ScreenId) => void
  collapsed: boolean
  onToggle: () => void
}) {
  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="brand">
        <div className="brand-mark"><span /><span /><span /></div>
        {!collapsed && <div className="brand-copy"><strong>HINGE</strong><small>LAND SYSTEMS LAB</small></div>}
        <button className="sidebar-toggle" onClick={onToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>
      {!collapsed && <div className="workspace-picker"><div className="workspace-avatar">{demo ? "PV" : "JC"}</div><div><strong>{demo ? "Prairie View" : "Johnston County"}</strong><small>{demo ? "Demo workspace" : "Study area"}</small></div></div>}
      <div className="nav-caption">{!collapsed && 'WORKSPACE'}</div>
      <nav className="side-nav" aria-label="Primary navigation">
        {navigation.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`nav-item ${active === id ? 'nav-active' : ''}`} onClick={() => onNavigate(id)} title={collapsed ? label : undefined}>
            <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
          </button>
        ))}
      </nav>
      {!collapsed && (
        <div className="sidebar-bottom">
          <div className="data-mode"><span className="pulse-dot" /><div><strong>{demo ? "Demo mode" : "Scientific analysis"}</strong><small>{demo ? "Synthetic fixtures active" : "Archived model results"}</small></div></div>
          <button className="help-link" onClick={() => onNavigate("evidence")}><CircleHelp size={16} /> Methodology & help</button>
          <div className="sidebar-footer"><Leaf size={14} /> NASA Space Apps Challenge 2026</div>
        </div>
      )}
    </aside>
  )
}

const shortLabels: Record<ScreenId, string> = {
  farm: 'Farm',
  compare: 'Compare',
  boundary: 'Explorer',
  history: 'Replay',
  evidence: 'Evidence',
}

export function MobileNav({
  active,
  onNavigate,
}: {
  active: ScreenId
  onNavigate: (screen: ScreenId) => void
}) {
  return (
    <nav className="mobile-tabbar" aria-label="Mobile primary navigation">
      {navigation.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`mobile-tab ${active === id ? 'mobile-tab-active' : ''}`}
          onClick={() => onNavigate(id)}
          aria-label={label}
          aria-current={active === id ? 'page' : undefined}
        >
          <Icon size={17} strokeWidth={1.8} />
          <span>{shortLabels[id]}</span>
        </button>
      ))}
    </nav>
  )
}
