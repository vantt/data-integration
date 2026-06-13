import { DuckDBInstance } from '@duckdb/node-api';
const inst = await DuckDBInstance.create('/app/sources/datalake/gateway.duckdb', { access_mode: 'READ_ONLY' });
const con = await inst.connect();
const r1 = await con.run(`SELECT schema_name, count(*) AS cnt FROM duckdb_views() GROUP BY schema_name ORDER BY schema_name`);
const toStr = v => typeof v === 'bigint' ? Number(v) : v;
console.log('Gateway schemas:', JSON.stringify((await r1.getRows()).map(r => r.map(toStr))));
const r2 = await con.run(`SELECT view_name FROM duckdb_views() WHERE schema_name='main_marts' ORDER BY view_name LIMIT 10`);
console.log('main_marts views (first 10):', JSON.stringify(await r2.getRows()));
try {
  const r3 = await con.run(`SELECT COUNT(*) FROM main_marts.fact_orders`);
  console.log('main_marts.fact_orders row count:', JSON.stringify((await r3.getRows()).map(r => r.map(toStr))));
} catch(e) { console.log('FAIL main_marts.fact_orders:', e.message.split('\n')[0]); }
