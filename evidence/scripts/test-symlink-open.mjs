import { DuckDBInstance } from '@duckdb/node-api';
import { existsSync, lstatSync, realpathSync } from 'fs';

const SYMLINK = '/app/sources/datalake/olap-serving.duckdb';
const TARGET  = '/app/var/data_lake/serving/olap.duckdb';

console.log('symlink exists:', existsSync(SYMLINK));
try { console.log('symlink lstat:', JSON.stringify(lstatSync(SYMLINK))); } catch(e) { console.log('lstat error:', e.message); }
try { console.log('realpath:', realpathSync(SYMLINK)); } catch(e) { console.log('realpath error:', e.message); }
console.log('target exists:', existsSync(TARGET));

try {
  const inst = await DuckDBInstance.create(SYMLINK, { access_mode: 'READ_ONLY' });
  const con = await inst.connect();
  const r = await con.run(`SELECT COUNT(*) FROM main_marts.fact_orders`);
  const rows = await r.getRows();
  console.log('SUCCESS — fact_orders count:', rows[0][0].toString());
} catch(e) {
  console.log('FAIL opening symlink:', e.message);
}
