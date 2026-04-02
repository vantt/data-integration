import dlt
import os
import sys

# Define the pipelines to clean
pipelines_to_clean = [
    "sapo_history_log_pipeline",
    "sapo_orders_batch",
    "sapo_customers_batch",
    "sapo_accounts_batch"
]

print("Starting DLT State Cleanup...")
print(f"Current working directory: {os.getcwd()}")

success_count = 0
fail_count = 0

for p_name in pipelines_to_clean:
    print(f"\n--------------------------------------------------")
    print(f"Processing pipeline: {p_name}")
    try:
        # Attach to the pipeline
        # We assume the state is located in the default location used by the ingestion scripts
        # executed from /app.
        p = dlt.attach(pipeline_name=p_name)
        
        print(f"Successfully attached to pipeline: {p.pipeline_name}")
        print(f"Pipeline State Location: {p.working_dir}")
        
        # Check for pending packages
        # Note: drop_pending_packages() is the method to use.
        print("Dropping pending packages...")
        p.drop_pending_packages()
        print(f"✅ Pending packages dropped for {p_name}")
        success_count += 1
        
    except Exception as e:
        print(f"❌ Failed to process {p_name}: {e}")
        fail_count += 1

print(f"\n--------------------------------------------------")
print(f"Cleanup Complete.")
print(f"Success: {success_count}")
print(f"Failed:  {fail_count}")

if fail_count > 0:
    print("Warning: Some pipelines could not be processed. Please check the logs.")
    # We exit with 0 to avoid crashing the runner, output logic handles verification
else:
    print("All pipelines processed successfully.")
