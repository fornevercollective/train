/**
 * Browser-side loader for the per-ticker history series.
 *
 * Architecture mirrors `health-shard-loader.ts`:
 *  - The small `manifest.json` lists every per-ticker file with a sha-256 etag.
 *  - Series JSONs are loaded on demand and cached in sessionStorage keyed by etag.
 *    When a single ticker's data is refreshed, its etag flips and only that one
 *    file is re-downloaded.
 *
 * Endpoints:
 *  - Static (GitHub Pages):  `${BASE_URL}data/history/...`
 *  - Versioning API:         `${API_ORIGIN}/v1/history/...` (set window.__QBITOS_API_ORIGIN__)
 *
 * Public surface:
 *  - `loadHistoryManifest()`             -> HistoryManifestV1
 *  - `getHistoryForTicker(ticker)`       -> HistorySeriesV1 | null
 *  - `summarizeHistoryWindow(series)`    -> PriceWindowSummary
 */

import type {
	HistoryManifestEntry,
	HistoryManifestV1,
	HistorySeriesV1,
	PriceWindowSummary,
} from './history-types';

type LoaderOptions = {
	baseUrl?: string;
	apiOrigin?: string | null;
};

const SESSION_PREFIX = 'qbitos:history:';
const MANIFEST_KEY = `${SESSION_PREFIX}manifest`;
const MANIFEST_TTL_MS = 5 * 60 * 1000;

let cachedManifest: HistoryManifestV1 | null = null;
let cachedManifestAt = 0;
const seriesPromises = new Map<string, Promise<HistorySeriesV1>>();
const entryByTicker = new Map<string, HistoryManifestEntry>();

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
		// Quota exceeded — silently ignore so we just refetch next time.
	}
}

function resolveBaseUrl(): string {
	if (typeof window !== 'undefined') {
		const winBase = window.__QBITOS_TRAIN_BASE_URL__;
		if (winBase) return winBase;
		const meta = document.querySelector('meta[name="qbitos:train-base"]');
		if (meta?.getAttribute('content')) return String(meta.getAttribute('content'));
	}
	return '/';
}

function resolveApiOrigin(): string | null {
	if (typeof window === 'undefined') return null;
	const winOrigin = window.__QBITOS_API_ORIGIN__;
	return winOrigin ? winOrigin.replace(/\/$/, '') : null;
}

function manifestUrl(opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin) return `${apiOrigin}/v1/history/manifest`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/history/manifest.json`;
}

function seriesUrl(entry: HistoryManifestEntry, opts: LoaderOptions): string {
	const apiOrigin = opts.apiOrigin ?? resolveApiOrigin();
	if (apiOrigin)
		return `${apiOrigin}/v1/history/listing?ticker=${encodeURIComponent(entry.ticker)}`;
	const base = opts.baseUrl ?? resolveBaseUrl();
	return `${base}data/history/${entry.url}`;
}

async function fetchJson<T>(url: string): Promise<T> {
	const response = await fetch(url, { headers: { Accept: 'application/json' } });
	if (!response.ok) {
		throw new Error(`Request failed (${response.status}) for ${url}`);
	}
	return (await response.json()) as T;
}

function indexManifest(manifest: HistoryManifestV1): void {
	entryByTicker.clear();
	for (const entry of manifest.entries) entryByTicker.set(entry.ticker, entry);
}

export async function loadHistoryManifest(opts: LoaderOptions = {}): Promise<HistoryManifestV1> {
	const fresh = Date.now() - cachedManifestAt < MANIFEST_TTL_MS;
	if (cachedManifest && fresh) return cachedManifest;

	const cached = readCache<{ at: number; manifest: HistoryManifestV1 }>(MANIFEST_KEY);
	if (cached && Date.now() - cached.at < MANIFEST_TTL_MS) {
		cachedManifest = cached.manifest;
		cachedManifestAt = cached.at;
		indexManifest(cached.manifest);
		return cached.manifest;
	}

	const manifest = await fetchJson<HistoryManifestV1>(manifestUrl(opts));
	cachedManifest = manifest;
	cachedManifestAt = Date.now();
	writeCache(MANIFEST_KEY, { at: cachedManifestAt, manifest });
	indexManifest(manifest);
	return manifest;
}

async function loadSeries(
	entry: HistoryManifestEntry,
	opts: LoaderOptions,
): Promise<HistorySeriesV1> {
	const cacheKey = `${SESSION_PREFIX}series:${entry.ticker}:${entry.etag}`;
	const cached = readCache<HistorySeriesV1>(cacheKey);
	if (cached) return cached;

	let pending = seriesPromises.get(entry.ticker);
	if (!pending) {
		pending = (async () => {
			const payload = await fetchJson<HistorySeriesV1>(seriesUrl(entry, opts));
			writeCache(cacheKey, payload);
			return payload;
		})();
		seriesPromises.set(entry.ticker, pending);
	}
	return pending;
}

export async function getHistoryForTicker(
	ticker: string,
	opts: LoaderOptions = {},
): Promise<HistorySeriesV1 | null> {
	await loadHistoryManifest(opts);
	const entry = entryByTicker.get(ticker);
	if (!entry) return null;
	try {
		return await loadSeries(entry, opts);
	} catch {
		return null;
	}
}

export async function hasHistoryForTicker(
	ticker: string,
	opts: LoaderOptions = {},
): Promise<boolean> {
	await loadHistoryManifest(opts);
	return entryByTicker.has(ticker);
}

export function summarizeHistoryWindow(series: HistorySeriesV1): PriceWindowSummary {
	const closes = series.c;
	const highs = series.h;
	const lows = series.l;
	const volumes = series.v;
	const rows = series.rows;

	if (rows === 0) {
		return {
			ticker: series.ticker,
			rangeStart: series.rangeStart,
			rangeEnd: series.rangeEnd,
			rows: 0,
			first: 0,
			last: 0,
			high: 0,
			low: 0,
			totalReturnPct: 0,
			annualizedReturnPct: 0,
			maxDrawdownPct: 0,
			avgVolume: 0,
		};
	}

	const first = closes[0];
	const last = closes[rows - 1];
	let high = highs[0];
	let low = lows[0];
	let peak = closes[0];
	let maxDrawdown = 0;
	let volumeSum = 0;

	for (let i = 0; i < rows; i += 1) {
		if (highs[i] > high) high = highs[i];
		if (lows[i] < low) low = lows[i];
		if (closes[i] > peak) peak = closes[i];
		const drawdown = peak === 0 ? 0 : (closes[i] - peak) / peak;
		if (drawdown < maxDrawdown) maxDrawdown = drawdown;
		volumeSum += volumes[i] || 0;
	}

	const totalReturn = first === 0 ? 0 : last / first - 1;
	const years = Math.max(rows / 252, 1 / 252);
	const annualizedReturn = first === 0 ? 0 : Math.pow(last / first, 1 / years) - 1;

	return {
		ticker: series.ticker,
		rangeStart: series.rangeStart,
		rangeEnd: series.rangeEnd,
		rows,
		first,
		last,
		high,
		low,
		totalReturnPct: totalReturn * 100,
		annualizedReturnPct: annualizedReturn * 100,
		maxDrawdownPct: maxDrawdown * 100,
		avgVolume: volumeSum / rows,
	};
}

export function dayKeyToISO(dayKey: number): string {
	const s = String(dayKey).padStart(8, '0');
	return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}
