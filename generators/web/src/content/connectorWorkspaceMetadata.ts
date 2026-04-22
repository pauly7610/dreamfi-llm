import type { ConsoleIntegration } from '../types/console'

export function workspaceTitleForSource(source: ConsoleIntegration): string {
  switch (source.id) {
    case 'jira':
      return 'Delivery board'
    case 'posthog':
      return 'Product analytics'
    case 'metabase':
      return 'Dashboard collection'
    case 'klaviyo':
      return 'Lifecycle workspace'
    case 'confluence':
      return 'Knowledge space'
    case 'ga':
      return 'Reports snapshot'
    case 'dragonboat':
      return 'Portfolio planner'
    case 'sardine':
      return 'Risk operations'
    case 'netxd':
      return 'Transaction monitor'
    default:
      return `${source.name} workspace`
  }
}

export function workspaceDescriptionForSource(source: ConsoleIntegration, fallback: string): string {
  switch (source.id) {
    case 'jira':
      return 'Review work as issues move across the board, then audit whether done work is really implemented.'
    case 'posthog':
      return 'Analyze product behavior using insight tabs, funnel breakdowns, and an event stream.'
    case 'metabase':
      return 'Open an official dashboard, inspect the verified questions behind it, and drill into the governed metric layer.'
    case 'klaviyo':
      return 'Check flow health, message performance, and lifecycle segments in one marketing workspace.'
    case 'confluence':
      return 'Browse the knowledge space the way Product would: recent pages, trusted docs, and structured page hierarchy.'
    case 'ga':
      return 'Start from the reports snapshot, then drop into realtime acquisition and event signals.'
    case 'dragonboat':
      return 'Plan and track initiatives like a portfolio layer sitting on top of delivery systems.'
    case 'sardine':
      return 'Review active fraud cases, risk rules, and signal coverage the way a modern risk ops team would.'
    case 'netxd':
      return 'Inspect payments, ledger movement, and queue monitors the way a transaction operations console would.'
    default:
      return fallback
  }
}
