import { render, type RenderResult } from '@testing-library/react'
import type { ReactElement } from 'react'

import { ConsoleWorkspaceProvider } from '../components/console/ConsoleWorkspaceContext'
import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import type { ConsoleIntegration, ConsoleTopicRecord, SourceInsight } from '../types/console'
import { currentConsoleLocation } from '../utils/consoleNavigation'

type RenderWithConsoleWorkspaceOptions = {
  integrations?: ConsoleIntegration[]
  initialCustomTopics?: ConsoleTopicRecord[]
  path?: string
  persistTopicsToBackend?: boolean
  sourceInsights?: SourceInsight[]
}

export function renderWithConsoleWorkspace(
  ui: ReactElement,
  options: RenderWithConsoleWorkspaceOptions = {},
): RenderResult {
  if (options.path) {
    window.history.replaceState(null, '', options.path)
  }

  return render(
    <ConsoleWorkspaceProvider
      initialCustomTopics={options.initialCustomTopics}
      location={currentConsoleLocation()}
      integrations={options.integrations ?? consoleDevelopmentSlice.integrations}
      sourceInsights={options.sourceInsights ?? consoleDevelopmentSlice.source_insights}
      persistTopicsToBackend={options.persistTopicsToBackend ?? false}
    >
      {ui}
    </ConsoleWorkspaceProvider>,
  )
}
