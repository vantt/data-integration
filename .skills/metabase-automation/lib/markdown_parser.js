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
 * - #### ❓ Question: <Name> -> (Dependent on Dashboard)
 *
 * Code Blocks:
 * - ```sql -> The logic
 * - ```json metabase-viz -> Viz Settings
 * - ```json metabase-pos -> Dashboard Position
 * - ```json metabase-model -> Model Metadata
 *
 * Collection Path Syntax:
 *   "## Collection: Operations > Daily Monitoring"
 *   creates "Operations" (if needed) then "Daily Monitoring" as a child.
 *   The dashboard is placed in the LAST segment (leaf collection).
 */

function parseMarkdownConfig(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');

    const config = {
        collections: [],
        models: [], // Flat list of models with collection_id linkage logic
        dashboards: [] // Flat list, hierarchically parsed
    };

    let currentCollection = null;
    let currentModel = null;
    let currentDashboard = null;
    let currentQuestion = null;
    let currentMetric = null;

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
            }
        } else if (codeBlockType === 'json-model') {
            if (currentModel) {
                 try { currentModel.metadata = JSON.parse(code); }
                 catch(e) { console.warn(`⚠️ Invalid JSON in Model block for ${currentModel.name}`); }
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

        // 2. Handle Hierarchy Headers (supports both emoji and plain formats)
        const collectionMatch = trimmed.match(/^##\s+(?:📂\s+)?Collection:\s*(.+)/);
        const modelMatch = trimmed.match(/^###\s+(?:🧊\s+)?Model:\s*(.+)/);
        const metricMatch = trimmed.match(/^####\s+(?:📏\s+)?Metric:\s*(.+)/);
        const dashboardMatch = trimmed.match(/^###\s+(?:🖥️\s*)?Dashboard:\s*(.+)/);
        const questionMatch = trimmed.match(/^####\s+(?:❓\s+)?Question:\s*(.+)/);

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
            // Look ahead for description? Simple for now.
            currentDashboard = { name, questions: [], collection_name: currentCollection.name };
            currentCollection.dashboards.push(currentDashboard);
            config.dashboards.push(currentDashboard);
            currentQuestion = null;
        }
        else if (questionMatch) {
            if (!currentDashboard) continue;
            const name = questionMatch[1].trim();
            currentQuestion = { name };
            currentDashboard.questions.push(currentQuestion);
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
