#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures
Fixtures defined here are automatically available to all test files.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path FIRST - this must happen before any imports
# that depend on the project structure (like config.config)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def mock_infra_config():
    """Mock infrastructure configuration"""
    return {
        's3_bucket': 'test-weather-data',
        'athena_output_bucket': 'test-athena-output',
        'glue_database': 'test_weather_db',
        'glue_table': 'test_historic_weather',
        'athena_workgroup': 'test-workgroup'
    }


@pytest.fixture
def mock_locations_config():
    """Mock locations configuration"""
    return {
        'locations': [
            {
                'name': 'San Francisco, CA',
                'lat': 37.7749,
                'lon': -122.4194
            },
            {
                'name': 'Menlo Park, CA',
                'lat': 37.4529,
                'lon': -122.1817
            }
        ]
    }


@pytest.fixture
def mock_aws_clients():
    """Mock AWS boto3 clients"""
    s3_client = MagicMock()
    athena_client = MagicMock()
    glue_client = MagicMock()
    return {
        's3': s3_client,
        'athena': athena_client,
        'glue': glue_client
    }


@pytest.fixture
def app():
    """Create Flask app for testing"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture
def mock_weather_api(mocker):
    """Mock weather_api module"""
    return mocker.patch('app.routes.weather_api')


@pytest.fixture
def mock_aws_fetcher(mocker):
    """Mock aws_fetcher module"""
    return mocker.patch('app.routes.aws_fetcher')


@pytest.fixture
def setup_aws_mocks(mocker, mock_infra_config, mock_locations_config, mock_aws_clients):
    """Helper fixture to set up common AWS mocks for AWSDataFetcher tests"""
    mock_get_infra = mocker.patch('app.aws_fetching.get_infra_config')
    mock_get_locations = mocker.patch('app.aws_fetching.get_locations_config')
    mock_boto3 = mocker.patch('app.aws_fetching.boto3.client')
    
    mock_get_infra.return_value = mock_infra_config
    mock_get_locations.return_value = mock_locations_config
    mock_boto3.side_effect = lambda service, **kwargs: mock_aws_clients.get(service)
    
    return {
        'get_infra': mock_get_infra,
        'get_locations': mock_get_locations,
        'boto3': mock_boto3
    }


@pytest.fixture
def mock_openmeteo_current_response():
    """Mock Open-Meteo current weather response"""
    return {
        'current': {
            'time': '2024-01-15T12:00',
            'temperature_2m': 18.5,
            'wind_speed_10m': 15.0,
            'precipitation': 0.0,
            'cloud_cover': 30,
            'relative_humidity_2m': 65
        }
    }


@pytest.fixture
def mock_openmeteo_historical_response():
    """Mock Open-Meteo historical weather response"""
    # Generate 24 hours of data
    times = [f'2024-01-15T{i:02d}:00' for i in range(24)]
    temperatures = [15.0 + i * 0.5 for i in range(24)]
    wind_speeds = [10.0 + i * 0.3 for i in range(24)]
    precipitations = [0.0] * 24
    cloud_covers = [20 + i * 2 for i in range(24)]
    
    return {
        'hourly': {
            'time': times,
            'temperature_2m': temperatures,
            'wind_speed_10m': wind_speeds,
            'precipitation': precipitations,
            'cloud_cover': cloud_covers
        }
    }


@pytest.fixture
def mock_openweather_geocoding_response():
    """Mock OpenWeather geocoding API response"""
    return [
        {
            'name': 'San Francisco',
            'lat': 37.7749,
            'lon': -122.4194,
            'country': 'US',
            'state': 'California'
        }
    ]


@pytest.fixture
def mock_backfilling_config():
    """Mock backfilling configuration"""
    return {
        'start_date': '2024-01-01',
        'end_date': '2024-01-03',
        'location': 'San Francisco, CA',
        'api': {
            'delay_between_requests': 1,
            'max_retries': 3
        },
        'logging': {
            'level': 'INFO',
            'detailed_progress': True
        }
    }


@pytest.fixture
def mock_weather_data_24_hours():
    """Mock 24 hours of weather data for backfilling"""
    from datetime import datetime
    return [
        {
            'location': 'San Francisco, CA',
            'date': '2024-01-15',
            'hour': i,
            'temperature_celsius': 15.0 + i * 0.5,
            'wind_speed_kmh': 10.0 + i * 0.3,
            'precipitation_mm': 0.0,
            'cloud_coverage_percent': 20 + i * 2,
            'ingestion_timestamp': datetime.now().isoformat()
        }
        for i in range(24)
    ]


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for S3 writer tests"""
    import pandas as pd
    return pd.DataFrame({
        'location': ['San Francisco, CA'] * 3,
        'date': ['2024-01-15'] * 3,
        'hour': [0, 1, 2],
        'temperature_celsius': [15.0, 15.5, 16.0],
        'wind_speed_kmh': [10.0, 10.3, 10.6],
        'precipitation_mm': [0.0, 0.0, 0.0],
        'cloud_coverage_percent': [20, 22, 24]
    })

