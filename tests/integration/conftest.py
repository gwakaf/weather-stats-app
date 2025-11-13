#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for integration tests
Fixtures defined here are automatically available to all integration test files.
"""

import sys
import os
import pytest

# Add project root to sys.path FIRST - this must happen before any imports
# that depend on the project structure
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope='session')
def flask_app():
    """Provides Flask test client for API endpoint testing"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(scope='session')
def test_config():
    """Supplies test-specific configuration (mock keys, URLs)"""
    return {
        'openweather_api_key': 'test-openweather-api-key',
        'openweather_base_url': 'https://api.openweathermap.org',
        'openmeteo_base_url': 'https://api.open-meteo.com',
        's3_bucket': 'test-weather-data-bucket',
        'athena_output_bucket': 'test-athena-output-bucket',
        'glue_database': 'test_weather_db',
        'glue_table': 'test_historic_weather',
        'athena_workgroup': 'test-workgroup',
        'aws_region': 'us-east-1'
    }


@pytest.fixture
def mock_openweather_api(mocker, test_config):
    """Mocks external HTTP calls to OpenWeather API"""
    import requests
    
    def mock_get(url, **kwargs):
        mock_response = mocker.Mock()
        if 'openweathermap.org' in url:
            if '/geo/1.0/direct' in url:
                # Geocoding API response
                mock_response.json.return_value = [{
                    'name': 'San Francisco',
                    'lat': 37.7749,
                    'lon': -122.4194,
                    'country': 'US',
                    'state': 'California'
                }]
            elif '/data/2.5/weather' in url:
                # Current weather API response
                mock_response.json.return_value = {
                    'main': {'temp': 288.15, 'humidity': 65},
                    'wind': {'speed': 4.2},
                    'weather': [{'main': 'Clear'}]
                }
        mock_response.raise_for_status = mocker.Mock()
        mock_response.status_code = 200
        return mock_response
    
    mocker.patch('requests.Session.get', side_effect=mock_get)
    mocker.patch('requests.get', side_effect=mock_get)
    
    return mock_get


@pytest.fixture(scope='session')
def aws_mocks(mocker):
    """Initializes mock AWS services (S3, Glue, Athena) via moto"""
    try:
        from moto import mock_s3, mock_athena, mock_glue
        
        # Start moto mocks
        s3_mock = mock_s3()
        athena_mock = mock_athena()
        glue_mock = mock_glue()
        
        s3_mock.start()
        athena_mock.start()
        glue_mock.start()
        
        yield {
            's3': s3_mock,
            'athena': athena_mock,
            'glue': glue_mock
        }
        
        # Cleanup
        s3_mock.stop()
        athena_mock.stop()
        glue_mock.stop()
        
    except ImportError:
        # If moto is not installed, use mocker to mock boto3 clients
        mock_s3_client = mocker.Mock()
        mock_athena_client = mocker.Mock()
        mock_glue_client = mocker.Mock()
        
        mocker.patch('boto3.client', side_effect=lambda service, **kwargs: {
            's3': mock_s3_client,
            'athena': mock_athena_client,
            'glue': mock_glue_client
        }.get(service))
        
        yield {
            's3': mock_s3_client,
            'athena': mock_athena_client,
            'glue': mock_glue_client
        }


@pytest.fixture
def s3_client(aws_mocks, test_config):
    """Creates and cleans up a mock S3 bucket for uploads/downloads"""
    import boto3
    
    s3 = boto3.client('s3', region_name=test_config['aws_region'])
    bucket_name = test_config['s3_bucket']
    
    # Create bucket if using moto
    try:
        s3.create_bucket(Bucket=bucket_name)
    except Exception:
        # Bucket might already exist or we're using mocks
        pass
    
    yield s3
    
    # Cleanup: delete all objects in bucket
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
    except Exception:
        # Cleanup might not be needed with mocks
        pass


@pytest.fixture
def s3_bucket(test_config):
    """Provides the S3 bucket name for tests"""
    return test_config['s3_bucket']


@pytest.fixture
def athena_client(aws_mocks, test_config):
    """Provides mocked AWS Athena client for querying/testing ETL flow"""
    import boto3
    
    athena = boto3.client('athena', region_name=test_config['aws_region'])
    return athena


@pytest.fixture
def glue_client(aws_mocks, test_config):
    """Provides mocked AWS Glue client for querying/testing ETL flow"""
    import boto3
    
    glue = boto3.client('glue', region_name=test_config['aws_region'])
    return glue


@pytest.fixture(scope='session')
def airflow_dag_env():
    """Optional: simulate Airflow DAG environment variables"""
    import os
    
    # Save original environment
    original_env = os.environ.copy()
    
    # Set Airflow-like environment variables
    os.environ['AIRFLOW_HOME'] = '/tmp/airflow'
    os.environ['AIRFLOW__CORE__DAGS_FOLDER'] = '/tmp/airflow/dags'
    os.environ['AIRFLOW__CORE__EXECUTOR'] = 'SequentialExecutor'
    os.environ['AIRFLOW__DATABASE__SQL_ALCHEMY_CONN'] = 'sqlite:////tmp/airflow/airflow.db'
    
    yield os.environ
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope='session')
def test_data_dir(tmp_path_factory):
    """Points to sample test data (e.g. JSON, CSV, or Parquet)"""
    # Create a temporary directory for test data
    test_dir = tmp_path_factory.mktemp('test_data')
    
    # Create sample test data files
    import pandas as pd
    import json
    
    # Sample JSON data
    sample_json = {
        'locations': [
            {'name': 'San Francisco, CA', 'lat': 37.7749, 'lon': -122.4194},
            {'name': 'Menlo Park, CA', 'lat': 37.4529, 'lon': -122.1817}
        ]
    }
    json_path = test_dir / 'locations.json'
    with open(json_path, 'w') as f:
        json.dump(sample_json, f)
    
    # Sample CSV data
    sample_df = pd.DataFrame({
        'location': ['San Francisco, CA'] * 3,
        'date': ['2024-01-15'] * 3,
        'hour': [0, 1, 2],
        'temperature_celsius': [15.0, 15.5, 16.0],
        'wind_speed_kmh': [10.0, 10.3, 10.6]
    })
    csv_path = test_dir / 'weather_data.csv'
    sample_df.to_csv(csv_path, index=False)
    
    # Sample Parquet data
    parquet_path = test_dir / 'weather_data.parquet'
    sample_df.to_parquet(parquet_path, index=False)
    
    yield test_dir
    
    # Cleanup is handled by tmp_path_factory

