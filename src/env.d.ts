/// <reference types="astro/client" />

interface ImportMetaEnv {
	/** Base URL of the Next.js Game console (no trailing slash), e.g. https://your-host/game or http://localhost:3000 */
	readonly PUBLIC_GAME_CONSOLE_URL?: string;
	/**
	 * Optional origin for a local or deployed live pipeline / broadcast workpad (no trailing slash),
	 * e.g. http://127.0.0.1:8787 — used on the Broadcast tab for deep links and optional embed hints.
	 */
	readonly PUBLIC_BROADCAST_PIPELINE_URL?: string;
	/**
	 * Optional comma-separated hostnames allowed for the Broadcast iframe (lowercase, no port in list).
	 * When set, the embed loads only if `PUBLIC_BROADCAST_PIPELINE_URL` parses to one of these hosts.
	 * When unset, any http(s) origin from `PUBLIC_BROADCAST_PIPELINE_URL` may embed (still no userinfo in URL).
	 */
	readonly PUBLIC_BROADCAST_EMBED_HOSTS?: string;
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
import type {
	getHistoryForTicker,
	hasHistoryForTicker,
	loadHistoryManifest,
	summarizeHistoryWindow,
	dayKeyToISO,
} from './lib/history-shard-loader';
import type { mountHistorySparkline } from './lib/history-sparkline';

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
		/** Bridge for the per-ticker 5y OHLCV history loader. */
		__qbitosHistoryLoader__?: {
			getHistoryForTicker: typeof getHistoryForTicker;
			hasHistoryForTicker: typeof hasHistoryForTicker;
			loadHistoryManifest: typeof loadHistoryManifest;
			summarizeHistoryWindow: typeof summarizeHistoryWindow;
			dayKeyToISO: typeof dayKeyToISO;
		};
		/** Bridge for the ECharts sparkline mounter. */
		__qbitosSparkline__?: {
			mountHistorySparkline: typeof mountHistorySparkline;
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
