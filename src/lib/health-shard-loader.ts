/**
 * Browser-side loader for the sharded snowflake coverage profiles.
 *
 * Architecture:
 *  - One small `manifest.json` lists every shard + patch with a sha-256 etag.
 *  - Shards (~256 listings each) and per-ticker patch overlays are cached in
 *    sessionStorage keyed by etag. Re-renders within the session are free.
 *  - When the manifest's etag for a shard or patch flips, only that one blob
 *    is re-downloaded; the rest of the catalog stays warm.
 *
 * Endpoints:
 *  - Static (GitHub Pages):  `${BASE_URL}data/health/...`
 *  - Versioning API:         `${API_ORIGIN}/v1/coverage/...` (set window.__QBITOS_API_ORIGIN__)
 *
 * Public surface:
 *  - `loadHealthManifest()`              -> HealthManifest
 *  - `getCoverageForTicker(ticker)`      -> SnowflakeProfileV1 | null
 *  - `prefetchShardForTicker(ticker)`    -> Promise<void>
 *  - `getCoverageMap()`                  -> Promise<Record<string, SnowflakeSummary>>
 */

import type { SnowflakeAxis, SnowflakeProfileV1 } from './health-snowflake-types';

export type HealthShardEntry = {
	id: string;
	url: string;
	etag: string;
	bytes: number;
	count: number;
	first: string;
	last: string;
};

export type HealthPatchEntry = {
	ticker: string;
	url: string;
	etag: string;
	bytes: number;
	asOfISO: string;
};

export type HealthManifest = {
	schemaVersion: 1;
	generatedAt: string;
	shardSize: number;
	tickerCount: number;
	shardCount: number;
	patchCount: number;
	axes: { name: string; label: string; checkCount: number }[];
	indexUrl: string;
	indexEtag: string;
	indexBytes: number;
	shards: HealthShardEntry[];
	patches: HealthPatchEntry[];
};

export type SnowflakeSummary = {
	ticker: string;
	displayName: string;
	asOfISO: string;
	totalChecks: number;
	passedChecks: number;
	naChecks: number;
	failedChecks: number;
	axes: { name: string; passed: number; total: number; na: number }[];
};

type ShardPayload = {
	schemaVersion: 1;
	shardId: string;
	tickers: string[];
	profiles: Record<string, SnowflakeProfileV1>;
};

type LoaderOptions = {
	baseUrl?: string;
	apiOrigin?: string | null;
};

const SESSION_PREFIX = 'qbitos:health:';
const MANIFEST_KEY = `${SESSION_PREFIX}manifest`;
const MANIFEST_TTL_MS = 5 * 60 * 1000;

let cachedManifest: HealthManifest | null = null;
let cachedManifestAt = 0;
let cachedIndex: Record<string, string> | null = null;
const shardPromises = new Map<string, Promise<ShardPayload>>();
const patchPromises = new Map<string, Promise<SnowflakeProfileV1>>();
const shardEntryById = new Map<string, HealthShardEntry>();
const patchEntryByTicker = new Map<string, HealthPatchEntry>();

function getStorage(): Storage | null {
	if (typeof window === 'undefined') return null;
	try {
		return window.sessionStorage;
	} catch {
		return null;
	}
}

function readCache<T>(key: string): T | null {
	const storage = getStorage();
	if (!storage) return null;
	const raw = storage.getItem(key);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as T;
	} catch {
		storage.removeItem(key);
		return null;
	}
}

function writeCache(key: string, value: unknown): void {
	const storage = getStorage();
	if (!storage) return;
	try {
		storage.setItem(key, JSON.stringify(value));
	} catch {
		// Storage full / disabled — silently ignore so we just refetch next time.
	}
}

function resolveBaseUrl(): string {
	if (typeof window !== 'undefined') {
		const winBase = (window as unknown as { __QBITOS_TRAIN_BASE_URL__?: string })
			.__QBITOS_TRAIN_BASE_URL__;
		if (winBase) return winBase;
		const meta = document.querySelector('meta[name="qbitos:train-base"]');
		if (meta?.getAttribute('content')) return String(meta.getAttribute('content'));
	}
	return '/';
}

function resolveApiOrigin(): string | null {
	if (typeof window === 'undefined') return null;
	const winOrigin = (window as unknown as { __QBITOS_API_ORIGIN__?: string }).__QBITOS_API_ORIGIN__;
	return winOrigin ? winOrigin.replace(/\/$/, '') : null;
}

function manifestUrl(opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin) return `${apiOrigin}/v1/coverage/manifest`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/health/manifest.json`;
}

function shardUrl(entry: HealthShardEntry, opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin) return `${apiOrigin}/v1/coverage/shard?id=${encodeURIComponent(entry.id)}`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/health/${entry.url}`;
}

function patchUrl(entry: HealthPatchEntry, opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin)
		return `${apiOrigin}/v1/coverage/listing?ticker=${encodeURIComponent(entry.ticker)}`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/health/${entry.url}`;
}

function indexUrl(manifest: HealthManifest, opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin) return `${apiOrigin}/v1/coverage/index`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/health/${manifest.indexUrl}`;
}

async function fetchJson<T>(url: string): Promise<T> {
	const response = await fetch(url, { headers: { Accept: 'application/json' } });
	if (!response.ok) {
		throw new Error(`Request failed (${response.status}) for ${url}`);
	}
	return (await response.json()) as T;
}

export async function loadHealthManifest(opts: LoaderOptions = {}): Promise<HealthManifest> {
	const fresh = Date.now() - cachedManifestAt < MANIFEST_TTL_MS;
	if (cachedManifest && fresh) return cachedManifest;

	const cached = readCache<{ at: number; manifest: HealthManifest }>(MANIFEST_KEY);
	if (cached && Date.now() - cached.at < MANIFEST_TTL_MS) {
		cachedManifest = cached.manifest;
		cachedManifestAt = cached.at;
		indexManifest(cached.manifest);
		return cached.manifest;
	}

	const manifest = await fetchJson<HealthManifest>(manifestUrl(opts));
	cachedManifest = manifest;
	cachedManifestAt = Date.now();
	writeCache(MANIFEST_KEY, { at: cachedManifestAt, manifest });
	indexManifest(manifest);
	return manifest;
}

function indexManifest(manifest: HealthManifest): void {
	shardEntryById.clear();
	for (const entry of manifest.shards) shardEntryById.set(entry.id, entry);
	patchEntryByTicker.clear();
	for (const entry of manifest.patches) patchEntryByTicker.set(entry.ticker, entry);
}

async function loadTickerIndex(
	manifest: HealthManifest,
	opts: LoaderOptions,
): Promise<Record<string, string>> {
	if (cachedIndex) return cachedIndex;
	const key = `${SESSION_PREFIX}index:${manifest.indexEtag}`;
	const cached = readCache<Record<string, string>>(key);
	if (cached) {
		cachedIndex = cached;
		return cached;
	}
	const index = await fetchJson<Record<string, string>>(indexUrl(manifest, opts));
	writeCache(key, index);
	cachedIndex = index;
	return index;
}

async function loadShard(entry: HealthShardEntry, opts: LoaderOptions): Promise<ShardPayload> {
	const cacheKey = `${SESSION_PREFIX}shard:${entry.id}:${entry.etag}`;
	const cached = readCache<ShardPayload>(cacheKey);
	if (cached) return cached;

	let pending = shardPromises.get(entry.id);
	if (!pending) {
		pending = (async () => {
			const payload = await fetchJson<ShardPayload>(shardUrl(entry, opts));
			writeCache(cacheKey, payload);
			return payload;
		})();
		shardPromises.set(entry.id, pending);
	}
	return pending;
}

async function loadPatch(
	entry: HealthPatchEntry,
	opts: LoaderOptions,
): Promise<SnowflakeProfileV1> {
	const cacheKey = `${SESSION_PREFIX}patch:${entry.ticker}:${entry.etag}`;
	const cached = readCache<SnowflakeProfileV1>(cacheKey);
	if (cached) return cached;

	let pending = patchPromises.get(entry.ticker);
	if (!pending) {
		pending = (async () => {
			const payload = await fetchJson<SnowflakeProfileV1>(patchUrl(entry, opts));
			writeCache(cacheKey, payload);
			return payload;
		})();
		patchPromises.set(entry.ticker, pending);
	}
	return pending;
}

function mergeProfiles(
	base: SnowflakeProfileV1,
	overlay: SnowflakeProfileV1 | null,
): SnowflakeProfileV1 {
	if (!overlay) return base;
	const checksByAxis = new Map<string, SnowflakeAxis>();
	for (const axis of overlay.axes) checksByAxis.set(axis.name, axis);

	const axes = base.axes.map((axis) => checksByAxis.get(axis.name) ?? axis);

	return {
		...base,
		...overlay,
		axes,
		sourceNotes: overlay.sourceNotes?.length ? overlay.sourceNotes : base.sourceNotes,
	};
}

export async function getCoverageForTicker(
	ticker: string,
	opts: LoaderOptions = {},
): Promise<SnowflakeProfileV1 | null> {
	const manifest = await loadHealthManifest(opts);
	const index = await loadTickerIndex(manifest, opts);
	const shardId = index[ticker];
	if (!shardId) return null;
	const shardEntry = shardEntryById.get(shardId);
	if (!shardEntry) return null;
	const shard = await loadShard(shardEntry, opts);
	const base = shard.profiles[ticker] ?? null;
	if (!base) return null;
	const patchEntry = patchEntryByTicker.get(ticker);
	if (!patchEntry) return base;
	try {
		const patch = await loadPatch(patchEntry, opts);
		return mergeProfiles(base, patch);
	} catch {
		// If a patch fails to load, fall back to the shard skeleton; never break the page.
		return base;
	}
}

export async function prefetchShardForTicker(
	ticker: string,
	opts: LoaderOptions = {},
): Promise<void> {
	const manifest = await loadHealthManifest(opts);
	const index = await loadTickerIndex(manifest, opts);
	const shardId = index[ticker];
	if (!shardId) return;
	const shardEntry = shardEntryById.get(shardId);
	if (!shardEntry) return;
	await loadShard(shardEntry, opts);
}

export function summarizeProfile(profile: SnowflakeProfileV1): SnowflakeSummary {
	let totalChecks = 0;
	let passedChecks = 0;
	let naChecks = 0;
	const axes = profile.axes.map((axis) => {
		const passed = axis.checks.filter((check) => check.state === 'pass').length;
		const na = axis.checks.filter((check) => check.state === 'na').length;
		totalChecks += axis.checks.length;
		passedChecks += passed;
		naChecks += na;
		return { name: axis.name, passed, total: axis.checks.length, na };
	});
	return {
		ticker: profile.ticker,
		displayName: profile.displayName ?? profile.ticker,
		asOfISO: profile.asOfISO,
		totalChecks,
		passedChecks,
		naChecks,
		failedChecks: totalChecks - passedChecks - naChecks,
		axes,
	};
}

export async function getCoverageSummaryForTicker(
	ticker: string,
	opts: LoaderOptions = {},
): Promise<SnowflakeSummary | null> {
	const profile = await getCoverageForTicker(ticker, opts);
	return profile ? summarizeProfile(profile) : null;
}
