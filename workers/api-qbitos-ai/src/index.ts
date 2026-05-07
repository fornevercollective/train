/**
 * api.qbitos.ai — health, cached catalog, Train Pages proxy.
 * Deploy: cd workers/api-qbitos-ai && npm i && npx wrangler deploy
 */

export interface Env {
	TRAIN_ORIGIN: string;
	CATALOG_PATH: string;
	ALLOWED_ORIGINS?: string;
}

const defaultCors = 'GET, HEAD, OPTIONS';

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
		'Access-Control-Allow-Headers': 'Content-Type, Authorization',
		'Access-Control-Max-Age': '86400',
	};
}

function withCors(env: Env, req: Request, res: Response): Response {
	const h = new Headers(res.headers);
	for (const [k, v] of Object.entries(corsHeaders(env, req))) h.set(k, v);
	return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

export default {
	async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);
		const origin = env.TRAIN_ORIGIN.replace(/\/$/, '');

		if (request.method === 'OPTIONS') {
			return new Response(null, { status: 204, headers: corsHeaders(env, request) });
		}

		// Health (worker + optional upstream ping)
		if (url.pathname === '/health' || url.pathname === '/v1/health') {
			let upstreamOk = false;
			try {
				const ping = await fetch(`${origin}/`, {
					method: 'HEAD',
					cf: { cacheTtl: 0 },
				});
				upstreamOk = ping.ok;
			} catch {
				upstreamOk = false;
			}
			const body = JSON.stringify({
				ok: true,
				service: 'api.qbitos.ai',
				ts: Date.now(),
				trainOrigin: origin,
				trainReachable: upstreamOk,
			});
			return withCors(
				env,
				request,
				new Response(body, { headers: { 'content-type': 'application/json' } }),
			);
		}

		// Cached catalog (edge cache)
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

		// Proxy Train static site: /v1/train/* → TRAIN_ORIGIN/*
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

		return withCors(
			env,
			request,
			new Response(JSON.stringify({ error: 'not_found', path: url.pathname }), {
				status: 404,
				headers: { 'content-type': 'application/json' },
			}),
		);
	},
};
