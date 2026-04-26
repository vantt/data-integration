# Metabase & DuckDB Driver Upgrade Analysis

**Date:** 2026-04-23  
**Research Focus:** Current vs. Latest Stable Versions, Compatibility, Breaking Changes

---

## Executive Summary

Upgrade path exists from Metabase 0.58.11 → 0.60.2, but **DuckDB driver support gap at Metabase 0.60**: Latest driver (1.5.2.0) targets Metabase 0.59 only. **Critical blocker:** No confirmed Metabase 0.60 support for metabase_duckdb_driver in official releases.

---

## 1. Metabase Version Analysis

### Current Installation
- **Version:** 0.58.11
- **Release Date:** ~January 2026

### Latest Stable Releases

| Version | Release Date | Status | Key Features |
|---------|--------------|--------|--------------|
| **0.60.2** | April 22, 2026 | Latest | AI open source, official MCP server, Metabot Slack, split panels, metrics explorer |
| 0.60.1 | April 20, 2026 | Stable | Same as 0.60.2 |
| 0.59.8 | April 22, 2026 | LTS (0.59 series) | Data Studio, AI SQL gen (OSS), semantic layer |
| 0.59.6 | April 9, 2026 | Stable (0.59 series) | — |
| 0.58.13 | ~February 2026 | Minimal updates | Improved docs, multi-tenant embedded, guest embeds |

### Upgrade Path: 0.58.11 → 0.60.x

**Strategy:** Direct upgrade supported (no step-by-step requirement for recent versions)
- Metabase runs automatic schema migrations during startup
- Backup required (stored in application database)
- No major documented breaking changes found for 0.58→0.59→0.60

**General upgrade guidance:** Always back up application database before upgrade

---

## 2. metabase_duckdb_driver Compatibility

### Current Installation
- **Version:** 1.4.4.0
- **Compatible with:** Metabase 0.59, DuckDB 1.4.4
- **Status:** Already ahead of production Metabase (0.58.11)

### Latest Driver Release

| Version | Date | Metabase | DuckDB | Status |
|---------|------|----------|--------|--------|
| **1.5.2.0** | Apr 21, 2026 | 0.59 | 1.5.2 | Latest release |
| 1.5.1.0 | Apr 6, 2026 | 0.59 | 1.5.1 | — |
| 1.4.4.0 | Mar 16, 2026 | 0.59 | 1.4.4 | Current in use |
| 1.4.3.1 | Jan 9, 2026 | 0.57 | 1.4.3 | — |

### Critical Finding: Metabase 0.60 Compatibility

**⚠️ BLOCKER:** No release notes confirm metabase_duckdb_driver 1.5.2.0 works with Metabase 0.60.
- Latest driver (1.5.2.0) explicitly targets Metabase 0.59
- GitHub releases page shows no 0.60-compatible build published yet
- **Likely status:** In development or not yet released

---

## 3. Java & System Requirements

### Metabase 0.60 Requirements
- **Java:** Minimum Java 21 (JRE)
- **Previous requirement:** Java 11/17 (dropped in v0.53+)
- **Recommended:** Eclipse Temurin JRE 21 with HotSpot JVM

### metabase_duckdb_driver Requirements
- Inherits Metabase's Java requirement
- DuckDB driver (1.5.2.0) requires Java 21 for Metabase 0.59
- Expected requirement for 0.60: Java 21

### Implication
- Current environment must support Java 21 before upgrading to 0.60
- If running Java 17 or earlier, upgrade Java first

---

## 4. Known Issues & Compatibility Notes

### Metabase 0.60 Issues
- General query issues post-upgrade reported on Discourse (isolated incidents)
- No systemic breaking changes documented for core functionality

### metabase_duckdb_driver Known Issues
- Connection timeout issues previously reported (Issue #71) — monitor for 1.5.2.0

### DuckDB Driver Architecture
- Built by MotherDuck as community/OSS plugin (not officially supported by Metabase)
- Cloud deployment does NOT support custom drivers (Self-hosted only)
- Backward compatibility expected across recent minor versions

---

## 5. Upgrade Recommendation

### Path Forward

**Option A: Conservative (Recommended for production)**
1. **Stay on:** Metabase 0.59.8 + metabase_duckdb_driver 1.5.2.0
   - Both versions released April 2026 (stable, battle-tested)
   - Full compatibility confirmed
   - Still get Data Studio + AI SQL gen (OSS)
   - **Timeline:** Can upgrade immediately

2. **Future:** Monitor for metabase_duckdb_driver 1.6.0 or 1.5.3.0 with 0.60 support
   - Check GitHub releases weekly
   - Plan 0.60 upgrade after driver compatibility confirmed
   - **Estimated:** 2-4 weeks post-0.60 release for driver catch-up

**Option B: Aggressive (If driver 0.60 support confirmed)**
1. Upgrade Java → 21 first
2. Upgrade Metabase 0.58.11 → 0.60.2 (direct)
3. Upgrade metabase_duckdb_driver 1.4.4.0 → 1.5.2.0 (once 0.60 compatibility verified)
4. Validate in staging environment first

### Pre-Upgrade Checklist
- [ ] Backup Metabase application database
- [ ] Verify Java 21 installed and running
- [ ] Test driver compatibility in staging (if going 0.60 route)
- [ ] Review Metabase changelog for feature removals (none documented 0.58→0.60)

---

## 6. Open Questions

1. **Has metabase_duckdb_driver 1.5.2.0 been tested with Metabase 0.60?**
   - GitHub releases don't mention 0.60 compatibility
   - Need to check motherduckdb/metabase_duckdb_driver issues or roadmap

2. **When will driver 0.60 support be released?**
   - MotherDuck release cadence suggests 1-4 weeks post-Metabase release
   - Monitor GitHub Actions build logs for clues

3. **Are there database schema migration issues specific to 0.60?**
   - General migration works, but version-specific gotchas not documented
   - Should test in staging before production upgrade

---

## Sources

- [Metabase Releases](https://www.metabase.com/releases)
- [GitHub: metabase/metabase Releases](https://github.com/metabase/metabase/releases)
- [GitHub: motherduckdb/metabase_duckdb_driver Releases](https://github.com/motherduckdb/metabase_duckdb_driver/releases)
- [Metabase Upgrading Guide](https://www.metabase.com/docs/latest/installation-and-operation/upgrading-metabase)
- [Metabase System Requirements: Java](https://www.metabase.com/docs/latest/installation-and-operation/running-the-metabase-jar-file)
- [MotherDuck Docs: Metabase Integration](https://motherduck.com/docs/integrations/bi-tools/metabase/)
- [Metabase Community: DuckDB Driver Discussion](https://discourse.metabase.com/t/metabase-oss-with-duckdb-driver/264720)
