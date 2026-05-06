import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { Chip, Cite, KPI, SectionHead, connectorKeyFromId, type ChipTone } from '../components/system/atoms'
import type { SettingsConnector, SettingsStatus } from '../types/console'
import {
  activateSettingsConnector,
  deactivateSettingsConnector,
  deleteConnectorSecret,
  ensureConnectorDocumentSet,
  fetchSettingsStatus,
  saveConnectorSecret,
  validateSettingsConnector,
} from '../utils/consoleApi'

type SettingsPageProps = {
  onConsoleDataChanged?: () => void
}

type Tab = 'environment' | 'connectors' | 'persistence'

type ActionState = {
  connectorId: string | null
  error: string | null
  label: string | null
}

function toneForReady(value: boolean): Extract<ChipTone, 'ready' | 'bad'> {
  return value ? 'ready' : 'bad'
}

function toneForActivation(status: SettingsConnector['activation_status']): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (status === 'active') {
    return 'ready'
  }
  if (status === 'degraded') {
    return 'warn'
  }
  return 'bad'
}

function toneForValidation(status: SettingsConnector['validation_status']): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (status === 'validated') {
    return 'ready'
  }
  if (status === 'validation_failed') {
    return 'bad'
  }
  return 'warn'
}

function toneForRetrieval(status: SettingsConnector['retrieval_status']): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (status === 'fresh') {
    return 'ready'
  }
  if (status === 'error' || status === 'empty') {
    return 'bad'
  }
  return 'warn'
}

function labelForBlocker(value: string): string {
  return value.replace(/_/g, ' ')
}

function emptyAction(): ActionState {
  return { connectorId: null, error: null, label: null }
}

function mergeConnector(status: SettingsStatus | null, connector: SettingsConnector): SettingsStatus | null {
  if (!status) {
    return status
  }

  return {
    ...status,
    connectors: status.connectors.map((item) => (
      item.connector_id === connector.connector_id ? connector : item
    )),
  }
}

export default function SettingsPage({ onConsoleDataChanged }: SettingsPageProps) {
  const [activeTab, setActiveTab] = useState<Tab>('connectors')
  const [status, setStatus] = useState<SettingsStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<ActionState>(emptyAction)
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [labels, setLabels] = useState<Record<string, string>>({})

  async function loadStatus() {
    setLoading(true)
    try {
      const payload = await fetchSettingsStatus()
      setStatus(payload)
      setAction(emptyAction())
    } catch (error) {
      setAction({
        connectorId: null,
        error: error instanceof Error ? error.message : 'Unable to load settings',
        label: null,
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadStatus()
  }, [])

  const selectedConnectorId = useMemo(() => {
    const search = new URLSearchParams(window.location.search)
    return search.get('connector')
  }, [status])
  const selectedConnector = (
    status?.connectors.find((connector) => connector.connector_id === selectedConnectorId)
    ?? status?.connectors[0]
    ?? null
  )

  async function runConnectorAction(
    connectorId: string,
    label: string,
    operation: () => Promise<{ connector: SettingsConnector }>,
  ) {
    setAction({ connectorId, error: null, label })
    try {
      const payload = await operation()
      setStatus((current) => mergeConnector(current, payload.connector))
      setAction(emptyAction())
    } catch (error) {
      setAction({
        connectorId,
        error: error instanceof Error ? error.message : `Unable to ${label.toLowerCase()}`,
        label,
      })
    }
  }

  async function handleSecretSubmit(event: FormEvent<HTMLFormElement>, connectorId: string) {
    event.preventDefault()
    const apiKey = keys[connectorId] ?? ''
    const label = labels[connectorId] ?? ''
    await runConnectorAction(connectorId, 'Save key', async () => {
      const payload = await saveConnectorSecret({ connector_id: connectorId, api_key: apiKey, label })
      setKeys((current) => ({ ...current, [connectorId]: '' }))
      return payload
    })
  }

  async function handleActivate(connectorId: string) {
    await runConnectorAction(connectorId, 'Activate', async () => {
      const payload = await activateSettingsConnector(connectorId)
      onConsoleDataChanged?.()
      return payload
    })
  }

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>SETTINGS / ACTIVATION</div>
      <div className="row" style={{ flexWrap: 'wrap', marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400 }}>
          Connect the operating layer
        </h1>
        <div className="spacer" />
        <button className="btn btn-sm btn-ghost" onClick={() => void loadStatus()} type="button">
          {loading ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      {action.error ? (
        <div className="banner" role="alert" style={{ marginBottom: 20 }}>
          <div>
            <div className="strong">{action.label ?? 'Settings action'} failed</div>
            <p>{action.error}</p>
          </div>
        </div>
      ) : null}

      <div className="surface" style={{ marginBottom: 20 }}>
        <div className="kpi-grid">
          <KPI label="STATUS" value={status?.status ?? '--'} delta={status?.failures.join(', ') || 'all gates clear'} deltaTone={status?.status === 'ready' ? 'up' : 'down'} />
          <KPI label="ACTIVE" value={status?.summary.active_connector_count ?? 0} delta={`${status?.summary.configured_connector_count ?? 0} configured`} deltaTone="up" />
          <KPI label="PERSISTENCE" value={status?.persistence.ready ? 'Ready' : 'Blocked'} delta={status?.persistence.uses_sqlite ? 'SQLite is local only' : 'storage gate'} deltaTone={status?.persistence.ready ? 'up' : 'down'} />
          <KPI label="REPLAY" value={status?.jobs.replay.due_schedule_count ?? 0} delta={`${status?.jobs.replay.error_count_24h ?? 0} errors / 24h`} deltaTone={(status?.jobs.replay.error_count_24h ?? 0) ? 'down' : 'flat'} />
        </div>
      </div>

      <div className="source-chrome" style={{ marginBottom: 20 }}>
        <div className="source-chrome-tabs">
          {([
            ['connectors', 'Connectors'],
            ['environment', 'Environment'],
            ['persistence', 'Data persistence'],
          ] as const).map(([id, label]) => (
            <button
              className={`source-tab ${activeTab === id ? 'active' : ''}`}
              key={id}
              onClick={() => setActiveTab(id)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'connectors' ? (
        <div className="surface">
          <SectionHead
            title="Connector activation"
            eyebrow="KEYS / ONYX / FRESHNESS"
            right={selectedConnector ? <Cite connector={connectorKeyFromId(selectedConnector.connector_id)} label={selectedConnector.name} /> : null}
          />
          <div className="table-scroll table-scroll-wide">
            <table className="dfi-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Credential</th>
                  <th>Onyx</th>
                  <th>Probe</th>
                  <th>Activation</th>
                  <th>Key</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(status?.connectors ?? []).map((connector) => {
                  const busy = action.connectorId === connector.connector_id
                  return (
                    <tr key={connector.connector_id}>
                      <td>
                        <div className="row" style={{ alignItems: 'flex-start' }}>
                          <Cite connector={connectorKeyFromId(connector.connector_id)} label={connector.name} />
                          <div className="col" style={{ gap: 2 }}>
                            <span className="strong">{connector.category.replace('_', ' ')}</span>
                            <span className="muted">{connector.expected_document_set}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <Chip tone={connector.credential.status === 'saved' ? 'ready' : 'bad'}>
                          {connector.credential.masked ?? 'missing'}
                        </Chip>
                        <div className="muted">{connector.credential.validated_at ? 'accepted' : 'not accepted'}</div>
                      </td>
                      <td>
                        <Chip tone={toneForReady(connector.document_set_present)}>
                          {connector.document_set_present ? 'document set' : 'missing'}
                        </Chip>
                        <div className="muted">{connector.document_set_name}</div>
                      </td>
                      <td>
                        <Chip tone={toneForRetrieval(connector.retrieval_status)}>{connector.retrieval_status.replace('_', ' ')}</Chip>
                        <div className="muted">{connector.freshest_document_at ? new Date(connector.freshest_document_at).toLocaleDateString() : 'no timestamp'}</div>
                      </td>
                      <td>
                        <Chip tone={toneForActivation(connector.activation_status)}>
                          {connector.activation_status}
                        </Chip>
                        <div className="muted">{connector.blockers.length ? connector.blockers.map(labelForBlocker).join(', ') : 'ready'}</div>
                      </td>
                      <td style={{ minWidth: 240 }}>
                        <form className="settings-key-form" onSubmit={(event) => void handleSecretSubmit(event, connector.connector_id)}>
                          <input
                            aria-label={`${connector.name} API key`}
                            autoComplete="off"
                            className="field-input"
                            onChange={(event) => setKeys((current) => ({ ...current, [connector.connector_id]: event.target.value }))}
                            placeholder="API key"
                            type="password"
                            value={keys[connector.connector_id] ?? ''}
                          />
                          <input
                            aria-label={`${connector.name} key label`}
                            autoComplete="off"
                            className="field-input"
                            onChange={(event) => setLabels((current) => ({ ...current, [connector.connector_id]: event.target.value }))}
                            placeholder="label"
                            type="text"
                            value={labels[connector.connector_id] ?? ''}
                          />
                          <button className="btn btn-sm" disabled={busy || !(keys[connector.connector_id] ?? '').trim()} type="submit">
                            Save
                          </button>
                        </form>
                      </td>
                      <td>
                        <div className="row" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                          <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void runConnectorAction(connector.connector_id, 'Create document set', () => ensureConnectorDocumentSet(connector.connector_id))} type="button">
                            Doc set
                          </button>
                          <button className="btn btn-sm btn-ghost" disabled={busy || connector.credential.status !== 'saved'} onClick={() => void runConnectorAction(connector.connector_id, 'Validate', () => validateSettingsConnector(connector.connector_id))} type="button">
                            Validate
                          </button>
                          {connector.activation_status === 'active' ? (
                            <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void runConnectorAction(connector.connector_id, 'Deactivate', () => deactivateSettingsConnector(connector.connector_id))} type="button">
                              Deactivate
                            </button>
                          ) : (
                            <button className="btn btn-sm btn-primary" disabled={busy || !connector.can_activate} onClick={() => void handleActivate(connector.connector_id)} type="button">
                              Activate
                            </button>
                          )}
                          <button className="btn btn-sm btn-ghost" disabled={busy || connector.credential.status !== 'saved'} onClick={() => void runConnectorAction(connector.connector_id, 'Delete key', () => deleteConnectorSecret(connector.connector_id))} type="button">
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {activeTab === 'environment' ? (
        <div className="surface">
          <SectionHead title="Environment gates" eyebrow="PRODUCTION READINESS" />
          <div className="table-scroll table-scroll-medium">
            <table className="dfi-table">
              <tbody>
                {(status?.environment.checks ?? []).map((check) => (
                  <tr key={check.name}>
                    <td className="strong">{check.name.replace(/_/g, ' ')}</td>
                    <td>
                      <Chip tone={toneForReady(Boolean(check.configured))}>{check.configured ? 'configured' : 'blocked'}</Chip>
                    </td>
                    <td className="muted">{check.detail}</td>
                  </tr>
                ))}
                {(status?.environment.placeholder_values ?? []).map((value) => (
                  <tr key={value}>
                    <td className="strong">{value}</td>
                    <td><Chip tone="bad">placeholder</Chip></td>
                    <td className="muted">Replace before production activation.</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {activeTab === 'persistence' ? (
        <div className="split-grid">
          <div className="surface">
            <SectionHead title="Persistence gates" eyebrow="DATABASE / AUDIT" />
            <div className="table-scroll table-scroll-medium">
              <table className="dfi-table">
                <tbody>
                  {(status?.persistence.checks ?? []).map((check) => (
                    <tr key={check.name}>
                      <td className="strong">{check.name.replace(/_/g, ' ')}</td>
                      <td><Chip tone={toneForReady(Boolean(check.passed))}>{check.passed ? 'pass' : 'blocked'}</Chip></td>
                      <td className="muted">{check.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="surface">
            <SectionHead title="Persisted evidence" eyebrow="ROW COUNTS" />
            <div className="table-scroll table-scroll-medium">
              <table className="dfi-table">
                <tbody>
                  {Object.entries(status?.persistence.counts ?? {}).map(([name, count]) => (
                    <tr key={name}>
                      <td className="strong">{name.replace(/_/g, ' ')}</td>
                      <td className="num">{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
