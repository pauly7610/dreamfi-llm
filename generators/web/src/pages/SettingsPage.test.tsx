// @vitest-environment jsdom
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import type { SettingsConnector, SettingsStatus } from '../types/console'
import SettingsPage from './SettingsPage'

const baseConnector: SettingsConnector = {
  activation_status: 'inactive',
  activated_at: null,
  blockers: ['document_set', 'freshness_probe', 'persistence'],
  can_activate: false,
  category: 'planning',
  connector_id: 'jira',
  connection_method: 'onyx_native',
  config: { missing_keys: [], values: {} },
  config_schema: [],
  credential: {
    label: null,
    masked: null,
    required: false,
    status: 'missing',
    storage: 'missing',
    usable: true,
    validated_at: null,
  },
  document_set_id: null,
  document_set_name: 'dreamfi-source-jira',
  document_set_present: false,
  expected_document_set: 'dreamfi-source-jira',
  freshest_document_at: null,
  href: '/console/settings?connector=jira',
  last_probe_at: null,
  latest_sync: null,
  metadata_keys: ['dreamfi_scope.source_ids'],
  name: 'Jira',
  purpose: 'Sprints and delivery state',
  retrieval_status: 'not_checked',
  requires_dreamfi_secret: false,
  setup_detail: 'Configure Jira credentials in Onyx, then let DreamFi validate the document set and freshness.',
  setup_method: 'Onyx native connector',
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
      configured_connector_count: connector.document_set_present || connector.credential.status === 'saved' ? 1 : 0,
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
  it('shows Onyx-native setup without a DreamFi API-key prompt', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(settingsStatus()), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    renderWithConsoleWorkspace(<SettingsPage />, { path: '/console/settings' })

    await screen.findByText('Onyx native connector')

    expect(screen.queryByLabelText('Jira DreamFi API key')).toBeNull()
    expect((screen.getByRole('button', { name: 'Validate' }) as HTMLButtonElement).disabled).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('activates ready connectors and refreshes console data', async () => {
    const readyConnector: SettingsConnector = {
      ...baseConnector,
      activation_status: 'inactive',
      blockers: [],
      can_activate: true,
      credential: {
        label: null,
        masked: null,
        required: false,
        status: 'missing',
        storage: 'missing',
        usable: true,
        validated_at: null,
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

    await screen.findByText('DreamFi stores no source secret for this setup.')
    fireEvent.click(screen.getByRole('button', { name: 'Activate' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/settings/connectors/jira/activate')
    await screen.findByText('active')
    expect(onConsoleDataChanged).toHaveBeenCalledTimes(1)
  })

  it('saves custom connector configuration before sync', async () => {
    const customConnector: SettingsConnector = {
      ...baseConnector,
      blockers: ['credential', 'configuration', 'document_set', 'freshness_probe', 'persistence'],
      category: 'metrics',
      connector_id: 'metabase',
      connection_method: 'custom_ingestion',
      config: { missing_keys: ['base_url'], values: {} },
      config_schema: [
        {
          default: null,
          help_text: 'Provider API root used by DreamFi sync jobs.',
          key: 'base_url',
          label: 'Metabase base URL',
          placeholder: 'https://metabase.company.com',
          required: true,
        },
        {
          default: '/api/card,/api/dashboard',
          help_text: 'Comma-separated paths to pull during sync.',
          key: 'endpoints',
          label: 'Endpoint paths',
          placeholder: '/api/card,/api/dashboard',
          required: false,
        },
        {
          default: null,
          help_text: 'Optional accountable owner written into connector document metadata.',
          key: 'owner',
          label: 'Owner',
          placeholder: 'team-or-person@dreamfi.com',
          required: false,
        },
      ],
      credential: {
        label: null,
        masked: null,
        required: true,
        status: 'missing',
        storage: 'missing',
        usable: false,
        validated_at: null,
      },
      document_set_name: 'dreamfi-source-metabase',
      expected_document_set: 'dreamfi-source-metabase',
      href: '/console/settings?connector=metabase',
      name: 'Metabase',
      requires_dreamfi_secret: true,
      setup_detail: 'Ingest through an Onyx File/Web/S3 source or a DreamFi source bridge.',
      setup_method: 'Custom/export ingestion',
    }
    const savedConnector: SettingsConnector = {
      ...customConnector,
      config: { missing_keys: [], values: { base_url: 'https://metabase.company.com' } },
    }
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(settingsStatus(customConnector)), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ connector: savedConnector, settings_status: 'blocked' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    renderWithConsoleWorkspace(<SettingsPage />, { path: '/console/settings' })

    await screen.findByText('Custom/export ingestion')
    expect(screen.getByText('Provider API root used by DreamFi sync jobs.')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Metabase Metabase base URL'), {
      target: { value: 'https://metabase.company.com' },
    })
    fireEvent.change(screen.getByLabelText('Metabase Endpoint paths'), {
      target: { value: '/api/card,/api/dashboard,/api/collection' },
    })
    fireEvent.change(screen.getByLabelText('Metabase Owner'), {
      target: { value: 'analytics@dreamfi.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save config' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/settings/connectors/metabase/config')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1].body))).toEqual({
      config: {
        base_url: 'https://metabase.company.com',
        endpoints: '/api/card,/api/dashboard,/api/collection',
        owner: 'analytics@dreamfi.com',
      },
    })
  })
})
