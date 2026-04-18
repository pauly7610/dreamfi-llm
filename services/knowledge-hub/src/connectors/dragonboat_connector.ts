/**
 * Dragonboat connector — syncs initiatives, features, and roadmap items
 * from the Dragonboat product portfolio management platform.
 *
 * Auth: Bearer token.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface DragonboatItem {
  id: string | number;
  name: string;
  description?: string | null;
  type: string;               // 'initiative' | 'feature' | 'roadmap_item'
  status?: string | null;
  priority?: string | null;
  rag?: string | null;         // Red / Amber / Green
  owner?: { name: string; email?: string } | null;
  product?: { name: string } | null;
  updated_at: string;
  created_at: string;
  url?: string | null;
}

interface DragonboatListResponse {
  data: DragonboatItem[];
  pagination?: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class DragonboatConnector extends BaseConnector {
  private bearerToken = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'dragonboat' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { token } = this.config.auth;
    if (!token) {
      throw new Error('[DragonboatConnector] Missing auth.token');
    }
    this.bearerToken = token;

    // Validate token
    await this.withRetry(async () => {
      const res = await fetch(this.buildUrl('/api/v1/me'), {
        headers: this.headers(),
      });
      if (!res.ok) {
        throw new Error(`Dragonboat auth check failed: ${res.status}`);
      }
    }, 'connect');

    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.bearerToken = '';
    this.connected = false;
  }

  // ── data fetching ─────────────────────────────────────────────────────

  protected async *fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    const endpoints = [
      '/api/v1/initiatives',
      '/api/v1/features',
      '/api/v1/roadmap-items',
    ];

    for (const endpoint of endpoints) {
      let page = 1;
      let totalPages = 1;

      while (page <= totalPages) {
        const params: Record<string, string> = {
          page: String(page),
          per_page: '100',
          sort: 'updated_at',
          order: 'desc',
        };
        if (watermark) {
          params.updated_since = watermark;
        }

        const data = await this.withRetry(async () => {
          const res = await fetch(this.buildUrl(endpoint, params), {
            headers: this.headers(),
          });
          if (!res.ok) {
            throw new Error(`Dragonboat ${endpoint} failed: ${res.status}`);
          }
          return (await res.json()) as DragonboatListResponse;
        }, `fetchRaw:${endpoint}`);

        totalPages = data.pagination?.total_pages ?? 1;

        for (const item of data.data) {
          yield item as unknown as Record<string, unknown>;
        }

        if (data.data.length === 0) break;
        page++;
      }
    }
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const item = rawPayload as unknown as DragonboatItem;
    const now = new Date().toISOString();

    return {
      source_system: 'dragonboat',
      source_object_id: String(item.id),
      entity_type: 'dragonboat_item',
      name: item.name,
      description: this.buildDescription(item),
      owner: item.owner?.name ?? null,
      status: this.mapStatus(item.status, item.rag),
      source_url: item.url ?? null,
      last_synced_at: now,
      freshness_score: this.computeFreshness(now),
      eligible_skill_families_json: this.inferSkillFamilies(item),
    };
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.bearerToken}`,
      Accept: 'application/json',
    };
  }

  private buildDescription(item: DragonboatItem): string {
    const parts: string[] = [];
    parts.push(`[${item.type}] ${item.name}`);
    if (item.priority) parts.push(`Priority: ${item.priority}`);
    if (item.rag) parts.push(`RAG: ${item.rag}`);
    if (item.product?.name) parts.push(`Product: ${item.product.name}`);
    if (item.description) parts.push(item.description);
    return parts.join(' | ');
  }

  private mapStatus(status?: string | null, rag?: string | null): string {
    if (!status) return 'unknown';
    const s = status.toLowerCase();
    if (['completed', 'done', 'shipped'].includes(s)) return 'done';
    if (['in progress', 'active'].includes(s)) return 'in_progress';
    if (['planned', 'backlog', 'not started'].includes(s)) return 'todo';
    // Append RAG if available
    if (rag) return `${s}_${rag.toLowerCase()}`;
    return s.replace(/\s+/g, '_');
  }

  private inferSkillFamilies(item: DragonboatItem): string[] {
    const type = item.type.toLowerCase();
    if (type === 'initiative') return ['summarization', 'copywriting'];
    if (type === 'feature') return ['agent', 'copywriting'];
    return ['general'];
  }
}
