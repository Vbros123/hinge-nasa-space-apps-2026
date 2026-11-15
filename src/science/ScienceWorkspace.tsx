import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { MapContainer, Polygon, TileLayer } from 'react-leaflet'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, SectionHeading } from '../components/ui'
import type { ScreenId } from '../components/Sidebar'
import { leaders, loadIndex, loadWindow, objectives, rotationIds, rotationNames } from './data'
import type { Objective, RotationId, ScienceIndex, ScienceRow } from './data'

const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const fmt = (value: number | null | undefined) => value == null ? 'Unavailable' : number.format(value)
const label = (id: string) => id.replaceAll('_', ' ')
const period = (id: string) => id.replace('historical_', '').replace('_', '–')
const colors = ['#56866a', '#6488ae', '#a77a44']
const comparisonMetrics = {
  ...objectives,
  crop_water_demand_mm: 'Crop-water demand',
  rainfall_on_crop_days_mm: 'Rainfall on planned crop days',
  living_cover_days: 'Planned living-cover days',
  calendar_slack_days_min: 'Minimum calendar slack',
}

function Details({ title, value }: { title: string; value: unknown }) {
  return <details><summary>{title}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
}
function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <Card className="science-panel"><h2>{title}</h2>{children}</Card>
}

function Farm({ index }: { index: ScienceIndex }) {
  const { manifest, vegetation } = index
  const coordinates = index.boundary.geometry.coordinates[0].map(([lng, lat]): [number, number] => [lat, lng])
  const [lat, lng] = coordinates[0]
  const [oppositeLat, oppositeLng] = coordinates[2]
  const observations = vegetation.observations.filter(row => row.quality_flag === 'usable' && row.ndvi_median !== null)
  return <>
    <div className="science-grid">
      <Panel title="Johnston County study area">
        <p>Approximate demonstration boundary. The location and agricultural use are provisional.</p>
        <div className="map-wrap"><MapContainer center={[(lat + oppositeLat) / 2, (lng + oppositeLng) / 2]} zoom={13} scrollWheelZoom={false}>
          <TileLayer attribution="© OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Polygon positions={coordinates} pathOptions={{ color: '#397354' }} />
        </MapContainer></div>
      </Panel>
      <Panel title="Weather and soil inputs">
        <p><strong>NASA POWER.</strong> {manifest.usable_weather_years.length} accepted years ({manifest.usable_weather_years.at(0)}–{manifest.usable_weather_years.at(-1)}). The source is a gridded weather product. Source grid elevation is {fmt(manifest.site.elevation_m)} m.</p>
        <p><strong>USDA SSURGO.</strong> Survey-derived soil storage scenarios. {fmt(manifest.soil_coverage.known_aoi_component_mass * 100)}% of area-weighted component mass had a usable estimate.</p>
        <ul>{Object.entries(manifest.soil_scenarios).map(([id, item]) => <li key={id}>{label(id)} · {fmt(item.value)} mm</li>)}</ul>
        <p>{manifest.soil_source}.</p>
      </Panel>
    </div>
    <Panel title="NASA HLS vegetation observations · 2025">
      <p>{vegetation.usable_observations} usable acquisitions out of {vegetation.total_observations}. Each point is an observed scene median. Gaps reflect coverage and quality screening. HLS NDVI is separate from simulated crop cover.</p>
      <div className="science-chart"><ResponsiveContainer><ScatterChart margin={{ left: 4, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="timestamp" domain={['dataMin', 'dataMax']} tickFormatter={value => new Date(value).toISOString().slice(5, 10)} />
        <YAxis dataKey="ndvi_median" name="NDVI" domain={[-1, 1]} width={40} />
        <Tooltip cursor={false} content={({ payload }) => {
          const row = payload?.[0]?.payload as (typeof observations)[number] | undefined
          return row ? <div className="science-tooltip">{row.observation_date} · NDVI {fmt(row.ndvi_median)}<br />{row.dataset_id} · {fmt(row.valid_pixel_fraction * 100)}% valid pixels</div> : null
        }} />
        <Scatter data={observations.map(row => ({ ...row, timestamp: Date.parse(row.observation_date) }))} fill={colors[0]} />
      </ScatterChart></ResponsiveContainer></div>
      <div className="science-table"><table><thead><tr><th>Season</th><th>Median NDVI</th><th>Usable scenes</th><th>Longest gap (days)</th></tr></thead><tbody>
        {vegetation.seasonal_summaries.map(row => <tr key={row.season}><th scope="row">{label(row.season)}</th><td>{fmt(row.ndvi_median_of_observations)}</td><td>{row.usable_observations}</td><td>{fmt(row.max_gap_days_including_edges)}</td></tr>)}
      </tbody></table></div>
      <Details title="Scene IDs, quality flags and observation limitations" value={vegetation} />
    </Panel>
  </>
}

function Comparison({ index, rows, metric, parameter }: { index: ScienceIndex; rows: ScienceRow[]; metric: Objective; parameter: string }) {
  const names = leaders(rows, metric).map(id => rotationNames[id])
  const paired = index.robustness.summary.paired_comparisons.filter(row => row.metric === metric && row.parameter_set_id === parameter)
  return <>
    <Panel title="Rotation trade-offs for the selected window">
      <p>{names.length ? `Lowest modeled ${objectives[metric].toLowerCase()} among eligible rotations: ${names.join(' and ')}.` : rows.some(row => row.feasible) ? 'The selected objective is unavailable for eligible rotations.' : 'No rotations are feasible under these assumptions.'}</p>
      <div className="science-chart"><ResponsiveContainer><BarChart data={rows.map(row => ({ name: row.rotation_id, value: row.feasible ? row.metrics[metric] : null }))}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tickFormatter={value => rotationNames[value as RotationId]} tick={{ fontSize: 10 }} /><YAxis unit=" mm" width={72} /><Tooltip /><Bar dataKey="value" name={objectives[metric]} unit=" mm" fill={colors[0]} />
      </BarChart></ResponsiveContainer></div>
      <div className="science-table"><table><thead><tr><th>Metric</th>{rows.map(row => <th key={row.rotation_id}>{rotationNames[row.rotation_id]}</th>)}</tr></thead><tbody>
        <tr><th scope="row">Calendar feasibility</th>{rows.map(row => <td key={row.rotation_id}>{row.feasibility_status ? label(row.feasibility_status) : row.feasible ? 'Passes modeled checks' : 'Excluded'}</td>)}</tr>
        {Object.entries(comparisonMetrics).map(([key, name]) => <tr key={key}><th scope="row" title={index.units[key]}>{name} ({key.endsWith('_mm') ? 'mm' : 'days'})</th>
          {rows.map(row => <td key={row.rotation_id}>{fmt(row.metrics[key])}</td>)}</tr>)}
      </tbody></table></div>
      <p>Rainfall on planned crop days comes from NASA POWER. The low-cover rainfall index is an exposure proxy. Water demand and deficits are modeled over the three-year window.</p>
      {rows.map(row => <Details key={row.rotation_id} title={`${rotationNames[row.rotation_id]} · assumptions and checks`} value={{
        result: row,
        calendar: parameter === 'reference'
          ? index.rotations.find(entry => entry.rotation_id === row.rotation_id)?.reference
          : index.rotations.find(entry => entry.rotation_id === row.rotation_id)?.other_parameter_sets[parameter],
        referenceExplanation: index.explanations.rotations.find(entry => entry.rotation_id === row.rotation_id),
      }} />)}
    </Panel>
    <Panel title="Paired differences against baseline across history">
      <p>{index.robustness.summary.note}</p>
      {paired.length ? <div className="science-table"><table><thead><tr><th>Rotation</th><th>Mean difference (mm)</th><th>Lower windows</th><th>Equal windows</th><th>Higher windows</th></tr></thead><tbody>
        {paired.map(row => <tr key={row.rotation_id}><th scope="row">{rotationNames[row.rotation_id]}</th><td>{fmt(row.mean_paired_difference)}</td><td>{row.blocks_lower_count}</td><td>{row.blocks_equal_count}</td><td>{row.blocks_higher_count}</td></tr>)}
      </tbody></table></div> : <p>Paired results unavailable.</p>}
    </Panel>
  </>
}

function Explorer({ index, rows, metric, parameter, selectParameter }: {
  index: ScienceIndex; rows: ScienceRow[]; metric: Objective; parameter: string; selectParameter: (id: string) => void
}) {
  const selected = rows.filter(row => row.parameter_set_id === parameter)
  const referenceLead = leaders(rows.filter(row => row.parameter_set_id === 'reference'), metric)
  const testedCases = Object.keys(index.manifest.parameter_sets).map(id => ({
    id, leaders: leaders(rows.filter(row => row.parameter_set_id === id), metric),
  }))
  const changed = testedCases.filter(entry => entry.leaders.join() !== referenceLead.join())
  return <>
    <Panel title="Explore sensitivity to model assumptions">
      <p>Each option is a discrete archived model run. Compare alternatives against the reference using the same weather window and objective.</p>
      <p><strong>{changed.length} of {testedCases.length} tested cases change the leader set.</strong> The reference leaders are {referenceLead.map(id => rotationNames[id]).join(' and ') || 'unavailable'}. A change identifies a tested case where the leader differs.</p>
      {changed.length > 0 && <ul className="science-cases">{changed.map(entry => <li key={entry.id}><button type="button" onClick={() => selectParameter(entry.id)}>
        {label(entry.id)} · {entry.leaders.map(id => rotationNames[id]).join(' and ') || 'no eligible result'}
      </button></li>)}</ul>}
      <div className="science-table"><table><thead><tr><th>Rotation</th><th>Selected (mm)</th><th>Change from reference (mm)</th><th>Feasibility</th></tr></thead><tbody>
        {selected.map(row => <tr key={row.rotation_id}><th scope="row">{rotationNames[row.rotation_id]}</th><td>{fmt(row.metrics[metric])}</td><td>{parameter === 'reference' ? 'Reference' : fmt(row.delta_vs_reference?.[metric])}</td><td>{row.feasible ? 'Eligible under modeled assumptions' : 'Excluded'}</td></tr>)}
      </tbody></table></div>
      <Details title="Selected parameter definition" value={index.manifest.parameter_sets[parameter]} />
    </Panel>
    <Comparison index={index} rows={selected} metric={metric} parameter={parameter} />
  </>
}

function Replay({ index, rows, metric, scenario, selectScenario }: {
  index: ScienceIndex; rows: ScienceRow[]; metric: Objective; scenario: string; selectScenario: (id: string) => void
}) {
  const position = index.manifest.scenario_ids.indexOf(scenario)
  const series: ({ year: string } & Partial<Record<RotationId, number | null>>)[] = Object.keys(rows[0]?.by_year ?? {}).map(year => ({
    year,
    ...Object.fromEntries(rows.map(row => [row.rotation_id, row.by_year?.[year]?.[metric]])),
  }))
  return <>
  <Panel title="NASA POWER weather in the selected window">
    <p>Precipitation sums and arithmetic mean temperatures use all accepted daily grid values for each year.</p>
    <div className="science-table"><table><thead><tr><th>Year</th><th>Precipitation (mm)</th><th>Mean temperature (°C)</th><th>Daily records</th></tr></thead><tbody>
      {series.map(({ year }) => <tr key={year}><th scope="row">{year}</th><td>{fmt(index.annualWeather[year]?.precipitationMm)}</td><td>{fmt(index.annualWeather[year]?.meanTemperatureC)}</td><td>{fmt(index.annualWeather[year]?.days)}</td></tr>)}
    </tbody></table></div>
  </Panel>
  <Panel title="Annual modeled responses in the reference replay">
    <p>Historical NASA POWER weather drives these modeled outcomes. Neighboring windows overlap and share weather years. The annual chart uses the reference parameters.</p>
    <div className="science-controls">
      <button type="button" disabled={position === 0} onClick={() => selectScenario(index.manifest.scenario_ids[position - 1])}>Previous window</button>
      <button type="button" disabled={position === index.manifest.scenario_ids.length - 1} onClick={() => selectScenario(index.manifest.scenario_ids[position + 1])}>Next window</button>
    </div>
    <div className="science-chart"><ResponsiveContainer><BarChart data={series}>
      <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="year" /><YAxis unit=" mm" width={70} /><Tooltip /><Legend />
      {rotationIds.map((id, i) => <Bar key={id} dataKey={id} name={rotationNames[id]} unit=" mm" fill={colors[i]} />)}
    </BarChart></ResponsiveContainer></div>
    <div className="science-table"><table><thead><tr><th>Year</th>{rotationIds.map(id => <th key={id}>{rotationNames[id]} (mm)</th>)}</tr></thead><tbody>
      {series.map(row => <tr key={row.year}><th scope="row">{row.year}</th>{rotationIds.map(id => <td key={id}>{fmt(row[id])}</td>)}</tr>)}
    </tbody></table></div>
  </Panel>
  </>
}

function Evidence({ index }: { index: ScienceIndex }) {
  return <>
    <Panel title="Where the evidence comes from">
      <ul>
        <li><strong>Archived source data.</strong> NASA POWER gridded meteorology and NASA HLS 2.0 NDVI observations.</li>
        <li><strong>Survey-derived.</strong> USDA SSURGO mapped component capacity estimates.</li>
        <li><strong>Modeled.</strong> FAO-56 reference ET and a daily soil-water balance applied to three rotation calendars.</li>
        <li><strong>Assumed.</strong> Site applicability, equipment, management, planting dates and crop parameters carry the statuses in the model manifest.</li>
      </ul>
      <p>{index.manifest.review_status}. Agricultural screening for an illustrative study area.</p>
      <ul>{index.explanations.global_limitations.map(item => <li key={item.code}>{item.message}</li>)}</ul>
      <Details title="Model manifest, assumptions, accepted years and input hashes" value={index.manifest} />
      <Details title="Environmental source manifest" value={index.environment} />
      <Details title="Scientific output SHA-256 hashes" value={index.outputHashes} />
      <Details title="Metric definitions and units" value={index.units} />
    </Panel>
    <Panel title="Robustness and model sensitivity">
      <p>{index.robustness.summary.note}</p>
      <Details title="Water deficit ranking across tested assumptions" value={index.robustness.ranking_stability_water_deficit} />
      <Details title="Low-cover rainfall exposure ranking across tested assumptions" value={index.robustness.ranking_stability_rainfall_low_cover} />
      <Details title="Structured explanations and rotation evidence" value={index.explanations} />
    </Panel>
  </>
}

const titles: Record<ScreenId, string> = {
  farm: 'Farm intelligence',
  compare: 'Rotation comparison',
  boundary: 'Decision explorer',
  history: 'Historical climate replay',
  evidence: 'Evidence & uncertainty',
}

export function ScienceWorkspace({ screen }: { screen: ScreenId }) {
  const [index, setIndex] = useState<ScienceIndex>()
  const [scenario, setScenario] = useState('')
  const [parameter, setParameter] = useState('reference')
  const [metric, setMetric] = useState<Objective>('water_deficit_mm')
  const [loaded, setLoaded] = useState<{ scenario: string; rows: ScienceRow[] }>()
  const [failure, setFailure] = useState<{ scope: string; detail: string }>()
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    loadIndex(controller.signal).then(data => {
      if (controller.signal.aborted) return
      setIndex(data)
      setScenario(previous => data.manifest.scenario_ids.includes(previous) ? previous : data.manifest.scenario_ids.at(-1)!)
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setFailure({ scope: 'index', detail: error.message })
    })
    return () => controller.abort()
  }, [retry])

  useEffect(() => {
    if (!index || !scenario) return
    const controller = new AbortController()
    loadWindow(index, scenario, controller.signal).then(rows => {
      if (!controller.signal.aborted) {
        setLoaded({ scenario, rows })
        setFailure(previous => previous?.scope === scenario ? undefined : previous)
      }
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setFailure({ scope: scenario, detail: error.message })
    })
    return () => controller.abort()
  }, [index, scenario])

  const rows = loaded?.scenario === scenario ? loaded.rows : undefined
  const needsRows = screen !== 'farm' && screen !== 'evidence'
  const error = failure?.scope === 'index' || (needsRows && failure?.scope === scenario) ? failure : undefined
  return <div className="science-workspace">
    <SectionHeading eyebrow="FIELD SHIFT · JOHNSTON COUNTY, NC" title={titles[screen]} description="Explore crop-rotation trade-offs using archived NASA weather, USDA soil survey data and precomputed scientific results." />
    <div className="science-status"><strong>Archived environmental analysis</strong><span>One study area · {index?.manifest.model_version ?? 'Screening model'} · Research demonstration</span></div>
    {error && <div className="error-state" role="alert">{error.detail} <button type="button" onClick={() => { setFailure(undefined); setLoaded(undefined); setRetry(value => value + 1) }}>Retry science data</button></div>}
    {!error && !index && <p role="status">Loading scientific data…</p>}
    {index && needsRows && <div className="science-controls">
      <label>Historical window<select value={scenario} onChange={event => setScenario(event.target.value)}>{index.manifest.scenario_ids.map(id => <option key={id} value={id}>{period(id)}</option>)}</select></label>
      {screen !== 'history' && <label>Parameter set<select value={parameter} onChange={event => setParameter(event.target.value)}>{Object.keys(index.manifest.parameter_sets).sort((a, b) => a === 'reference' ? -1 : b === 'reference' ? 1 : a.localeCompare(b)).map(id => <option key={id} value={id}>{label(id)}</option>)}</select></label>}
      <label>Objective<select value={metric} onChange={event => setMetric(event.target.value as Objective)}>{Object.entries(objectives).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
    </div>}
    {index && !error && !rows && needsRows && <p role="status">Loading historical window…</p>}
    {index && !error && screen === 'farm' && <Farm index={index} />}
    {index && !error && screen === 'evidence' && <Evidence index={index} />}
    {index && rows && !error && screen === 'compare' && <Comparison index={index} rows={rows.filter(row => row.parameter_set_id === parameter)} metric={metric} parameter={parameter} />}
    {index && rows && !error && screen === 'boundary' && <Explorer index={index} rows={rows} metric={metric} parameter={parameter} selectParameter={setParameter} />}
    {index && rows && !error && screen === 'history' && <Replay index={index} rows={rows.filter(row => row.parameter_set_id === 'reference')} metric={metric} scenario={scenario} selectScenario={setScenario} />}
  </div>
}
