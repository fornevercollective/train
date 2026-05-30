/// <reference types="node" />

// @ts-check
import { defineConfig, sessionDrivers } from 'astro/config';

import cloudflare from '@astrojs/cloudflare';

/**
 * @param {string} base
 */
function normalizeBase(base) {
  if (!base || base === '/') {
    return '/';
  }

  return `/${base.replace(/^\/+|\/+$/g, '')}/`;
}

function inferBasePath() {
  if (process.env.PUBLIC_BASE_PATH) {
    return normalizeBase(process.env.PUBLIC_BASE_PATH);
  }

  if (process.env.GITHUB_ACTIONS === 'true') {
    const [, repositoryName] = (process.env.GITHUB_REPOSITORY || '').split('/');
    const owner = (process.env.GITHUB_REPOSITORY_OWNER || '').toLowerCase();
    const repo = (repositoryName || '').toLowerCase();

    if (repo && owner && repo === `${owner}.github.io`) {
      return '/';
    }

    if (repositoryName) {
      return normalizeBase(repositoryName);
    }
  }

  return '/';
}

// https://astro.build/config
export default defineConfig({
  base: inferBasePath(),
  integrations: [],
  output: 'static',
  trailingSlash: 'always',
  // Static catalog site — no Astro sessions; avoids auto SESSION KV on deploy.
  session: {
    driver: sessionDrivers.null()
  },
  adapter: cloudflare({
    // No Cloudflare Images binding required for this static build.
    imageService: 'passthrough'
  })
});