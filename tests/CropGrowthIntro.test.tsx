import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CropGrowthIntro } from '../src/components/CropGrowthIntro'

function Page() {
  const main = useRef<HTMLElement>(null)
  return <>
    <CropGrowthIntro dashboard={main} />
    <main ref={main} tabIndex={-1}>Scientific dashboard</main>
  </>
}

beforeEach(() => {
  sessionStorage.clear()
  vi.useFakeTimers()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('crop-growth intro', () => {
  it('shows immediately while the dashboard mounts and dismisses after 3.8 seconds', () => {
    render(<Page />)
    expect(screen.getByRole('button', { name: 'Skip intro' })).toBeTruthy()
    expect(screen.getByRole('main').textContent).toBe('Scientific dashboard')
    act(() => vi.advanceTimersByTime(3799))
    expect(screen.getByRole('button', { name: 'Skip intro' })).toBeTruthy()
    act(() => vi.advanceTimersByTime(1))
    expect(screen.queryByRole('button', { name: 'Skip intro' })).toBeNull()
  })

  it('skips immediately and focuses the dashboard without scrolling', () => {
    render(<Page />)
    fireEvent.click(screen.getByRole('button', { name: 'Skip intro' }))
    expect(screen.queryByRole('button', { name: 'Skip intro' })).toBeNull()
    expect(document.activeElement).toBe(screen.getByRole('main'))
  })

  it('records a visit before playback ends and plays again in a fresh session', () => {
    render(<Page />).unmount()
    const reload = render(<Page />)
    expect(screen.queryByRole('button', { name: 'Skip intro' })).toBeNull()
    reload.unmount()
    sessionStorage.clear()
    render(<Page />)
    expect(screen.getByRole('button', { name: 'Skip intro' })).toBeTruthy()
  })

  it('bypasses the intro for reduced motion', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
    render(<Page />)
    expect(screen.queryByRole('button', { name: 'Skip intro' })).toBeNull()
    expect(screen.getByRole('main')).toBeTruthy()
  })

  it('can dismiss when session storage rejects access', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Storage blocked') })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
    render(<Page />)
    fireEvent.click(screen.getByRole('button', { name: 'Skip intro' }))
    expect(screen.queryByRole('button', { name: 'Skip intro' })).toBeNull()
  })
})
