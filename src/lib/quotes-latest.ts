/**
 * Latest session quote snapshot (public/data/quotes/latest.json).
 */

export type QuoteSnapshot = {
	price: number;
	dayOpen: number;
	previousClose: number;
	changePct: number;
	sessionDate: string;
	shortName: string;
	ingestSource?: string;
};

export type QuotesLatestFile = {
	version: number;
	asOf: string;
	builtAt: string;
	symbolCount: number;
	symbols: Record<string, QuoteSnapshot>;
};

let cached: QuotesLatestFile | null = null;

function resolveBaseUrl(): string {
	if (typeof window !== 'undefined') {
		const winBase = (window as unknown as { __QBITOS_TRAIN_BASE_URL__?: string }).__QBITOS_TRAIN_BASE_URL__;
		if (winBase) return winBase;
		const meta = document.querySelector('meta[name="qbitos:train-base"]');
		if (meta?.getAttribute('content')) return String(meta.getAttribute('content'));
	}
	return '/';
}

export async function loadQuotesLatest(): Promise<QuotesLatestFile | null> {
	if (cached) return cached;
	try {
		const base = resolveBaseUrl();
		const response = await fetch(`${base}data/quotes/latest.json`, {
			headers: { Accept: 'application/json' },
		});
		if (!response.ok) return null;
		const parsed = (await response.json()) as QuotesLatestFile;
		if (!parsed?.symbols) return null;
		cached = parsed;
		return parsed;
	} catch {
		return null;
	}
}

export function quoteForTicker(
	quotes: QuotesLatestFile | null,
	ticker: string,
): QuoteSnapshot | null {
	if (!quotes) return null;
	const key = ticker.trim().toUpperCase();
	return quotes.symbols[key] ?? quotes.symbols[ticker] ?? null;
}
