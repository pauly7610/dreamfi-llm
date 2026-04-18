/**
 * Lucidchart connector — syncs documents and pages (flow diagrams)
 * via the Lucidchart API using OAuth2 authentication.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface LucidchartDocument {
  documentId: string;
  title: string;
  description?: string | null;
  editUrl: string;
  viewUrl: string;
  thumbnailUrl?: string | null;
  owner?: { name: string; email?: string } | null;
  lastModified: string;
  createdDate: string;
  pageCount?: number;
  status?: string | null;
  pages?: LucidchartPage[];
}

interface LucidchartPage {
  pageId: string;
  title: string;
  index: number;
}

interface LucidchartListResponse {
  documents: LucidchartDocument[];
  nextPageToken?: string | null;
}

interface OAuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class LucidchartConnector extends BaseConnector {
  private accessToken = '';
  private tokenExpiresAt = 0;

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'lucidchart' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { clientId, clientSecret, refreshToken } = this.config.auth;
    if (!clientId || !clientSecret) {
      throw new Error(
        '[LucidchartConnector] Missing auth.clientId or auth.clientSecret',
      );
    }

    await this.refreshAccessToken();
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.accessToken = '';
    this.tokenExpiresAt = 0;
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    await this.ensureValidToken();

    let pageToken: string | undefined;

    do {
      const params: Record<string, string> = { pageSize: '100' };
      if (pageToken) params.pageToken = pageToken;
      if (watermark) params.modifiedSince = watermark;

      const data = await this.withRetry(async () => {
        const res = await fetch(
          this.buildUrl('/api/v1/documents', params),
          { headers: this.headers() },
        );
        if (!res.ok) {
          throw new Error(`Lucidchart documents list failed: ${res.status}`);
        }
        return (await res.json()) as LucidchartListResponse;
      }, 'fetchRaw:documents');

      for (const doc of data.documents) {
        // Optionally fetch pages for each document
        const enriched = await this.enrichWithPages(doc);
        yield enriched as unknown as Record<string, unknown>;
      }

      pageToken = data.nextPageToken ?? undefined;
    } while (pageToken);
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const doc = rawPayload as unknown as LucidchartDocument;
    const now = new Date().toISOString();

    const pageNames = (doc.pages ?? []).map((p) => p.title);

    return {
      source_system: 'lucidchart',
      source_object_id: doc.documentId,
      entity_type: 'lucidchart_document',
      name: doc.title,
      description: this.buildDescription(doc, pageNames),
      owner: doc.owner?.name ?? null,
      status: doc.status ?? 'active',
      source_url: doc.viewUrl,
      last_synced_at: now,
      freshness_score: this.computeFreshness(doc.lastModified),
      eligible_skill_families_json: ['summarization', 'general'],
      metadata: {
        thumbnailUrl: doc.thumbnailUrl,
        pageCount: doc.pageCount ?? pageNames.length,
        pages: pageNames,
      },
    };
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.accessToken}`,
      Accept: 'application/json',
    };
  }

  private async refreshAccessToken(): Promise<void> {
    const { clientId, clientSecret, refreshToken } = this.config.auth;

    const body = new URLSearchParams({
      grant_type: refreshToken ? 'refresh_token' : 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
    });
    if (refreshToken) {
      body.set('refresh_token', refreshToken);
    }

    const res = await fetch(this.buildUrl('/oauth2/token'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) {
      throw new Error(`Lucidchart OAuth token refresh failed: ${res.status}`);
    }

    const data = (await res.json()) as OAuthTokenResponse;
    this.accessToken = data.access_token;
    this.tokenExpiresAt = Date.now() + data.expires_in * 1000 - 60_000; // 1 min buffer
  }

  private async ensureValidToken(): Promise<void> {
    if (Date.now() >= this.tokenExpiresAt) {
      await this.refreshAccessToken();
    }
  }

  private async enrichWithPages(
    doc: LucidchartDocument,
  ): Promise<LucidchartDocument> {
    try {
      await this.ensureValidToken();
      const res = await fetch(
        this.buildUrl(`/api/v1/documents/${doc.documentId}/pages`),
        { headers: this.headers() },
      );
      if (res.ok) {
        const pagesData = (await res.json()) as { pages: LucidchartPage[] };
        return { ...doc, pages: pagesData.pages };
      }
    } catch {
      // Non-fatal — proceed without page data
    }
    return doc;
  }

  private buildDescription(
    doc: LucidchartDocument,
    pageNames: string[],
  ): string {
    const parts: string[] = [];
    if (doc.description) parts.push(doc.description);
    if (pageNames.length) {
      parts.push(`Pages: ${pageNames.join(', ')}`);
    }
    if (doc.pageCount) parts.push(`Total pages: ${doc.pageCount}`);
    return parts.join(' | ') || doc.title;
  }
}
