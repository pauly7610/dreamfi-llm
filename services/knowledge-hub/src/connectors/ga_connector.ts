/**
 * Google Analytics Data API connector — syncs report data (dimensions +
 * metrics) and real-time data from GA4 properties.
 *
 * Auth: Service account credentials via a JSON key file.  Uses the
 * Google Auth Library to generate short-lived access tokens.
 */

import * as fs from 'fs';
import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface ServiceAccountKey {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
}

interface GAReportRow {
  dimensionValues: Array<{ value: string }>;
  metricValues: Array<{ value: string }>;
}

interface GARunReportResponse {
  dimensionHeaders: Array<{ name: string }>;
  metricHeaders: Array<{ name: string; type: string }>;
  rows?: GAReportRow[];
  rowCount?: number;
  metadata?: { currencyCode?: string; timeZone?: string };
}

/** Describes a report to sync. */
export interface GAReportDefinition {
  /** Human-readable report name used as entity name. */
  name: string;
  dimensions: string[];
  metrics: string[];
  /** ISO-8601 date strings (YYYY-MM-DD). */
  dateRange: { startDate: string; endDate: string };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class GAConnector extends BaseConnector {
  private accessToken = '';
  private tokenExpiresAt = 0;
  private serviceAccountKey: ServiceAccountKey | null = null;
  private propertyId = '';

  /** Reports to fetch on each sync. */
  private reportDefinitions: GAReportDefinition[] = [];

  constructor(
    config: ConnectorConfig,
    options?: {
      propertyId?: string;
      reports?: GAReportDefinition[];
    },
  ) {
    super({ ...config, sourceSystem: 'google_analytics' });
    this.propertyId = options?.propertyId ?? config.auth.propertyId ?? '';
    this.reportDefinitions = options?.reports ?? this.defaultReports();
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { keyFilePath } = this.config.auth;
    if (!keyFilePath) {
      throw new Error('[GAConnector] Missing auth.keyFilePath');
    }
    if (!this.propertyId) {
      throw new Error('[GAConnector] Missing propertyId');
    }

    const keyContent = fs.readFileSync(keyFilePath, 'utf-8');
    this.serviceAccountKey = JSON.parse(keyContent) as ServiceAccountKey;

    await this.refreshAccessToken();
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.accessToken = '';
    this.serviceAccountKey = null;
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    _watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    await this.ensureValidToken();

    for (const report of this.reportDefinitions) {
      const data = await this.withRetry(async () => {
        return this.runReport(report);
      }, `fetchRaw:${report.name}`);

      yield {
        _reportName: report.name,
        _reportDef: report,
        ...data,
      } as unknown as Record<string, unknown>;
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const payload = rawPayload as unknown as GARunReportResponse & {
      _reportName: string;
      _reportDef: GAReportDefinition;
    };
    const now = new Date().toISOString();

    const dimNames = payload.dimensionHeaders?.map((h) => h.name) ?? [];
    const metricNames = payload.metricHeaders?.map((h) => h.name) ?? [];

    // Flatten row data into a summary
    const rowCount = payload.rowCount ?? payload.rows?.length ?? 0;
    const topRows = (payload.rows ?? []).slice(0, 10).map((row) => {
      const obj: Record<string, string> = {};
      row.dimensionValues.forEach((v, i) => {
        obj[dimNames[i]] = v.value;
      });
      row.metricValues.forEach((v, i) => {
        obj[metricNames[i]] = v.value;
      });
      return obj;
    });

    return {
      source_system: 'google_analytics',
      source_object_id: `ga-report-${payload._reportName.replace(/\s+/g, '-').toLowerCase()}`,
      entity_type: 'ga_report',
      name: payload._reportName,
      description: `GA4 report: ${dimNames.join(', ')} x ${metricNames.join(', ')} | ${rowCount} rows | ${payload._reportDef.dateRange.startDate} to ${payload._reportDef.dateRange.endDate}`,
      owner: null,
      status: 'active',
      source_url: `https://analytics.google.com/analytics/web/#/p${this.propertyId}/reports`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(now),
      eligible_skill_families_json: ['summarization', 'general'],
      metadata: {
        dimensions: dimNames,
        metrics: metricNames,
        rowCount,
        topRows,
        dateRange: payload._reportDef.dateRange,
      },
    };
  }

  // ── public: run an ad-hoc report ──────────────────────────────────────

  /**
   * Execute a custom GA4 report and return the raw response.
   */
  async runReport(report: GAReportDefinition): Promise<GARunReportResponse> {
    await this.ensureValidToken();

    const url = `https://analyticsdata.googleapis.com/v1beta/properties/${this.propertyId}:runReport`;

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        dimensions: report.dimensions.map((d) => ({ name: d })),
        metrics: report.metrics.map((m) => ({ name: m })),
        dateRanges: [report.dateRange],
        limit: 10000,
      }),
    });

    if (!res.ok) {
      throw new Error(`GA runReport failed: ${res.status} ${await res.text()}`);
    }

    return (await res.json()) as GARunReportResponse;
  }

  // ── private helpers ───────────────────────────────────────────────────

  private async refreshAccessToken(): Promise<void> {
    if (!this.serviceAccountKey) {
      throw new Error('[GAConnector] Service account key not loaded');
    }

    const jwt = await this.createSignedJwt(this.serviceAccountKey);

    const res = await fetch(this.serviceAccountKey.token_uri, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        assertion: jwt,
      }),
    });

    if (!res.ok) {
      throw new Error(`GA token exchange failed: ${res.status}`);
    }

    const data = (await res.json()) as {
      access_token: string;
      expires_in: number;
    };
    this.accessToken = data.access_token;
    this.tokenExpiresAt = Date.now() + data.expires_in * 1000 - 60_000;
  }

  private async ensureValidToken(): Promise<void> {
    if (Date.now() >= this.tokenExpiresAt) {
      await this.refreshAccessToken();
    }
  }

  /**
   * Create a signed JWT for the Google OAuth2 token exchange.
   * Uses Node.js crypto to sign with the service account private key.
   */
  private async createSignedJwt(key: ServiceAccountKey): Promise<string> {
    const { createSign } = await import('crypto');

    const header = Buffer.from(
      JSON.stringify({ alg: 'RS256', typ: 'JWT' }),
    ).toString('base64url');

    const now = Math.floor(Date.now() / 1000);
    const payload = Buffer.from(
      JSON.stringify({
        iss: key.client_email,
        scope: 'https://www.googleapis.com/auth/analytics.readonly',
        aud: key.token_uri,
        iat: now,
        exp: now + 3600,
      }),
    ).toString('base64url');

    const signInput = `${header}.${payload}`;
    const signer = createSign('RSA-SHA256');
    signer.update(signInput);
    const signature = signer.sign(key.private_key, 'base64url');

    return `${signInput}.${signature}`;
  }

  private defaultReports(): GAReportDefinition[] {
    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000)
      .toISOString()
      .split('T')[0];

    return [
      {
        name: 'Traffic Overview (30d)',
        dimensions: ['date', 'sessionDefaultChannelGroup'],
        metrics: ['sessions', 'activeUsers', 'screenPageViews'],
        dateRange: { startDate: thirtyDaysAgo, endDate: today },
      },
      {
        name: 'Top Pages (30d)',
        dimensions: ['pagePath', 'pageTitle'],
        metrics: ['screenPageViews', 'activeUsers', 'averageSessionDuration'],
        dateRange: { startDate: thirtyDaysAgo, endDate: today },
      },
    ];
  }
}
