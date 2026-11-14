import { demoDashboard, demoFarmLocations, historicalScenarios } from '../fixtures/demo'
import type { FarmDashboardData, HistoricalScenario } from '../types/domain'

export interface HingeDataService {
  getFarmDashboard(farmId: string): Promise<FarmDashboardData>
  getHistoricalScenarios(farmId: string): Promise<HistoricalScenario[]>
}

export class DemoDataService implements HingeDataService {
  async getFarmDashboard(farmId: string): Promise<FarmDashboardData> {
    const farm = demoFarmLocations.find((item) => item.id === farmId) ?? demoDashboard.farm
    const isNorth = farmId === 'demo-farm-north'
    const isSouth = farmId === 'demo-farm-south'
    const precipitationOffset = isNorth ? 24 : isSouth ? -19 : 0
    const temperatureOffset = isNorth ? -0.8 : isSouth ? 1.1 : 0
    return {
      ...demoDashboard,
      farm,
      climate: demoDashboard.climate.map((month) => ({
        ...month,
        farmId,
        precipitationMm: Math.max(0, month.precipitationMm + Math.round(precipitationOffset / demoDashboard.climate.length)),
        temperatureC: Math.round((month.temperatureC + temperatureOffset) * 10) / 10,
      })),
      soil: {
        ...demoDashboard.soil,
        farmId,
        organicCarbonPercent: Math.round((demoDashboard.soil.organicCarbonPercent + (isNorth ? 0.3 : isSouth ? -0.2 : 0)) * 10) / 10,
      },
      vegetation: demoDashboard.vegetation.map((item) => ({ ...item, farmId })),
    }
  }

  async getHistoricalScenarios(_farmId: string): Promise<HistoricalScenario[]> {
    return historicalScenarios
  }
}

export class HttpDataService implements HingeDataService {
  private readonly baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async getFarmDashboard(farmId: string): Promise<FarmDashboardData> {
    return this.get<FarmDashboardData>(`/farms/${encodeURIComponent(farmId)}/dashboard`)
  }

  async getHistoricalScenarios(farmId: string): Promise<HistoricalScenario[]> {
    return this.get<HistoricalScenario[]>(`/farms/${encodeURIComponent(farmId)}/history`)
  }

  private async get<T>(path: string): Promise<T> {
    const base = `${this.baseUrl.replace(/\/+$/, '')}/`
    const response = await fetch(new URL(path.replace(/^\/+/, ''), base))
    if (!response.ok) throw new Error(`HINGE API request failed (${response.status}): ${path}`)
    return response.json() as Promise<T>
  }
}

const apiBaseUrl = import.meta.env.VITE_HINGE_API_BASE_URL
export const dataService: HingeDataService = apiBaseUrl
  ? new HttpDataService(apiBaseUrl)
  : new DemoDataService()
