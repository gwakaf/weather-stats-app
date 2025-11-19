#!/usr/bin/env python3
"""
Daily Ingestion DAG for Weather Finder
Fetches yesterday's weather data for all configured locations and saves to S3.
Runs daily to maintain historic data for current weather requests.
"""

import sys
import os
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Add project paths for Airflow container
project_path = '/opt/airflow/weather_finder'
if os.path.exists(project_path):
    sys.path.insert(0, project_path)
    sys.path.insert(0, os.path.join(project_path, 'app'))
    sys.path.insert(0, os.path.join(project_path, 'config'))
    sys.path.insert(0, os.path.join(project_path, 'pipelines'))
else:
    # For local development
    local_project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, local_project_path)
    sys.path.insert(0, os.path.join(local_project_path, 'app'))
    sys.path.insert(0, os.path.join(local_project_path, 'config'))
    sys.path.insert(0, os.path.join(local_project_path, 'pipelines'))

# Import the pipeline functions - DAG will fail if import fails
from pipelines.daily_ingest import run_daily_ingestion
from pipelines.data_quality import run_daily_data_quality_check

# Airflow imports
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

# DAG configuration
default_args = {
    'owner': 'weather_finder',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
with DAG(
    dag_id='daily_weather_ingestion',
    default_args=default_args,
    description='Ingest weather data for all predefined locations (1 week ago due to API delay)',
    schedule_interval='0 6 * * *',  # Every day at 6 AM
    catchup=False,
    tags=['weather', 'daily', 'api'],
    max_active_runs=1
) as dag:

    # DAG tasks
    ingest_weather_data = PythonOperator(
        task_id='ingest_weather_data',
        python_callable=run_daily_ingestion,
        provide_context=True,
        dag=dag
    )
    
    # Data quality check task - runs after ingestion
    check_data_quality = PythonOperator(
        task_id='check_data_quality',
        python_callable=run_daily_data_quality_check,
        provide_context=True,
        dag=dag
    )

    # Task dependencies: ingestion -> data quality check
    ingest_weather_data >> check_data_quality 