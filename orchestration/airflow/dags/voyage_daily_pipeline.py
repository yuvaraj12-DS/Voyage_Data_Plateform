import logging
import os
import time
from datetime import timedelta

import pendulum
import requests

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks import (
    DatabricksRunNowOperator,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Airflow callbacks
# ---------------------------------------------------------------------------

def on_failure_callback(context):
    """Log task failure after all configured retries are exhausted."""
    task = context["task_instance"]
    dag_run = context["dag_run"]
    exception = context.get("exception")

    logger.error(
        "PIPELINE FAILURE | "
        "dag_id=%s | "
        "run_id=%s | "
        "task_id=%s | "
        "dag_start=%s | "
        "task_start=%s | "
        "failed_at=%s | "
        "error=%s",
        dag_run.dag_id,
        dag_run.run_id,
        task.task_id,
        dag_run.start_date,
        task.start_date,
        pendulum.now("UTC"),
        str(exception)[:500],
    )


def on_retry_callback(context):
    """Log task retry information."""
    task = context["task_instance"]
    dag_run = context["dag_run"]

    logger.warning(
        "TASK RETRY | "
        "dag_id=%s | "
        "run_id=%s | "
        "task_id=%s | "
        "try_number=%s",
        dag_run.dag_id,
        dag_run.run_id,
        task.task_id,
        task.try_number,
    )


def on_success_callback(context):
    """Log successful task completion."""
    task = context["task_instance"]
    dag_run = context["dag_run"]

    logger.info(
        "TASK SUCCESS | "
        "dag_id=%s | "
        "run_id=%s | "
        "task_id=%s | "
        "task_start=%s | "
        "completed_at=%s",
        dag_run.dag_id,
        dag_run.run_id,
        task.task_id,
        task.start_date,
        pendulum.now("UTC"),
    )


# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

AIRBYTE_BASE_URL = os.environ["AIRBYTE_BASE_URL"]

AIRBYTE_USERNAME = os.getenv(
    "AIRBYTE_USERNAME",
    "airbyte",
)

AIRBYTE_PASSWORD = os.getenv(
    "AIRBYTE_PASSWORD",
    "password",
)

AIRBYTE_API_TOKEN = os.getenv(
    "AIRBYTE_API_TOKEN",
)

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


# ---------------------------------------------------------------------------
# Airbyte authentication
# ---------------------------------------------------------------------------

def get_auth_config():
    """
    Return the headers and authentication configuration
    required by the Airbyte API.
    """

    headers = {
        "Content-Type": "application/json",
    }

    auth = None

    if AIRBYTE_API_TOKEN:
        headers["Authorization"] = (
            f"Bearer {AIRBYTE_API_TOKEN}"
        )
    else:
        auth = (
            AIRBYTE_USERNAME,
            AIRBYTE_PASSWORD,
        )

    return headers, auth


# ---------------------------------------------------------------------------
# Airbyte sync function factory
# ---------------------------------------------------------------------------

def create_airbyte_sync_function(connection_id):
    """
    Create a callable that triggers and monitors
    one Airbyte connection sync.
    """

    def sync_connection():
        # ---------------------------------------------------------------
        # Trigger Airbyte sync
        # ---------------------------------------------------------------

        trigger_url = (
            f"{AIRBYTE_BASE_URL}/api/v1/connections/sync"
        )

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

        job_id = (
            payload
            .get("job", {})
            .get("id")
        )

        if job_id is None:
            raise RuntimeError(
                "Airbyte did not return a sync job ID."
            )

        logger.info(
            "AIRBYTE SYNC STARTED | "
            "connection_id=%s | "
            "job_id=%s",
            connection_id,
            job_id,
        )

        # ---------------------------------------------------------------
        # Monitor Airbyte job
        # ---------------------------------------------------------------

        status_url = (
            f"{AIRBYTE_BASE_URL}/api/v1/jobs/get"
        )

        success_statuses = {
            "succeeded",
        }

        failure_statuses = {
            "failed",
            "error",
            "cancelled",
        }

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

            status = (
                status_payload
                .get("job", {})
                .get("status")
            )

            logger.info(
                "AIRBYTE JOB STATUS | "
                "connection_id=%s | "
                "job_id=%s | "
                "status=%s",
                connection_id,
                job_id,
                status,
            )

            # -----------------------------------------------------------
            # Successful Airbyte sync
            # -----------------------------------------------------------

            if status in success_statuses:
                logger.info(
                    "AIRBYTE SYNC SUCCESS | "
                    "connection_id=%s | "
                    "job_id=%s",
                    connection_id,
                    job_id,
                )

                return

            # -----------------------------------------------------------
            # Failed Airbyte sync
            # -----------------------------------------------------------

            if status in failure_statuses:
                logger.error(
                    "AIRBYTE SYNC FAILED | "
                    "connection_id=%s | "
                    "job_id=%s | "
                    "status=%s",
                    connection_id,
                    job_id,
                    status,
                )

                raise RuntimeError(
                    "Airbyte connection failed. "
                    f"Connection={connection_id}, "
                    f"job={job_id}, "
                    f"status={status}"
                )

            # -----------------------------------------------------------
            # Continue polling
            # -----------------------------------------------------------

            time.sleep(10)

    return sync_connection


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

dag = DAG(
    dag_id="voyage_daily_pipeline",

    default_args={
        "owner": "airflow",

        "retries": 3,

        "retry_delay": timedelta(
            minutes=1
        ),

        "on_failure_callback": on_failure_callback,

        "on_retry_callback": on_retry_callback,

        "on_success_callback": on_success_callback,
    },

    schedule="@daily",

    start_date=pendulum.datetime(
        2026,
        9,
        30,
        tz="Asia/Kolkata",
    ),

    catchup=False,

    max_active_runs=1,

    on_failure_callback=on_failure_callback,

    tags=[
        "voyage",
        "airbyte",
        "databricks",
        "dbt",
    ],

    description=(
        "VoyageData daily ingestion and transformation pipeline"
    ),
)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

with dag:

    # ---------------------------------------------------------------
    # 1. Booking sync
    # ---------------------------------------------------------------

    booking_sync = PythonOperator(
        task_id="sync_bookings",

        python_callable=create_airbyte_sync_function(
            AIRBYTE_BOOKING_CONNECTION_ID
        ),
    )


    # ---------------------------------------------------------------
    # 2. Marketing sync
    # ---------------------------------------------------------------

    marketing_sync = PythonOperator(
        task_id="sync_marketing",

        python_callable=create_airbyte_sync_function(
            AIRBYTE_MARKETING_CONNECTION_ID
        ),
    )


    # ---------------------------------------------------------------
    # 3. Website sync
    # ---------------------------------------------------------------

    website_sync = PythonOperator(
        task_id="sync_website",

        python_callable=create_airbyte_sync_function(
            AIRBYTE_WEBSITE_CONNECTION_ID
        ),
    )


    # ---------------------------------------------------------------
    # 4. Marketing booking sync
    # ---------------------------------------------------------------

    marketing_booking_sync = PythonOperator(
        task_id="sync_marketing_bookings",

        python_callable=create_airbyte_sync_function(
            AIRBYTE_MARKETING_BOOKING_CONNECTION_ID
        ),
    )


    # ---------------------------------------------------------------
    # 5. Databricks refresh
    # ---------------------------------------------------------------

    refresh_databricks = DatabricksRunNowOperator(
    task_id="refresh_databricks",
    databricks_conn_id="databricks_default",
    job_id=DATABRICKS_JOB_ID,
    job_parameters={
        "airbyte_status": "SUCCESS",
    },
    execution_timeout=timedelta(
        seconds=7200
    ),
)


# ---------------------------------------------------------------------------
# Task dependencies
# ---------------------------------------------------------------------------

booking_sync >> marketing_sync
marketing_sync >> website_sync
website_sync >> marketing_booking_sync
marketing_booking_sync >> refresh_databricks