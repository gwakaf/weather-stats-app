#!/usr/bin/env python3
"""
Unit tests for Weather API
Tests WeatherAPI class methods with mocked HTTP requests.
"""

import pytest
from datetime import datetime
import requests


class TestWeatherAPI:
    """Test class for WeatherAPI functionality"""
    
    def test_init_with_api_key(self, mocker):
        """Test WeatherAPI initialization with API key"""
        mocker.patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-api-key'})
        
        from app.weather_api import WeatherAPI
        
        api = WeatherAPI()
        assert api.api_key == 'test-api-key'
        assert api.base_url == "https://api.openweathermap.org/data/2.5/onecall/timemachine"
        assert api.current_url == "https://api.openweathermap.org/data/2.5/weather"
        assert api.geocoding_url == "https://api.openweathermap.org/geo/1.0/direct"
        assert api.session is not None
    
    def test_init_without_api_key(self, mocker):
        """Test WeatherAPI initialization without API key"""
        mocker.patch.dict('os.environ', {}, clear=True)
        
        from app.weather_api import WeatherAPI
        
        api = WeatherAPI()
        assert api.api_key is None
    
    def test_get_current_weather_success(self, mocker, mock_openmeteo_current_response):
        """Test successful current weather fetch"""
        from app.weather_api import WeatherAPI
        
        # Mock the session.get response
        mock_response = mocker.Mock()
        mock_response.json.return_value = mock_openmeteo_current_response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_current_weather(37.7749, -122.4194, 'San Francisco, CA')
        
        assert result is not None
        assert result['location'] == 'San Francisco, CA'
        assert result['temperature_celsius'] == 18.5
        assert result['wind_speed_kmh'] == 15.0
        assert result['precipitation_mm'] == 0.0
        assert result['cloud_coverage_percent'] == 30
        assert result['humidity'] == 65
        assert 'date' in result
        assert 'hour' in result
        assert 'timestamp' in result
        
        # Verify API was called correctly
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert 'https://api.open-meteo.com/v1/forecast' in call_args[0][0]
        assert call_args[1]['params']['latitude'] == 37.7749
        assert call_args[1]['params']['longitude'] == -122.4194
    
    def test_get_current_weather_without_location_name(self, mocker, mock_openmeteo_current_response):
        """Test current weather fetch without location name"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = mock_openmeteo_current_response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_current_weather(37.7749, -122.4194)
        
        assert result is not None
        assert result['location'] == '37.7749, -122.4194'
    
    def test_get_current_weather_api_error(self, mocker):
        """Test current weather fetch when API returns error"""
        from app.weather_api import WeatherAPI
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_current_weather(37.7749, -122.4194)
        
        assert result is None
    
    def test_get_current_weather_http_error(self, mocker):
        """Test current weather fetch when HTTP error occurs"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_current_weather(37.7749, -122.4194)
        
        assert result is None
    
    def test_get_historical_weather_success(self, mocker, mock_openmeteo_historical_response):
        """Test successful historical weather fetch"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = mock_openmeteo_historical_response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather(37.7749, -122.4194, '2024-01-15', '14:00')
        
        assert result is not None
        assert result['date'] == '2024-01-15'
        assert result['hour'] == 14
        assert result['temperature_celsius'] == 22.0  # 15.0 + 14 * 0.5
        assert result['wind_speed_kmh'] == 14.2  # 10.0 + 14 * 0.3
        assert result['precipitation_mm'] == 0.0
        assert result['cloud_coverage_percent'] == 48  # 20 + 14 * 2
        
        # Verify API was called correctly
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert 'https://archive-api.open-meteo.com/v1/archive' in call_args[0][0]
        assert call_args[1]['params']['start_date'] == '2024-01-15'
        assert call_args[1]['params']['end_date'] == '2024-01-15'
    
    def test_get_historical_weather_default_time(self, mocker, mock_openmeteo_historical_response):
        """Test historical weather fetch with default time (12:00)"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = mock_openmeteo_historical_response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather(37.7749, -122.4194, '2024-01-15')
        
        assert result is not None
        assert result['hour'] == 12
    
    def test_get_historical_weather_hour_not_found(self, mocker):
        """Test historical weather when target hour is not in response"""
        from app.weather_api import WeatherAPI
        
        # Mock response with no data
        mock_response = mocker.Mock()
        mock_response.json.return_value = {'hourly': {'time': []}}
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather(37.7749, -122.4194, '2024-01-15', '14:00')
        
        assert result is not None
        assert result['temperature_celsius'] is None
        assert result['wind_speed_kmh'] is None
    
    def test_get_historical_weather_api_error(self, mocker):
        """Test historical weather fetch when API returns error"""
        from app.weather_api import WeatherAPI
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather(37.7749, -122.4194, '2024-01-15', '14:00')
        
        assert result is None
    
    def test_get_historical_weather_all_hours_success(self, mocker, mock_openmeteo_historical_response):
        """Test successful historical weather fetch for all hours"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openmeteo_historical_response
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15', 'San Francisco, CA')
        
        assert result is not None
        assert len(result) == 24
        assert all(hour_data['date'] == '2024-01-15' for hour_data in result)
        assert all(hour_data['location'] == 'San Francisco, CA' for hour_data in result)
        assert all('hour' in hour_data for hour_data in result)
        assert all('temperature_celsius' in hour_data for hour_data in result)
        assert all('wind_speed_kmh' in hour_data for hour_data in result)
        assert all('precipitation_mm' in hour_data for hour_data in result)
        assert all('cloud_coverage_percent' in hour_data for hour_data in result)
        assert all('ingestion_timestamp' in hour_data for hour_data in result)
    
    def test_get_historical_weather_all_hours_rate_limit(self, mocker):
        """Test historical weather all hours with rate limit (429)"""
        from app.weather_api import WeatherAPI
        import time
        
        # First call returns 429, second call succeeds
        mock_response_429 = mocker.Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '1'}
        
        mock_response_200 = mocker.Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            'hourly': {
                'time': [f'2024-01-15T{i:02d}:00' for i in range(24)],
                'temperature_2m': [20.0] * 24,
                'wind_speed_10m': [10.0] * 24,
                'precipitation': [0.0] * 24,
                'cloud_cover': [30] * 24
            }
        }
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = [mock_response_429, mock_response_200]
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        # Mock time.sleep to speed up test
        mocker.patch('app.weather_api.time.sleep')
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15', max_retries=2)
        
        assert result is not None
        assert len(result) == 24
        assert mock_session.get.call_count == 2
    
    def test_get_historical_weather_all_hours_server_error_retry(self, mocker):
        """Test historical weather all hours with server error and retry"""
        from app.weather_api import WeatherAPI
        
        # First call returns 500, second call succeeds
        mock_response_500 = mocker.Mock()
        mock_response_500.status_code = 500
        
        mock_response_200 = mocker.Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            'hourly': {
                'time': [f'2024-01-15T{i:02d}:00' for i in range(24)],
                'temperature_2m': [20.0] * 24,
                'wind_speed_10m': [10.0] * 24,
                'precipitation': [0.0] * 24,
                'cloud_cover': [30] * 24
            }
        }
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = [mock_response_500, mock_response_200]
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        # Mock time.sleep to speed up test
        mocker.patch('app.weather_api.time.sleep')
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15', max_retries=2)
        
        assert result is not None
        assert len(result) == 24
        assert mock_session.get.call_count == 2
    
    def test_get_historical_weather_all_hours_timeout_retry(self, mocker):
        """Test historical weather all hours with timeout and retry"""
        from app.weather_api import WeatherAPI
        from requests.exceptions import Timeout
        
        # First call times out, second call succeeds
        mock_response_200 = mocker.Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            'hourly': {
                'time': [f'2024-01-15T{i:02d}:00' for i in range(24)],
                'temperature_2m': [20.0] * 24,
                'wind_speed_10m': [10.0] * 24,
                'precipitation': [0.0] * 24,
                'cloud_cover': [30] * 24
            }
        }
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = [Timeout("Request timeout"), mock_response_200]
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        # Mock time.sleep to speed up test
        mocker.patch('app.weather_api.time.sleep')
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15', max_retries=2)
        
        assert result is not None
        assert len(result) == 24
        assert mock_session.get.call_count == 2
    
    def test_get_historical_weather_all_hours_no_data(self, mocker):
        """Test historical weather all hours when no data is returned"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'hourly': {
                'time': []
            }
        }
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15')
        
        assert result is None
    
    def test_get_historical_weather_all_hours_invalid_response_structure(self, mocker):
        """Test historical weather all hours with invalid response structure"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing 'hourly' key
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15')
        
        assert result is None
    
    def test_get_historical_weather_all_hours_max_retries_exceeded(self, mocker):
        """Test historical weather all hours when max retries exceeded"""
        from app.weather_api import WeatherAPI
        
        mock_response = mocker.Mock()
        mock_response.status_code = 500
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        # Mock time.sleep to speed up test
        mocker.patch('app.weather_api.time.sleep')
        
        result = api.get_historical_weather_all_hours(37.7749, -122.4194, '2024-01-15', max_retries=2)
        
        assert result is None
        assert mock_session.get.call_count == 2
    
    def test_get_coordinates_by_name_success(self, mocker, mock_openweather_geocoding_response):
        """Test successful geocoding by location name"""
        from app.weather_api import WeatherAPI
        
        mocker.patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-api-key'})
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = mock_openweather_geocoding_response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_coordinates_by_name('San Francisco, CA')
        
        assert result is not None
        assert result['name'] == 'San Francisco'
        assert result['lat'] == 37.7749
        assert result['lon'] == -122.4194
        assert result['country'] == 'US'
        assert result['state'] == 'California'
        
        # Verify API was called correctly
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert 'https://api.openweathermap.org/geo/1.0/direct' in call_args[0][0]
        assert call_args[1]['params']['q'] == 'San Francisco, CA'
        assert call_args[1]['params']['appid'] == 'test-api-key'
    
    def test_get_coordinates_by_name_no_api_key(self, mocker):
        """Test geocoding without API key"""
        from app.weather_api import WeatherAPI
        
        mocker.patch.dict('os.environ', {}, clear=True)
        
        api = WeatherAPI()
        
        result = api.get_coordinates_by_name('San Francisco, CA')
        
        assert result is None
    
    def test_get_coordinates_by_name_not_found(self, mocker):
        """Test geocoding when location not found"""
        from app.weather_api import WeatherAPI
        
        mocker.patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-api-key'})
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = []  # Empty response
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_coordinates_by_name('NonExistentCity, XX')
        
        assert result is None
    
    def test_get_coordinates_by_name_api_error(self, mocker):
        """Test geocoding when API returns error"""
        from app.weather_api import WeatherAPI
        
        mocker.patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-api-key'})
        
        mock_session = mocker.Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_coordinates_by_name('San Francisco, CA')
        
        assert result is None
    
    def test_get_coordinates_by_name_with_limit(self, mocker):
        """Test geocoding with custom limit parameter"""
        from app.weather_api import WeatherAPI
        
        mocker.patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-api-key'})
        
        mock_response = mocker.Mock()
        mock_response.json.return_value = [
            {'name': 'San Francisco', 'lat': 37.7749, 'lon': -122.4194, 'country': 'US', 'state': 'California'},
            {'name': 'San Francisco', 'lat': 40.7128, 'lon': -74.0060, 'country': 'US', 'state': 'New York'}
        ]
        mock_response.raise_for_status = mocker.Mock()
        
        mock_session = mocker.Mock()
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        api = WeatherAPI()
        api.session = mock_session
        
        result = api.get_coordinates_by_name('San Francisco', limit=2)
        
        assert result is not None
        assert result['name'] == 'San Francisco'
        # Verify limit parameter was passed
        call_args = mock_session.get.call_args
        assert call_args[1]['params']['limit'] == 2


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility"""
    
    def test_get_current_temperature(self, mocker):
        """Test get_current_temperature convenience function"""
        from app.weather_api import get_current_temperature
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_current_weather.return_value = {
            'temperature_celsius': 18.5
        }
        
        result = get_current_temperature(37.7749, -122.4194, 'San Francisco, CA')
        
        assert result == 18.5
    
    def test_get_current_temperature_none(self, mocker):
        """Test get_current_temperature when weather API returns None"""
        from app.weather_api import get_current_temperature
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_current_weather.return_value = None
        
        result = get_current_temperature(37.7749, -122.4194)
        
        assert result is None
    
    def test_get_current_wind_speed(self, mocker):
        """Test get_current_wind_speed convenience function"""
        from app.weather_api import get_current_wind_speed
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_current_weather.return_value = {
            'wind_speed_kmh': 15.0
        }
        
        result = get_current_wind_speed(37.7749, -122.4194)
        
        assert result == 15.0
    
    def test_get_current_precipitation(self, mocker):
        """Test get_current_precipitation convenience function"""
        from app.weather_api import get_current_precipitation
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_current_weather.return_value = {
            'precipitation_mm': 5.0
        }
        
        result = get_current_precipitation(37.7749, -122.4194)
        
        assert result == 5.0
    
    def test_get_current_cloud_coverage(self, mocker):
        """Test get_current_cloud_coverage convenience function"""
        from app.weather_api import get_current_cloud_coverage
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_current_weather.return_value = {
            'cloud_coverage_percent': 30
        }
        
        result = get_current_cloud_coverage(37.7749, -122.4194)
        
        assert result == 30
    
    def test_get_historical_temperature_openmeteo(self, mocker):
        """Test get_historical_temperature_openmeteo convenience function"""
        from app.weather_api import get_historical_temperature_openmeteo
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_historical_weather.return_value = {
            'temperature_celsius': 18.5
        }
        
        result = get_historical_temperature_openmeteo(37.7749, -122.4194, '2024-01-15', '14:00')
        
        assert result == 18.5
    
    def test_get_historical_wind_openmeteo(self, mocker):
        """Test get_historical_wind_openmeteo convenience function"""
        from app.weather_api import get_historical_wind_openmeteo
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_historical_weather.return_value = {
            'wind_speed_kmh': 12.3
        }
        
        result = get_historical_wind_openmeteo(37.7749, -122.4194, '2024-01-15')
        
        assert result == 12.3
    
    def test_get_historical_precipitation_openmeteo(self, mocker):
        """Test get_historical_precipitation_openmeteo convenience function"""
        from app.weather_api import get_historical_precipitation_openmeteo
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_historical_weather.return_value = {
            'precipitation_mm': 5.0
        }
        
        result = get_historical_precipitation_openmeteo(37.7749, -122.4194, '2024-01-15')
        
        assert result == 5.0
    
    def test_get_historical_cloud_coverage_openmeteo(self, mocker):
        """Test get_historical_cloud_coverage_openmeteo convenience function"""
        from app.weather_api import get_historical_cloud_coverage_openmeteo
        
        mock_api = mocker.patch('app.weather_api.weather_api')
        mock_api.get_historical_weather.return_value = {
            'cloud_coverage_percent': 50
        }
        
        result = get_historical_cloud_coverage_openmeteo(37.7749, -122.4194, '2024-01-15')
        
        assert result == 50
