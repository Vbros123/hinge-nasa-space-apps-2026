import { useMemo, useState } from 'react'
import { CheckCircle2, CircleAlert, CircleHelp, Database, Eye, FlaskConical, Layers3, ShieldAlert } from 'lucide-react'
import { Card, Eyebrow, SectionHeading, StatusPill } from '../components/ui'
import type { DecisionState, EvidenceItem } from '../types/domain'

const stateDetails: Record<DecisionState, { title: string; detail: string; icon: typeof CheckCircle2 }> = {
  supported: {
    title: 'Modeled preference',
    detail: 'A feasible rotation ranks highest under the declared assumptions and remains above the modeled sensitivity threshold.',
    icon: CheckCircle2,
  },
  sensitive: {
    title: 'Comparison is sensitive',
    detail: 'The current leader is close or its confidence is limited. Small changes in assumptions could change the ordering.',
    icon: CircleAlert,
  },
  insufficient: {
    title: 'Insufficient evidence',
    detail: 'Confidence is too low to distinguish a supported preference. Collect better local evidence before interpreting results.',
    icon: CircleHelp,
  },
  'no-feasible': {
    title: 'No feasible rotation',
    detail: 'Every candidate violates at least one hard constraint under the current scenario, so no recommendation is supported.',
    icon: ShieldAlert,
  },
}

const statusMetadata = {
  observed: { title: 'Observed', description: 'Measured or retrieved from a named source. None is connected in this demo.', icon: Eye },
  modeled: { title: 'Modeled', description: 'Produced by a calculation; dependent on stated model structure and inputs.', icon: FlaskConical },
  assumed: { title: 'Assumed / synthetic', description: 'Illustrative placeholder for demonstration, not an authentic observation.', icon: Layers3 },
  unavailable: { title: 'Unavailable', description: 'Not provided or not connected; no value is inferred.', icon: Database },
} as const

export function EvidencePage({
  evidence,
  decisionState,
}: {
  evidence: EvidenceItem[]
  decisionState: DecisionState
}) {
  const [filter, setFilter] = useState('all')
  const shown = useMemo(() => filter === 'all' ? evidence : evidence.filter((item) => item.status === filter), [evidence, filter])
  const state = stateDetails[decisionState]
  const StateIcon = state.icon

  return (
    <>
      <SectionHeading eyebrow="PROVENANCE / 05" title="Evidence & uncertainty" description="Know what is observed, what is modeled, and what is not yet available." action={<span className="evidence-shield"><ShieldAlert size={16} /> No live datasets connected</span>} />
      <Card className={`decision-state-card state-card-${decisionState}`}>
        <div className="state-card-icon"><StateIcon size={21} /></div>
        <div><Eyebrow>DECISION STATUS RIGHT NOW</Eyebrow><h2>{state.title}</h2><p>{state.detail}</p></div>
        <StatusPill status="modeled" />
      </Card>
      <div className="evidence-kind-grid">
        {(Object.keys(statusMetadata) as Array<keyof typeof statusMetadata>).map((key) => {
          const Icon = statusMetadata[key].icon
          const count = evidence.filter((item) => item.status === key).length
          return <Card className={`evidence-kind kind-${key}`} key={key}><span className="kind-icon"><Icon size={17} /></span><span className="kind-count">{count}</span><strong>{statusMetadata[key].title}</strong><p>{statusMetadata[key].description}</p></Card>
        })}
      </div>
      <Card className="evidence-list-card">
        <div className="card-heading"><div><Eyebrow>DATA REGISTER</Eyebrow><h2>Inputs & provenance</h2><p>Trace every included and unavailable source.</p></div><label className="filter-select"><span>Show</span><select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter evidence by status"><option value="all">All evidence</option><option value="observed">Observed</option><option value="modeled">Modeled</option><option value="assumed">Synthetic</option><option value="unavailable">Unavailable</option></select></label></div>
        <div className="evidence-list">{shown.map((item) => <div className="evidence-row" key={item.id}><div className={`evidence-row-icon evidence-${item.status}`}>{item.status === 'unavailable' ? <CircleHelp size={17} /> : item.status === 'observed' ? <Eye size={17} /> : item.status === 'modeled' ? <FlaskConical size={17} /> : <Layers3 size={17} />}</div><div className="evidence-main"><div className="evidence-title-row"><strong>{item.label}</strong><StatusPill status={item.status} /></div><p>{item.detail}</p><small>{item.source}</small></div>{item.updatedAt && <span className="evidence-date">{item.updatedAt}</span>}</div>)}</div>
      </Card>
      <div className="uncertainty-grid">
        <Card className="uncertainty-card"><div className="uncertainty-icon"><CircleAlert size={18} /></div><Eyebrow>MODEL UNCERTAINTY</Eyebrow><h2>Rankings are conditional</h2><p>All scores are generated from a lightweight, transparent client-side formula. Rotation attributes and confidence values are mock inputs that require agronomist review.</p></Card>
        <Card className="uncertainty-card"><div className="uncertainty-icon"><Database size={18} /></div><Eyebrow>DATA LIMITATION</Eyebrow><h2>No NASA connection yet</h2><p>There are no authentic NASA climate, vegetation, or soil data sources wired into this frontend. Contract shapes are documented for future integration.</p></Card>
        <Card className="uncertainty-card"><div className="uncertainty-icon"><ShieldAlert size={18} /></div><Eyebrow>SAFE INTERPRETATION</Eyebrow><h2>Not agronomic advice</h2><p>Do not use this demo to allocate water, select seed, or make financial decisions. Validate with local measurements and qualified advisors.</p></Card>
      </div>
    </>
  )
}
