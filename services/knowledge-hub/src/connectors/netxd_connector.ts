/**
 * Ledger NetXD connector — syncs transactions, balances, settlements,
 * and journal entries from the NetXD ledger platform.
 *
 * Auth: API key + client ID.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface NetXDTransaction {
  transaction_id: string;
  type: string;
  status: string;
  amount: number;
  currency: string;
  from_account: string;
  to_account: string;
  description?: string | null;
  reference?: string | null;
  created_at: string;
  updated_at: string;
  settled_at?: string | null;
}

interface NetXDBalance {
  account_id: string;
  account_name: string;
  currency: string;
  available: number;
  pending: number;
  total: number;
  updated_at: string;
}

interface NetXDSettlement {
  settlement_id: string;
  status: string;
  amount: number;
  currency: string;
  transaction_count: number;
  settlement_date: string;
  created_at: string;
}

interface NetXDJournalEntry {
  entry_id: string;
  type: string;
  debit_account: string;
  credit_account: string;
  amount: number;
  currency: string;
  description?: string | null;
  created_at: string;
}

interface NetXDListResponse<T> {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    has_more: boolean;
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class NetXDConnector extends BaseConnector {
  private apiKey = '';
  private clientId = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'netxd' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { apiKey, clientId } = this.config.auth;
    if (!apiKey || !clientId) {
      throw new Error('[NetXDConnector] Missing auth.apiKey or auth.clientId');
    }
    this.apiKey = apiKey;
    this.clientId = clientId;

    // Validate credentials
    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/v1/health'), {
        headers: this.headers(),
      });
      if (!res.ok) {
        throw new Error(`NetXD auth check failed: ${res.status}`);
      }
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.apiKey = '';
    this.clientId = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    // 1. Transactions
    yield* this.paginateEndpoint<NetXDTransaction>(
      '/api/v1/transactions',
      'transaction',
      watermark,
    );

    // 2. Balances (snapshot — no pagination needed)
    const balances = await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/v1/balances'), {
        headers: this.headers(),
      });
      if (!res.ok) throw new Error(`NetXD balances failed: ${res.status}`);
      return (await res.json()) as { data: NetXDBalance[] };
    }, 'fetchRaw:balances');

    for (const bal of balances.data) {
      yield { ...bal, _itemType: 'balance' } as unknown as Record<
        string,
        unknown
      >;
    }

    // 3. Settlements
    yield* this.paginateEndpoint<NetXDSettlement>(
      '/api/v1/settlements',
      'settlement',
      watermark,
    );

    // 4. Journal entries
    yield* this.paginateEndpoint<NetXDJournalEntry>(
      '/api/v1/journal-entries',
      'journal_entry',
      watermark,
    );
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const itemType = rawPayload._itemType as string;
    const now = new Date().toISOString();

    switch (itemType) {
      case 'transaction':
        return this.normalizeTransaction(
          rawPayload as unknown as NetXDTransaction,
          now,
        );
      case 'balance':
        return this.normalizeBalance(
          rawPayload as unknown as NetXDBalance,
          now,
        );
      case 'settlement':
        return this.normalizeSettlement(
          rawPayload as unknown as NetXDSettlement,
          now,
        );
      case 'journal_entry':
        return this.normalizeJournalEntry(
          rawPayload as unknown as NetXDJournalEntry,
          now,
        );
      default:
        throw new Error(`Unknown NetXD item type: ${itemType}`);
    }
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      'X-Api-Key': this.apiKey,
      'X-Client-Id': this.clientId,
      Accept: 'application/json',
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
        per_page: '100',
        sort: 'updated_at',
        order: 'desc',
      };
      if (watermark) params.updated_since = watermark;

      const data = await this.withRetry(async () => {
        const res = await fetch(this.buildUrl(path, params), {
          headers: this.headers(),
        });
        if (!res.ok) {
          throw new Error(`NetXD ${path} failed: ${res.status}`);
        }
        return (await res.json()) as NetXDListResponse<T>;
      }, `fetchRaw:${itemType}`);

      for (const item of data.data) {
        yield {
          ...(item as Record<string, unknown>),
          _itemType: itemType,
        };
      }

      hasMore = data.pagination.has_more;
      page++;
    }
  }

  private normalizeTransaction(
    t: NetXDTransaction,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'netxd',
      source_object_id: t.transaction_id,
      entity_type: 'netxd_transaction',
      name: `${t.type} — ${t.amount} ${t.currency}`,
      description: `Transaction ${t.transaction_id}: ${t.type} ${t.amount} ${t.currency} from ${t.from_account} to ${t.to_account}. Status: ${t.status}. ${t.description ?? ''}`.trim(),
      owner: null,
      status: t.status,
      source_url: `${this.config.baseUrl}/transactions/${t.transaction_id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(t.updated_at),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeBalance(
    b: NetXDBalance,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'netxd',
      source_object_id: `balance-${b.account_id}`,
      entity_type: 'netxd_balance',
      name: `${b.account_name} Balance`,
      description: `Account ${b.account_id}: available ${b.available} ${b.currency}, pending ${b.pending}, total ${b.total}`,
      owner: null,
      status: 'active',
      source_url: `${this.config.baseUrl}/accounts/${b.account_id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(b.updated_at),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeSettlement(
    s: NetXDSettlement,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'netxd',
      source_object_id: s.settlement_id,
      entity_type: 'netxd_settlement',
      name: `Settlement ${s.settlement_id}`,
      description: `Settlement: ${s.amount} ${s.currency}, ${s.transaction_count} transactions, date: ${s.settlement_date}, status: ${s.status}`,
      owner: null,
      status: s.status,
      source_url: `${this.config.baseUrl}/settlements/${s.settlement_id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(s.created_at),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeJournalEntry(
    j: NetXDJournalEntry,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'netxd',
      source_object_id: j.entry_id,
      entity_type: 'netxd_journal_entry',
      name: `Journal ${j.entry_id} — ${j.type}`,
      description: `${j.type}: debit ${j.debit_account}, credit ${j.credit_account}, ${j.amount} ${j.currency}. ${j.description ?? ''}`.trim(),
      owner: null,
      status: 'active',
      source_url: `${this.config.baseUrl}/journal-entries/${j.entry_id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(j.created_at),
      eligible_skill_families_json: ['general'],
    };
  }
}
