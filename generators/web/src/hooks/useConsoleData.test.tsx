// @vitest-environment jsdom
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { consoleDevelopmentSlice } from '../fixtures/consoleDevelopmentSlice'
import useConsoleData from './useConsoleData'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('useConsoleData', () => {
  it('can force the development data slice with the demo query parameter', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console/?demo=1#sources')
    vi.stubGlobal('fetch', vi.fn())

    const { result } = renderHook(() => useConsoleData())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(fetch).not.toHaveBeenCalled()
    expect(result.current.error).toBeNull()
    expect(result.current.data?.headline).toBe(consoleDevelopmentSlice.headline)
  })

  it('uses the development data slice when the API is unavailable in Vite dev', async () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_USE_API', 'false')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('backend offline')))

    const { result } = renderHook(() => useConsoleData())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.error).toBeNull()
    expect(result.current.data?.headline).toBe(consoleDevelopmentSlice.headline)
    expect(result.current.data?.integrations.length).toBeGreaterThan(0)
  })

  it('surfaces the API error when explicit API mode is requested', async () => {
    vi.stubEnv('DEV', true)
    vi.stubEnv('VITE_USE_API', 'true')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('backend offline')))

    const { result } = renderHook(() => useConsoleData())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBe('backend offline')
  })
})
