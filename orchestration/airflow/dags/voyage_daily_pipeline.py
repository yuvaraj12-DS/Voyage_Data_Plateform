# pyright: reportMissingImports=false

from datetime import timedelta
import os
import time

import pendulum
import requests

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks import (
    DatabricksRunNowOperator,
)

AIRBYTE_BASE_URL = os.environ["AIRBYTE_BASE_URL"]

# Load Airbyte Credentials from Environment Variables
AIRBYTE_USERNAME = os.getenv("AIRBYTE_USERNAME", "airbyte")
AIRBYTE_PASSWORD = os.getenv("AIRBYTE_PASSWORD", "password")
AIRBYTE_API_TOKEN = os.getenv("AIRBYTE_API_TOKEN")

AIRBYTE_BOOKING_CONNECTION_ID = os.environ[
    "AIRBYTE_BOOKING_CONNECTION_ID"
]

AIRBYTE_MARKETING_CONNECTION_ID = os.environ[
    "AIRBYTE_MARKETING_CONNECTION_ID"
]

AIRBYTE_WEBSITE_CONNECTION_ID = os.environ[
    "AIRBYTE_WEBSITE_CONNECTION_ID"
]

AIRBYTE_MARKETING_BOOKING_CONNECTION_ID = os.environ[
    "AIRBYTE_MARKETING_BOOKING_CONNECTION_ID"
]

DATABRICKS_JOB_ID = int(
    os.environ["DATABRICKS_JOB_ID"]
)


def get_auth_config():
    """Returns headers or auth tuple depending on configured credentials."""
    headers = {"Content-Type": "application/json"}
    auth = None

    if AIRBYTE_API_TOKEN:
        headers["Authorization"] = f"Bearer {AIRBYTE_API_TOKEN}"
    else:
        auth = (AIRBYTE_USERNAME, AIRBYTE_PASSWORD)

    return headers, auth


def create_airbyte_sync_function(connection_id):
    """Create a function that syncs an Airbyte connection."""

    def sync_connection():
        trigger_url = f"{AIRBYTE_BASE_URL}/api/v1/connections/sync"
        headers, auth = get_auth_config()

        response = requests.post(
            trigger_url,
            headers=headers,
            auth=auth,
            json={
                "connectionId": connection_id,
            },
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()
        job_id = payload.get("job", {}).get("id")

        if job_id is None:
            raise RuntimeError("Airbyte did not return a sync job ID.")

        print(f"Triggered Airbyte connection {connection_id} with job {job_id}")

        status_url = f"{AIRBYTE_BASE_URL}/api/v1/jobs/get"
        success_statuses = {"succeeded"}
        failure_statuses = {"failed", "error", "cancelled"}

        while True:
            status_response = requests.post(
                status_url,
                headers=headers,
                auth=auth,
                json={
                    "id": job_id,
                },
                timeout=30,
            )

            status_response.raise_for_status()
            status_payload = status_response.json()
            status = status_payload.get("job", {}).get("status")

            print(f"Airbyte job {job_id}: {status}")

            if status in success_statuses:
                return

            if status in failure_statuses:
                raise RuntimeError(
                    f"Airbyte connection failed. "
                    f"Connection={connection_id}, "
                    f"job={job_id}, "
                    f"status={status}"
                )

            time.sleep(10)

    return sync_connection


with DAG(
    dag_id="voyage_daily_pipeline",
    schedule="@daily",
    start_date=pendulum.datetime(
        2026,
        9,
        30,
        tz="Asia/Kolkata",
    ),
    catchup=True,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=[
        "voyage",
        "airbyte",
        "databricks",
        "dbt",
    ],
    description=(
        "VoyageData daily ingestion and transformation pipeline"
    ),
) as dag:

    booking_sync = PythonOperator(
        task_id="sync_bookings",
        python_callable=create_airbyte_sync_function(
            AIRBYTE_BOOKING_CONNECTION_ID
        ),
    )

    marketing_sync = PythonOperator(
        task_id="sync_marketing",
        python_callable=create_airbyte_sync_function(
            AIRBYTE_MARKETING_CONNECTION_ID
        ),
    )

    website_sync = PythonOperator(
        task_id="sync_website",
        python_callable=create_airbyte_sync_function(
            AIRBYTE_WEBSITE_CONNECTION_ID
        ),
    )

    marketing_booking_sync = PythonOperator(
        task_id="sync_marketing_bookings",
        python_callable=create_airbyte_sync_function(
            AIRBYTE_MARKETING_BOOKING_CONNECTION_ID
        ),
    )

    refresh_databricks = DatabricksRunNowOperator(
        task_id="refresh_databricks",
        databricks_conn_id= "databricks_default",
        job_id=DATABRICKS_JOB_ID,
        execution_timeout=timedelta(seconds=7200),
    )

    booking_sync >> marketing_sync
    marketing_sync >> website_sync
    website_sync >> marketing_booking_sync
    marketing_booking_sync >> refresh_databricks