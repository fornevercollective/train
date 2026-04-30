/// <reference types="node" />

// @ts-check
import { defineConfig } from 'astro/config';

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
});
