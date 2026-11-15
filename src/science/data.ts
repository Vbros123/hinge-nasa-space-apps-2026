export const rotationNames = {
  rotation_a: 'Baseline',
  rotation_b: 'Rye cover',
  rotation_c: 'Wheat + double-crop soybean',
}
export type RotationId = keyof typeof rotationNames
export const rotationIds = Object.keys(rotationNames) as RotationId[]
export const objectives = {
  water_deficit_mm: 'Unmet crop-water demand',
  rainfall_low_cover_index_mm: 'Rainfall exposure under low cover',
}
export type Objective = keyof typeof objectives
type Metrics = Record<string, number | null>
export interface ScienceRow {
  scenario_id: string
  parameter_set_id: string
  rotation_id: RotationId
  feasible: boolean
  assumption_status: string
  feasibility_status?: string
  weather_sha256_16: string
  metrics: Metrics
  by_year?: Record<string, Metrics>
  delta_vs_reference?: Metrics
  warnings?: unknown[]
  data_quality_flags?: unknown[]
  parameters?: unknown
}
export interface ScienceIndex {
  schema: string
  manifest: {
    model_version: string
    scenario_ids: string[]
    usable_weather_years: number[]
    excluded_years: Record<string, string>
    parameter_sets: Record<string, { category: string; status: string }>
    site: { latitude_deg: number; elevation_m: number }
    soil_scenarios: Record<string, { value: number; status: string }>
    soil_coverage: { known_aoi_component_mass: number; unknown_aoi_component_mass: number }
    soil_source: string
    et0_method: string
    review_status: string
    limitations: string[]
  }
  environment: unknown
  boundary: { geometry: { coordinates: number[][][] } }
  outputHashes: Record<string, string>
  annualWeather: Record<string, { precipitationMm: number; meanTemperatureC: number; days: number }>
  units: Record<string, string>
  rotations: { rotation_id: RotationId; reference: unknown; other_parameter_sets: Record<string, unknown> }[]
  explanations: {
    global_limitations: { code: string; message: string }[]
    rotations: { rotation_id: RotationId; explanation_text: string; assumptions: unknown[]; warnings: unknown[] }[]
  }
  robustness: {
    summary: { note: string; paired_comparisons: {
      parameter_set_id: string; rotation_id: RotationId; metric: string; mean_paired_difference: number | null;
      blocks_lower_count: number; blocks_equal_count: number; blocks_higher_count: number
    }[] }
    ranking_stability_water_deficit: unknown
    ranking_stability_rainfall_low_cover: unknown
  }
  vegetation: {
    total_observations: number
    usable_observations: number
    limitations: string[]
    seasonal_summaries: { season: string; usable_observations: number; ndvi_median_of_observations: number | null; max_gap_days_including_edges: number | null }[]
    observations: { observation_date: string; dataset_id: string; quality_flag: string; valid_pixel_fraction: number; spatial_coverage_fraction: number; ndvi_median: number | null; scene_ids: string[] }[]
  }
}

function requireData(condition: unknown, context: string): asserts condition {
  if (!condition) throw new Error(`Invalid scientific data (${context})`)
}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function textList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string')
}

function numericTree(value: unknown): boolean {
  if (typeof value === 'number') return Number.isFinite(value)
  if (Array.isArray(value)) return value.every(numericTree)
  if (object(value)) return Object.values(value).every(numericTree)
  return true
}

export function validateIndex(value: unknown): ScienceIndex {
  requireData(object(value) && numericTree(value) && value.schema === 'hinge.science.v1', 'index schema')
  const { manifest, environment, boundary, outputHashes, units, rotations, explanations, robustness, vegetation } = value
  requireData(object(manifest) && object(environment) && object(boundary) && object(outputHashes) && object(units), 'provenance')
  requireData(Object.keys(outputHashes).length === 8 && Object.values(outputHashes).every(hash => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash)), 'source hashes')
  requireData(Array.isArray(manifest.scenario_ids) && manifest.scenario_ids.length > 0 &&
    manifest.scenario_ids.every(id => typeof id === 'string' && /^historical_\d{4}_\d{4}$/.test(id)) &&
    new Set(manifest.scenario_ids).size === manifest.scenario_ids.length &&
    object(manifest.parameter_sets) && object(manifest.parameter_sets.reference) &&
    Object.values(manifest.parameter_sets).every(set => object(set) && typeof set.status === 'string'), 'scenario catalog')
  requireData(Array.isArray(manifest.usable_weather_years) && object(manifest.excluded_years) &&
    manifest.usable_weather_years.every(year => Number.isInteger(year)) &&
    object(manifest.site) && Number.isFinite(manifest.site.elevation_m) &&
    object(manifest.soil_scenarios) && Object.values(manifest.soil_scenarios)
      .every(soil => object(soil) && Number.isFinite(soil.value) && typeof soil.status === 'string') &&
    object(manifest.soil_coverage) && Number.isFinite(manifest.soil_coverage.known_aoi_component_mass) &&
    typeof manifest.soil_source === 'string' && typeof manifest.review_status === 'string' &&
    typeof manifest.model_version === 'string' && textList(manifest.limitations), 'model manifest')
  requireData(object(boundary.geometry) && Array.isArray(boundary.geometry.coordinates) &&
    boundary.geometry.coordinates[0]?.length >= 4 &&
    boundary.geometry.coordinates[0].every((point: unknown) => Array.isArray(point) &&
      point.length === 2 && point.every(Number.isFinite)), 'study boundary')
  requireData(Array.isArray(rotations) && rotations.length === rotationIds.length &&
    rotationIds.every(id => rotations.some(row => object(row) && row.rotation_id === id &&
      object(row.reference) && object(row.other_parameter_sets))), 'rotations')
  requireData(object(explanations) && Array.isArray(explanations.rotations) && Array.isArray(explanations.global_limitations) &&
    object(robustness) && object(robustness.summary) && Array.isArray(robustness.summary.paired_comparisons) &&
    object(vegetation) && Array.isArray(vegetation.limitations) && Array.isArray(vegetation.observations) &&
    Array.isArray(vegetation.seasonal_summaries) && vegetation.total_observations === vegetation.observations.length &&
    vegetation.usable_observations === vegetation.observations.filter(row => object(row) && row.quality_flag === 'usable').length, 'evidence')
  requireData(explanations.global_limitations.every(item => object(item) &&
    typeof item.code === 'string' && typeof item.message === 'string') &&
    typeof robustness.summary.note === 'string' &&
    robustness.summary.paired_comparisons.every(item => object(item) && typeof item.rotation_id === 'string' &&
      rotationIds.includes(item.rotation_id as RotationId) && typeof item.metric === 'string' &&
      typeof item.parameter_set_id === 'string' &&
      (item.mean_paired_difference === null || Number.isFinite(item.mean_paired_difference)) &&
      [item.blocks_lower_count, item.blocks_equal_count, item.blocks_higher_count].every(Number.isInteger)),
    'explanations and robustness')
  requireData(vegetation.observations.every(row => object(row) && typeof row.observation_date === 'string' &&
    Number.isFinite(Date.parse(row.observation_date)) && typeof row.quality_flag === 'string' &&
    typeof row.dataset_id === 'string' && textList(row.scene_ids) && Number.isFinite(row.valid_pixel_fraction) &&
    Number.isFinite(row.spatial_coverage_fraction) && (row.ndvi_median === null || Number.isFinite(row.ndvi_median))) &&
    vegetation.seasonal_summaries.every(row => object(row) && typeof row.season === 'string' &&
      Number.isInteger(row.usable_observations) &&
      (row.max_gap_days_including_edges === null || Number.isInteger(row.max_gap_days_including_edges)) &&
      (row.ndvi_median_of_observations === null || Number.isFinite(row.ndvi_median_of_observations))),
    'HLS observations')
  const annualWeather = value.annualWeather
  requireData(object(annualWeather) && manifest.usable_weather_years.every(year => {
    const row = annualWeather[String(year)]
    return object(row) && Number.isFinite(row.precipitationMm) && Number.isFinite(row.meanTemperatureC) &&
      (row.days === 365 || row.days === 366)
  }), 'annual NASA POWER aggregates')
  requireData(Object.keys(objectives).every(key => typeof units[key] === 'string'), 'objective units')
  return value as unknown as ScienceIndex
}

export function validateWindow(value: unknown, index: ScienceIndex, scenario: string): ScienceRow[] {
  requireData(index.manifest.scenario_ids.includes(scenario), 'unknown historical window')
  const parameters = Object.keys(index.manifest.parameter_sets)
  requireData(Array.isArray(value) && value.length === parameters.length * rotationIds.length, 'window size')
  const keys = new Set<string>()
  let weatherHash: unknown
  for (const row of value) {
    requireData(object(row) && numericTree(row) && row.scenario_id === scenario && typeof row.rotation_id === 'string' &&
      rotationIds.includes(row.rotation_id as RotationId) && typeof row.parameter_set_id === 'string' &&
      parameters.includes(row.parameter_set_id) && typeof row.feasible === 'boolean' &&
      typeof row.assumption_status === 'string' && typeof row.weather_sha256_16 === 'string' &&
      /^[a-f0-9]{16}$/.test(row.weather_sha256_16) && object(row.metrics), 'window row')
    weatherHash ??= row.weather_sha256_16
    requireData(weatherHash === row.weather_sha256_16, 'paired weather data')
    const metrics = row.metrics
    requireData(Object.keys(index.units).every(key => metrics[key] === null || Number.isFinite(metrics[key])), 'window metrics')
    const objectiveKeys = Object.keys(objectives)
    const validObjectives = (entry: unknown) => object(entry) &&
      objectiveKeys.every(key => entry[key] === null || Number.isFinite(entry[key]))
    if (row.parameter_set_id === 'reference') {
      const years = row.by_year
      const firstYear = Number(scenario.split('_')[1])
      requireData(object(years) && [firstYear, firstYear + 1, firstYear + 2]
        .every(year => validObjectives(years[String(year)])), 'annual reference outcomes')
    } else {
      requireData(validObjectives(row.delta_vs_reference), 'parameter deltas')
    }
    const key = `${row.rotation_id}/${row.parameter_set_id}`
    requireData(!keys.has(key), 'duplicate scenario row')
    keys.add(key)
  }
  return value as ScienceRow[]
}

async function request(file: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(`${import.meta.env.BASE_URL}science/v1/${file}.json`, { signal })
  if (!response.ok) throw new Error(`Science request failed (HTTP ${response.status})`)
  return response.json()
}

export async function loadIndex(signal?: AbortSignal) {
  return validateIndex(await request('index', signal))
}

export async function loadWindow(index: ScienceIndex, scenario: string, signal?: AbortSignal) {
  requireData(index.manifest.scenario_ids.includes(scenario), 'unknown historical window')
  return validateWindow(await request(scenario, signal), index, scenario)
}

export function leaders(rows: ScienceRow[], metric: Objective): RotationId[] {
  const eligible = rows.filter(row => row.feasible && row.metrics[metric] != null)
  const best = Math.min(...eligible.map(row => row.metrics[metric]!))
  return eligible.filter(row => row.metrics[metric] === best).map(row => row.rotation_id)
}
