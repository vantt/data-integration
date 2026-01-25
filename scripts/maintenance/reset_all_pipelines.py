import dlt

def reset_all():
    pipelines = [
        #"sapo_orders_batch",
        #"sapo_customers_batch",
        "sapo_history_log_pipeline",
        "sapo_webhook_consumer"
    ]

    for p_name in pipelines:
        print(f"🔄 Dropping pipeline: {p_name}")
        p = dlt.pipeline(pipeline_name=p_name, destination="filesystem", dataset_name="sapo_raw")
        p.drop()
        print(f"✅ Dropped {p_name}")

if __name__ == "__main__":
    reset_all()
