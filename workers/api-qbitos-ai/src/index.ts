/**
 * api.qbitos.ai — health, cached catalog, Train Pages proxy + sharded coverage versioning.
 *
 * Coverage versioning endpoints (small shim/blob delivery so clients don't refetch
 * the 20MB catalog for minor edits):
 *   GET  /v1/coverage/manifest                     -> the small manifest.json
 *   GET  /v1/coverage/index                        -> ticker -> shardId map (single download)
 *   GET  /v1/coverage/shard?id=NNNN                -> one shard JSON (~600KB, etag-cached)
 *   GET  /v1/coverage/listing?ticker=AAPL          -> single profile (shard entry + patch overlay)
 *   GET  /v1/coverage/diff?since=<manifestEtag>    -> what shards/patches changed since `since`
 *
 * History (5y daily OHLCV) endpoints — same shim/blob model so clients refresh one
 * ticker's series file at a time:
 *   GET  /v1/history/manifest                      -> ticker index with sha-256 etags
 *   GET  /v1/history/listing?ticker=AAPL           -> per-ticker OHLCV (etag-cached, 304-aware)
 *   GET  /v1/history/diff?since=<seriesEtag>       -> tickers whose series file changed
 *
 * Deploy: cd workers/api-qbitos-ai && npm i && npx wrangler deploy
 */

export interface Env {
	TRAIN_ORIGIN: string;
	CATALOG_PATH: string;
	HEALTH_PATH?: string;
	HISTORY_PATH?: string;
	ALLOWED_ORIGINS?: string;
}

const defaultCors = 'GET, HEAD, OPTIONS';

type ManifestShard = {
	id: string;
	url: string;
	etag: string;
	bytes: number;
	count: number;
	first: string;
	last: string;
};

type ManifestPatch = {
	ticker: string;
	url: string;
	etag: string;
	bytes: number;
	asOfISO: string;
};

type CoverageManifest = {
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
	shards: ManifestShard[];
	patches: ManifestPatch[];
};

type ShardPayload = {
	schemaVersion: 1;
	shardId: string;
	tickers: string[];
	profiles: Record<string, unknown>;
};

type HistoryManifestEntry = {
	ticker: string;
	exchange: string;
	url: string;
	etag: string;
	bytes: number;
	rows: number;
	rangeStart: number;
	rangeEnd: number;
	asOfISO: string;
	source: string;
};

type HistoryManifest = {
	schemaVersion: 1;
	generatedAt: string;
	lookbackYears: number;
	lookbackMode?: 'fixed' | 'max';
	tickerCount: number;
	totalBytes: number;
	earliest: number;
	latest: number;
	entries: HistoryManifestEntry[];
};

function corsHeaders(env: Env, req: Request): HeadersInit {
	const origin = req.headers.get('Origin') ?? '';
	const allowed = (env.ALLOWED_ORIGINS ?? '')
		.split(',')
		.map((s) => s.trim())
		.filter(Boolean);
	const allow =
		allowed.length === 0 ? '*' : allowed.includes(origin) ? origin : allowed[0] ?? '*';
	return {
		'Access-Control-Allow-Origin': allow,
		'Access-Control-Allow-Methods': defaultCors,
		'Access-Control-Allow-Headers': 'Content-Type, Authorization, If-None-Match',
		'Access-Control-Max-Age': '86400',
		Vary: 'Origin, If-None-Match',
	};
}

function withCors(env: Env, req: Request, res: Response): Response {
	const h = new Headers(res.headers);
	for (const [k, v] of Object.entries(corsHeaders(env, req))) h.set(k, v);
	return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
	const body = JSON.stringify(payload);
	const headers = new Headers(init.headers);
	headers.set('content-type', 'application/json; charset=utf-8');
	return new Response(body, { ...init, headers });
}

function healthBaseUrl(env: Env): string {
	const origin = env.TRAIN_ORIGIN.replace(/\/$/, '');
	const path = (env.HEALTH_PATH ?? '/data/health').replace(/\/$/, '');
	return `${origin}${path}`;
}

function historyBaseUrl(env: Env): string {
	const origin = env.TRAIN_ORIGIN.replace(/\/$/, '');
	const path = (env.HISTORY_PATH ?? '/data/history').replace(/\/$/, '');
	return `${origin}${path}`;
}

async function fetchUpstreamJson<T>(url: string, cacheTtl: number): Promise<{ json: T; etag: string | null }>
{
	const upstream = await fetch(url, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl, cacheEverything: true },
	});
	if (!upstream.ok) {
		throw new Error(`upstream ${upstream.status}: ${url}`);
	}
	const text = await upstream.text();
	const json = JSON.parse(text) as T;
	return { json, etag: upstream.headers.get('etag') };
}

async function loadManifest(env: Env): Promise<CoverageManifest> {
	const { json } = await fetchUpstreamJson<CoverageManifest>(
		`${healthBaseUrl(env)}/manifest.json`,
		60,
	);
	return json;
}

function notFound(env: Env, req: Request, message: string): Response {
	return withCors(env, req, jsonResponse({ error: 'not_found', message }, { status: 404 }));
}

function badRequest(env: Env, req: Request, message: string): Response {
	return withCors(env, req, jsonResponse({ error: 'bad_request', message }, { status: 400 }));
}

async function handleCoverageManifest(env: Env, req: Request): Promise<Response> {
	const url = `${healthBaseUrl(env)}/manifest.json`;
	const upstream = await fetch(url, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl: 60, cacheEverything: true },
	});
	const out = new Response(upstream.body, {
		status: upstream.status,
		headers: {
			'content-type': 'application/json; charset=utf-8',
			'cache-control': 'public, max-age=30, s-maxage=120',
		},
	});
	return withCors(env, req, out);
}

async function handleCoverageIndex(env: Env, req: Request): Promise<Response> {
	const manifest = await loadManifest(env);
	const url = `${healthBaseUrl(env)}/${manifest.indexUrl}`;
	const upstream = await fetch(url, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl: 600, cacheEverything: true },
	});
	const out = new Response(upstream.body, {
		status: upstream.status,
		headers: {
			'content-type': 'application/json; charset=utf-8',
			etag: manifest.indexEtag,
			'cache-control': 'public, max-age=300, s-maxage=86400, immutable',
		},
	});
	return withCors(env, req, out);
}

async function handleCoverageShard(env: Env, req: Request, url: URL): Promise<Response> {
	const id = url.searchParams.get('id');
	if (!id) return badRequest(env, req, "missing required query parameter 'id'");

	const manifest = await loadManifest(env);
	const entry = manifest.shards.find((shard) => shard.id === id);
	if (!entry) return notFound(env, req, `unknown shard id: ${id}`);

	const ifNoneMatch = req.headers.get('If-None-Match');
	if (ifNoneMatch && ifNoneMatch === entry.etag) {
		return withCors(env, req, new Response(null, { status: 304, headers: { etag: entry.etag } }));
	}

	const upstream = await fetch(`${healthBaseUrl(env)}/${entry.url}`, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl: 86400, cacheEverything: true },
	});
	const out = new Response(upstream.body, {
		status: upstream.status,
		headers: {
			'content-type': 'application/json; charset=utf-8',
			etag: entry.etag,
			'x-shard-id': entry.id,
			'x-shard-count': String(entry.count),
			'cache-control': 'public, max-age=300, s-maxage=86400, immutable',
		},
	});
	return withCors(env, req, out);
}

async function handleCoverageListing(env: Env, req: Request, url: URL): Promise<Response> {
	const ticker = url.searchParams.get('ticker');
	if (!ticker) return badRequest(env, req, "missing required query parameter 'ticker'");

	const manifest = await loadManifest(env);
	const patchEntry = manifest.patches.find((entry) => entry.ticker === ticker);

	if (patchEntry) {
		const upstream = await fetch(`${healthBaseUrl(env)}/${patchEntry.url}`, {
			headers: { Accept: 'application/json' },
			cf: { cacheTtl: 300, cacheEverything: true },
		});
		const out = new Response(upstream.body, {
			status: upstream.status,
			headers: {
				'content-type': 'application/json; charset=utf-8',
				etag: patchEntry.etag,
				'x-source': 'patch',
				'cache-control': 'public, max-age=60, s-maxage=600, must-revalidate',
			},
		});
		return withCors(env, req, out);
	}

	const indexResp = await fetchUpstreamJson<Record<string, string>>(
		`${healthBaseUrl(env)}/${manifest.indexUrl}`,
		3600,
	);
	const shardId = indexResp.json[ticker];
	if (!shardId) return notFound(env, req, `ticker not in coverage index: ${ticker}`);
	const shardEntry = manifest.shards.find((shard) => shard.id === shardId);
	if (!shardEntry) return notFound(env, req, `shard not in manifest: ${shardId}`);

	const shardJson = await fetchUpstreamJson<ShardPayload>(
		`${healthBaseUrl(env)}/${shardEntry.url}`,
		86400,
	);
	const profile = shardJson.json.profiles[ticker];
	if (!profile) return notFound(env, req, `ticker not in shard ${shardId}: ${ticker}`);

	return withCors(
		env,
		req,
		jsonResponse(profile, {
			headers: {
				etag: `${shardEntry.etag}#${ticker}`,
				'x-source': 'shard',
				'x-shard-id': shardId,
				'cache-control': 'public, max-age=60, s-maxage=600',
			},
		}),
	);
}

async function loadHistoryManifest(env: Env): Promise<HistoryManifest> {
	const { json } = await fetchUpstreamJson<HistoryManifest>(
		`${historyBaseUrl(env)}/manifest.json`,
		60,
	);
	return json;
}

async function handleHistoryManifest(env: Env, req: Request): Promise<Response> {
	const url = `${historyBaseUrl(env)}/manifest.json`;
	const upstream = await fetch(url, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl: 60, cacheEverything: true },
	});
	const out = new Response(upstream.body, {
		status: upstream.status,
		headers: {
			'content-type': 'application/json; charset=utf-8',
			'cache-control': 'public, max-age=30, s-maxage=120',
		},
	});
	return withCors(env, req, out);
}

async function handleHistoryListing(env: Env, req: Request, url: URL): Promise<Response> {
	const ticker = url.searchParams.get('ticker');
	if (!ticker) return badRequest(env, req, "missing required query parameter 'ticker'");

	const manifest = await loadHistoryManifest(env);
	const entry = manifest.entries.find((e) => e.ticker === ticker);
	if (!entry) return notFound(env, req, `ticker not in history manifest: ${ticker}`);

	const ifNoneMatch = req.headers.get('If-None-Match');
	if (ifNoneMatch && ifNoneMatch === entry.etag) {
		return withCors(env, req, new Response(null, { status: 304, headers: { etag: entry.etag } }));
	}

	const upstream = await fetch(`${historyBaseUrl(env)}/${entry.url}`, {
		headers: { Accept: 'application/json' },
		cf: { cacheTtl: 86400, cacheEverything: true },
	});
	const out = new Response(upstream.body, {
		status: upstream.status,
		headers: {
			'content-type': 'application/json; charset=utf-8',
			etag: entry.etag,
			'x-history-rows': String(entry.rows),
			'x-history-source': entry.source,
			'x-history-range': `${entry.rangeStart}..${entry.rangeEnd}`,
			'cache-control': 'public, max-age=300, s-maxage=86400, immutable',
		},
	});
	return withCors(env, req, out);
}

async function handleHistoryDiff(env: Env, req: Request, url: URL): Promise<Response> {
	const since = url.searchParams.get('since') ?? '';
	const manifest = await loadHistoryManifest(env);
	const changed = manifest.entries
		.filter((entry) => entry.etag !== since)
		.map((entry) => ({
			ticker: entry.ticker,
			etag: entry.etag,
			bytes: entry.bytes,
			rows: entry.rows,
			rangeStart: entry.rangeStart,
			rangeEnd: entry.rangeEnd,
			asOfISO: entry.asOfISO,
		}));
	return withCors(
		env,
		req,
		jsonResponse({
			schemaVersion: manifest.schemaVersion,
			generatedAt: manifest.generatedAt,
			tickerCount: manifest.tickerCount,
			since,
			changed,
		}),
	);
}

async function handleCoverageDiff(env: Env, req: Request, url: URL): Promise<Response> {
	const since = url.searchParams.get('since') ?? '';
	const manifest = await loadManifest(env);

	const changedShards = manifest.shards
		.filter((entry) => entry.etag !== since)
		.map((entry) => ({ id: entry.id, etag: entry.etag, bytes: entry.bytes, count: entry.count }));
	const changedPatches = manifest.patches
		.filter((entry) => entry.etag !== since)
		.map((entry) => ({ ticker: entry.ticker, etag: entry.etag, bytes: entry.bytes }));

	return withCors(
		env,
		req,
		jsonResponse({
			schemaVersion: manifest.schemaVersion,
			generatedAt: manifest.generatedAt,
			indexEtag: manifest.indexEtag,
			since,
			changed: { shards: changedShards, patches: changedPatches },
		}),
	);
}

export default {
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);
		const origin = env.TRAIN_ORIGIN.replace(/\/$/, '');

		if (request.method === 'OPTIONS') {
			return new Response(null, { status: 204, headers: corsHeaders(env, request) });
		}

		try {
			if (url.pathname === '/health' || url.pathname === '/v1/health') {
				let upstreamOk = false;
				try {
					const ping = await fetch(`${origin}/`, { method: 'HEAD', cf: { cacheTtl: 0 } });
					upstreamOk = ping.ok;
				} catch {
					upstreamOk = false;
				}
				return withCors(
					env,
					request,
					jsonResponse({
						ok: true,
						service: 'api.qbitos.ai',
						ts: Date.now(),
						trainOrigin: origin,
						trainReachable: upstreamOk,
					}),
				);
			}

			if (url.pathname === '/v1/catalog.json' || url.pathname === '/v1/catalog') {
				const catalogUrl = `${origin}${env.CATALOG_PATH ?? '/data/catalog.json'}`;
				const res = await fetch(catalogUrl, {
					headers: { Accept: 'application/json' },
					cf: { cacheTtl: 300, cacheEverything: true },
				});
				const out = new Response(res.body, {
					status: res.status,
					headers: {
						'content-type': res.headers.get('content-type') ?? 'application/json',
						'cache-control': 'public, max-age=60',
					},
				});
				return withCors(env, request, out);
			}

			if (url.pathname === '/v1/coverage/manifest') {
				return handleCoverageManifest(env, request);
			}
			if (url.pathname === '/v1/coverage/index') {
				return handleCoverageIndex(env, request);
			}
			if (url.pathname === '/v1/coverage/shard') {
				return handleCoverageShard(env, request, url);
			}
			if (url.pathname === '/v1/coverage/listing') {
				return handleCoverageListing(env, request, url);
			}
			if (url.pathname === '/v1/coverage/diff') {
				return handleCoverageDiff(env, request, url);
			}

			if (url.pathname === '/v1/history/manifest') {
				return handleHistoryManifest(env, request);
			}
			if (url.pathname === '/v1/history/listing') {
				return handleHistoryListing(env, request, url);
			}
			if (url.pathname === '/v1/history/diff') {
				return handleHistoryDiff(env, request, url);
			}

			if (url.pathname.startsWith('/v1/train')) {
				const rest = url.pathname.slice('/v1/train'.length) || '/';
				const upstream = `${origin}${rest}${url.search}`;
				const res = await fetch(upstream, {
					method: request.method,
					headers: request.headers,
					body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
					cf: { cacheTtl: 120, cacheEverything: true },
				});
				return withCors(env, request, res);
			}

			return notFound(env, request, url.pathname);
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error);
			return withCors(
				env,
				request,
				jsonResponse({ error: 'upstream_failure', message }, { status: 502 }),
			);
		}
	},
};
