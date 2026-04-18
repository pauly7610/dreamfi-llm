/**
 * PostHog connector — syncs event definitions, actions, insights,
 * feature flags, and funnels from a PostHog instance.
 *
 * Auth: Personal API key passed via the `Authorization` header.
 */

import {
  BaseConnector,
  ConnectorConfig,
  NormalizedEntity,
} from './base_connector';

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface PostHogPaginatedResponse<T> {
  count: number;
  results: T[];
  next: string | null;
  previous: string | null;
}

interface PostHogEventDefinition {
  id: string;
  name: string;
  description?: string | null;
  volume_30_day?: number | null;
  query_usage_30_day?: number | null;
  created_at: string;
  last_seen_at?: string | null;
}

interface PostHogAction {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  steps?: Array<{ event: string; url?: string }>;
  tags?: string[];
}

interface PostHogInsight {
  id: number;
  short_id: string;
  name?: string | null;
  description?: string | null;
  filters: Record<string, unknown>;
  result?: unknown;
  created_at: string;
  updated_at: string;
  created_by?: { first_name: string; email: string } | null;
  tags?: string[];
}

interface PostHogFeatureFlag {
  id: number;
  key: string;
  name: string;
  active: boolean;
  filters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  created_by?: { first_name: string } | null;
  rollout_percentage?: number | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Connector
// ────────────────────────────────────────────────────────────────────────────

export class PostHogConnector extends BaseConnector {
  private apiKey = '';
  private projectId = '';

  constructor(config: ConnectorConfig) {
    super({ ...config, sourceSystem: 'posthog' });
  }

  // ── lifecycle ─────────────────────────────────────────────────────────

  async connect(): Promise<void> {
    const { apiKey, projectId } = this.config.auth;
    if (!apiKey) {
      throw new Error('[PostHogConnector] Missing auth.apiKey');
    }
    this.apiKey = apiKey;
    this.projectId = projectId ?? '1';

    // Validate key
    await this.withRetry(async () => {
      const res = await fetch(
        this.buildUrl(`/api/projects/${this.projectId}/`),
        { headers: this.headers() },
      );
      if (!res.ok) {
        throw new Error(`PostHog auth check failed: ${res.status}`);
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
    const base = `/api/projects/${this.projectId}`;

    // 1. Event definitions
    yield* this.paginate<PostHogEventDefinition>(
      `${base}/event_definitions`,
      'event_definition',
      watermark,
    );

    // 2. Actions
    yield* this.paginate<PostHogAction>(
      `${base}/actions`,
      'action',
      watermark,
    );

    // 3. Insights
    yield* this.paginate<PostHogInsight>(
      `${base}/insights`,
      'insight',
      watermark,
    );

    // 4. Feature flags
    yield* this.paginate<PostHogFeatureFlag>(
      `${base}/feature_flags`,
      'feature_flag',
      watermark,
    );
  }

  // ── normalisation ─────────────────────────────────────────────────────

  normalize(rawPayload: Record<string, unknown>): NormalizedEntity {
    const itemType = rawPayload._itemType as string;
    const now = new Date().toISOString();

    switch (itemType) {
      case 'event_definition':
        return this.normalizeEventDef(
          rawPayload as unknown as PostHogEventDefinition,
          now,
        );
      case 'action':
        return this.normalizeAction(
          rawPayload as unknown as PostHogAction,
          now,
        );
      case 'insight':
        return this.normalizeInsight(
          rawPayload as unknown as PostHogInsight,
          now,
        );
      case 'feature_flag':
        return this.normalizeFeatureFlag(
          rawPayload as unknown as PostHogFeatureFlag,
          now,
        );
      default:
        throw new Error(`Unknown PostHog item type: ${itemType}`);
    }
  }

  // ── private helpers ───────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      Accept: 'application/json',
    };
  }

  private async *paginate<T extends Record<string, unknown>>(
    path: string,
    itemType: string,
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>> {
    let url: string | null = this.buildUrl(path, { limit: '100' });

    while (url) {
      const data = await this.withRetry(async () => {
        const res = await fetch(url!, { headers: this.headers() });
        if (!res.ok) throw new Error(`PostHog ${path} failed: ${res.status}`);
        return (await res.json()) as PostHogPaginatedResponse<T>;
      }, `fetchRaw:${itemType}`);

      for (const item of data.results) {
        const updatedAt =
          (item as Record<string, unknown>).updated_at as string | undefined;
        if (watermark && updatedAt && updatedAt < watermark) continue;
        yield { ...item, _itemType: itemType };
      }

      url = data.next;
    }
  }

  private normalizeEventDef(
    def: PostHogEventDefinition,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'posthog',
      source_object_id: `event-${def.id}`,
      entity_type: 'posthog_event_definition',
      name: def.name,
      description:
        def.description ??
        `Event (30-day volume: ${def.volume_30_day ?? 'unknown'})`,
      owner: null,
      status: 'active',
      source_url: `${this.config.baseUrl}/data-management/events/${def.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(
        def.last_seen_at ?? def.created_at,
      ),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeAction(
    action: PostHogAction,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'posthog',
      source_object_id: `action-${action.id}`,
      entity_type: 'posthog_action',
      name: action.name,
      description:
        action.description ??
        `Action with ${action.steps?.length ?? 0} step(s)`,
      owner: null,
      status: 'active',
      source_url: `${this.config.baseUrl}/data-management/actions/${action.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(action.updated_at),
      eligible_skill_families_json: ['general'],
    };
  }

  private normalizeInsight(
    insight: PostHogInsight,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'posthog',
      source_object_id: `insight-${insight.short_id}`,
      entity_type: 'posthog_insight',
      name: insight.name ?? `Insight ${insight.short_id}`,
      description: insight.description ?? 'PostHog insight',
      owner: insight.created_by?.first_name ?? null,
      status: 'active',
      source_url: `${this.config.baseUrl}/insights/${insight.short_id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(insight.updated_at),
      eligible_skill_families_json: ['summarization', 'general'],
      metadata: {
        tags: insight.tags,
      },
    };
  }

  private normalizeFeatureFlag(
    flag: PostHogFeatureFlag,
    now: string,
  ): NormalizedEntity {
    return {
      source_system: 'posthog',
      source_object_id: `flag-${flag.id}`,
      entity_type: 'posthog_feature_flag',
      name: flag.name || flag.key,
      description: `Feature flag "${flag.key}" — ${flag.active ? 'active' : 'inactive'}, rollout: ${flag.rollout_percentage ?? 'N/A'}%`,
      owner: flag.created_by?.first_name ?? null,
      status: flag.active ? 'active' : 'inactive',
      source_url: `${this.config.baseUrl}/feature_flags/${flag.id}`,
      last_synced_at: now,
      freshness_score: this.computeFreshness(flag.updated_at),
      eligible_skill_families_json: ['general'],
    };
  }
}
