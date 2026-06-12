#!/usr/bin/env node
/**
 * Rename API-added "Chu kỳ báo cáo · {Tab Name}" cards → "Chu kỳ báo cáo"
 * Aligns with blueprint convention (existing blueprints declare plain "Chu kỳ báo cáo" per tab).
 * Metabase allows same-named cards across tabs (matched by (tab_id, card_name)).
 */

const URL = process.env.METABASE_URL || "http://127.0.0.1:3001";
const KEY = process.env.METABASE_API_KEY;
if (!KEY) { console.error("METABASE_API_KEY required"); process.exit(1); }

async function main() {
  // Search for cards matching the suffix pattern
  const res = await fetch(`${URL}/api/search?models=card&archived=false&q=Chu%20k%E1%BB%B3%20b%C3%A1o%20c%C3%A1o`, {
    headers: {"x-api-key": KEY}
  });
  const data = await res.json();
  const cards = (data.data || []).filter(c => c.name.startsWith("Chu kỳ báo cáo · "));
  console.log(`Found ${cards.length} cards with suffix to rename.\n`);

  let ok = 0, fail = 0;
  for (const c of cards) {
    const r = await fetch(`${URL}/api/card/${c.id}`, {
      method: "PUT",
      headers: {"x-api-key": KEY, "Content-Type": "application/json"},
      body: JSON.stringify({name: "Chu kỳ báo cáo"})
    });
    if (r.ok) { ok++; console.log(`✓ [${c.id}] "${c.name}" → "Chu kỳ báo cáo"`); }
    else { fail++; const e = await r.text(); console.log(`✗ [${c.id}] ${r.status}: ${e.slice(0,100)}`); }
    await new Promise(r => setTimeout(r, 100));
  }
  console.log(`\nDone. ${ok} renamed, ${fail} failed.`);
}

main().catch(e => { console.error(e); process.exit(1); });
