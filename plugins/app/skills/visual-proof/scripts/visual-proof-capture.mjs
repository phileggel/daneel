#!/usr/bin/env node

/**
 * Playwright capture script for the /visual-proof skill.
 *
 * Reads environment variables, opens the project's Vite preview at light+dark,
 * screenshots one element per state, records any console errors. Invoked from
 * the visual-proof skill's Step 4, from the project's checkout; not intended for
 * direct CLI use.
 *
 * Arguments (each also read from its environment variable, the argument first):
 *   --port / VP_PORT, --host / VP_HOST, --name / VP_NAME, --states / VP_STATES,
 *   --mask / VP_MASK, --out / VP_OUT_DIR.
 *
 * Env contract:
 *   VP_PORT   — Vite preview port (required)
 *   VP_HOST   — Vite preview host (required)
 *   VP_NAME   — component name for output filenames (required)
 *   VP_STATES — comma-separated state names matching `#state-{name}` ids (default: "idle")
 *   VP_MASK   — comma-separated CSS selectors to mask in screenshots (optional)
 *   VP_OUT_DIR — output directory (optional, default "screenshots", under the
 *               working directory)
 *
 * Outputs (stdout reserved for future machine-readable output; progress and
 * warnings go to stderr):
 *   {VP_OUT_DIR}/{VP_NAME}-{scheme}-{state}.png per scheme×state combination.
 *   {VP_OUT_DIR}/.console-errors.json if any console errors were observed.
 *
 * Exit codes: 0 ok, 2 usage error (missing env), 1 runtime/Playwright error.
 */

import { mkdir, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join } from "node:path";

// `--port 1420` or `--port=1420`; a skill's allowed-tools can name the script with
// its arguments, where an environment-variable prefix would not match.
// A flag it does not know is a usage error: `--state` for `--states` would capture idle
// alone and pass.
const FLAGS = new Set(["port", "host", "name", "states", "mask", "out"]);
const ARGS = {};
for (let i = 2; i < process.argv.length; i++) {
  const match = /^--([a-z]+)(?:=(.*))?$/.exec(process.argv[i]);
  if (!match || !FLAGS.has(match[1])) {
    console.error(`error: unexpected argument ${process.argv[i]}`);
    process.exit(2);
  }
  ARGS[match[1]] = match[2] ?? process.argv[++i];
  if (ARGS[match[1]] === undefined || ARGS[match[1]].startsWith("--")) {
    console.error(`error: --${match[1]} takes a value`);
    process.exit(2);
  }
}
const PORT = ARGS.port ?? process.env.VP_PORT;
const HOST = ARGS.host ?? process.env.VP_HOST;
const NAME = ARGS.name ?? process.env.VP_NAME;
const STATES = (ARGS.states ?? process.env.VP_STATES ?? "idle").split(",");
const MASK_SELECTORS = (ARGS.mask ?? process.env.VP_MASK ?? "").split(",").filter(Boolean);
const OUT_DIR = ARGS.out ?? process.env.VP_OUT_DIR ?? "screenshots";

if (!PORT || !HOST || !NAME) {
  console.error("error: --port, --host and --name (or VP_PORT, VP_HOST, VP_NAME) are required");
  process.exit(2);
}

// Playwright is the project's dependency, not the plugin's: resolve it from the
// project's checkout (the working directory), never from this script's folder.
const { chromium } = createRequire(join(process.cwd(), "package.json"))("playwright");

const consoleErrors = [];
const missing = new Set();
await mkdir(OUT_DIR, { recursive: true });
// The file exists after a run only if that run saw console errors.
await rm(`${OUT_DIR}/.console-errors.json`, { force: true });

const browser = await chromium.launch({ args: ["--no-sandbox"] });
try {
  for (const scheme of ["light", "dark"]) {
    const context = await browser.newContext({
      colorScheme: scheme,
      viewport: { width: 1600, height: 900 },
    });
    try {
      const page = await context.newPage();

      page.on("console", (msg) => {
        if (msg.type() === "error") {
          consoleErrors.push({ scheme, text: msg.text() });
        }
      });

      const url = `http://${HOST}:${PORT}/preview.html${scheme === "dark" ? "?theme=dark" : ""}`;
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(`#state-${STATES[0]}`, { timeout: 10000 });

      const masks = MASK_SELECTORS.map((sel) => page.locator(sel));

      for (const state of STATES) {
        const el = page.locator(`#state-${state}`);
        if ((await el.count()) === 0) {
          missing.add(state);
          continue;
        }
        const path = `${OUT_DIR}/${NAME}-${scheme}-${state}.png`;
        await el.screenshot({ path, mask: masks });
        console.error(`  → ${path}`);
      }
    } finally {
      await context.close();
    }
  }

  if (consoleErrors.length > 0) {
    console.error("\n⚠️  Console errors detected during capture:");
    for (const err of consoleErrors) {
      console.error(`  [${err.scheme}] ${err.text}`);
    }
    await writeFile(`${OUT_DIR}/.console-errors.json`, JSON.stringify(consoleErrors, null, 2));
  }
} finally {
  await browser.close();
}

// A state asked for and not rendered is a capture that failed, never a silent gap.
if (missing.size > 0) {
  console.error(`error: no #state-{name} element for: ${[...missing].join(", ")}`);
  process.exit(1);
}
