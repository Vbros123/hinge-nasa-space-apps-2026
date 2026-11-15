import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { leaders, validateIndex, validateWindow } from '../src/science/data'

const directory = resolve('public/science/v1')
const read = (name: string): unknown => JSON.parse(readFileSync(resolve(directory, name), 'utf8'))
const index = validateIndex(read('index.json'))
const scenario = 'historical_1984_1986'
const firstWindow = () => validateWindow(read(`${scenario}.json`), index, scenario)

describe('archived Phase 3 frontend contract', () => {
  it('validates the complete archived grid', () => {
    expect(readdirSync(directory).filter(file => file.startsWith('historical_'))).toHaveLength(40)
    expect(index.manifest.usable_weather_years).toHaveLength(42)
    expect(index.vegetation.usable_observations).toBe(94)
    const rows = index.manifest.scenario_ids.flatMap(id => validateWindow(read(`${id}.json`), index, id))
    expect(rows).toHaveLength(2880)
  })

  it('keeps the archived scenario, reference and sensitivity values in source units', () => {
    const rows = firstWindow()
    const baseline = rows.find(row => row.rotation_id === 'rotation_a' && row.parameter_set_id === 'reference')
    const lowStorage = rows.find(row => row.rotation_id === 'rotation_a' && row.parameter_set_id === 'low_storage')
    expect(baseline?.metrics.water_deficit_mm).toBe(72.605162)
    expect(baseline?.by_year?.['1986'].water_deficit_mm).toBe(68.573604)
    expect(lowStorage?.delta_vs_reference?.water_deficit_mm).toBe(64.6)
  })

  it('rejects cross-window, repeated and non-finite records', () => {
    const rows = firstWindow()
    expect(() => validateWindow(rows, index, 'historical_1985_1987')).toThrow()
    expect(() => validateWindow([rows[1], ...rows.slice(1)], index, scenario)).toThrow()
    const invalid = structuredClone(rows)
    invalid[0].metrics.water_deficit_mm = Infinity
    expect(() => validateWindow(invalid, index, scenario)).toThrow()
  })

  it('rejects empty catalogs, missing evidence and unsupported parameter sets', () => {
    expect(() => validateIndex({})).toThrow()
    const withoutEvidence = structuredClone(index)
    Reflect.deleteProperty(withoutEvidence, 'vegetation')
    expect(() => validateIndex(withoutEvidence)).toThrow()
    const rows = firstWindow()
    rows[0].parameter_set_id = 'not_in_archive'
    expect(() => validateWindow(rows, index, scenario)).toThrow()
  })

  it('handles ties and omits missing and excluded candidates', () => {
    const rows = firstWindow().filter(row => row.parameter_set_id === 'reference')
    rows[0].metrics.water_deficit_mm = 12
    rows[1].metrics.water_deficit_mm = 12
    rows[2].metrics.water_deficit_mm = 0
    rows[2].feasible = false
    expect(leaders(rows, 'water_deficit_mm')).toEqual(['rotation_a', 'rotation_b'])
    rows[0].metrics.water_deficit_mm = null
    rows[1].metrics.water_deficit_mm = null
    expect(leaders(rows, 'water_deficit_mm')).toEqual([])
  })
})
