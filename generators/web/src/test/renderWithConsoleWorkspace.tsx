import { render, type RenderResult } from '@testing-library/react'
import type { ReactElement } from 'react'

import { ConsoleWorkspaceProvider } from '../components/console/ConsoleWorkspaceContext'
import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { currentConsoleLocation } from '../utils/consoleNavigation'
import type { ConsoleIntegration } from '../types/console'

type RenderWithConsoleWorkspaceOptions = {
  integrations?: ConsoleIntegration[]
  path?: string
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
      location={currentConsoleLocation()}
      integrations={options.integrations ?? consoleDevelopmentSlice.integrations}
    >
      {ui}
    </ConsoleWorkspaceProvider>,
  )
}
