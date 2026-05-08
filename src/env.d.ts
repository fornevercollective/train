/// <reference types="astro/client" />

interface ImportMetaEnv {
	/** Base URL of the Next.js Game console (no trailing slash), e.g. https://your-host/game or http://localhost:3000 */
	readonly PUBLIC_GAME_CONSOLE_URL?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}

import type {
	getCoverageForTicker,
	getCoverageSummaryForTicker,
	loadHealthManifest,
	prefetchShardForTicker,
	summarizeProfile,
} from './lib/health-shard-loader';

declare global {
	interface Window {
		/** Bridge published by `pages/{directory,listing}/index.astro` so inline scripts can
		 * reach the bundled snowflake shard loader without using dynamic import. */
		__qbitosHealthLoader__?: {
			getCoverageForTicker: typeof getCoverageForTicker;
			getCoverageSummaryForTicker: typeof getCoverageSummaryForTicker;
			loadHealthManifest: typeof loadHealthManifest;
			prefetchShardForTicker: typeof prefetchShardForTicker;
			summarizeProfile: typeof summarizeProfile;
		};
		/** Optional override: when set, the loader fetches coverage from `api.qbitos.ai`
		 * (the versioning API) instead of the static GitHub Pages assets. */
		__QBITOS_API_ORIGIN__?: string;
		/** Optional override for the Train static base URL when running behind a reverse
		 * proxy or in an embed. */
		__QBITOS_TRAIN_BASE_URL__?: string;
	}
}

export {};
