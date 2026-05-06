/// <reference types="astro/client" />

interface ImportMetaEnv {
	/** Base URL of the Next.js Game console (no trailing slash), e.g. https://your-host/game or http://localhost:3000 */
	readonly PUBLIC_GAME_CONSOLE_URL?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
