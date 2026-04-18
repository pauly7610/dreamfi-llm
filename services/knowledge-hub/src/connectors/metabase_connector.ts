/**
 * Metabase connector — syncs saved questions (cards), dashboards, and
 * database metadata.  Can also execute saved queries to retrieve results.
 *
 * Auth: session-based (username + password -> session token).
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface MetabaseCard {
  id: number;
  name: string;
  description?: string | null;
  display: string;
  collection_id?: number | null;
  collection?: { name: string } | null;
  database_id: number;
  table_id?: number | null;
  query_type: string;
  creator?: { common_name: string; email: string } | null;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

interface MetabaseDashboard {
  id: number;
  name: string;
  description?: string | null;
  collection_id?: number | null;
  collection?: { name: string } | null;
  creator?: { common_name: string } | null;
  created_at: string;
  updated_at: string;
  archived: boolean;
  parameters?: unknown[];
  ordered_cards?: Array<{ card_id: number; card: { name: string } }>;
}

interface MetabaseDatabase {
  id: number;
  name: string;
  engine: string;
  tables?: Array<{
    id: number;
    name: string;
    schema: string;
    description?: string | null;
  }>;
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class MetabaseConnector extends BaseConnector {
  private sessionToken = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'metabase' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { username, password } = this.config.auth;
    if (!username || !password) {
      throw new Error('[MetabaseConnector] Missing auth.username or auth.password');
    }

    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/session'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        throw new Error(`Metabase session creation failed: ${res.status}`);
      }
      const data = (await res.json()) as { id: string };
      this.sessionToken = data.id;
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    if (this.sessionToken) {
      try {
        await fetch(this.buildUrl('/api/session'), {
          method: 'DELETE',
          headers: this.headers(),
        });
      } catch {
        // Best-effort logout
      }
    }
    this.sessionToken = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    // 1. Fetch all cards (saved questions)
    const cards = await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/card'), {
        headers: this.headers(),
      });
      if (!res.ok) throw new Error(`Metabase cards fetch failed: ${res.status}`);
      return (await res.json()) as MetabaseCard[];
    }, 'fetchRaw:cards');

    for (const card of cards) {
      if (card.archived) continue;
      if (watermark && card.updated_at < watermark) continue;
      yield { _type: 'card', ...card } as unknown as Record<string, unknown>;
    }

    // 2. Fetch all dashboards
    const dashboards = await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/dashboard'), {
        headers: this.headers(),
      });
      if (!res.ok) throw new Error(`Metabase dashboards fetch failed: ${res.status}`);
      return (await res.json()) as MetabaseDashboard[];
    }, 'fetchRaw:dashboards');

    for (const dash of dashboards) {
      if (dash.archived) continue;
      if (watermark && dash.updated_at < watermark) continue;
      yield { _type: 'dashboard', ...dash } as unknown as Record<string, unknown>;
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const raw = rawPayload as Record<string, unknown>;
    const type = raw._type as string;

    if (type === 'dashboard') {
      return this.normalizeDashboard(raw as unknown as MetabaseDashboard);
    }
    return this.normalizeCard(raw as unknown as MetabaseCard);
  }

  // ── public: execute a saved query ─────────────────────────────────────

  /**
   * Execute a saved question (card) and return the result rows.
   */
  async executeCard(cardId: number): Promise<Record<string, unknown>[]> {
    if (!this.connected) {
      throw new Error('[MetabaseConnector] Not connected');
    }

    const res = await this.withRetry(async () => {
      const r = await fetch(this.buildUrl(`/api/card/${cardId}/query`), {
        method: 'POST',
        headers: this.headers(),
      });
      if (!r.ok) throw new Error(`Metabase card execution failed: ${r.status}`);
      return r;
    }, 'executeCard');

    const data = (await res.json()) as {
      data: { rows: unknown[][]; cols: Array<{ name: string }> };
    };

    const colNames = data.data.cols.map((c) => c.name);
    return data.data.rows.map((row) => {
      const obj: Record<string, unknown> = {};
      row.forEach((val, i) => {
        obj[colNames[i]] = val;
      });
      return obj;
    });
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      'X-Metabase-Session': this.sessionToken,
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
  }

  private normalizeCard(card: MetabaseCard): NormalizedEntity {
    const now = new Date().toISOString();
    return {
      source_system: 'metabase',
      source_object_id: `card-${card.id}`,
      entity_type: 'metabase_card',
      name: card.name,
      description: card.description ?? `Saved question (${card.display})`,
      owner: card.creator?.common_name ?? null,
      status: 'active',
      source_url: `${this.config.baseUrl}/question/${card.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(card.updated_at),
      eligible_skill_families_json: ['summarization', 'general'],
      metadata: {
        display: card.display,
        queryType: card.query_type,
        databaseId: card.database_id,
        collection: card.collection?.name,
      },
    };
  }

  private normalizeDashboard(dash: MetabaseDashboard): NormalizedEntity {
    const now = new Date().toISOString();
    const cardNames =
      dash.ordered_cards?.map((c) => c.card?.name).filter(Boolean) ?? [];

    return {
      source_system: 'metabase',
      source_object_id: `dashboard-${dash.id}`,
      entity_type: 'metabase_dashboard',
      name: dash.name,
      description:
        dash.description ??
        (cardNames.length
          ? `Dashboard with cards: ${cardNames.join(', ')}`
          : 'Metabase dashboard'),
      owner: dash.creator?.common_name ?? null,
      status: 'active',
      source_url: `${this.config.baseUrl}/dashboard/${dash.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(dash.updated_at),
      eligible_skill_families_json: ['summarization', 'general'],
      metadata: {
        collection: dash.collection?.name,
        cardCount: dash.ordered_cards?.length ?? 0,
        cards: cardNames,
      },
    };
  }
}
