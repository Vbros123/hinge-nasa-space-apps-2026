import { useMemo, useState } from 'react'
import { ArrowLeftRight, CalendarDays, CloudRain, Thermometer, Wind } from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, Eyebrow, SectionHeading, StatusPill } from '../components/ui'
import type { HistoricalScenario } from '../types/domain'

export function HistoryPage({ scenarios }: { scenarios: HistoricalScenario[] }) {
  const [selectedYear, setSelectedYear] = useState(scenarios.at(-1)?.year ?? 2025)
  const [comparisonYear, setComparisonYear] = useState(scenarios.at(-3)?.year ?? 2023)
  const selected = scenarios.find((scenario) => scenario.year === selectedYear) ?? scenarios[0]
  const compared = scenarios.find((scenario) => scenario.year === comparisonYear) ?? scenarios[0]
  const rainfallDelta = selected && compared ? selected.precipitationMm - compared.precipitationMm : 0
  const updateSelectedYear = (year: number) => {
    setSelectedYear(year)
    if (comparisonYear === year) {
      const alternate = scenarios.find((scenario) => scenario.year !== year)
      if (alternate) setComparisonYear(alternate.year)
    }
  }
  const chartData = useMemo(() => scenarios.map((scenario) => ({
    ...scenario,
    isSelected: scenario.year === selectedYear,
    isComparison: scenario.year === comparisonYear,
  })), [scenarios, selectedYear, comparisonYear])

  return (
    <>
      <SectionHeading eyebrow="SEASONAL CONTEXT / 04" title="Historical climate replay" description="Scrub through illustrative past-season scenarios and compare what a different year could mean." action={<StatusPill status="assumed" />} />
      <div className="demo-banner"><span className="banner-dot" /><strong>SYNTHETIC SCENARIOS</strong><span>Years are scenario labels, not a reconstruction of verified historical observations.</span><StatusPill status="assumed" /></div>
      <Card className="timeline-card">
        <div className="card-heading"><div><Eyebrow>SEASON SELECTOR</Eyebrow><h2>Replay the growing season context</h2><p>Select a year to update the season summary and comparison below.</p></div><div className="year-chip"><CalendarDays size={15} />{selected?.year}</div></div>
        <input className="timeline-slider" type="range" min={0} max={scenarios.length - 1} step={1} value={Math.max(0, scenarios.findIndex((scenario) => scenario.year === selectedYear))} onChange={(event) => updateSelectedYear(scenarios[Number(event.target.value)]?.year ?? selectedYear)} aria-label="Select replay year" />
        <div className="year-markers">{scenarios.map((scenario) => <button key={scenario.year} className={scenario.year === selectedYear ? 'year-active' : ''} onClick={() => updateSelectedYear(scenario.year)}>{scenario.year}</button>)}</div>
      </Card>
      <div className="history-summary-grid">
        <Card className="history-selected-card">
          <div className="history-selected-top"><span className="history-icon"><CloudRain size={19} /></span><span className="scenario-tag">SELECTED SCENARIO</span></div>
          <Eyebrow>{selected?.year} SEASON PROFILE</Eyebrow><h2>{selected?.note}</h2>
          <div className="history-stat-row"><div><span>Scenario precipitation</span><strong>{selected?.precipitationMm}<small> mm</small></strong></div><div><span>Mean temperature</span><strong>{selected?.temperatureC}<small> °C</small></strong></div></div>
          <div className="history-stat-row"><div><span>Dry-day indicator</span><strong>{selected?.dryDays}<small> days</small></strong></div><div><span>Modeled yield index</span><strong>{selected?.modeledYieldIndex}<small> / 100</small></strong></div></div>
        </Card>
        <Card className="history-compare-card">
          <div className="card-heading"><div><Eyebrow>YEAR-TO-YEAR COMPARISON</Eyebrow><h2>Compare season conditions</h2></div><label className="compare-select"><ArrowLeftRight size={14} /><select value={comparisonYear} onChange={(event) => setComparisonYear(Number(event.target.value))} aria-label="Select comparison year">{scenarios.filter((scenario) => scenario.year !== selectedYear).map((scenario) => <option key={scenario.year} value={scenario.year}>{scenario.year}</option>)}</select></label></div>
          <div className="year-compare-row">
            <div className="year-compare-item"><span>{selected?.year}</span><strong>{selected?.precipitationMm} mm</strong><small>{selected?.temperatureC}°C mean</small></div>
            <div className="year-delta"><span className={rainfallDelta >= 0 ? 'delta-positive' : 'delta-negative'}>{rainfallDelta > 0 ? '+' : ''}{rainfallDelta} mm</span><small>precipitation difference</small></div>
            <div className="year-compare-item year-compare-right"><span>{compared?.year}</span><strong>{compared?.precipitationMm} mm</strong><small>{compared?.temperatureC}°C mean</small></div>
          </div>
          <p className="compare-implication">{rainfallDelta >= 0 ? 'The selected scenario has more precipitation than the comparison year.' : 'The selected scenario has less precipitation than the comparison year.'} Different water availability can shift a rotation’s modeled fit.</p>
        </Card>
      </div>
      <div className="history-charts-grid">
        <Card className="history-chart-card">
          <div className="card-heading"><div><Eyebrow>CLIMATE CONTEXT</Eyebrow><h2>Precipitation & temperature</h2><p>Scenario-level annual summaries · not measured data</p></div><span className="chart-unit">MM / °C</span></div>
          <div className="chart-history">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ left: -18, right: 12, top: 10, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#edf0eb" />
                <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: '#8a958d', fontSize: 11 }} />
                <YAxis yAxisId="rain" axisLine={false} tickLine={false} tick={{ fill: '#8a958d', fontSize: 10 }} />
                <YAxis yAxisId="temp" orientation="right" domain={[10, 18]} hide />
                <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3' }} />
                <Area yAxisId="rain" type="monotone" dataKey="precipitationMm" name="Precipitation assumption (mm)" stroke="#719fc1" strokeWidth={2} fill="#dbeaf3" />
                <Line yAxisId="temp" type="monotone" dataKey="temperatureC" name="Temperature assumption (°C)" stroke="#de9e62" strokeWidth={2} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footnote">Both series are synthetic scenario inputs. Temperature uses a separate scale.</div>
        </Card>
        <Card className="history-chart-card">
          <div className="card-heading"><div><Eyebrow>AGRICULTURAL IMPLICATION</Eyebrow><h2>Modeled response index</h2><p>Illustrative index for scenario exploration only</p></div><span className="chart-unit">INDEX</span></div>
          <div className="chart-history">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ left: -18, right: 12, top: 10, bottom: 0 }}>
                <defs><linearGradient id="yieldFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#58a27e" stopOpacity={0.28} /><stop offset="100%" stopColor="#58a27e" stopOpacity={0.02} /></linearGradient></defs>
                <CartesianGrid vertical={false} stroke="#edf0eb" />
                <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fill: '#8a958d', fontSize: 11 }} />
                <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#8a958d', fontSize: 10 }} />
                <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3' }} />
                <Area type="monotone" dataKey="modeledYieldIndex" name="Simulated response index" stroke="#58a27e" strokeWidth={2.5} fill="url(#yieldFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footnote">Simulated index has no yield units and is not calibrated to a crop or farm.</div>
        </Card>
      </div>
      <div className="history-provenance"><Wind size={16} /><span><strong>Observed vs. simulated:</strong> No observations are currently connected. All climate series are labeled synthetic assumptions; the response index is a simulated illustration.</span><Thermometer size={16} /></div>
    </>
  )
}
