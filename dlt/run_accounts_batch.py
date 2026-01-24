import dlt
from dlt.common.pipeline import LoadInfo
from src.sapo.accounts import sapo_accounts_source
import os

def run():
    # 1. Pipeline define
    pipeline = dlt.pipeline(
        pipeline_name="sapo_accounts_batch",
        destination="filesystem",
        dataset_name="sapo_raw", # -> data_lake/sapo_raw
    )

    # 2. Configure Source
    source = sapo_accounts_source(
        max_pages=1000, 
        page_size=50
    )

    # 3. Explicitly configure layout to match Unified Dataset structure
    # sapo_raw/{entity}/ingest_method={method}/year={yyyy}/month={mm}/{file}
    # Note: 'entity' is derived from table name.
    
    # We must set this env var so filesystem destination uses it
    os.environ['DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT'] = 'parquet'
    os.environ['DESTINATION__FILESYSTEM__LAYOUT'] = '{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}'
    os.environ['DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS'] = '{"ingest_method": "text", "year": "text", "month": "text"}'

    # 4. Run
    load_info = pipeline.run(source)
    print(load_info)

if __name__ == "__main__":
    run()
