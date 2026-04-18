/**
 * Socure connector — syncs verification decisions, risk scores, and
 * module results from the Socure identity-verification platform.
 *
 * Auth: API key via the `Authorization` header.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface SocureDecision {
  referenceId: string;
  decision: string;               // 'accept' | 'reject' | 'review' | 'resubmit'
  riskScore: number;              // 0–1
  status: string;
  modules: SocureModuleResult[];
  customerReference?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface SocureModuleResult {
  name: string;                   // e.g. 'emailrisk', 'phonerisk', 'addressrisk', 'kyc', 'fraud'
  decision: string;
  score: number;
  reasonCodes?: string[];
}

interface SocureRiskScore {
  referenceId: string;
  overallScore: number;
  emailRisk?: number | null;
  phoneRisk?: number | null;
  addressRisk?: number | null;
  syntheticScore?: number | null;
  createdAt: string;
}

interface SocureListResponse<T> {
  data: T[];
  pagination?: {
    page: number;
    totalPages: number;
    totalRecords: number;
    hasMore: boolean;
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class SocureConnector extends BaseConnector {
  private apiKey = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'socure' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { apiKey } = this.config.auth;
    if (!apiKey) {
      throw new Error('[SocureConnector] Missing auth.apiKey');
    }
    this.apiKey = apiKey;

    // Validate key
    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/3.0/health'), {
        headers: this.headers(),
      });
      if (!res.ok) {
        throw new Error(`Socure auth check failed: ${res.status}`);
      }
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.apiKey = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    // 1. Verification decisions
    yield* this.paginateEndpoint<SocureDecision>(
      '/api/3.0/decisions',
      'decision',
      watermark,
    );

    // 2. Risk scores (aggregated)
    yield* this.paginateEndpoint<SocureRiskScore>(
      '/api/3.0/risk-scores',
      'risk_score',
      watermark,
    );
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const itemType = rawPayload._itemType as string;
    const now = new Date().toISOString();

    switch (itemType) {
      case 'decision':
        return this.normalizeDecision(
          rawPayload as unknown as SocureDecision,
          now,
        );
      case 'risk_score':
        return this.normalizeRiskScore(
          rawPayload as unknown as SocureRiskScore,
          now,
        );
      default:
        throw new Error(`Unknown Socure item type: ${itemType}`);
    }
  }

  // ── public: on-demand verification lookup ─────────────────────────────

  /**
   * Look up a specific verification decision by reference ID.
   */
  async getDecision(referenceId: string): Promise<SocureDecision | null> {
    if (!this.connected) {
      throw new Error('[SocureConnector] Not connected');
    }

    const res = await this.withRetry(async () => {
      return fetch(
        this.buildUrl(`/api/3.0/decisions/${referenceId}`),
        { headers: this.headers() },
      );
    }, 'getDecision');

    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Socure decision lookup failed: ${res.status}`);
    }

    return (await res.json()) as SocureDecision;
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: `SocureApiKey ${this.apiKey}`,
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
  }

  private async *paginateEndpoint<T>(
    path: string,
    itemType: string,
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const params: Record<string, string> = {
        page: String(page),
        pageSize: '100',
        sort: 'updatedAt',
        order: 'desc',
      };
      if (watermark) params.updatedSince = watermark;

      const data = await this.withRetry(async () => {
        const res = await fetch(this.buildUrl(path, params), {
          headers: this.headers(),
        });
        if (!res.ok) {
          throw new Error(`Socure ${path} failed: ${res.status}`);
        }
        return (await res.json()) as SocureListResponse<T>;
      }, `fetchRaw:${itemType}`);

      for (const item of data.data) {
        yield {
          ...(item as Record<string, unknown>),
          _itemType: itemType,
        };
      }

      hasMore = data.pagination?.hasMore ?? false;
      page++;
    }
  }

  private normalizeDecision(
    d: SocureDecision,
    now: string,
  ): NormalizedEntity {
    const modulesSummary = d.modules
      .map((m) => `${m.name}=${m.decision}(${m.score.toFixed(2)})`)
      .join(', ');

    const failedReasons = d.modules
      .filter((m) => m.reasonCodes?.length)
      .flatMap((m) =>
        (m.reasonCodes ?? []).map((r) => `${m.name}:${r}`),
      );

    return {
      source_system: 'socure',
      source_object_id: d.referenceId,
      entity_type: 'socure_decision',
      name: `Verification ${d.referenceId} — ${d.decision}`,
      description: `Decision: ${d.decision}, risk: ${d.riskScore.toFixed(2)}. Modules: ${modulesSummary}${failedReasons.length ? `. Reasons: ${failedReasons.join(', ')}` : ''}`,
      owner: null,
      status: d.status,
      source_url: `${this.config.baseUrl}/decisions/${d.referenceId}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(d.updatedAt),
      eligible_skill_families_json: ['agent', 'general'],
      metadata: {
        decision: d.decision,
        riskScore: d.riskScore,
        modules: d.modules,
      },
    };
  }

  private normalizeRiskScore(
    r: SocureRiskScore,
    now: string,
  ): NormalizedEntity {
    const scores: string[] = [`overall=${r.overallScore}`];
    if (r.emailRisk != null) scores.push(`email=${r.emailRisk}`);
    if (r.phoneRisk != null) scores.push(`phone=${r.phoneRisk}`);
    if (r.addressRisk != null) scores.push(`address=${r.addressRisk}`);
    if (r.syntheticScore != null) scores.push(`synthetic=${r.syntheticScore}`);

    return {
      source_system: 'socure',
      source_object_id: `risk-${r.referenceId}`,
      entity_type: 'socure_risk_score',
      name: `Risk Score ${r.referenceId}`,
      description: `Risk scores: ${scores.join(', ')}`,
      owner: null,
      status: 'active',
      source_url: `${this.config.baseUrl}/risk-scores/${r.referenceId}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(r.createdAt),
      eligible_skill_families_json: ['agent', 'general'],
      metadata: {
        overallScore: r.overallScore,
        emailRisk: r.emailRisk,
        phoneRisk: r.phoneRisk,
        addressRisk: r.addressRisk,
        syntheticScore: r.syntheticScore,
      },
    };
  }
}
