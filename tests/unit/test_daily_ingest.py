#!/usr/bin/env python3
"""
Unit tests for Daily Ingestion Pipeline
Tests daily ingestion functions with mocked dependencies.
"""

import pytest
from datetime import datetime


class TestGetLocations:
    """Test get_locations function"""
    
    def test_get_locations_success(self, mocker, mock_locations_config):
        """Test successful location loading"""
        from pipelines.daily_ingest import get_locations
        
        # Mock the config module using pytest-mock
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_locations()
        
        assert len(result) == 2
        assert result[0]['name'] == 'San Francisco, CA'
        assert result[0]['lat'] == 37.7749
        assert result[1]['name'] == 'Menlo Park, CA'
    
    def test_get_locations_empty_config(self, mocker):
        """Test location loading when config is empty"""
        from pipelines.daily_ingest import get_locations
        
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = {'locations': []}
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_locations()
        
        assert result == []
    
    def test_get_locations_config_error(self, mocker):
        """Test location loading when config error occurs"""
        from pipelines.daily_ingest import get_locations
        
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.side_effect = Exception("Config error")
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_locations()
        
        assert result == []
    
    def test_get_locations_missing_locations_key(self, mocker):
        """Test location loading when locations key is missing"""
        from pipelines.daily_ingest import get_locations
        
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = {}
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_locations()
        
        assert result == []


class TestRunDailyIngestion:
    """Test run_daily_ingestion function"""
    
    def test_run_daily_ingestion_success(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test successful daily ingestion"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        # Mock datetime.now() to return a fixed date using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)  # This will make week_ago = 2024-01-15
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2  # 2 locations
        assert mock_save_to_s3.call_count == 2
    
    def test_run_daily_ingestion_no_locations(self, mocker):
        """Test daily ingestion when no locations are configured"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module with empty locations
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = {'locations': []}
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True  # Returns True even with no locations
    
    def test_run_daily_ingestion_weather_api_returns_none(self, mocker, mock_locations_config):
        """Test daily ingestion when weather API returns None"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI returning None
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = None
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True  # Still returns True even if some fail
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2
    
    def test_run_daily_ingestion_weather_api_returns_empty_list(self, mocker, mock_locations_config):
        """Test daily ingestion when weather API returns empty list"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI returning empty list
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = []
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2
    
    def test_run_daily_ingestion_s3_save_failure(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test daily ingestion when S3 save fails"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save returning False
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = False
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True  # Still returns True even if saves fail
        assert mock_save_to_s3.call_count == 2
    
    def test_run_daily_ingestion_partial_failure(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test daily ingestion with partial failures"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI - first location succeeds, second fails
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.side_effect = [
            mock_weather_data_24_hours,  # First location succeeds
            None  # Second location fails
        ]
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2
        assert mock_save_to_s3.call_count == 1  # Only called for first location
    
    def test_run_daily_ingestion_weather_api_exception(self, mocker, mock_locations_config):
        """Test daily ingestion when weather API raises exception"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI raising exception
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.side_effect = Exception("API Error")
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True  # Still returns True even with exceptions
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2
    
    def test_run_daily_ingestion_with_airflow_context(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test daily ingestion with Airflow context"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        # Airflow context
        airflow_context = {
            'ds': '2024-01-15',
            'dag': mocker.MagicMock(),
            'task': mocker.MagicMock()
        }
        
        result = run_daily_ingestion(**airflow_context)
        
        assert result is True
        assert mock_weather_api.get_historical_weather_all_hours.call_count == 2
    
    def test_run_daily_ingestion_date_calculation(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test that date is calculated correctly (1 week ago)"""
        from pipelines.daily_ingest import run_daily_ingestion
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Mock WeatherAPI
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        # Mock datetime - test with a specific date
        test_date = datetime(2024, 1, 22, 12, 0, 0)
        expected_week_ago = '2024-01-15'  # 7 days before Jan 22
        
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=test_date)
        
        result = run_daily_ingestion()
        
        assert result is True
        # Verify the date passed to get_historical_weather_all_hours is 1 week ago
        calls = mock_weather_api.get_historical_weather_all_hours.call_args_list
        for call in calls:
            assert call.kwargs['date'] == expected_week_ago
    
    def test_run_daily_ingestion_dataframe_columns_added(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test that location_name and ingestion_timestamp are added to DataFrame"""
        from pipelines.daily_ingest import run_daily_ingestion
        import pandas as pd
        
        # Mock config module
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        # Create weather data without location_name and ingestion_timestamp
        weather_data_without_metadata = [
            {
                'date': '2024-01-15',
                'hour': i,
                'temperature_celsius': 15.0 + i * 0.5,
                'wind_speed_kmh': 10.0 + i * 0.3,
                'precipitation_mm': 0.0,
                'cloud_coverage_percent': 20 + i * 2
            }
            for i in range(24)
        ]
        
        # Mock WeatherAPI
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = weather_data_without_metadata
        mocker.patch('pipelines.daily_ingest.WeatherAPI', return_value=mock_weather_api)
        
        # Mock S3 save and capture the DataFrame
        saved_dataframes = []
        def capture_df(df, location_name, date):
            saved_dataframes.append(df.copy())
            return True
        
        mock_save_to_s3 = mocker.patch('pipelines.daily_ingest.save_to_s3_parquet', side_effect=capture_df)
        
        # Mock datetime using pytest-mock
        mock_now = datetime(2024, 1, 22, 12, 0, 0)
        mocker.patch('pipelines.daily_ingest.datetime', wraps=datetime)
        mocker.patch('pipelines.daily_ingest.datetime.now', return_value=mock_now)
        
        result = run_daily_ingestion()
        
        assert result is True
        assert len(saved_dataframes) == 2  # 2 locations
        
        # Check that metadata columns were added
        for df in saved_dataframes:
            assert 'location_name' in df.columns
            assert 'ingestion_timestamp' in df.columns
            assert df['location_name'].isin(['San Francisco, CA', 'Menlo Park, CA']).all()
