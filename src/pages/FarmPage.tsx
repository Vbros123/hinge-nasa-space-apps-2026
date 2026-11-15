import { useMemo } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowDownRight, ArrowUpRight, Droplets, MapPin, Sprout, Sun, ThermometerSun } from 'lucide-react'
import { FarmMap } from '../components/FarmMap'
import { Card, Eyebrow, MetricCard, SectionHeading, StatusPill } from '../components/ui'
import { demoFarmLocations } from '../fixtures/demo'
import type { FarmDashboardData, RotationComparison } from '../types/domain'

export function FarmPage({
  dashboard,
  comparison,
  onFarmChange,
}: {
  dashboard: FarmDashboardData
  comparison: RotationComparison
  onFarmChange: (farmId: string) => void
}) {
  const farm = demoFarmLocations.find((option) => option.id === dashboard.farm.id) ?? dashboard.farm
  const monthlyData = useMemo(() => dashboard.climate.map((month, index) => ({
    month: new Date(`${month.date}T00:00:00`).toLocaleString('en', { month: 'short' }),
    rainfall: month.precipitationMm,
    moisture: month.soilMoisturePercent,
    ndvi: dashboard.vegetation[index]?.ndvi
      ? Math.round((dashboard.vegetation[index].ndvi ?? 0) * 100)
      : null,
  })), [dashboard])
  const top = comparison.results.find((result) => result.rotationId === comparison.preferredRotationId)
  const topRotation = dashboard.rotations.find((rotation) => rotation.id === top?.rotationId)
  const seasonalRainfall = dashboard.climate.reduce((sum, month) => sum + month.precipitationMm, 0)
  const meanTemperature = dashboard.climate.reduce((sum, month) => sum + month.temperatureC, 0) / dashboard.climate.length

  return (
    <>
      <SectionHeading
        eyebrow="FIELD OVERVIEW / 01"
        title="Farm intelligence"
        description="A clear read on the conditions shaping your next rotation decision."
        action={
          <label className="farm-select-wrap">
            <MapPin size={15} />
            <select value={farm.id} onChange={(event) => onFarmChange(event.target.value)} aria-label="Select demonstration farm">
              {demoFarmLocations.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
            </select>
          </label>
        }
      />
      <div className="demo-banner"><span className="banner-dot" /><strong>SYNTHETIC DEMO</strong><span>Illustrative scenario data only — no authentic NASA observations are connected.</span><StatusPill status="assumed" /></div>
      <div className="metric-grid">
        <MetricCard label="Seasonal rainfall" value={String(seasonalRainfall)} unit="mm" trend={<><ArrowDownRight size={13} /> synthetic</>} icon={<Droplets size={18} />} tone="blue" />
        <MetricCard label="Mean temperature" value={meanTemperature.toFixed(1)} unit="°C" trend={<><ArrowUpRight size={13} /> synthetic</>} icon={<ThermometerSun size={18} />} tone="amber" />
        <MetricCard label="Soil water capacity" value={String(dashboard.soil.availableWaterCapacityMmPerM)} unit="mm/m" trend="Silt loam profile" icon={<Sprout size={18} />} tone="green" />
        <MetricCard label="Rotation leader" value={topRotation?.name.split(' · ')[0] ?? '—'} unit="" trend={top ? `${top.totalScore} modeled points` : 'No eligible option'} icon={<Sun size={18} />} tone="slate" />
      </div>
      <div className="farm-grid">
        <Card className="map-card">
          <div className="card-heading"><div><Eyebrow>LOCATION CONTEXT</Eyebrow><h2>{farm.name}</h2><p>{farm.region} · {farm.areaHectares} ha</p></div><span className="map-coordinates">{farm.latitude.toFixed(2)}°N<br />{Math.abs(farm.longitude).toFixed(2)}°W</span></div>
          <FarmMap farm={farm} onSelect={onFarmChange} />
          <div className="location-meta"><span><i className="location-dot" /> Selected demonstration site</span><span>{farm.elevationMeters.toLocaleString()} m elevation</span></div>
        </Card>
        <Card className="climate-card">
          <div className="card-heading"><div><Eyebrow>SEASONAL SIGNAL</Eyebrow><h2>Water & canopy pulse</h2><p>Monthly climate and vegetation illustration</p></div><StatusPill status="assumed" /></div>
          <div className="legend-row"><span><i className="legend-line rain-line" />Rainfall</span><span><i className="legend-line veg-line" />Canopy index × 100</span></div>
          <div className="chart-large">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthlyData} margin={{ top: 10, right: 12, bottom: 0, left: -18 }}>
                <defs>
                  <linearGradient id="rainFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#77a8cb" stopOpacity={0.3} /><stop offset="100%" stopColor="#77a8cb" stopOpacity={0.02} /></linearGradient>
                  <linearGradient id="vegFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#54a383" stopOpacity={0.22} /><stop offset="100%" stopColor="#54a383" stopOpacity={0.02} /></linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#edf0eb" />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#88928c', fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#88928c', fontSize: 11 }} />
                <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e6e9e3', fontSize: 12 }} />
                <Area type="monotone" dataKey="rainfall" name="Rainfall (mm)" stroke="#6c9ebf" strokeWidth={2} fill="url(#rainFill)" />
                <Area type="monotone" dataKey="ndvi" name="Canopy index × 100" stroke="#55a180" strokeWidth={2} fill="url(#vegFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footnote">Vegetation values are synthetic NDVI-like indices, not satellite-derived products.</div>
        </Card>
      </div>
      <div className="farm-lower-grid">
        <Card className="soil-card">
          <div className="card-heading"><div><Eyebrow>SOIL PROFILE</Eyebrow><h2>Working soil assumptions</h2></div><StatusPill status={dashboard.soil.status} /></div>
          <div className="soil-stats">
            <div><span>Texture class</span><strong>{dashboard.soil.texture}</strong></div>
            <div><span>Organic carbon</span><strong>{dashboard.soil.organicCarbonPercent}%</strong></div>
            <div><span>Available water</span><strong>{dashboard.soil.availableWaterCapacityMmPerM} <small>mm/m</small></strong></div>
            <div><span>pH</span><strong>{dashboard.soil.ph}</strong></div>
          </div>
          <div className="soft-note"><Sprout size={15} /> Replace these profile values with field or soil-survey data before decision use.</div>
        </Card>
        <Card className="insight-card">
          <div className="insight-icon"><Sun size={18} /></div><Eyebrow>MODEL READOUT</Eyebrow>
          <h2>{topRotation?.name ?? (comparison.decisionState === 'no-feasible' ? 'No feasible rotation' : 'No supported leader')}</h2>
          <p>{comparison.explanation} This is a relative demonstration score, not a crop-yield prediction.</p>
          <div className="insight-score"><span>Current modeled score</span><strong>{top?.totalScore ?? '—'}<small> / 100</small></strong></div>
          <button className="text-button" onClick={() => document.dispatchEvent(new CustomEvent('hinge:navigate', { detail: 'boundary' }))}>Explore what changes the ranking <span>→</span></button>
        </Card>
      </div>
    </>
  )
}
