// config.mjs — shared config loader for ui-spec compiler tools.
// Reads spec.config.yaml from spec root. Spec root is found via:
//   1. --root <path> CLI arg
//   2. Walking up from CWD looking for spec.config.yaml

import { readFileSync, existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import yaml from "js-yaml";

/** Find spec root by walking up from startDir looking for spec.config.yaml. */
function findSpecRoot(startDir) {
  let dir = resolve(startDir);
  for (let i = 0; i < 10; i++) {
    if (existsSync(join(dir, "spec.config.yaml"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break; // filesystem root
    dir = parent;
  }
  return null;
}

/** Parse --root <path> from process.argv. Returns null if not present. */
function parseRootArg() {
  const idx = process.argv.indexOf("--root");
  if (idx !== -1 && process.argv[idx + 1]) {
    return resolve(process.argv[idx + 1]);
  }
  return null;
}

/** Load and validate spec.config.yaml. Exits with helpful message on failure. */
function loadConfig() {
  const specRoot = parseRootArg() ?? findSpecRoot(process.cwd());

  if (!specRoot) {
    console.error(
      "ERROR: Cannot find spec.config.yaml.\n" +
      "  Run from a directory inside your spec, or pass --root <spec-root>.\n" +
      "  Example: node validate.mjs --root ./docs/ui-spec"
    );
    process.exit(1);
  }

  const configPath = join(specRoot, "spec.config.yaml");
  let config;
  try {
    config = yaml.load(readFileSync(configPath, "utf8")) || {};
  } catch (e) {
    console.error(`ERROR: Cannot read spec.config.yaml at ${configPath}\n  ${e.message}`);
    process.exit(1);
  }

  // Required fields with defaults
  const contractTag = config.contract_tag ?? "ui-spec-contract";
  const surfaceDirs = config.surface_dirs ?? ["screens", "panels", "modals", "overlays", "components"];
  const crossCutting = config.cross_cutting ?? [];
  const schemaPath = join(specRoot, config.schema_path ?? "schema/surface-contract.schema.json");

  return { specRoot, config, contractTag, surfaceDirs, crossCutting, schemaPath };
}

export const { specRoot, config, contractTag, surfaceDirs, crossCutting, schemaPath } = loadConfig();
export const SPEC_ROOT = specRoot;
