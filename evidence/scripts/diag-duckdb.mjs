import { DuckDBInstance } from '@duckdb/node-api';
const OLAP = '/app/var/data_lake/serving/olap.duckdb';
const inst = await DuckDBInstance.create(':memory:');
const con = await inst.connect();
await con.run(`ATTACH '${OLAP}' AS olap (READ_ONLY)`);

const r1 = await con.run(`SELECT DISTINCT database_name, schema_name FROM duckdb_views() ORDER BY 1,2 LIMIT 20`);
const schemas = await r1.getRows();
console.log('databases/schemas with views:', JSON.stringify(schemas));

const r2 = await con.run(`SELECT database_name, schema_name, view_name FROM duckdb_views() WHERE database_name='olap' LIMIT 5`);
const views = await r2.getRows();
console.log('sample olap views:', JSON.stringify(views));

for (const expr of [
  `SELECT 1 FROM olap.main_marts.fact_orders LIMIT 1`,
  `SELECT 1 FROM main_marts.fact_orders LIMIT 1`,
  `SELECT 1 FROM olap.fact_orders LIMIT 1`,
  `SELECT 1 FROM olap.main.fact_orders LIMIT 1`,
]) {
  try {
    await con.run(expr);
    console.log('OK:', expr);
  } catch(e) {
    console.log('FAIL:', expr, '→', e.message.split('\n')[0]);
  }
}
con.close();
