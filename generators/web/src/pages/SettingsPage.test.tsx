// @vitest-environment jsdom
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import type { SettingsConnector, SettingsStatus } from '../types/console'
import SettingsPage from './SettingsPage'

const baseConnector: SettingsConnector = {
  activation_status: 'inactive',
  activated_at: null,
  blockers: ['credential', 'document_set', 'freshness_probe', 'persistence'],
  can_activate: false,
  category: 'planning',
  connector_id: 'jira',
  credential: {
    label: null,
    masked: null,
    status: 'missing',
    validated_at: null,
  },
  document_set_id: null,
  document_set_name: 'dreamfi-source-jira',
  document_set_present: false,
  expected_document_set: 'dreamfi-source-jira',
  freshest_document_at: null,
  href: '/console/settings?connector=jira',
  last_probe_at: null,
  metadata_keys: ['dreamfi_scope.source_ids'],
  name: 'Jira',
  purpose: 'Sprints and delivery state',
  retrieval_status: 'not_checked',
  used_for: ['technical-prd'],
  validation_error: null,
  validation_status: 'not_validated',
}

function settingsStatus(connector: SettingsConnector = baseConnector): SettingsStatus {
  return {
    connectors: [connector],
    environment: {
      checks: [
        { configured: true, detail: 'Onyx is configured.', name: 'ONYX_BASE_URL', present: true },
      ],
      placeholder_values: [],
      ready: false,
    },
    failures: ['persistence', 'connectors'],
    jobs: {
      connector_health_checks: { active_connector_count: 0, configured: false },
      replay: { due_schedule_count: 0, error_count_24h: 0, latest_run: null },
    },
    persistence: {
      alembic_version: null,
      audit: { enabled: true },
      checks: [
        { detail: 'SQLite is local-only.', name: 'persistent_postgres', passed: false },
      ],
      counts: { audit_events: 1, connector_settings: 0 },
      expected_alembic_head: '20260506_0009',
      ready: false,
      uses_sqlite: true,
    },
    status: 'blocked',
    summary: {
      active_connector_count: 0,
      blocked_connector_count: 1,
      configured_connector_count: connector.credential.status === 'saved' ? 1 : 0,
      connector_count: 1,
    },
  }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

describe('SettingsPage', () => {
  it('saves connector keys without rendering the raw secret', async () => {
    const savedConnector: SettingsConnector = {
      ...baseConnector,
      blockers: ['document_set', 'freshness_probe', 'persistence'],
      credential: {
        label: 'prod jira',
        masked: '****3456',
        status: 'saved',
        validated_at: '2026-05-06T20:00:00Z',
      },
      validation_status: 'validated',
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(settingsStatus()), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ connector: savedConnector, settings_status: 'blocked' }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)

    renderWithConsoleWorkspace(<SettingsPage />, { path: '/console/settings' })

    await screen.findByLabelText('Jira API key')
    fireEvent.change(screen.getByLabelText('Jira API key'), { target: { value: 'jira-live-token-123456' } })
    fireEvent.change(screen.getByLabelText('Jira key label'), { target: { value: 'prod jira' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/settings/connectors/jira/secret')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1].body))).toMatchObject({
      api_key: 'jira-live-token-123456',
      label: 'prod jira',
    })
    await screen.findByText('****3456')
    expect((screen.getByLabelText('Jira API key') as HTMLInputElement).value).toBe('')
    expect(document.body.textContent).not.toContain('jira-live-token-123456')
  })

  it('activates ready connectors and refreshes console data', async () => {
    const readyConnector: SettingsConnector = {
      ...baseConnector,
      activation_status: 'inactive',
      blockers: [],
      can_activate: true,
      credential: {
        label: null,
        masked: '****3456',
        status: 'saved',
        validated_at: '2026-05-06T20:00:00Z',
      },
      document_set_id: 1,
      document_set_present: true,
      freshest_document_at: '2026-05-06T20:00:00Z',
      retrieval_status: 'fresh',
      validation_status: 'validated',
    }
    const activeConnector: SettingsConnector = {
      ...readyConnector,
      activated_at: '2026-05-06T20:01:00Z',
      activation_status: 'active',
      can_activate: true,
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(settingsStatus(readyConnector)), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ connector: activeConnector, settings_status: 'ready' }), { status: 200 }))
    const onConsoleDataChanged = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderWithConsoleWorkspace(<SettingsPage onConsoleDataChanged={onConsoleDataChanged} />, {
      path: '/console/settings',
    })

    await screen.findByText('****3456')
    fireEvent.click(screen.getByRole('button', { name: 'Activate' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/settings/connectors/jira/activate')
    await screen.findByText('active')
    expect(onConsoleDataChanged).toHaveBeenCalledTimes(1)
  })
})
