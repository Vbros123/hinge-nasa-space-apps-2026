import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { BoundaryPage } from '../src/pages/BoundaryPage'
import { Sidebar } from '../src/components/Sidebar'
import { HistoryPage } from '../src/pages/HistoryPage'
import { demoDashboard } from '../src/fixtures/demo'
import { historicalScenarios } from '../src/fixtures/demo'
import { defaultDecisionInputs, scoreRotations } from '../src/services/decisionModel'
import type { DecisionInputs } from '../src/types/domain'

vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return { ...actual, ResponsiveContainer: () => null }
})

beforeAll(() => {
  Object.defineProperty(globalThis, 'ResizeObserver', {
    configurable: true,
    value: class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  })
})

afterEach(cleanup)

function BoundaryHarness() {
  const [inputs, setInputs] = useState<DecisionInputs>(defaultDecisionInputs)
  const comparison = scoreRotations(demoDashboard.rotations, inputs)
  return (
    <BoundaryPage
      rotations={demoDashboard.rotations}
      inputs={inputs}
      comparison={comparison}
      baselineRainMm={281}
      onChange={setInputs}
    />
  )
}

describe('Decision Boundary Explorer', () => {
  it('updates the live preference state when a scenario preset changes', () => {
    render(<BoundaryHarness />)
    expect(screen.getByText('SUPPORTED*')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Dry year' }))
    expect(screen.getByText('INSUFFICIENT')).toBeTruthy()
    expect((screen.getByRole('slider', { name: 'Precipitation shift' }) as HTMLInputElement).value).toBe('-25')
    expect((screen.getByRole('slider', { name: 'Irrigation availability' }) as HTMLInputElement).value).toBe('70')
  })
})

describe('primary navigation', () => {
  it('routes all five screen buttons to their matching screen IDs', () => {
    const navigated: string[] = []
    render(
      <Sidebar
        active="farm"
        onNavigate={(screen) => navigated.push(screen)}
        collapsed={false}
        onToggle={() => undefined}
      />,
    )
    for (const [label, screen] of [
      ['Farm intelligence', 'farm'],
      ['Rotation comparison', 'compare'],
      ['Decision explorer', 'boundary'],
      ['Climate replay', 'history'],
      ['Evidence & uncertainty', 'evidence'],
    ]) {
      fireEvent.click(screenRoleButton(label))
      expect(navigated.at(-1)).toBe(screen)
    }
  })
})

describe('Historical Climate Replay', () => {
  it('keeps the selected season and comparison season distinct', () => {
    render(<HistoryPage scenarios={historicalScenarios} />)
    fireEvent.click(screen.getByRole('button', { name: '2023' }))
    expect((screen.getByRole('combobox', { name: 'Select comparison year' }) as HTMLSelectElement).value).toBe('2018')
    expect(screen.getByText('Moderately wet scenario')).toBeTruthy()
  })
})

function screenRoleButton(label: string): HTMLElement {
  const button = [...document.querySelectorAll('button')].find((item) => item.textContent?.includes(label))
  if (!button) throw new Error(`Missing navigation button: ${label}`)
  return button
}
