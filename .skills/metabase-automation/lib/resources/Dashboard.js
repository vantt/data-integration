const { extractTextId } = require('../text-card-helpers');

class Dashboard {
    constructor(core) {
        this.core = core;
    }

    async find(name) {
        const dbs = await this.core.request('/api/dashboard');
        return dbs.find(d => d.name === name) || null;
    }

    async ensure(name, description, collectionId, parameters = []) {
        const existing = await this.find(name);
        if (existing) {
             console.log(`ℹ️ Dashboard '${name}' exists (ID: ${existing.id})`);

             // If archived, unarchive it
             if (existing.archived) {
                 console.log(`♻️ Unarchiving Dashboard '${name}'...`);
                 await this.core.request(`/api/dashboard/${existing.id}`, 'PUT', { archived: false });
             }

             // Ensure it's in the right collection (fix potential mismatch)
             if (existing.collection_id !== collectionId) {
                  console.log(`📦 Moving Dashboard '${name}' to collection ${collectionId}...`);
                  await this.core.request(`/api/dashboard/${existing.id}`, 'PUT', { collection_id: collectionId });
             }

             // Sync description from blueprint if provided and differs from live state
             if (description != null && description !== existing.description) {
                  console.log(`📝 Updating description for Dashboard '${name}'...`);
                  await this.core.request(`/api/dashboard/${existing.id}`, 'PUT', { description });
             }

             return existing;
        }

        const created = await this.core.request('/api/dashboard', 'POST', {
            name,
            description,
            collection_id: collectionId,
            parameters: parameters // e.g., [{ name: "Date", slug: "date", id: "...", type: "date/all-options" }]
        });
        console.log(`✅ Created Dashboard '${name}' (ID: ${created.id})`);
        return created;
    }

    /**
     * Build tabs payload for a dashboard. Returns { tabsPayload, tabMap }.
     * tabMap maps tab names to IDs (negative temp IDs for new tabs).
     * IMPORTANT: Metabase requires tabs and dashcards in the same PUT request.
     */
    buildTabsPayload(existingTabs, tabNames) {
        const tabsPayload = [];
        const tabMap = new Map();

        // Reuse existing tabs by name
        for (const tab of existingTabs) {
            if (tabNames.includes(tab.name)) {
                tabsPayload.push({ id: tab.id, name: tab.name });
                tabMap.set(tab.name, tab.id);
            }
        }

        // Add new tabs with negative temp IDs
        let tempId = -1;
        for (const name of tabNames) {
            if (!tabMap.has(name)) {
                tabsPayload.push({ id: tempId, name });
                tabMap.set(name, tempId);
                tempId--;
            }
        }

        return { tabsPayload, tabMap };
    }

    /**
     * Validate that no tab has a non-cycle card at row=0 conflicting with the
     * cycle-indicator ("Chu kỳ báo cáo"). Logs a warning — does NOT auto-fix.
     * Blueprint is the source of truth; fix conflicts in the blueprint file.
     */
    validateCycleIndicatorPosition(cardConfigs, tabMap) {
        const CYCLE_NAME = 'Chu kỳ báo cáo';
        const byTab = new Map();
        for (const cfg of cardConfigs) {
            let tabKey = cfg.tab && tabMap.has(cfg.tab) ? String(tabMap.get(cfg.tab))
                       : cfg.dashboard_tab_id != null ? String(cfg.dashboard_tab_id)
                       : '__none__';
            if (!byTab.has(tabKey)) byTab.set(tabKey, []);
            byTab.get(tabKey).push(cfg);
        }
        for (const [, tabCards] of byTab) {
            const cycleCard = tabCards.find(c => c.name === CYCLE_NAME && c.row === 0);
            if (!cycleCard) continue;
            const conflicts = tabCards.filter(c => c !== cycleCard && c.row === 0);
            if (conflicts.length > 0) {
                const label = cycleCard.tab || 'default';
                console.warn(`⚠️  Blueprint conflict: tab "${label}" has ${conflicts.length} card(s) at row=0 alongside cycle-indicator — fix row positions in the blueprint file.`);
            }
        }
    }

    async syncCards(dashboardId, cardConfigs, tabNames = []) {
        // Version Check
        const isModern = this.core.isVersionAtLeast("v0.60.0");
        console.log(`ℹ️ Metabase Version: ${this.core.version} (Strategy: ${isModern ? 'Modern/Dashcards' : 'Legacy/OrderedCards'})`);

        // cardConfigs: [{ id, row, col, size_x, size_y, parameter_mappings }]
        
        const dashboard = await this.core.request(`/api/dashboard/${dashboardId}`);
        // Support both property names if Metabase version varies, but v0.60+ uses dashcards
        let currentCards = dashboard.dashcards || dashboard.ordered_cards || [];
        const existingTabs = dashboard.tabs || [];

        // Build tabs payload if tab names are provided
        let tabsPayload = null;
        let tabMap = new Map();
        if (tabNames.length > 0) {
            const result = this.buildTabsPayload(existingTabs, tabNames);
            tabsPayload = result.tabsPayload;
            tabMap = result.tabMap;
            console.log(`📑 Tab payload: ${tabsPayload.map(t => `${t.name}(${t.id})`).join(', ')}`);
        }

        // Validate cycle-indicator position — warns if blueprint has row=0 conflict.
        // Blueprint is source of truth: fix conflicts in the blueprint file, not here.
        this.validateCycleIndicatorPosition(cardConfigs, tabMap);

        let tempIdCounter = -1;
        const usedDashCardIds = new Set();

        const cardPayload = cardConfigs.map(config => {
            const isTextCard = config.id === null;

            // Match by card_id AND tab — avoid reusing the same dashcard across tabs
            // Text cards: match by text-id marker + tab (idempotent redeploy)
            const tabId = config.tab && tabMap.has(config.tab) ? tabMap.get(config.tab) : (config.dashboard_tab_id || null);
            let existing;
            if (isTextCard) {
                const configTextId = extractTextId((config.visualization_settings || {}).text);
                // Primary match: by text-id marker + tab
                existing = configTextId ? currentCards.find(dc =>
                    dc.card_id === null
                    && !usedDashCardIds.has(dc.id)
                    && (tabId == null || dc.dashboard_tab_id === tabId)
                    && extractTextId((dc.visualization_settings || {}).text) === configTextId
                ) : null;
                // Fallback: match legacy text cards (no marker) by tab + position
                if (!existing && configTextId) {
                    existing = currentCards.find(dc =>
                        dc.card_id === null
                        && !usedDashCardIds.has(dc.id)
                        && (tabId == null || dc.dashboard_tab_id === tabId)
                        && !extractTextId((dc.visualization_settings || {}).text)
                        && dc.row === config.row && dc.col === config.col
                    ) || null;
                }
            } else {
                existing = currentCards.find(dc =>
                    dc.card_id === config.id
                    && !usedDashCardIds.has(dc.id)
                    && (tabId == null || dc.dashboard_tab_id === tabId)
                );
            }
            if (existing) usedDashCardIds.add(existing.id);

            let dashCardId;
            if (existing) {
                dashCardId = existing.id;
            } else {
                dashCardId = isModern ? tempIdCounter-- : undefined;
            }

            const cardObj = {
                card_id: config.id,      // The Question ID (null for text cards)
                row: config.row,
                col: config.col,
                size_x: config.size_x,
                size_y: config.size_y,
                visualization_settings: config.visualization_settings || {},
                parameter_mappings: config.parameter_mappings || (existing ? existing.parameter_mappings : []) || [],
                series: []
            };

            // Assign to tab: use tab name to look up ID from tabMap
            if (config.tab && tabMap.has(config.tab)) {
                cardObj.dashboard_tab_id = tabMap.get(config.tab);
            } else if (config.dashboard_tab_id) {
                cardObj.dashboard_tab_id = config.dashboard_tab_id;
            }
            
            // Only add 'id' if modern or if existing
            if (dashCardId !== undefined) {
                cardObj.id = dashCardId;
            }

            return cardObj;
        });

        try {
            let payload;
            
            if (isModern) {
                payload = { dashcards: cardPayload };
            } else {
                payload = { ordered_cards: cardPayload };
            }

            // Include tabs in the same PUT (Metabase requires tabs+cards together)
            if (tabsPayload) {
                payload.tabs = tabsPayload;
            }

            console.log(`Using '${isModern ? 'dashcards' : 'ordered_cards'}' payload...`);

            const updatedDashboard = await this.core.request(`/api/dashboard/${dashboardId}`, 'PUT', payload);
            
            // Response might use differing keys
            const count = (updatedDashboard.dashcards ? updatedDashboard.dashcards.length : 0) || 
                          (updatedDashboard.ordered_cards ? updatedDashboard.ordered_cards.length : 0);
            
            console.log(`✅ Synced cards. Dashboard now has ${count} cards.`);
            
            if (count === 0 && cardPayload.length > 0) {
                 console.warn("⚠️ Warning: Dashboard returned 0 cards. Payload might be rejected.", JSON.stringify(payload));
            }

        } catch (e) {
            console.error(`❌ Failed syncCards (PUT /api/dashboard/${dashboardId}): ${e.message}`);
            if (e.data) console.error("Error Data:", JSON.stringify(e.data));
        }
    }
}

module.exports = Dashboard;
