const fs = require('fs');
const path = require('path');

/**
 * Parses a "Literate Configuration" Markdown file into a Metabase Config object.
 *
 * Syntax:
 * - ## 📂 Collection: <Name>              -> Top-level collection
 * - ## 📂 Collection: <Parent> > <Child>   -> Nested collection (child under parent)
 * - ### 🧊 Model: <Name>     -> (Dependent on Collection)
 * - #### 📏 Metric: <Name>   -> (Dependent on Model)
 * - ### 🖥️ Dashboard: <Name> -> (Dependent on Collection)
 * - ### 📑 Tab: <Name>       -> (Dependent on Dashboard) Groups subsequent questions
 * - #### ❓ Question: <Name> -> (Dependent on Dashboard, optionally scoped to a Tab)
 * - #### 📝 Text: <Name>     -> Text annotation card (no SQL, card_id = null)
 *
 * Code Blocks:
 * - ```sql -> The logic
 * - ```json metabase-viz -> Viz Settings
 * - ```json metabase-pos -> Dashboard Position
 * - ```json metabase-model -> Model Metadata
 * - ```json metabase-filter -> Dashboard Filter/Parameter definition
 *
 * Collection Path Syntax:
 *   "## Collection: Operations > Daily Monitoring"
 *   creates "Operations" (if needed) then "Daily Monitoring" as a child.
 *   The dashboard is placed in the LAST segment (leaf collection).
 *
 * Tab Syntax:
 *   "### 📑 Tab: Overview" placed after a Dashboard header.
 *   All subsequent Questions belong to that tab until the next Tab header.
 *   Questions get a `tab` property; the dashboard gets a `tabs[]` array.
 *   Tabs are optional — dashboards without tabs work as single flat layouts.
 */

function parseMarkdownConfig(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');

    const config = {
        database: null, // Parsed from "> **Database:** `Name`" blockquote
        collections: [],
        models: [], // Flat list of models with collection_id linkage logic
        dashboards: [] // Flat list, hierarchically parsed
    };

    let currentCollection = null;
    let currentModel = null;
    let currentDashboard = null;
    let currentQuestion = null;
    let currentMetric = null;
    let currentTab = null;
    let currentFilter = null;
    let currentTextCard = null;

    let inCodeBlock = false;
    let codeBlockType = null; // 'sql', 'json-viz', 'json-pos', 'json-model'
    let codeBuffer = [];

    // Helper to save buffered code to the active entity
    const flushCodeBlock = () => {
        if (!inCodeBlock || codeBuffer.length === 0) return;

        const code = codeBuffer.join('\n').trim();

        if (codeBlockType === 'sql') {
            // SQL can belong to a Question, a Model, or a Metric
            if (currentQuestion) currentQuestion.sql = code;
            else if (currentMetric) currentMetric.formula = code; // "Formula" or SQL for metric
            else if (currentModel) currentModel.sql = code;
        } else if (codeBlockType === 'json-viz') {
            if (currentQuestion) {
                 try { currentQuestion.viz = JSON.parse(code); } 
                 catch(e) { console.warn(`⚠️ Invalid JSON in Viz block for ${currentQuestion.name}`); }
            }
        } else if (codeBlockType === 'json-pos') {
            if (currentQuestion) {
                try { currentQuestion.pos = JSON.parse(code); }
                catch(e) { console.warn(`⚠️ Invalid JSON in Pos block for ${currentQuestion.name}`); }
            } else if (currentTextCard) {
                try { currentTextCard.pos = JSON.parse(code); }
                catch(e) { console.warn(`⚠️ Invalid JSON in Pos block for text card '${currentTextCard.name}'`); }
            }
        } else if (codeBlockType === 'json-model') {
            if (currentModel) {
                 try { currentModel.metadata = JSON.parse(code); }
                 catch(e) { console.warn(`⚠️ Invalid JSON in Model block for ${currentModel.name}`); }
            }
        } else if (codeBlockType === 'json-filter') {
            if (currentFilter && currentDashboard) {
                try {
                    const filterDef = JSON.parse(code);
                    // Merge name from header if not in JSON
                    if (!filterDef.name) filterDef.name = currentFilter.name;
                    if (!filterDef.slug) filterDef.slug = filterDef.name.toLowerCase().replace(/\s+/g, '_');
                    if (!filterDef.id) filterDef.id = filterDef.slug;
                    Object.assign(currentFilter, filterDef);
                } catch(e) { console.warn(`⚠️ Invalid JSON in Filter block for ${currentFilter.name}`); }
            }
        } else if (codeBlockType === 'metric-sql') {
             if (currentMetric) currentMetric.sql = code;
        }

        codeBuffer = [];
        inCodeBlock = false;
        codeBlockType = null;
    };

    const cleanName = (line, prefix) => line.replace(prefix, '').trim();

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // 1. Handle Code Blocks
        if (trimmed.startsWith('```')) {
            if (inCodeBlock) {
                // Closing block
                flushCodeBlock();
            } else {
                // Opening block - determine type
                const lang = trimmed.replace('```', '').trim().toLowerCase();
                if (lang === 'sql') codeBlockType = 'sql';
                else if (lang === 'sql --metric') codeBlockType = 'metric-sql';
                else if (lang.includes('metabase-viz')) codeBlockType = 'json-viz';
                else if (lang.includes('metabase-pos')) codeBlockType = 'json-pos';
                else if (lang.includes('metabase-model')) codeBlockType = 'json-model';
                else if (lang.includes('metabase-filter')) codeBlockType = 'json-filter';
                else codeBlockType = 'ignore';

                if (codeBlockType !== 'ignore') {
                    inCodeBlock = true;
                }
            }
            continue;
        }

        if (inCodeBlock) {
            codeBuffer.push(line);
            continue;
        }

        // 1b. Parse blueprint metadata from blockquotes (e.g. "> **Database:** `Name`")
        // Must be after inCodeBlock guard to avoid consuming lines inside code blocks
        const dbMatch = trimmed.match(/^>\s*\*\*Database:\*\*\s*`([^`]+)`/);
        if (dbMatch && !config.database) {
            config.database = dbMatch[1].trim();
            continue;
        }

        // 2. Handle Hierarchy Headers (supports both emoji and plain formats)
        const collectionMatch = trimmed.match(/^##\s+(?:📂\s+)?Collection:\s*(.+)/);
        const modelMatch = trimmed.match(/^###\s+(?:🧊\s+)?Model:\s*(.+)/);
        const metricMatch = trimmed.match(/^####\s+(?:📏\s+)?Metric:\s*(.+)/);
        const dashboardMatch = trimmed.match(/^###\s+(?:🖥️\s*)?Dashboard:\s*(.+)/);
        const tabMatch = trimmed.match(/^###\s+(?:📑\s+)?Tab:\s*(.+)/);
        const questionMatch = trimmed.match(/^####\s+(?:❓\s+)?Question:\s*(.+)/);
        const filterMatch = trimmed.match(/^####\s+(?:🔍\s+)?Filter:\s*(.+)/);
        const textMatch = trimmed.match(/^####\s+(?:📝\s+)?Text:\s*(.+)/);

        if (collectionMatch) {
            const rawName = collectionMatch[1].trim();

            // Support path syntax: "Parent > Child > Grandchild"
            // Splits on ">" and trims each segment.
            // Each segment becomes a collection entry with a `parent` reference.
            const segments = rawName.split('>').map(s => s.trim()).filter(Boolean);

            let parentName = null;
            for (const segment of segments) {
                // Avoid duplicates: reuse existing collection if same name+parent
                const existing = config.collections.find(
                    c => c.name === segment && c.parent === parentName
                );
                if (existing) {
                    currentCollection = existing;
                } else {
                    currentCollection = { name: segment, parent: parentName, dashboards: [], models: [] };
                    config.collections.push(currentCollection);
                }
                parentName = segment;
            }

            // currentCollection is now the LEAF (deepest segment) — dashboards go here
            currentDashboard = null;
            currentModel = null;
            currentTextCard = null;
        }
        else if (modelMatch) {
            if (!currentCollection) continue; // Orphan model?
            const name = modelMatch[1].trim();
            currentModel = { name, metrics: [], collection_name: currentCollection.name };
            currentCollection.models.push(currentModel); // Link to collection
            config.models.push(currentModel); // Keep flat list too? Or just traverse tree.
            currentMetric = null; // Reset metric context
        }
        else if (metricMatch) {
            if (!currentModel) continue; // Metric needs model
            const name = metricMatch[1].trim();
            currentMetric = { name };
            currentModel.metrics.push(currentMetric);
        }
        else if (dashboardMatch) {
            if (!currentCollection) continue;
            const name = dashboardMatch[1].trim();
            currentDashboard = { name, questions: [], textCards: [], tabs: [], collection_name: currentCollection.name };
            currentCollection.dashboards.push(currentDashboard);
            config.dashboards.push(currentDashboard);
            currentQuestion = null;
            currentTab = null;
            currentTextCard = null;
        }
        else if (tabMatch) {
            if (!currentDashboard) continue;
            const name = tabMatch[1].trim();
            currentTab = name;
            if (!currentDashboard.tabs.includes(name)) {
                currentDashboard.tabs.push(name);
            }
            currentQuestion = null;
            currentTextCard = null;
        }
        else if (filterMatch) {
            if (!currentDashboard) continue;
            const name = filterMatch[1].trim();
            currentFilter = { name, slug: name.toLowerCase().replace(/\s+/g, '_') };
            if (!currentDashboard.filters) currentDashboard.filters = [];
            currentDashboard.filters.push(currentFilter);
            currentQuestion = null; // Filter is not a question
            currentTextCard = null;
        }
        else if (textMatch) {
            if (!currentDashboard) continue;
            const name = textMatch[1].trim();
            currentTextCard = { name, text: '' };
            if (currentTab) currentTextCard.tab = currentTab;
            if (!currentDashboard.textCards) currentDashboard.textCards = [];
            currentDashboard.textCards.push(currentTextCard);
            currentQuestion = null;
            currentFilter = null;
        }
        else if (questionMatch) {
            if (!currentDashboard) continue;
            const name = questionMatch[1].trim();
            currentQuestion = { name };
            if (currentTab) currentQuestion.tab = currentTab;
            currentDashboard.questions.push(currentQuestion);
            currentFilter = null; // Question is not a filter
            currentTextCard = null;
        }
        // Collect text card content (allow markdown headings like "# Title" but not parser-structural headers)
        else if (currentTextCard && trimmed) {
            currentTextCard.text += (currentTextCard.text ? '\n' : '') + trimmed;
        }
    }

    // Validate: warn about questions without tab in a tabbed dashboard
    for (const dashboard of config.dashboards) {
        if (dashboard.tabs.length > 0) {
            const untabbed = dashboard.questions.filter(q => !q.tab);
            if (untabbed.length > 0) {
                console.warn(`⚠️ Dashboard '${dashboard.name}' has ${dashboard.tabs.length} tab(s) but ${untabbed.length} question(s) without a tab:`);
                untabbed.forEach(q => console.warn(`   - ${q.name}`));
                console.warn(`   These questions will appear outside any tab.`);
            }
        }
    }

    return config;
}

// CLI usage if run directly
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error("Usage: node parse_markdown_config.js <file.md>");
        process.exit(1);
    }
    const result = parseMarkdownConfig(args[0]);
    console.log(JSON.stringify(result, null, 2));
}

module.exports = parseMarkdownConfig;
