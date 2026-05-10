/**
 * Daily OHLCV history schema, shared by Train UI and api.qbitos.ai consumers.
 *
 * Stored as parallel arrays for gzip efficiency and zero-copy charting:
 * the i-th element of `d`, `o`, `h`, `l`, `c`, `v` describes the same trading day.
 * Dates are encoded as compact YYYYMMDD integers (e.g. 20260507) so the wire format
 * stays numeric and predictable — no timezone strings, no 10-byte string per row.
 */

export type HistoryInterval = 'daily';

export type HistorySource = 'stooq' | 'yahoo' | 'manual' | 'unknown';

export type HistoryLookbackMode = 'fixed' | 'max';

export type HistorySeriesV1 = {
	schemaVersion: 1;
	ticker: string;
	exchange?: string;
	displayName?: string;
	source: HistorySource;
	sourceSymbol?: string;
	interval: HistoryInterval;
	asOfISO: string;
	/**
	 * Hint about how far back the series intends to go. `0` together with
	 * `lookbackMode === 'max'` means "the full history available from the source".
	 * The actual span is always `rangeStart..rangeEnd`.
	 */
	lookbackYears: number;
	lookbackMode?: HistoryLookbackMode;
	rows: number;
	rangeStart: number;
	rangeEnd: number;
	d: number[];
	o: number[];
	h: number[];
	l: number[];
	c: number[];
	v: number[];
};

export type HistoryManifestEntry = {
	ticker: string;
	exchange: string;
	url: string;
	etag: string;
	bytes: number;
	rows: number;
	rangeStart: number;
	rangeEnd: number;
	asOfISO: string;
	source: HistorySource;
};

export type HistoryManifestV1 = {
	schemaVersion: 1;
	generatedAt: string;
	lookbackYears: number;
	lookbackMode?: HistoryLookbackMode;
	tickerCount: number;
	totalBytes: number;
	earliest: number;
	latest: number;
	entries: HistoryManifestEntry[];
};

export type PriceWindowSummary = {
	ticker: string;
	rangeStart: number;
	rangeEnd: number;
	rows: number;
	first: number;
	last: number;
	high: number;
	low: number;
	totalReturnPct: number;
	annualizedReturnPct: number;
	maxDrawdownPct: number;
	avgVolume: number;
};
