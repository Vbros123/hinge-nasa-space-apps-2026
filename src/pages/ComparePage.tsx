import { ArrowUpRight, Check, Droplets, Leaf, ShieldCheck, Sprout } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Radar,
  RadarChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, Eyebrow, MiniLegend, SectionHeading, StatusPill } from '../components/ui'
import type { FarmDashboardData, RotationComparison } from '../types/domain'

export function ComparePage({
  dashboard,
  comparison,
}: {
  dashboard: FarmDashboardData
  comparison: RotationComparison
}) {
  const scoreRows = comparison.results.map((result) => ({
    name: dashboard.rotations.find((rotation) => rotation.id === result.rotationId)?.name ?? result.rotationId,
    score: result.totalScore,
    fill: dashboard.rotations.find((rotation) => rotation.id === result.rotationId)?.color ?? '#678',
  }))
  const radarData = [
    { dimension: 'Water fit', ...Object.fromEntries(comparison.results.map((result) => [result.rotationId, result.waterFit])) },
    { dimension: 'Soil water', ...Object.fromEntries(comparison.results.map((result) => [result.rotationId, result.modeledSoilWater])) },
    { dimension: 'Feasibility', ...Object.fromEntries(comparison.results.map((result) => [result.rotationId, result.dynamicFeasibility])) },
    { dimension: 'Environment', ...Object.fromEntries(comparison.results.map((result) => [result.rotationId, result.environmentalScore])) },
  ]

  return (
    <>
      <SectionHeading eyebrow="OPTIONS / 02" title="Rotation comparison" description="Compare the trade-offs behind each modeled rotation, using one shared set of assumptions." action={<StatusPill status="modeled" />} />
      <div className="demo-banner"><span className="banner-dot" /><strong>SCENARIO COMPARISON</strong><span>Relative scores are illustrative and do not predict yield or prescribe a crop.</span><StatusPill status="assumed" /></div>
      <div className="comparison-summary">
        {comparison.results.map((result, index) => {
          const rotation = dashboard.rotations.find((item) => item.id === result.rotationId)
          return (
            <Card key={result.rotationId} className={`rotation-card ${index === 0 ? 'rotation-leader' : ''}`}>
              <div className="rotation-card-top"><span className="rotation-swatch" style={{ backgroundColor: rotation?.color }} />{index === 0 && <span className="leader-chip"><Check size={12} /> LEADS THIS SCENARIO</span>}</div>
              <h2>{rotation?.name}</h2><p>{rotation?.description}</p>
              <div className="rotation-score"><strong>{result.totalScore}</strong><span>modeled points</span></div>
              <div className="rotation-mini-metrics"><span><Droplets size={14} />{rotation?.annualWaterNeedMm} mm / yr</span><span><Sprout size={14} />{result.modeledSoilWater} soil-water</span></div>
            </Card>
          )
        })}
      </div>
      <div className="compare-grid">
        <Card className="chart-card">
          <div className="card-heading"><div><Eyebrow>OVERALL RESULT</Eyebrow><h2>Modeled fit score</h2><p>Current weights: water {comparison.inputs.waterPriority}% · soil {comparison.inputs.soilPriority}% · risk {comparison.inputs.riskTolerance}%</p></div><span className="chart-unit">0–100</span></div>
          <div className="chart-medium">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreRows} layout="vertical" margin={{ left: 4, right: 28, top: 8, bottom: 4 }}>
                <CartesianGrid horizontal={false} stroke="#edf0eb" />
                <XAxis type="number" domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#8b958e', fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={112} axisLine={false} tickLine={false} tick={{ fill: '#59665e', fontSize: 12 }} />
                <Tooltip cursor={{ fill: '#f5f7f3' }} formatter={(value) => [`${value} pts`, 'Fit score']} contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3' }} />
                <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={24}>
                  {scoreRows.map((row) => <Cell key={row.name} fill={row.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footnote">Score combines modeled water fit and soil-water conditions with dynamic feasibility and environmental factors, so agronomic constraints now change the ranking.</div>
        </Card>
        <Card className="radar-card">
          <div className="card-heading"><div><Eyebrow>TRADE-OFF PROFILE</Eyebrow><h2>Where options differ</h2><p>Each axis is a relative 0–100 indicator</p></div></div>
          <div className="chart-medium radar-chart">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} outerRadius="70%">
                <PolarGrid stroke="#e8ece6" />
                <PolarAngleAxis dataKey="dimension" tick={{ fill: '#68746c', fontSize: 10 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                {comparison.results.map((result) => {
                  const rotation = dashboard.rotations.find((item) => item.id === result.rotationId)
                  return <Radar key={result.rotationId} name={rotation?.name} dataKey={result.rotationId} stroke={rotation?.color} fill={rotation?.color} fillOpacity={0.09} strokeWidth={2} />
                })}
                <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <MiniLegend items={dashboard.rotations.map((rotation) => ({ label: rotation.name, color: rotation.color }))} />
        </Card>
      </div>
      <Card className="table-card">
        <div className="card-heading"><div><Eyebrow>DECISION DETAIL</Eyebrow><h2>Modeled indicators by rotation</h2><p>Inputs can be adjusted in Decision explorer.</p></div><button className="small-link" onClick={() => document.dispatchEvent(new CustomEvent('hinge:navigate', { detail: 'boundary' }))}>Open explorer <ArrowUpRight size={14} /></button></div>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead><tr><th>Rotation</th><th>Water need</th><th>Water fit</th><th>Soil-water</th><th>Feasibility</th><th>Environment</th><th>Confidence</th></tr></thead>
            <tbody>{comparison.results.map((result) => {
              const rotation = dashboard.rotations.find((item) => item.id === result.rotationId)
              return <tr key={result.rotationId}><td><span className="table-rotation"><i style={{ background: rotation?.color }} />{rotation?.name}</span></td><td>{rotation?.annualWaterNeedMm} mm / yr</td><td><span className="table-score">{result.waterFit}</span></td><td>{result.modeledSoilWater}</td><td>{result.dynamicFeasibility}</td><td>{result.environmentalScore}</td><td><span className="confidence-cell"><span className="confidence-track"><i style={{ width: `${(result.confidence * 100)}%` }} /></span>{Math.round(result.confidence * 100)}%</span></td></tr>
            })}</tbody>
          </table>
        </div>
      </Card>
      <div className="tradeoff-note"><ShieldCheck size={17} /><div><strong>Use this as a conversation starter, not a recommendation.</strong><span>Rotation attributes and formula weights are synthetic placeholders pending agronomic review and real backend outputs.</span></div><Leaf size={17} /></div>
    </>
  )
}
