/* eslint-disable */
// Cloudflare Worker bindings for train (ASSETS only — static site).
// Refresh with: npm run generate-types
interface Env {
	ASSETS: Fetcher;
}

declare namespace Cloudflare {
	interface Env {
		ASSETS: Fetcher;
	}
}
