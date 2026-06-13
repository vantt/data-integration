import { DuckDBInstance } from '@duckdb/node-api';
const OLAP = '/app/var/data_lake/serving/olap.duckdb';

// Open olap.duckdb directly (no ATTACH) — same as Evidence would do
const inst = await DuckDBInstance.create(OLAP, { access_mode: 'READ_ONLY' });
const con = await inst.connect();

const r1 = await con.run(`SELECT DISTINCT database_name, schema_name FROM duckdb_views() ORDER BY 1,2`);
console.log('schemas:', JSON.stringify(await r1.getRows()));

for (const sql of [
  `SELECT COUNT(*) FROM main_marts.fact_orders`,
  `SELECT COUNT(*) FROM fact_orders`,
  `SELECT COUNT(*) FROM main.fact_orders`,
]) {
  try {
    const r = await con.run(sql);
    const rows = await r.getRows();
    console.log('OK:', sql, '→', rows[0][0].toString());
  } catch(e) {
    console.log('FAIL:', sql, '→', e.message.split('\n')[0]);
  }
}
