import { useMemo } from 'react'
import { ArrowDown, ArrowRightLeft, CircleHelp, Droplets, FlaskConical, Gauge, Leaf, RotateCcw, Sprout } from 'lucide-react'
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, Eyebrow, SectionHeading, StatusPill } from '../components/ui'
import { buildDecisionBoundary } from '../services/decisionModel'
import type { CropRotation, DecisionInputs, RotationComparison } from '../types/domain'

function RangeControl({
  label,
  value,
  min,
  max,
  step,
  unit,
  help,
  onChange,
  tone,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  help: string
  onChange: (value: number) => void
  tone: 'blue' | 'green' | 'amber' | 'slate'
}) {
  return (
    <label className="control-row">
      <div className="control-label"><span className={`control-icon tone-${tone}`}>{tone === 'blue' ? <Droplets size={16} /> : tone === 'green' ? <Leaf size={16} /> : tone === 'amber' ? <Sprout size={16} /> : <Gauge size={16} />}</span><span><strong>{label}</strong><small>{help}</small></span><b>{value}{unit}</b></div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} aria-label={label} />
      <div className="range-limits"><span>{min}{unit}</span><span>{max}{unit}</span></div>
    </label>
  )
}

export function BoundaryPage({
  rotations,
  inputs,
  comparison,
  baselineRainMm,
  onChange,
}: {
  rotations: CropRotation[]
  inputs: DecisionInputs
  comparison: RotationComparison
  baselineRainMm: number
  onChange: (next: DecisionInputs) => void
}) {
  const boundary = useMemo(() => buildDecisionBoundary(rotations, inputs, baselineRainMm), [rotations, inputs, baselineRainMm])
  const chartData = boundary.points.map((point) => ({
    precipitation: point.precipitationShiftPercent,
    ...point.scores,
  }))
  const activeRotation = rotations.find((rotation) => rotation.id === comparison.preferredRotationId)
  const transitionText = boundary.transitions.length
    ? `A modeled ranking transition appears near ${boundary.transitions.join('% and ')}% precipitation shift.`
    : 'No ranking transition appears across the current precipitation range.'
  const stateText = comparison.decisionState === 'supported'
    ? 'One option leads clearly within this scenario.'
    : comparison.decisionState === 'sensitive'
      ? 'The leading option is sensitive to small input changes.'
      : 'Evidence is insufficient to support a preferred option.'

  const update = (key: keyof DecisionInputs, value: number) => onChange({ ...inputs, [key]: value })

  return (
    <>
      <SectionHeading eyebrow="PREFERENCE SENSITIVITY / 03" title="Decision boundary explorer" description="Change what matters to you and see exactly when the modeled ranking changes." action={<span className="core-feature-tag"><FlaskConical size={14} /> CORE FEATURE</span>} />
      <div className="boundary-intro"><div className="boundary-intro-mark"><ArrowRightLeft size={20} /></div><div><strong>No single “best” rotation — explore the boundary.</strong><p>Every control below recalculates the score, comparison cards, and sensitivity curves from the same transparent formula.</p></div><StatusPill status="modeled" /></div>
      <div className="boundary-layout">
        <Card className="assumptions-panel">
          <div className="card-heading"><div><Eyebrow>SCENARIO CONTROLS</Eyebrow><h2>Adjust your assumptions</h2><p>Move a slider; the model updates immediately.</p></div><button className="icon-button" aria-label="Reset controls" title="Reset to defaults" onClick={() => onChange({ precipitationShiftPercent: 0, irrigationCapMm: 100, waterPriority: 65, soilPriority: 55, heatStressTolerance: 68, soilWorkability: 62, riskTolerance: 58 })}><RotateCcw size={15} /></button></div>
          <div className="preset-row"><span>Quick scenario</span><button onClick={() => onChange({ ...inputs, precipitationShiftPercent: -25, irrigationCapMm: 70, heatStressTolerance: 56, soilWorkability: 48, riskTolerance: 45 })}>Dry year</button><button onClick={() => onChange({ ...inputs, precipitationShiftPercent: 0, irrigationCapMm: 100, heatStressTolerance: 68, soilWorkability: 62, riskTolerance: 58 })}>Baseline</button><button onClick={() => onChange({ ...inputs, precipitationShiftPercent: 25, irrigationCapMm: 160, heatStressTolerance: 78, soilWorkability: 72, riskTolerance: 72 })}>Wetter year</button></div>
          <div className="controls-list">
            <RangeControl label="Precipitation shift" value={inputs.precipitationShiftPercent} min={-40} max={40} step={1} unit="%" help="Relative change from illustrative baseline" tone="blue" onChange={(value) => update('precipitationShiftPercent', value)} />
            <RangeControl label="Irrigation availability" value={inputs.irrigationCapMm} min={0} max={220} step={5} unit=" mm" help="Seasonal water available to the rotation" tone="amber" onChange={(value) => update('irrigationCapMm', value)} />
            <RangeControl label="Water priority" value={inputs.waterPriority} min={0} max={100} step={1} unit="%" help="How strongly water fit influences your choice" tone="blue" onChange={(value) => update('waterPriority', value)} />
            <RangeControl label="Soil-water priority" value={inputs.soilPriority} min={0} max={100} step={1} unit="%" help="How strongly modeled soil water matters" tone="green" onChange={(value) => update('soilPriority', value)} />
            <RangeControl label="Heat stress tolerance" value={inputs.heatStressTolerance} min={0} max={100} step={1} unit="%" help="Farm tolerance for warm-season stress and canopy loss" tone="amber" onChange={(value) => update('heatStressTolerance', value)} />
            <RangeControl label="Soil workability" value={inputs.soilWorkability} min={0} max={100} step={1} unit="%" help="Seeding and field-access conditions after rainfall" tone="green" onChange={(value) => update('soilWorkability', value)} />
            <RangeControl label="Risk tolerance" value={inputs.riskTolerance} min={0} max={100} step={1} unit="%" help="How much uncertainty the farmer accepts before choosing a rotation" tone="slate" onChange={(value) => update('riskTolerance', value)} />
          </div>
          <div className="formula-note"><CircleHelp size={15} /><span><strong>Score recipe:</strong> weighted water fit + modeled soil-water + dynamic feasibility + environmental indicators, with agronomic constraints increasingly penalizing rotations when stress, soil access, or risk tolerance are tight.</span></div>
        </Card>
        <div className="boundary-results">
          <Card className="boundary-chart-card">
            <div className="card-heading"><div><Eyebrow>DECISION BOUNDARY</Eyebrow><h2>Where does the leader change?</h2><p>Rotation score under a range of precipitation assumptions</p></div><span className="chart-unit">SCORE / 100</span></div>
            <div className="boundary-legend">{rotations.map((rotation) => <span key={rotation.id}><i style={{ background: rotation.color }} />{rotation.name}</span>)}</div>
            <div className="chart-boundary">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 12, right: 15, bottom: 5, left: -16 }}>
                  <CartesianGrid vertical={false} stroke="#edf0eb" />
                  <XAxis dataKey="precipitation" type="number" domain={[-40, 40]} ticks={[-40, -20, 0, 20, 40]} axisLine={false} tickLine={false} tick={{ fill: '#89938c', fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
                  <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#89938c', fontSize: 11 }} />
                  <Tooltip labelFormatter={(value) => `Precipitation shift: ${value}%`} formatter={(value, name) => [`${value} pts`, rotations.find((rotation) => rotation.id === name)?.name ?? name]} contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3', fontSize: 12 }} />
                  <ReferenceLine x={inputs.precipitationShiftPercent} stroke="#273d33" strokeDasharray="4 4" label={{ value: 'YOU ARE HERE', fill: '#52665b', fontSize: 9, position: 'insideTopRight' }} />
                  {rotations.map((rotation) => <Line key={rotation.id} type="monotone" dataKey={rotation.id} name={rotation.name} stroke={rotation.color} strokeWidth={rotation.id === comparison.preferredRotationId ? 3.5 : 2} dot={false} activeDot={{ r: 5 }} />)}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-axis-caption"><span>← DRIER CONDITIONS</span><span>PRECIPITATION ASSUMPTION</span><span>WETTER CONDITIONS →</span></div>
            <div className="transition-note"><span className="transition-mark"><ArrowDown size={14} /></span><span>{transitionText}</span></div>
          </Card>
          <Card className="current-decision-card">
            <div className="current-decision-head"><div><Eyebrow>UNDER YOUR INPUTS</Eyebrow><h2>Current modeled preference</h2></div><span className={`decision-state state-${comparison.decisionState}`}>{comparison.decisionState === 'supported' ? 'SUPPORTED*' : comparison.decisionState === 'sensitive' ? 'SENSITIVE' : 'INSUFFICIENT'}</span></div>
            <div className="decision-leader"><span className="decision-leader-dot" style={{ background: activeRotation?.color }} /><div><strong>{activeRotation?.name ?? 'No leading option'}</strong><small>{stateText}</small></div><b>{comparison.results[0]?.totalScore ?? '—'}<small> pts</small></b></div>
            <p className="decision-explanation">{comparison.explanation}</p>
            <div className="ranked-list">{comparison.results.map((result, index) => {
              const rotation = rotations.find((item) => item.id === result.rotationId)
              return <div key={result.rotationId} className="rank-row"><span className="rank-num">0{index + 1}</span><span className="rank-name"><i style={{ background: rotation?.color }} />{rotation?.name}</span><span className="rank-score">{result.totalScore}</span><span className="rank-track"><i style={{ width: `${result.totalScore}%`, background: rotation?.color }} /></span></div>
            })}</div>
            <div className="footnote">* “Supported” describes only the synthetic scoring scenario. It does not imply a real-world recommendation.</div>
          </Card>
        </div>
      </div>
    </>
  )
}
