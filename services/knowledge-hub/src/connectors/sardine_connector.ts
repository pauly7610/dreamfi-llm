/**
 * Sardine connector — syncs transactions, alerts, risk scores, and
 * monitoring rules from the Sardine fraud-prevention platform.
 *
 * Auth: client ID + secret key (HMAC-signed requests).
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface SardineAlert {
  id: string;
  type: string;
  severity: string;                  // 'low' | 'medium' | 'high' | 'critical'
  status: string;                    // 'open' | 'investigating' | 'resolved' | 'dismissed'
  description: string;
  customer_id?: string | null;
  transaction_id?: string | null;
  risk_score?: number | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

interface SardineRiskScore {
  session_key: string;
  customer_id: string;
  overall_score: number;             // 0–100
  level: string;                     // 'low' | 'medium' | 'high' | 'very_high'
  signals: Array<{ name: string; score: number }>;
  device_score?: number | null;
  behavior_score?: number | null;
  created_at: string;
}

interface SardineTransaction {
  id: string;
  type: string;
  amount: number;
  currency: string;
  status: string;
  risk_level: string;
  customer_id: string;
  created_at: string;
  updated_at: string;
}

interface SardineRule {
  id: string;
  name: string;
  description?: string | null;
  status: string;                    // 'active' | 'inactive' | 'shadow'
  action: string;                    // 'block' | 'flag' | 'allow'
  conditions: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface SardineListResponse<T> {
  data: T[];
  pagination?: { cursor?: string; has_more: boolean };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class SardineConnector extends BaseConnector {
  private clientId = '';
  private secretKey = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'sardine' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { clientId, secretKey } = this.config.auth;
    if (!clientId || !secretKey) {
      throw new Error(
        '[SardineConnector] Missing auth.clientId or auth.secretKey',
      );
    }
    this.clientId = clientId;
    this.secretKey = secretKey;

    // Validate credentials
    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/v1/auth/validate'), {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify({ client_id: this.clientId }),
      });
      if (!res.ok) {
        throw new Error(`Sardine auth check failed: ${res.status}`);
      }
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.clientId = '';
    this.secretKey = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    // 1. Alerts
    yield* this.paginateCursor<SardineAlert>(
      '/v1/alerts',
      'alert',
      watermark,
    );

    // 2. Transactions
    yield* this.paginateCursor<SardineTransaction>(
      '/v1/transactions',
      'transaction',
      watermark,
    );

    // 3. Rules (typically small set, no pagination needed)
    const rules = await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/v1/rules'), {
        headers: this.headers(),
      });
      if (!res.ok) throw new Error(`Sardine rules failed: ${res.status}`);
      return (await res.json()) as { data: SardineRule[] };
    }, 'fetchRaw:rules');

    for (const rule of rules.data) {
      yield { ...rule, _itemType: 'rule' } as unknown as Record<
        string,
        unknown
      >;
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const itemType = rawPayload._itemType as string;
    const now = new Date().toISOString();

    switch (itemType) {
      case 'alert':
        return this.normalizeAlert(
          rawPayload as unknown as SardineAlert,
          now,
        );
      case 'transaction':
        return this.normalizeTransaction(
          rawPayload as unknown as SardineTransaction,
          now,
        );
      case 'rule':
        return this.normalizeRule(
          rawPayload as unknown as SardineRule,
          now,
        );
      default:
        throw new Error(`Unknown Sardine item type: ${itemType}`);
    }
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    // Sardine uses Basic auth with clientId:secretKey
    const credentials = Buffer.from(
      `${this.clientId}:${this.secretKey}`,
    ).toString('base64');

    return {
      Authorization: `Basic ${credentials}`,
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
  }

  private async *paginateCursor<T>(
    path: string,
    itemType: string,
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    let cursor: string | undefined;
    let hasMore = true;

    while (hasMore) {
      const params: Record<string, string> = { limit: '100' };
      if (cursor) params.cursor = cursor;
      if (watermark) params.updated_since = watermark;

      const data = await this.withRetry(async () => {
        const res = await fetch(this.buildUrl(path, params), {
          headers: this.headers(),
        });
        if (!res.ok) {
          throw new Error(`Sardine ${path} failed: ${res.status}`);
        }
        return (await res.json()) as SardineListResponse<T>;
      }, `fetchRaw:${itemType}`);

      for (const item of data.data) {
        yield {
          ...(item as Record<string, unknown>),
          _itemType: itemType,
        };
      }

      hasMore = data.pagination?.has_more ?? false;
      cursor = data.pagination?.cursor ?? undefined;
    }
  }

  private normalizeAlert(
    a: SardineAlert,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'sardine',
      source_object_id: a.id,
      entity_type: 'sardine_alert',
      name: `[${a.severity.toUpperCase()}] ${a.type} Alert`,
      description: `Alert ${a.id}: ${a.description}. Severity: ${a.severity}, status: ${a.status}. Risk score: ${a.risk_score ?? 'N/A'}. Customer: ${a.customer_id ?? 'N/A'}`,
      owner: null,
      status: a.status,
      source_url: `${this.config.baseUrl}/alerts/${a.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(a.updated_at),
      eligible_skill_families_json: ['agent', 'general'],
    };
  }

  private normalizeTransaction(
    t: SardineTransaction,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'sardine',
      source_object_id: t.id,
      entity_type: 'sardine_transaction',
      name: `${t.type} — ${t.amount} ${t.currency}`,
      description: `Transaction ${t.id}: ${t.type} ${t.amount} ${t.currency}, risk: ${t.risk_level}, status: ${t.status}`,
      owner: null,
      status: t.status,
      source_url: `${this.config.baseUrl}/transactions/${t.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(t.updated_at),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeRule(
    r: SardineRule,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'sardine',
      source_object_id: r.id,
      entity_type: 'sardine_rule',
      name: r.name,
      description: `Rule "${r.name}": action=${r.action}, status=${r.status}. ${r.description ?? ''}`.trim(),
      owner: null,
      status: r.status,
      source_url: `${this.config.baseUrl}/rules/${r.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(r.updated_at),
      eligible_skill_families_json: ['agent', 'general'],
    };
  }
}
