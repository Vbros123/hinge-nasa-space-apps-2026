import { useEffect, useState } from 'react'
import { dataService } from '../services/api'
import type { FarmDashboardData, HistoricalScenario } from '../types/domain'

interface FarmDataState {
  farmId: string
  dashboard: FarmDashboardData | null
  history: HistoricalScenario[]
  loading: boolean
  error: string | null
}

export function useFarmData(farmId: string): FarmDataState {
  const [state, setState] = useState<FarmDataState>({
    farmId: '',
    dashboard: null,
    history: [],
    loading: true,
    error: null,
  })

  useEffect(() => {
    let active = true
    Promise.all([
      dataService.getFarmDashboard(farmId),
      dataService.getHistoricalScenarios(farmId),
    ]).then(([dashboard, history]) => {
      if (active) setState({ farmId, dashboard, history, loading: false, error: null })
    }).catch((error: unknown) => {
      if (active) setState({
        farmId,
        dashboard: null,
        history: [],
        loading: false,
        error: error instanceof Error ? error.message : 'Unable to load farm data.',
      })
    })
    return () => { active = false }
  }, [farmId])

  return state.farmId === farmId ? state : { ...state, loading: true, error: null }
}
