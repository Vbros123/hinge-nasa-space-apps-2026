import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpDataService } from '../src/services/api'
import { demoDashboard } from '../src/fixtures/demo'

afterEach(() => vi.unstubAllGlobals())

describe('optional HTTP integration adapter', () => {
  it('preserves a configured base path when building proposed routes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => demoDashboard,
    })
    vi.stubGlobal('fetch', fetchMock)
    const service = new HttpDataService('https://api.example.test/hinge/v1/')

    await service.getFarmDashboard('farm 7')

    expect(fetchMock).toHaveBeenCalledWith(
      new URL('farms/farm%207/dashboard', 'https://api.example.test/hinge/v1/'),
    )
  })

  it('surfaces non-success responses rather than substituting fixture data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    const service = new HttpDataService('https://api.example.test')

    await expect(service.getHistoricalScenarios('farm-7'))
      .rejects.toThrow('HINGE API request failed (503)')
  })
})
