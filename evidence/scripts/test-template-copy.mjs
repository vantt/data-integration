import { DuckDBInstance } from '@duckdb/node-api';
const TEMPLATE_COPY = '/app/.evidence/template/sources/datalake/olap-serving.duckdb';

try {
  const inst = await DuckDBInstance.create(TEMPLATE_COPY, { access_mode: 'READ_ONLY' });
  const con = await inst.connect();
  const r1 = await con.run(`SELECT DISTINCT schema_name FROM duckdb_views() ORDER BY 1`);
  console.log('schemas:', JSON.stringify(await r1.getRows()));
  for (const sql of [
    `SELECT COUNT(*) FROM main_marts.fact_orders`,
    `SELECT COUNT(*) FROM fact_orders`,
  ]) {
    try {
      const r = await con.run(sql);
      console.log('OK:', sql, '→', (await r.getRows())[0][0].toString());
    } catch(e) { console.log('FAIL:', sql, '→', e.message.split('\n')[0]); }
  }
} catch(e) { console.log('OPEN FAIL:', e.message); }
