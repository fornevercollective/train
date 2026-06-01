/**
 * Load the full listing catalog from sharded static JSON (Cloudflare Workers safe).
 * Falls back to monolithic catalog.json when shards are unavailable.
 */

export type CatalogShardEntry = {
	id: string;
	count: number;
	bytes: number;
	etag: string;
	first: string;
	last: string;
};

export type CatalogManifestV1 = {
	schemaVersion: number;
	generatedAt: string;
	recordCount: number;
	shardCount: number;
	shardSize: number;
	shards: CatalogShardEntry[];
};

function normalizeBaseUrl(baseUrl: string): string {
	return baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
}

export async function loadCatalogManifest(baseUrl: string): Promise<CatalogManifestV1> {
	const root = normalizeBaseUrl(baseUrl);
	const response = await fetch(`${root}data/catalog/manifest.json`);
	if (!response.ok) {
		throw new Error(`Failed to load catalog manifest: ${response.status}`);
	}
	return response.json();
}

export async function loadCatalog(baseUrl: string): Promise<Record<string, unknown>[]> {
	const root = normalizeBaseUrl(baseUrl);

	try {
		const manifest = await loadCatalogManifest(root);
		const shards = await Promise.all(
			manifest.shards.map(async (shard) => {
				const response = await fetch(`${root}data/catalog/shards/v1/${shard.id}.json`);
				if (!response.ok) {
					throw new Error(`Failed to load catalog shard ${shard.id}: ${response.status}`);
				}
				return response.json();
			}),
		);
		return shards.flat();
	} catch (err) {
		const response = await fetch(`${root}data/catalog.json`);
		if (!response.ok) {
			throw err instanceof Error ? err : new Error(`Failed to load catalog: ${response.status}`);
		}
		return response.json();
	}
}
