/**
 * Confluence connector — syncs pages and blog posts from Atlassian Confluence
 * using the REST API with Basic auth (email + API token).
 *
 * Supports CQL-based incremental sync via the `lastModified` watermark.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface ConfluencePage {
  id: string;
  type: string;                    // 'page' | 'blogpost'
  title: string;
  status: string;
  space: { key: string; name: string };
  version: { number: number; when: string; by?: { displayName: string } };
  body?: {
    storage?: { value: string };
    view?: { value: string };
  };
  metadata?: {
    labels?: { results: Array<{ name: string }> };
  };
  _links: {
    webui: string;
    self: string;
  };
}

interface ConfluenceSearchResponse {
  results: ConfluencePage[];
  start: number;
  limit: number;
  size: number;
  _links?: { next?: string };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class ConfluenceConnector extends BaseConnector {
  private authHeader = '';

  /** Comma-separated space keys to scope the sync (optional). */
  private spaceKeys: string[] = [];

  constructor(
    config: ConnectorConfig,
    options?: { spaceKeys?: string[] },
  ) {
    super({ ...config, sourceSystem: 'confluence' });
    this.spaceKeys = options?.spaceKeys ?? [];
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { email, apiToken } = this.config.auth;
    if (!email || !apiToken) {
      throw new Error('[ConfluenceConnector] Missing auth.email or auth.apiToken');
    }

    this.authHeader =
      'Basic ' + Buffer.from(`${email}:${apiToken}`).toString('base64');

    await this.withRetry(async () => {
      const res = await fetch(
        this.buildUrl('/wiki/rest/api/space', { limit: '1' }),
        { headers: this.headers() },
      );
      if (!res.ok) {
        throw new Error(`Confluence auth check failed: ${res.status}`);
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
    // Build CQL
    const cqlParts: string[] = ['type in (page, blogpost)'];
    if (this.spaceKeys.length) {
      cqlParts.push(
        `space in (${this.spaceKeys.map((k) => `"${k}"`).join(',')})`,
      );
    }
    if (watermark) {
      cqlParts.push(`lastModified >= "${watermark}"`);
    }
    cqlParts.push('ORDER BY lastModified DESC');

    const cql = cqlParts.join(' AND ');
    const pageSize = 50;
    let start = 0;
    let hasMore = true;

    while (hasMore) {
      const data = await this.withRetry(async () => {
        const res = await fetch(
          this.buildUrl('/wiki/rest/api/content/search', {
            cql,
            start: String(start),
            limit: String(pageSize),
            expand: 'body.storage,version,space,metadata.labels',
          }),
          { headers: this.headers() },
        );
        if (!res.ok) {
          throw new Error(`Confluence search failed: ${res.status}`);
        }
        return (await res.json()) as ConfluenceSearchResponse;
      }, 'fetchRaw');

      for (const page of data.results) {
        yield page as unknown as Record<string, unknown>;
      }

      hasMore = !!data._links?.next && data.size === pageSize;
      start += data.size;
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const page = rawPayload as unknown as ConfluencePage;
    const now = new Date().toISOString();
    const labels =
      page.metadata?.labels?.results.map((l) => l.name) ?? [];

    return {
      source_system: 'confluence',
      source_object_id: page.id,
      entity_type: 'confluence_page',
      name: page.title,
      description: this.buildDescription(page, labels),
      owner: page.version?.by?.displayName ?? null,
      status: page.status === 'current' ? 'active' : page.status,
      source_url: `${this.config.baseUrl}/wiki${page._links.webui}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(page.version.when),
      eligible_skill_families_json: this.inferSkillFamilies(labels, page.type),
      metadata: {
        spaceKey: page.space.key,
        spaceName: page.space.name,
        version: page.version.number,
        labels,
        contentType: page.type,
      },
    };
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: this.authHeader,
      Accept: 'application/json',
    };
  }

  private buildDescription(
    page: ConfluencePage,
    labels: string[],
  ): string {
    const parts: string[] = [];
    parts.push(`[${page.type}] ${page.title}`);
    parts.push(`Space: ${page.space.name} (${page.space.key})`);
    parts.push(`Version: ${page.version.number}`);
    if (labels.length) parts.push(`Labels: ${labels.join(', ')}`);

    // Extract plain text from storage format (strip HTML)
    const rawBody = page.body?.storage?.value;
    if (rawBody) {
      const text = rawBody.replace(/<[^>]*>/g, '').trim();
      if (text.length > 500) {
        parts.push(text.substring(0, 500) + '...');
      } else if (text) {
        parts.push(text);
      }
    }

    return parts.join(' | ');
  }

  private inferSkillFamilies(labels: string[], type: string): string[] {
    const families: string[] = [];
    const lowerLabels = labels.map((l) => l.toLowerCase());

    if (lowerLabels.some((l) => ['support', 'kb', 'knowledge-base'].includes(l))) {
      families.push('agent');
    }
    if (lowerLabels.some((l) => ['marketing', 'copy', 'brand'].includes(l))) {
      families.push('copywriting');
    }
    if (type === 'blogpost') {
      families.push('copywriting');
    }
    if (families.length === 0) {
      families.push('summarization', 'general');
    }
    return families;
  }
}
