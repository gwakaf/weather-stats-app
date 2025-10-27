#!/usr/bin/env python3
"""
Backfilling DAG for Weather Finder
Processes specific date ranges for configured locations to backfill historic data.
"""

import os
import sys
from datetime import datetime
import logging

# Configure logging first
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

# Import the pipeline function
try:
    from pipelines.backfilling_ingest import backfill_historic_weather, load_backfilling_config
except ImportError as e:
    logger.error(f"Failed to import backfilling_ingest: {e}")
    # Define a fallback function
    def backfill_historic_weather(start_date, end_date, location_name, save_to_s3=True):
        print("Using fallback backfilling function")
        return 0, 0, 0

def airflow_backfill_task(**context):
    """Airflow task: Run backfilling for single location using configuration"""
    try:
        logger.info(f"🚀 Starting Airflow backfilling task")
        
        # Load backfilling configuration
        backfill_config = load_backfilling_config()
        
        # Use config parameters (can be overridden by DAG run conf)
        dag_run = context['dag_run']
        run_conf = dag_run.conf if dag_run else {}
        
        # Use DAG run config if provided, otherwise use loaded config
        start_date = run_conf.get('start_date', backfill_config['start_date'])
        end_date = run_conf.get('end_date', backfill_config['end_date'])
        location = run_conf.get('location', backfill_config['location'])
        
        logger.info(f"📅 Date range: {start_date} to {end_date}")
        logger.info(f"📍 Location: {location}")
        
        # Run backfilling using the centralized pipeline function
        # API key handling is internal to WeatherAPI class
        successful_days, total_days, failed_days = backfill_historic_weather(
            start_date, end_date, location, save_to_s3=True
        )
        
        # Log results for Airflow
        logger.info(f"📊 Airflow backfilling task completed:")
        logger.info(f"   ✅ Successful days: {successful_days}/{total_days}")
        logger.info(f"   ❌ Failed days: {failed_days}/{total_days}")
        
        if successful_days == total_days:
            logger.info(f"✅ Backfilling completed successfully!")
        elif successful_days > 0:
            logger.warning(f"⚠️ Backfilling completed with some failures")
        else:
            logger.error(f"❌ Backfilling failed completely")
            raise Exception("Backfilling task failed - no successful days")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Airflow backfilling task failed: {e}")
        raise

def get_backfilling_status(**context):
    """Get backfilling status and configuration."""
    try:
        backfill_config = load_backfilling_config()
        
        logger.info(f"📊 Backfilling configuration status:")
        logger.info(f"   📅 Date range: {backfill_config['start_date']} to {backfill_config['end_date']}")
        logger.info(f"   📍 Location: {backfill_config['location']}")
        logger.info(f"   ⚙️ API delay: {backfill_config.get('api', {}).get('delay_between_requests', 1)}s")
        logger.info(f"   🔄 Max retries: {backfill_config.get('api', {}).get('max_retries', 3)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to get backfilling status: {e}")
        return False

# Airflow DAG definition
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'weather_finder',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'backfilling',
    default_args=default_args,
    description='Historic weather data backfilling for configured locations',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    max_active_runs=1,
)

# Tasks
status_task = PythonOperator(
    task_id='get_backfilling_status',
    python_callable=get_backfilling_status,
    dag=dag,
)

backfill_task = PythonOperator(
    task_id='backfill_historic_data',
    python_callable=airflow_backfill_task,
    dag=dag,
)

# Task dependencies
status_task >> backfill_task 