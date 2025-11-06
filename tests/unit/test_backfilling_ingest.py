#!/usr/bin/env python3
"""
Unit tests for Backfilling Ingestion Pipeline
Tests backfilling functions with mocked dependencies.
"""

import pytest
from unittest.mock import mock_open
from datetime import datetime
import os


class TestLoadBackfillingConfig:
    """Test load_backfilling_config function"""
    
    def test_load_backfilling_config_success(self, mocker, mock_backfilling_config):
        """Test successful loading of backfilling config"""
        from pipelines.backfilling_ingest import load_backfilling_config
        
        # Mock file exists and content
        mock_file_content = """
start_date: '2024-01-01'
end_date: '2024-01-03'
location: 'San Francisco, CA'
api:
  delay_between_requests: 1
  max_retries: 3
logging:
  level: 'INFO'
  detailed_progress: true
"""
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data=mock_file_content))
        
        config = load_backfilling_config()
        
        assert config is not None
        assert config['start_date'] == '2024-01-01'
        assert config['end_date'] == '2024-01-03'
        assert config['location'] == 'San Francisco, CA'
        assert config['api']['delay_between_requests'] == 1
    
    def test_load_backfilling_config_not_found(self, mocker):
        """Test loading config when file not found"""
        from pipelines.backfilling_ingest import load_backfilling_config
        
        # Mock file doesn't exist
        mocker.patch('os.path.exists', return_value=False)
        
        config = load_backfilling_config()
        
        # Should return default config
        assert config is not None
        assert 'start_date' in config
        assert 'end_date' in config
        assert 'location' in config
    
    def test_load_backfilling_config_invalid_yaml(self, mocker):
        """Test loading config with invalid YAML"""
        from pipelines.backfilling_ingest import load_backfilling_config
        
        # Mock file exists but has invalid YAML
        mock_file_content = "invalid: yaml: content: ["
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data=mock_file_content))
        
        config = load_backfilling_config()
        
        # Should return default config on error
        assert config is not None
        assert 'start_date' in config


class TestGetLocationCoordinates:
    """Test get_location_coordinates function"""
    
    def test_get_location_coordinates_success(self, mocker, mock_locations_config):
        """Test successful location coordinate retrieval"""
        from pipelines.backfilling_ingest import get_location_coordinates
        
        # Mock the config module using pytest-mock - patch it in sys.modules
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_location_coordinates('San Francisco, CA')
        
        assert result is not None
        assert result['lat'] == 37.7749
        assert result['lon'] == -122.4194
        assert result['name'] == 'San Francisco, CA'
    
    def test_get_location_coordinates_not_found(self, mocker, mock_locations_config):
        """Test location coordinate retrieval when location not found"""
        from pipelines.backfilling_ingest import get_location_coordinates
        
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_location_coordinates('Non-existent Location')
        
        assert result is None
    
    def test_get_location_coordinates_config_error(self, mocker):
        """Test location coordinate retrieval when config error occurs"""
        from pipelines.backfilling_ingest import get_location_coordinates
        
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.side_effect = Exception("Config error")
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        result = get_location_coordinates('San Francisco, CA')
        
        assert result is None


class TestBackfillHistoricWeather:
    """Test backfill_historic_weather function"""
    
    def test_backfill_historic_weather_success(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test successful backfilling of historic weather"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        # Mock dependencies - create mock config module for dynamic import
        mock_config_module = mocker.MagicMock()
        mock_config_module.get_locations_config.return_value = mock_locations_config
        mocker.patch.dict('sys.modules', {'config': mock_config_module})
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        # Mock time.sleep to speed up tests
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-16', 'San Francisco, CA', save_to_s3=True
        )
        
        assert successful == 2  # 2 days
        assert total == 2
        assert failed == 0
        assert mock_save_to_s3.call_count == 2
    
    def test_backfill_historic_weather_no_s3(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test backfilling without saving to S3"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'San Francisco, CA', save_to_s3=False
        )
        
        assert successful == 1
        assert total == 1
        assert failed == 0
        mock_save_to_s3.assert_not_called()
    
    def test_backfill_historic_weather_location_not_found(self, mocker):
        """Test backfilling when location not found"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = {'locations': []}
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'Non-existent Location'
        )
        
        assert successful == 0
        assert total == 0
        assert failed == 0
    
    def test_backfill_historic_weather_invalid_date_format(self, mocker, mock_locations_config):
        """Test backfilling with invalid date format"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        successful, total, failed = backfill_historic_weather(
            'invalid-date', '2024-01-15', 'San Francisco, CA'
        )
        
        assert successful == 0
        assert total == 0
        assert failed == 0
    
    def test_backfill_historic_weather_no_data(self, mocker, mock_locations_config):
        """Test backfilling when no weather data is available"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = None
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'San Francisco, CA'
        )
        
        assert successful == 0
        assert total == 1
        assert failed == 1
    
    def test_backfill_historic_weather_empty_data(self, mocker, mock_locations_config):
        """Test backfilling when weather API returns empty list"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = []
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'San Francisco, CA'
        )
        
        assert successful == 0
        assert total == 1
        assert failed == 1
    
    def test_backfill_historic_weather_s3_save_failure(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test backfilling when S3 save fails"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = False
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'San Francisco, CA', save_to_s3=True
        )
        
        assert successful == 0
        assert total == 1
        assert failed == 1
    
    def test_backfill_historic_weather_api_exception(self, mocker, mock_locations_config):
        """Test backfilling when weather API raises exception"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.side_effect = Exception("API Error")
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-15', 'San Francisco, CA'
        )
        
        assert successful == 0
        assert total == 1
        assert failed == 1
    
    def test_backfill_historic_weather_multiple_days(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test backfilling multiple days"""
        from pipelines.backfilling_ingest import backfill_historic_weather
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        successful, total, failed = backfill_historic_weather(
            '2024-01-15', '2024-01-17', 'San Francisco, CA', save_to_s3=True
        )
        
        assert successful == 3  # 3 days
        assert total == 3
        assert failed == 0
        assert mock_save_to_s3.call_count == 3


class TestBackfillMultipleLocations:
    """Test backfill_multiple_locations function"""
    
    def test_backfill_multiple_locations_success(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test successful backfilling for multiple locations"""
        from pipelines.backfilling_ingest import backfill_multiple_locations
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        locations = ['San Francisco, CA', 'Menlo Park, CA']
        results = backfill_multiple_locations(
            '2024-01-15', '2024-01-15', locations, save_to_s3=True
        )
        
        assert len(results) == 2
        assert 'San Francisco, CA' in results
        assert 'Menlo Park, CA' in results
        assert results['San Francisco, CA']['successful_days'] == 1
        assert results['Menlo Park, CA']['successful_days'] == 1
    
    def test_backfill_multiple_locations_partial_failure(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test backfilling multiple locations with some failures"""
        from pipelines.backfilling_ingest import backfill_multiple_locations
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        # First location exists, second doesn't
        mock_get_locations.return_value = {
            'locations': [mock_locations_config['locations'][0]]
        }
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        mock_save_to_s3.return_value = True
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        locations = ['San Francisco, CA', 'Non-existent Location']
        results = backfill_multiple_locations(
            '2024-01-15', '2024-01-15', locations, save_to_s3=True
        )
        
        assert len(results) == 2
        assert results['San Francisco, CA']['successful_days'] == 1
        assert results['Non-existent Location']['successful_days'] == 0
    
    def test_backfill_multiple_locations_empty_list(self, mocker):
        """Test backfilling with empty locations list"""
        from pipelines.backfilling_ingest import backfill_multiple_locations
        
        results = backfill_multiple_locations(
            '2024-01-15', '2024-01-15', [], save_to_s3=True
        )
        
        assert results == {}
    
    def test_backfill_multiple_locations_no_s3(self, mocker, mock_locations_config, mock_weather_data_24_hours):
        """Test backfilling multiple locations without saving to S3"""
        from pipelines.backfilling_ingest import backfill_multiple_locations
        
        mock_get_locations = mocker.patch('config.get_locations_config')
        mock_get_locations.return_value = mock_locations_config
        
        mock_weather_api = mocker.Mock()
        mock_weather_api.get_historical_weather_all_hours.return_value = mock_weather_data_24_hours
        mocker.patch('pipelines.backfilling_ingest.WeatherAPI', return_value=mock_weather_api)
        
        mock_save_to_s3 = mocker.patch('pipelines.backfilling_ingest.save_to_s3_parquet')
        
        mock_load_config = mocker.patch('pipelines.backfilling_ingest.load_backfilling_config')
        mock_load_config.return_value = {
            'api': {'delay_between_requests': 0, 'max_retries': 3}
        }
        
        mocker.patch('pipelines.backfilling_ingest.time.sleep')
        
        locations = ['San Francisco, CA']
        results = backfill_multiple_locations(
            '2024-01-15', '2024-01-15', locations, save_to_s3=False
        )
        
        assert len(results) == 1
        assert results['San Francisco, CA']['successful_days'] == 1
        mock_save_to_s3.assert_not_called()
