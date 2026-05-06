import { useState } from 'react'

import type { ConsolePayload } from '../types/console'
import { Chip, Cite, SectionHead, connectorKeyFromId } from '../components/system/atoms'
import { captureArtifactFeedback, publishArtifact, recordProductionOutcome } from '../utils/consoleApi'
import { artifactHref } from './redesignSupport'

type InboxNewPageProps = {
  data: ConsolePayload | null
  onDataChanged?: () => void
}

type InboxRow = {
  age: string
  artifact?: { outputId: string; skillId: string | null; status: string }
  cta: string
  href: string
  kind: 'decision' | 'blocked' | 'review' | 'signal'
  source?: { href: string; id: string; label: string }
  title: string
  context: string
}

export function InboxNewPage({ data, onDataChanged }: InboxNewPageProps) {
  const degraded = (data?.integrations ?? []).find((integration) => integration.status === 'degraded') ?? null
  const [action, setAction] = useState<{ error: string | null; outputId: string | null }>({
    error: null,
    outputId: null,
  })
  const rows: InboxRow[] = [
    ...(data?.artifact_queue ?? []).map((artifact) => ({
      age: new Date(artifact.created_at).toLocaleDateString(),
      artifact: {
        outputId: artifact.output_id,
        skillId: artifact.skill_id,
        status: artifact.status,
      },
      context: `${artifact.skill_display_name ?? 'Artifact'} / confidence ${artifact.confidence?.toFixed(2) ?? '--'}`,
      cta: artifact.status === 'publish_ready' ? 'Review' : 'Inspect',
      href: artifactHref(artifact.output_id),
      kind: (artifact.status === 'blocked' ? 'blocked' : artifact.status === 'publish_ready' ? 'decision' : 'review') as InboxRow['kind'],
      source: undefined,
      title: artifact.test_input_label,
    })),
    ...(data?.alerts ?? []).map((alert) => ({
      age: alert.created_at ? new Date(alert.created_at).toLocaleDateString() : 'Open',
      context: alert.message,
      cta: 'Open',
      href: alert.href ?? '/console/trust',
      kind: 'signal' as const,
      source: degraded ? { href: degraded.href, id: degraded.id, label: degraded.name } : undefined,
      title: alert.title,
    })),
  ].slice(0, 6)

  async function handlePublish(row: InboxRow) {
    if (!row.artifact?.skillId) {
      setAction({ error: 'Artifact is missing a skill id', outputId: row.artifact?.outputId ?? null })
      return
    }

    setAction({ error: null, outputId: row.artifact.outputId })
    try {
      await publishArtifact({
        output_id: row.artifact.outputId,
        skill_id: row.artifact.skillId,
      })
      onDataChanged?.()
      setAction({ error: null, outputId: null })
    } catch (error) {
      setAction({
        error: error instanceof Error ? error.message : 'Unable to publish artifact',
        outputId: row.artifact.outputId,
      })
    }
  }

  async function handleFeedback(row: InboxRow, outcome: 'approved' | 'rejected') {
    if (!row.artifact?.outputId) {
      setAction({ error: 'Artifact is missing an output id', outputId: null })
      return
    }

    setAction({ error: null, outputId: row.artifact.outputId })
    try {
      await captureArtifactFeedback({
        output_id: row.artifact.outputId,
        outcome,
        reason: outcome === 'approved' ? 'review_ready' : 'blocked_by_review',
        notes:
          outcome === 'approved'
            ? 'Console reviewer approved the artifact for learning memory.'
            : 'Console reviewer rejected the artifact and preserved it as a regression signal.',
        promote_to_gold_role: outcome === 'approved' ? 'exemplar' : 'regression',
      })
      onDataChanged?.()
      setAction({ error: null, outputId: null })
    } catch (error) {
      setAction({
        error: error instanceof Error ? error.message : 'Unable to record feedback',
        outputId: row.artifact.outputId,
      })
    }
  }

  async function handleUsedInDecision(row: InboxRow) {
    if (!row.artifact?.outputId) {
      setAction({ error: 'Artifact is missing an output id', outputId: null })
      return
    }

    setAction({ error: null, outputId: row.artifact.outputId })
    try {
      await recordProductionOutcome({
        output_id: row.artifact.outputId,
        outcome: 'used_in_decision',
        notes: 'Console operator marked this artifact as used in a product decision.',
      })
      onDataChanged?.()
      setAction({ error: null, outputId: null })
    } catch (error) {
      setAction({
        error: error instanceof Error ? error.message : 'Unable to record production outcome',
        outputId: row.artifact.outputId,
      })
    }
  }

  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>INBOX</div>
      <div className="row" style={{ marginBottom: 20, flexWrap: 'wrap' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.02em' }}>
          What needs you
        </h1>
        <div className="spacer" />
        <a className="btn btn-sm btn-ghost" href="/console/trust">Trust</a>
        <a className="btn btn-sm" href="/console/artifacts">Artifacts</a>
      </div>

      <div className="surface">
        <SectionHead title="Operator queue" eyebrow="REVIEW AND DECISION" />
        {action.error ? (
          <div role="alert" style={{ padding: '12px 18px', color: 'var(--bad)', borderBottom: '1px solid var(--line)' }}>
            {action.error}
          </div>
        ) : null}
        <div className="table-scroll table-scroll-medium">
          <table className="dfi-table">
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.kind}-${row.title}`}>
                  <td style={{ width: 120 }}>
                    <Chip tone={row.kind === 'blocked' ? 'bad' : row.kind === 'review' || row.kind === 'signal' ? 'warn' : 'signal'}>
                      {row.kind}
                    </Chip>
                  </td>
                  <td>
                    <div className="strong" style={{ fontSize: 14 }}>{row.title}</div>
                    <div className="muted">{row.context}</div>
                  </td>
                  <td>
                    {row.source ? (
                      <Cite connector={connectorKeyFromId(row.source.id)} href={row.source.href} label={row.source.label} />
                    ) : (
                      <span className="muted">Product thread</span>
                    )}
                  </td>
                  <td className="muted" style={{ width: 90 }}>{row.age}</td>
                  <td style={{ textAlign: 'right', minWidth: 220 }}>
                    {row.artifact?.status === 'publish_ready' ? (
                      <div className="row" style={{ justifyContent: 'flex-end', gap: 6 }}>
                        <button
                          className="btn btn-sm btn-primary"
                          disabled={action.outputId === row.artifact.outputId}
                          onClick={() => void handlePublish(row)}
                          type="button"
                        >
                          {action.outputId === row.artifact.outputId ? 'Saving...' : 'Publish'}
                        </button>
                        <button
                          className="btn btn-sm btn-ghost"
                          disabled={action.outputId === row.artifact.outputId}
                          onClick={() => void handleFeedback(row, 'approved')}
                          type="button"
                        >
                          Approve
                        </button>
                      </div>
                    ) : row.artifact ? (
                      <div className="row" style={{ justifyContent: 'flex-end', gap: 6 }}>
                        <button
                          className="btn btn-sm btn-ghost"
                          disabled={action.outputId === row.artifact.outputId}
                          onClick={() => void handleFeedback(row, row.artifact!.status === 'blocked' ? 'rejected' : 'approved')}
                          type="button"
                        >
                          {row.artifact.status === 'blocked' ? 'Reject' : 'Approve'}
                        </button>
                        <button
                          className="btn btn-sm btn-ghost"
                          disabled={action.outputId === row.artifact.outputId}
                          onClick={() => void handleUsedInDecision(row)}
                          type="button"
                        >
                          Used
                        </button>
                        <a className={`btn btn-sm ${row.kind === 'decision' ? 'btn-primary' : ''}`.trim()} href={row.href}>
                          {row.cta}
                        </a>
                      </div>
                    ) : (
                      <a className={`btn btn-sm ${row.kind === 'decision' ? 'btn-primary' : ''}`.trim()} href={row.href}>
                        {row.cta}
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
