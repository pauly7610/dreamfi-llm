export const CONSOLE_DATA_REFRESH_EVENT = 'dreamfi:console-data-refresh'

export type AskCitation = {
  document_id: string
  title: string
  blurb: string
  score: number
  link: string | null
  updated_at: string | null
}

export type AskResponse = {
  question: string
  answer: string
  confidence: number
  citations: AskCitation[]
  followups: string[]
}

export type GenerateArtifactRequest = {
  workflow_slug: string
  question?: string | null
  topic_id?: string | null
  source_id?: string | null
  regenerate_from_output_id?: string | null
}

export type GenerateArtifactResponse = {
  round_id: string
  output_id: string
  workflow_slug: string
  workflow_title: string
  skill_id: string
  pass_fail: string
  confidence: number
  export_readiness: number
  destination_href: string
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T
  }

  let detail = `Request failed with ${response.status}`
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string') {
      detail = payload.detail
    }
  } catch {
    // Keep the status-based message.
  }
  throw new Error(detail)
}

export function refreshConsoleData() {
  window.dispatchEvent(new CustomEvent(CONSOLE_DATA_REFRESH_EVENT))
}

export async function askDreamFi(request: {
  question: string
  topic_id?: string | null
  source_id?: string | null
  source_ids?: string[]
}): Promise<AskResponse> {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return parseJsonResponse<AskResponse>(response)
}

export async function generateArtifact(request: GenerateArtifactRequest): Promise<GenerateArtifactResponse> {
  const response = await fetch('/api/workflows/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const payload = await parseJsonResponse<GenerateArtifactResponse>(response)
  refreshConsoleData()
  return payload
}

export async function publishArtifact(request: {
  skill_id: string
  output_id: string
  destination?: 'confluence' | 'jira' | 'return-only'
  destination_ref?: string | null
}): Promise<{ publish_id: string; decision: string }> {
  const response = await fetch(`/v1/skills/${encodeURIComponent(request.skill_id)}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      output_id: request.output_id,
      destination: request.destination ?? 'return-only',
      destination_ref: request.destination_ref ?? null,
    }),
  })
  const payload = await parseJsonResponse<{ publish_id: string; decision: string }>(response)
  refreshConsoleData()
  return payload
}
