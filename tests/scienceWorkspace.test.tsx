import { readFileSync } from 'node:fs'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App'

vi.mock('react-leaflet', () => ({
  MapContainer: () => <div>Study area map</div>,
  Polygon: () => null,
  TileLayer: () => null,
}))
vi.mock('recharts', async (importOriginal) => ({
  ...await importOriginal<typeof import('recharts')>(),
  ResponsiveContainer: () => <div>Chart</div>,
}))

const view = (name: string) => fireEvent.click(within(screen.getByRole('navigation', { name: 'Primary navigation', exact: true })).getByRole('button', { name }))
let indexFailure: 'http' | 'json' | undefined

beforeEach(() => {
  indexFailure = undefined
  vi.stubGlobal('scrollTo', vi.fn())
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.endsWith('/index.json')) {
      if (indexFailure === 'http') return new Response('', { status: 503 })
      if (indexFailure === 'json') return new Response('{invalid')
    }
    return new Response(readFileSync(`public${path}`, 'utf8'))
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('science workspace flows', () => {
  it('defaults to archived science, preserves comparison settings and enters demo explicitly', async () => {
    render(<App />)
    await screen.findByText(/94 usable acquisitions out of 191/)
    expect(vi.mocked(fetch).mock.calls.every(([url]) => String(url).endsWith('/index.json'))).toBe(true)
    view('Rotation comparison')
    const window = await screen.findByLabelText('Historical window')
    fireEvent.change(window, { target: { value: 'historical_1984_1986' } })
    expect(await screen.findByText('72.61', { exact: true })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Parameter set'), { target: { value: 'low_storage' } })
    expect(await screen.findByText('137.21', { exact: true })).toBeTruthy()
    view('Decision explorer')
    expect((screen.getByLabelText('Parameter set') as HTMLSelectElement).value).toBe('low_storage')
    expect(await screen.findByRole('row', { name: /^Baseline 137.21 64.6/ })).toBeTruthy()
    view('Climate replay')
    expect(await screen.findByRole('row', { name: /^1986 68.57/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Next window' }))
    expect((await screen.findAllByRole('row', { name: /^1987 .+/ })).length).toBe(2)
  })

  it('shows a failed archive request and recovers without falling back to synthetic data', async () => {
    indexFailure = 'http'
    render(<App />)
    expect((await screen.findByRole('alert')).textContent).toContain('HTTP 503')
    expect(screen.queryByText('Synthetic fixtures active')).toBeNull()
    indexFailure = undefined
    fireEvent.click(screen.getByRole('button', { name: 'Retry science data' }))
    expect(await screen.findByText(/94 usable acquisitions out of 191/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Open synthetic demo' }))
    expect(await screen.findByText('Synthetic fixtures active')).toBeTruthy()
  })

  it('shows malformed science JSON as an error', async () => {
    indexFailure = 'json'
    render(<App />)
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText('Synthetic fixtures active')).toBeNull()
  })
})
