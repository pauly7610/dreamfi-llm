/**
 * Klaviyo connector — syncs campaigns, flows, lists, and metrics
 * from Klaviyo's v3 API (revision 2024-02-15).
 *
 * Auth: Private API key via the `Authorization` header.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types (JSON:API envelope)
// ────────────────────────────────────────────────────────────────────────────

interface KlaviyoResource<A = Record<string, unknown>> {
  type: string;
  id: string;
  attributes: A;
  links?: { self: string };
}

interface KlaviyoListResponse<A = Record<string, unknown>> {
  data: KlaviyoResource<A>[];
  links?: { self: string; next?: string; prev?: string };
}

interface CampaignAttributes {
  name: string;
  status: string;
  audiences?: { included?: Array<{ id: string }> };
  send_strategy?: { method: string };
  created_at: string;
  updated_at: string;
  archived: boolean;
}

interface FlowAttributes {
  name: string;
  status: string;
  trigger_type?: string;
  created: string;
  updated: string;
  archived: boolean;
}

interface ListAttributes {
  name: string;
  created: string;
  updated: string;
  opt_in_process?: string;
}

interface MetricAttributes {
  name: string;
  created: string;
  updated: string;
  integration?: { name: string } | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class KlaviyoConnector extends BaseConnector {
  private apiKey = '';
  private static readonly API_REVISION = '2024-02-15';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'klaviyo' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { apiKey } = this.config.auth;
    if (!apiKey) {
      throw new Error('[KlaviyoConnector] Missing auth.apiKey');
    }
    this.apiKey = apiKey;

    // Validate key by fetching account info
    await this.withRetry(async () => {
      const res = await fetch('https://a.klaviyo.com/api/accounts/', {
        headers: this.headers(),
      });
      if (!res.ok) {
        throw new Error(`Klaviyo auth check failed: ${res.status}`);
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
    // 1. Campaigns
    yield* this.paginateResource<CampaignAttributes>(
      'https://a.klaviyo.com/api/campaigns/',
      'campaign',
      watermark,
    );

    // 2. Flows
    yield* this.paginateResource<FlowAttributes>(
      'https://a.klaviyo.com/api/flows/',
      'flow',
      watermark,
    );

    // 3. Lists
    yield* this.paginateResource<ListAttributes>(
      'https://a.klaviyo.com/api/lists/',
      'list',
      watermark,
    );

    // 4. Metrics
    yield* this.paginateResource<MetricAttributes>(
      'https://a.klaviyo.com/api/metrics/',
      'metric',
      watermark,
    );
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const resource = rawPayload as unknown as KlaviyoResource & {
      _itemType: string;
    };
    const now = new Date().toISOString();

    switch (resource._itemType) {
      case 'campaign':
        return this.normalizeCampaign(
          resource as KlaviyoResource<CampaignAttributes>,
          now,
        );
      case 'flow':
        return this.normalizeFlow(
          resource as KlaviyoResource<FlowAttributes>,
          now,
        );
      case 'list':
        return this.normalizeList(
          resource as KlaviyoResource<ListAttributes>,
          now,
        );
      case 'metric':
        return this.normalizeMetric(
          resource as KlaviyoResource<MetricAttributes>,
          now,
        );
      default:
        throw new Error(`Unknown Klaviyo resource type: ${resource._itemType}`);
    }
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: `Klaviyo-API-Key ${this.apiKey}`,
      Accept: 'application/json',
      revision: KlaviyoConnector.API_REVISION,
    };
  }

  private async *paginateResource<A>(
    startUrl: string,
    itemType: string,
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    let url: string | null = startUrl;

    while (url) {
      const data = await this.withRetry(async () => {
        const res = await fetch(url!, { headers: this.headers() });
        if (!res.ok) {
          throw new Error(`Klaviyo ${itemType} fetch failed: ${res.status}`);
        }
        return (await res.json()) as KlaviyoListResponse<A>;
      }, `fetchRaw:${itemType}`);

      for (const item of data.data) {
        const attrs = item.attributes as Record<string, unknown>;
        const updatedAt =
          (attrs.updated_at as string) ??
          (attrs.updated as string) ??
          '';
        if (watermark && updatedAt && updatedAt < watermark) continue;
        yield { ...item, _itemType: itemType } as unknown as Record<
          string,
          unknown
        >;
      }

      url = data.links?.next ?? null;
    }
  }

  private normalizeCampaign(
    r: KlaviyoResource<CampaignAttributes>,
    now: string,
  ): NormalizedEntity {
    const a = r.attributes;
    return {
      source_system: 'klaviyo',
      source_object_id: r.id,
      entity_type: 'klaviyo_campaign',
      name: a.name,
      description: `Campaign "${a.name}" — ${a.status}, strategy: ${a.send_strategy?.method ?? 'N/A'}`,
      owner: null,
      status: a.archived ? 'archived' : a.status,
      source_url: `https://www.klaviyo.com/campaign/${r.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(a.updated_at),
      eligible_skill_families_json: ['copywriting', 'outreach'],
    };
  }

  private normalizeFlow(
    r: KlaviyoResource<FlowAttributes>,
    now: string,
  ): NormalizedEntity {
    const a = r.attributes;
    return {
      source_system: 'klaviyo',
      source_object_id: r.id,
      entity_type: 'klaviyo_flow',
      name: a.name,
      description: `Flow "${a.name}" — ${a.status}, trigger: ${a.trigger_type ?? 'N/A'}`,
      owner: null,
      status: a.archived ? 'archived' : a.status,
      source_url: `https://www.klaviyo.com/flow/${r.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(a.updated),
      eligible_skill_families_json: ['copywriting', 'outreach'],
    };
  }

  private normalizeList(
    r: KlaviyoResource<ListAttributes>,
    now: string,
  ): NormalizedEntity {
    const a = r.attributes;
    return {
      source_system: 'klaviyo',
      source_object_id: r.id,
      entity_type: 'klaviyo_list',
      name: a.name,
      description: `Subscriber list "${a.name}" — opt-in: ${a.opt_in_process ?? 'N/A'}`,
      owner: null,
      status: 'active',
      source_url: `https://www.klaviyo.com/list/${r.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(a.updated),
      eligible_skill_families_json: ['outreach'],
    };
  }

  private normalizeMetric(
    r: KlaviyoResource<MetricAttributes>,
    now: string,
  ): NormalizedEntity {
    const a = r.attributes;
    return {
      source_system: 'klaviyo',
      source_object_id: r.id,
      entity_type: 'klaviyo_metric',
      name: a.name,
      description: `Metric "${a.name}" — integration: ${a.integration?.name ?? 'none'}`,
      owner: null,
      status: 'active',
      source_url: null,
      last_synced_at: now,
      freshness_score: this.computeFreshness(a.updated),
      eligible_skill_families_json: ['general'],
    };
  }
}
