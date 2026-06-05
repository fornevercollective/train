#!/usr/bin/env node
/**
 * Local builds run prepare:data (Python). Cloudflare Workers Builds sets WORKERS_CI=1
 * and uses committed public/data — skip Python there.
 */
import { spawnSync } from "node:child_process";

const skipPrepare =
  process.env.WORKERS_CI === "1" ||
  process.env.SKIP_PREPARE_DATA === "1" ||
  process.env.CF_PAGES === "1";

function run(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32" });
  if (r.error) {
    console.error(r.error);
    process.exit(1);
  }
  process.exit(r.status ?? 1);
}

if (!skipPrepare) {
  const prep = spawnSync("npm", ["run", "prepare:data"], {
    stdio: "inherit",
    shell: process.platform === "win32"
  });
  if (prep.status !== 0) process.exit(prep.status ?? 1);
} else {
  console.log("[build] Skipping prepare:data (WORKERS_CI / SKIP_PREPARE_DATA / CF_PAGES)");
}

run("npx", ["astro", "build"]);
