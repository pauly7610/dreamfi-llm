import { useCallback, useEffect, useState } from 'react'

import {
  consoleDevelopmentSlice,
  shouldForceDevelopmentSlice,
  shouldUseDevelopmentSlice,
} from '../content/consoleDevelopmentSlice'
import type { ConsolePayload } from '../types/console'

type UseConsoleDataResult = {
  data: ConsolePayload | null
  loading: boolean
  error: string | null
  retry: () => void
}

function useConsoleData(): UseConsoleDataResult {
  const [data, setData] = useState<ConsolePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [requestKey, setRequestKey] = useState(0)

  const retry = useCallback(() => {
    setRequestKey((value) => value + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    async function loadConsoleData() {
      try {
        setLoading(true)
        if (shouldForceDevelopmentSlice()) {
          setData(consoleDevelopmentSlice)
          setError(null)
          return
        }
        const response = await fetch('/api/console', { signal: controller.signal })
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`)
        }
        const payload = (await response.json()) as ConsolePayload
        setData(payload)
        setError(null)
      } catch (loadError) {
        if (controller.signal.aborted) {
          return
        }
        if (shouldUseDevelopmentSlice()) {
          setData(consoleDevelopmentSlice)
          setError(null)
          return
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load console data')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadConsoleData()

    return () => {
      controller.abort()
    }
  }, [requestKey])

  return { data, loading, error, retry }
}

export default useConsoleData
