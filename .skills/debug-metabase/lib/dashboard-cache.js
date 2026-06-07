'use strict';

/**
 * File-based cache for Metabase dashboard metadata.
 *
 * What's cached: dashboard structure (name, parameters, tabs, cards with SQL
 * templates and parameter_mappings). Query execution results are always fresh.
 *
 * Cache dir: <project_root>/.cache/metabase/
 * File per dashboard: dashboard-<id>.json
 * Default TTL: 24 hours (dashboard structure rarely changes)
 */

const fs   = require('fs');
const path = require('path');

const DEFAULT_TTL_MS = 24 * 60 * 60 * 1000; // 24h

class DashboardCache {
  /**
   * @param {string} cacheDir  Absolute path to cache directory
   * @param {number} ttlMs     Cache TTL in milliseconds
   */
  constructor(cacheDir, ttlMs = DEFAULT_TTL_MS) {
    this.cacheDir = cacheDir;
    this.ttlMs    = ttlMs;
    fs.mkdirSync(cacheDir, { recursive: true });
  }

  _filePath(dashboardId) {
    return path.join(this.cacheDir, `dashboard-${dashboardId}.json`);
  }

  /** Returns cached dashboard data, or null if missing / expired. */
  get(dashboardId) {
    const file = this._filePath(dashboardId);
    if (!fs.existsSync(file)) return null;

    let entry;
    try { entry = JSON.parse(fs.readFileSync(file, 'utf8')); }
    catch { return null; }

    if (Date.now() - entry.cachedAt > this.ttlMs) return null;
    return entry.dashboard;
  }

  /** Writes dashboard data to cache. */
  set(dashboardId, dashboard) {
    const entry = { cachedAt: Date.now(), ttlMs: this.ttlMs, dashboard };
    fs.writeFileSync(this._filePath(dashboardId), JSON.stringify(entry, null, 2));
  }

  /** Removes cached entry for a dashboard (use with --no-cache). */
  invalidate(dashboardId) {
    const file = this._filePath(dashboardId);
    if (fs.existsSync(file)) fs.unlinkSync(file);
  }

  /** Returns human-readable age string, or null if not cached. */
  age(dashboardId) {
    const file = this._filePath(dashboardId);
    if (!fs.existsSync(file)) return null;
    let entry;
    try { entry = JSON.parse(fs.readFileSync(file, 'utf8')); }
    catch { return null; }
    const ageMs = Date.now() - entry.cachedAt;
    if (ageMs < 60_000) return `${Math.round(ageMs / 1000)}s`;
    if (ageMs < 3_600_000) return `${Math.round(ageMs / 60_000)}m`;
    return `${Math.round(ageMs / 3_600_000)}h`;
  }
}

module.exports = DashboardCache;
