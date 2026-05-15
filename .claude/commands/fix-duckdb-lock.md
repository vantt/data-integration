# Fix DuckDB Stale Lock

Fix `ingestion_health.duckdb` stale lock (PID 0 / "Conflicting lock" error) without restarting Docker Desktop.

## Steps

1. **Kill dllhost.exe** (Windows Defender COM proxy that sometimes holds file handles):
   ```powershell
   Get-Process -Name "dllhost" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
   ```

2. **File-copy recovery** — copy+replace the DB file to break the embedded stale lock, then CHECKPOINT.

   If `data_platform` container is running:
   ```powershell
   docker exec data_platform python -c "
   import shutil, os, duckdb
   db = '/app/var/data_lake/monitoring/ingestion_health.duckdb'
   bak = db + '.recovering'
   shutil.copy2(db, bak)
   os.replace(bak, db)
   con = duckdb.connect(db)
   con.execute('CHECKPOINT')
   con.close()
   print('CHECKPOINT OK')
   "
   ```

   If container is **not** running, run from host:
   ```powershell
   python -c "
   import shutil, os, duckdb
   db = r'D:\Vantt\app\data-integration\app_data\data_lake\monitoring\ingestion_health.duckdb'
   bak = db + '.recovering'
   shutil.copy2(db, bak)
   os.replace(bak, db)
   con = duckdb.connect(db)
   con.execute('CHECKPOINT')
   con.close()
   print('CHECKPOINT OK (host)')
   "
   ```

3. **Verify** write access from inside the container:
   ```powershell
   docker exec data_platform python -c "
   import duckdb
   con = duckdb.connect('/app/var/data_lake/monitoring/ingestion_health.duckdb')
   count = con.execute('SELECT COUNT(*) FROM ingestion_runs').fetchone()[0]
   latest = con.execute('SELECT MAX(run_started_at) FROM ingestion_runs').fetchone()[0]
   con.close()
   print(f'Write OK - {count} runs, latest: {latest}')
   "
   ```

4. **Report** result to user.

## Notes

- PID 0 = no live process holds the lock — it's embedded in the DB file itself (happens after SIGKILL / container crash)
- File-copy creates a new inode, which resets the embedded lock metadata — direct CHECKPOINT won't work without this
- Do NOT restart Docker Desktop to fix this (freezes WSL2)
- Recovery script also runs automatically on container startup: `scripts/maintenance/recover_health_db.py`
