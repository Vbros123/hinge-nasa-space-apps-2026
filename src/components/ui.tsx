import type { ReactNode } from 'react'
import type { EvidenceStatus } from '../types/domain'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={`card ${className}`}>{children}</section>
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow">{children}</div>
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="section-heading">
      <div>
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  )
}

export function StatusPill({ status }: { status: EvidenceStatus }) {
  const label = status === 'observed'
    ? 'Observed'
    : status === 'modeled'
      ? 'Modeled'
      : status === 'assumed'
        ? 'Synthetic'
        : 'Unavailable'
  return <span className={`status-pill status-${status}`}>{label}</span>
}

export function MetricCard({
  label,
  value,
  unit,
  trend,
  icon,
  tone = 'green',
}: {
  label: string
  value: string
  unit?: string
  trend?: ReactNode
  icon: ReactNode
  tone?: 'green' | 'blue' | 'amber' | 'slate'
}) {
  return (
    <Card className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon tone-${tone}`}>{icon}</span>
        {trend && <span className="metric-trend">{trend}</span>}
      </div>
      <p className="metric-label">{label}</p>
      <div className="metric-value">{value}<span>{unit}</span></div>
    </Card>
  )
}

export function MiniLegend({
  items,
}: {
  items: Array<{ label: string; color: string }>
}) {
  return (
    <div className="mini-legend">
      {items.map((item) => (
        <span key={item.label}><i style={{ backgroundColor: item.color }} />{item.label}</span>
      ))}
    </div>
  )
}
