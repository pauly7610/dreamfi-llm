/**
 * Base connector module for the Knowledge Hub.
 *
 * Every external-system connector extends {@link BaseConnector} and implements
 * the four abstract methods.  The base class provides shared helpers for
 * freshness scoring, retry logic, and result normalisation.
 */

// ────────────────────────────────────────────────────────────────────────────
// Interfaces
// ────────────────────────────────────────────────────────────────────────────

/** Configuration every connector needs at construction time. */
export interface ConnectorConfig {
  /** Human-readable name shown in logs and the admin UI. */
  name: string;

  /** Canonical source_system key written into every synced entity. */
  sourceSystem: string;

  /** Base URL of the external API (protocol + host). */
  baseUrl: string;

  /** Authentication fields — shape varies by connector. */
  auth: Record<string, string>;

  /** How often to poll for changes, in seconds.  Defaults to 3600 (1 h). */
  syncIntervalSeconds?: number;

  /** Maximum retry attempts on transient failures.  Defaults to 3. */
  maxRetries?: number;

  /** Milliseconds between retries (doubles on each attempt).  Defaults to 1000. */
  retryBaseDelayMs?: number;
}

/** One entity normalised from external data, ready for upsert. */
export interface NormalizedEntity {
  source_system: string;
  source_object_id: string;
  entity_type: string;
  name: string;
  description: string | null;
  owner: string | null;
  status: string | null;
  source_url: string | null;
  last_synced_at: string;           // ISO-8601
  freshness_score: number;          // 0–1
  eligible_skill_families_json: string[];
  /** Extra fields the connector wants to persist (stored as JSON). */
  metadata?: Record<string, unknown>;
}

/** Result returned by a full sync run. */
export interface SyncResult {
  /** Source system identifier. */
  sourceSystem: string;

  /** Number of entities successfully synced (created or updated). */
  entitiesSynced: number;

  /** Per-entity errors that did not abort the run. */
  errors: SyncError[];

  /**
   * Opaque watermark the connector can use on the next call to
   * perform incremental sync (e.g. a timestamp or cursor token).
   */
  watermark: string | null;

  /** Wall-clock duration of the sync, in milliseconds. */
  durationMs: number;
}

/** A non-fatal error encountered during sync. */
export interface SyncError {
  sourceObjectId: string;
  message: string;
  code?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Abstract base class
// ────────────────────────────────────────────────────────────────────────────

/**
 * Abstract connector that every source-system integration must extend.
 *
 * Subclasses implement four methods:
 *  - {@link connect}      – authenticate / open a session
 *  - {@link disconnect}   – tear down the session
 *  - {@link fetchRaw}     – paginate through the external API
 *  - {@link normalize}    – turn one raw payload into a {@link NormalizedEntity}
 *
 * The base class provides {@link sync}, {@link computeFreshness}, and
 * {@link withRetry}.
 */
export abstract class BaseConnector {
  protected readonly config: ConnectorConfig;
  protected connected = false;

  constructor(config: ConnectorConfig) {
    this.config = {
      syncIntervalSeconds: 3600,
      maxRetries: 3,
      retryBaseDelayMs: 1000,
      ...config,
    };
  }

  // ── lifecycle ──────────────────────────────────────────────────────────

  /**
   * Open a connection / authenticate with the external system.
   * Implementations should set `this.connected = true` on success.
   */
  abstract connect(): Promise<void>;

  /**
   * Tear down the connection.
   * Implementations should set `this.connected = false`.
   */
  abstract disconnect(): Promise<void>;

  // ── data fetching ─────────────────────────────────────────────────────

  /**
   * Fetch raw payloads from the external API.
   *
   * @param watermark  Opaque token from a previous sync (may be `null`
   *                   for a full initial sync).
   * @returns An async generator that yields raw API payloads one at a time.
   */
  protected abstract fetchRaw(
    watermark: string | null,
  ): AsyncGenerator<Record<string, unknown>>;

  /**
   * Transform a single raw API payload into a {@link NormalizedEntity}.
   */
  abstract normalize(rawPayload: Record<string, unknown>): NormalizedEntity;

  // ── sync orchestration ────────────────────────────────────────────────

  /**
   * Run a full sync pass.
   *
   * 1. Calls {@link fetchRaw} to paginate through all changed records.
   * 2. Normalises each raw payload via {@link normalize}.
   * 3. Collects results and errors.
   *
   * Callers are responsible for persisting the returned entities and
   * storing the new watermark.
   *
   * @param watermark  Previous watermark, or `null` for a full sync.
   */
  async sync(watermark: string | null): Promise<{
    entities: NormalizedEntity[];
    result: SyncResult;
  }> {
    if (!this.connected) {
      throw new Error(
        `[${this.config.name}] Cannot sync — connector is not connected.`,
      );
    }

    const start = Date.now();
    const entities: NormalizedEntity[] = [];
    const errors: SyncError[] = [];
    let newWatermark: string | null = null;

    for await (const raw of this.fetchRaw(watermark)) {
      try {
        const entity = this.normalize(raw);
        entities.push(entity);

        // The latest last_synced_at becomes the next watermark.
        if (
          !newWatermark ||
          entity.last_synced_at > newWatermark
        ) {
          newWatermark = entity.last_synced_at;
        }
      } catch (err) {
        const id =
          (raw as Record<string, unknown>).id?.toString() ??
          (raw as Record<string, unknown>).key?.toString() ??
          'unknown';
        errors.push({
          sourceObjectId: id,
          message: err instanceof Error ? err.message : String(err),
        });
      }
    }

    return {
      entities,
      result: {
        sourceSystem: this.config.sourceSystem,
        entitiesSynced: entities.length,
        errors,
        watermark: newWatermark,
        durationMs: Date.now() - start,
      },
    };
  }

  // ── helpers ───────────────────────────────────────────────────────────

  /**
   * Compute a freshness score (0–1) based on how recently data was synced.
   *
   * | Age         | Score |
   * |-------------|-------|
   * | < 1 day     | 1.0   |
   * | < 7 days    | 0.8   |
   * | < 30 days   | 0.5   |
   * | >= 30 days  | 0.2   |
   */
  computeFreshness(lastSyncedAt: Date | string): number {
    const synced =
      typeof lastSyncedAt === 'string'
        ? new Date(lastSyncedAt)
        : lastSyncedAt;
    const ageMs = Date.now() - synced.getTime();
    const ageDays = ageMs / (1000 * 60 * 60 * 24);

    if (ageDays < 1) return 1.0;
    if (ageDays < 7) return 0.8;
    if (ageDays < 30) return 0.5;
    return 0.2;
  }

  /**
   * Execute an async function with exponential-back-off retry.
   *
   * @param fn          The function to attempt.
   * @param context     Label used in error messages.
   * @param maxRetries  Override for `config.maxRetries`.
   */
  protected async withRetry<T>(
    fn: () => Promise<T>,
    context: string,
    maxRetries?: number,
  ): Promise<T> {
    const attempts = maxRetries ?? this.config.maxRetries ?? 3;
    const baseDelay = this.config.retryBaseDelayMs ?? 1000;
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= attempts; attempt++) {
      try {
        return await fn();
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        if (attempt < attempts) {
          const delay = baseDelay * Math.pow(2, attempt - 1);
          await new Promise((r) => setTimeout(r, delay));
        }
      }
    }

    throw new Error(
      `[${this.config.name}] ${context} failed after ${attempts} attempts: ${lastError?.message}`,
    );
  }

  /**
   * Build a URL by appending a path to the configured `baseUrl`.
   */
  protected buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(path, this.config.baseUrl);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
      }
    }
    return url.toString();
  }
}
