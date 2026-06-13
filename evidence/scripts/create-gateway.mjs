/**
 * Creates a gateway DuckDB with ONLY mart views from olap.duckdb.
 * Evidence connects to gateway instead of olap directly, avoiding scanning
 * thousands of raw parquet files.
 *
 * Mount requirement: data_lake must be at /app/var/data_lake (same as data_platform)
 * because olap.duckdb view definitions reference absolute parquet paths there.
 */
import { DuckDBInstance } from '@duckdb/node-api';
import { existsSync, unlinkSync } from 'fs';

const GATEWAY = '/app/sources/datalake/gateway.duckdb';
const OLAP    = '/app/var/data_lake/serving/olap.duckdb';

async function main() {
  if (!existsSync(OLAP)) {
    throw new Error(`olap.duckdb not found at ${OLAP} — check volume mount`);
  }

  if (existsSync(GATEWAY)) unlinkSync(GATEWAY);

  const instance = await DuckDBInstance.create(GATEWAY);
  const con      = await instance.connect();

  await con.run(`ATTACH '${OLAP}' AS olap (READ_ONLY)`);
  // Expose views in both 'main' (unqualified queries) and 'main_marts' (schema-qualified queries)
  await con.run(`CREATE SCHEMA IF NOT EXISTS main_marts`);

  // Only source from 'main' schema — main_marts views in olap are alias views that
  // loop back through the search path and cause infinite recursion in gateway context.
  const result = await con.run(`
    SELECT view_name
    FROM duckdb_views()
    WHERE database_name = 'olap' AND schema_name = 'main'
    ORDER BY view_name
  `);
  const rows = await result.getRows();

  let ok = 0;
  for (const [view_name] of rows) {
    try {
      const src = `olap.main."${view_name}"`;
      // Expose in both main (unqualified queries) and main_marts (schema-qualified queries)
      await con.run(`CREATE OR REPLACE VIEW main."${view_name}" AS SELECT * FROM ${src}`);
      await con.run(`CREATE OR REPLACE VIEW main_marts."${view_name}" AS SELECT * FROM ${src}`);
      ok++;
    } catch (e) {
      console.warn(`  skip ${view_name}: ${e.message.split('\n')[0]}`);
    }
  }

  console.log(`Gateway ready: ${ok}/${rows.length} views (main + main_marts from olap)`);
}

main().catch(e => { console.error('Gateway creation failed:', e.message); process.exit(1); });
