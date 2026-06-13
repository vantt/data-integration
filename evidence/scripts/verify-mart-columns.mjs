import { DuckDBInstance } from '@duckdb/node-api';
const inst = await DuckDBInstance.create('/app/sources/datalake/olap-serving.duckdb', { access_mode: 'READ_ONLY' });
const con = await inst.connect();
for (const t of ['fact_orders','dim_customers','dim_channels','fact_targets','fact_order_economics','fact_order_returns']) {
  try {
    const r = await con.run(`DESCRIBE main_marts.${t}`);
    const rows = await r.getRows();
    console.log(t + ':', rows.map(r => r[0]).join(', '));
  } catch(e) { console.log(t + ' FAIL:', e.message.split('\n')[0]); }
}
