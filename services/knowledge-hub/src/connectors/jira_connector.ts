/**
 * Jira connector — syncs epics, stories, and bugs from Atlassian Jira
 * using the REST API v3 (cloud) with Basic auth (email + API token).
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

/** Minimal representation of a Jira issue returned by the REST API. */
interface JiraIssue {
  id: string;
  key: string;
  self: string;
  fields: {
    summary: string;
    description?: string | null;
    status: { name: string };
    priority?: { name: string } | null;
    issuetype: { name: string };
    assignee?: { displayName: string; emailAddress?: string } | null;
    creator?: { displayName: string } | null;
    labels?: string[];
    fixVersions?: Array<{ name: string }>;
    sprint?: { name: string; state?: string } | null;
    updated: string;
    created: string;
    /* Epic link — custom field varies per instance; we also try parent. */
    parent?: { key: string } | null;
    [customField: string]: unknown;
  };
}

interface JiraSearchResponse {
  startAt: number;
  maxResults: number;
  total: number;
  issues: JiraIssue[];
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class JiraConnector extends BaseConnector {
  private authHeader = '';

  constructor(config: ConnectorConfig) {
    super({
      ...config,
      sourceSystem: 'jira',
    });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { email, apiToken } = this.config.auth;
    if (!email || !apiToken) {
      throw new Error('[JiraConnector] Missing auth.email or auth.apiToken');
    }

    this.authHeader =
      'Basic ' + Buffer.from(`${email}:${apiToken}`).toString('base64');

    // Validate credentials with a lightweight call
    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/rest/api/3/myself'), {
        headers: { Authorization: this.authHeader, Accept: 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Jira auth check failed: ${res.status} ${res.statusText}`);
      }
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.authHeader = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    const pageSize = 100;
    let startAt = 0;
    let total = Infinity;

    // JQL: fetch epics, stories, bugs; optionally filter by updated date
    let jql = 'issuetype in (Epic, Story, Bug) ORDER BY updated DESC';
    if (watermark) {
      // watermark is an ISO-8601 timestamp
      const jiraDate = watermark.replace('T', ' ').substring(0, 19);
      jql = `issuetype in (Epic, Story, Bug) AND updated >= "${jiraDate}" ORDER BY updated DESC`;
    }

    while (startAt < total) {
      const data = await this.withRetry(async () => {
        const url = this.buildUrl('/rest/api/3/search', {
          jql,
          startAt: String(startAt),
          maxResults: String(pageSize),
          fields:
            'summary,description,status,priority,issuetype,assignee,creator,' +
            'labels,fixVersions,sprint,updated,created,parent',
        });

        const res = await fetch(url, {
          headers: {
            Authorization: this.authHeader,
            Accept: 'application/json',
          },
        });
        if (!res.ok) {
          throw new Error(`Jira search failed: ${res.status}`);
        }
        return (await res.json()) as JiraSearchResponse;
      }, 'fetchRaw');

      total = data.total;

      for (const issue of data.issues) {
        yield issue as unknown as Record<string, unknown>;
      }

      startAt += data.issues.length;
      if (data.issues.length === 0) break;
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const issue = rawPayload as unknown as JiraIssue;
    const f = issue.fields;
    const now = new Date().toISOString();

    return {
      source_system: 'jira',
      source_object_id: issue.key,
      entity_type: 'jira_issue',
      name: f.summary,
      description: this.buildDescription(f),
      owner: f.assignee?.displayName ?? f.creator?.displayName ?? null,
      status: this.mapStatus(f.status.name),
      source_url: `${this.config.baseUrl}/browse/${issue.key}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(now),
      eligible_skill_families_json: this.inferSkillFamilies(f),
    };
  }

  // ── private helpers ───────────────────────────────────────────────────

  /**
   * Build a human-readable description from Jira fields.
   */
  private buildDescription(f: JiraIssue['fields']): string {
    const parts: string[] = [];
    parts.push(`[${f.issuetype.name}] ${f.summary}`);
    if (f.priority?.name) parts.push(`Priority: ${f.priority.name}`);
    if (f.labels?.length) parts.push(`Labels: ${f.labels.join(', ')}`);
    if (f.sprint?.name) parts.push(`Sprint: ${f.sprint.name}`);
    if (f.fixVersions?.length) {
      parts.push(`Fix versions: ${f.fixVersions.map((v) => v.name).join(', ')}`);
    }
    if (f.parent?.key) parts.push(`Epic: ${f.parent.key}`);
    if (typeof f.description === 'string') {
      parts.push(`\n${f.description}`);
    }
    return parts.join(' | ');
  }

  /**
   * Map Jira status names to a normalised status string.
   */
  private mapStatus(jiraStatus: string): string {
    const s = jiraStatus.toLowerCase();
    if (['done', 'closed', 'resolved'].includes(s)) return 'done';
    if (['in progress', 'in review', 'in development'].includes(s)) return 'in_progress';
    if (['to do', 'open', 'backlog', 'new'].includes(s)) return 'todo';
    return s.replace(/\s+/g, '_');
  }

  /**
   * Heuristic: infer which skill families might consume this entity.
   */
  private inferSkillFamilies(f: JiraIssue['fields']): string[] {
    const families: string[] = [];
    const labels = (f.labels ?? []).map((l) => l.toLowerCase());

    if (labels.includes('support') || f.issuetype.name === 'Bug') {
      families.push('agent');
    }
    if (labels.includes('copy') || labels.includes('marketing')) {
      families.push('copywriting');
    }
    if (labels.includes('outreach')) {
      families.push('outreach');
    }
    // Product issues are generally useful across all families
    if (families.length === 0) {
      families.push('general');
    }
    return families;
  }
}
