#!/usr/bin/env python3
"""
Unit tests for Flask Routes
Tests all API endpoints with mocked dependencies.
"""

import pytest
import json


class TestIndexRoute:
    """Test the index route"""
    
    def test_index_route(self, client):
        """Test that index route renders the template"""
        response = client.get('/')
        assert response.status_code == 200


class TestCurrentWeatherRoute:
    """Test /api/current_weather POST endpoint"""
    
    def test_get_current_weather_success(self, client, mock_weather_api):
        """Test successful current weather fetch"""
        mock_weather_data = {
            'temperature_celsius': 20.5,
            'wind_speed_kmh': 15.0,
            'precipitation_mm': 0.0,
            'cloud_coverage_percent': 30,
            'humidity': 65,
            'timestamp': '2024-01-15T12:00:00'
        }
        mock_weather_api.get_current_weather.return_value = mock_weather_data
        
        response = client.post('/api/current_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194, 'location_name': 'San Francisco'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['temperature'] == 20.5
        mock_weather_api.get_current_weather.assert_called_once_with(37.7749, -122.4194, 'San Francisco')
    
    def test_get_current_weather_no_json(self, client):
        """Test current weather with no JSON data"""
        response = client.post('/api/current_weather')
        
        assert response.status_code == 500  # 415 error from Flask becomes 500 in exception handler
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No JSON data provided' in data['error'] or 'Unsupported Media Type' in data['error']
    
    def test_get_current_weather_invalid_coordinates(self, client):
        """Test current weather with invalid coordinates"""
        response = client.post('/api/current_weather', 
                              json={'lat': 200, 'lon': 300})  # Invalid coordinates
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid coordinates' in data['error']
    
    def test_get_current_weather_api_failure(self, client, mock_weather_api):
        """Test current weather when API returns None"""
        mock_weather_api.get_current_weather.return_value = None
        
        response = client.post('/api/current_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194})
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to fetch current weather' in data['error']
    
    def test_get_current_weather_exception(self, client, mock_weather_api):
        """Test current weather when exception occurs"""
        mock_weather_api.get_current_weather.side_effect = Exception("API Error")
        
        response = client.post('/api/current_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194})
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False


class TestHistoricWeatherRoute:
    """Test /api/historic_weather POST endpoint"""
    
    def test_get_historic_weather_success(self, client, mock_weather_api):
        """Test successful historic weather fetch"""
        mock_weather_data = {
            'temperature_celsius': 18.5,
            'wind_speed_kmh': 12.3,
            'precipitation_mm': 5.0,
            'cloud_coverage_percent': 50,
            'date': '2024-01-15',
            'hour': 14
        }
        mock_weather_api.get_historical_weather.return_value = mock_weather_data
        
        response = client.post('/api/historic_weather', 
                              json={
                                  'lat': 37.7749,
                                  'lon': -122.4194,
                                  'date': '2024-01-15',
                                  'time': '14:00',
                                  'location_name': 'San Francisco'
                              })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['temperature'] == 18.5
        mock_weather_api.get_historical_weather.assert_called_once_with(37.7749, -122.4194, '2024-01-15', '14:00')
    
    def test_get_historic_weather_no_json(self, client):
        """Test historic weather with no JSON data"""
        response = client.post('/api/historic_weather')
        
        assert response.status_code == 500  # 415 error from Flask becomes 500 in exception handler
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No JSON data provided' in data['error'] or 'Unsupported Media Type' in data['error']
    
    def test_get_historic_weather_invalid_coordinates(self, client):
        """Test historic weather with invalid coordinates"""
        response = client.post('/api/historic_weather', 
                              json={'lat': 200, 'lon': 300, 'date': '2024-01-15'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid coordinates' in data['error']
    
    def test_get_historic_weather_missing_date(self, client):
        """Test historic weather with missing date"""
        response = client.post('/api/historic_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Date is required' in data['error']
    
    def test_get_historic_weather_invalid_date_format(self, client):
        """Test historic weather with invalid date format"""
        response = client.post('/api/historic_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194, 'date': '01-15-2024'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid date format' in data['error']
    
    def test_get_historic_weather_invalid_time_format(self, client):
        """Test historic weather with invalid time format"""
        response = client.post('/api/historic_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194, 'date': '2024-01-15', 'time': '25:00'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid time format' in data['error']
    
    def test_get_historic_weather_api_failure(self, client, mock_weather_api):
        """Test historic weather when API returns None"""
        mock_weather_api.get_historical_weather.return_value = None
        
        response = client.post('/api/historic_weather', 
                              json={'lat': 37.7749, 'lon': -122.4194, 'date': '2024-01-15'})
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to fetch historical weather data' in data['error']


class TestPredefinedLocationsRoute:
    """Test /api/predefined_locations GET endpoint"""
    
    def test_get_predefined_locations_success(self, client, mock_aws_fetcher):
        """Test successful predefined locations fetch"""
        mock_locations = ['San Francisco, CA', 'Menlo Park, CA', 'Walnut Creek, CA']
        mock_aws_fetcher.get_available_locations.return_value = mock_locations
        
        response = client.get('/api/predefined_locations')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['count'] == 3
        assert len(data['data']['locations']) == 3
    
    def test_get_predefined_locations_exception(self, client, mock_aws_fetcher):
        """Test predefined locations when exception occurs"""
        mock_aws_fetcher.get_available_locations.side_effect = Exception("AWS Error")
        
        response = client.get('/api/predefined_locations')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False


class TestLocationsRoute:
    """Test /api/locations GET endpoint"""
    
    def test_get_locations_success(self, client, mock_aws_fetcher):
        """Test successful locations fetch with coordinates"""
        mock_locations = ['San Francisco, CA', 'Menlo Park, CA']
        mock_aws_fetcher.get_available_locations.return_value = mock_locations
        mock_aws_fetcher.get_location_coordinates.side_effect = [
            {'lat': 37.7749, 'lon': -122.4194},
            {'lat': 37.4529, 'lon': -122.1817}
        ]
        
        response = client.get('/api/locations')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['locations']) == 2
        assert 'location_data' in data
        assert data['count'] == 2
    
    def test_get_locations_exception(self, client, mock_aws_fetcher):
        """Test locations when exception occurs"""
        mock_aws_fetcher.get_available_locations.side_effect = Exception("AWS Error")
        
        response = client.get('/api/locations')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False


class TestWeatherPredefinedRoute:
    """Test /api/weather-predefined GET endpoint"""
    
    def test_get_weather_predefined_current_success(self, client, mock_aws_fetcher, mock_weather_api):
        """Test successful current weather for predefined location"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        mock_weather_data = {
            'temperature_celsius': 20.5,
            'wind_speed_kmh': 15.0,
            'precipitation_mm': 0.0,
            'cloud_coverage_percent': 30
        }
        mock_weather_api.get_current_weather.return_value = mock_weather_data
        
        response = client.get('/api/weather-predefined?location=San Francisco, CA')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'weather' in data
        assert data['location'] == 'San Francisco, CA'
        assert 'data_source' in data
    
    def test_get_weather_predefined_historic_success(self, client, mock_aws_fetcher, mock_weather_api):
        """Test successful historic weather for predefined location"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        mock_weather_data = {
            'temperature_celsius': 18.5,
            'wind_speed_kmh': 12.3,
            'precipitation_mm': 5.0,
            'cloud_coverage_percent': 50,
            'date': '2024-01-15',
            'hour': 14
        }
        mock_weather_api.get_historical_weather.return_value = mock_weather_data
        
        response = client.get('/api/weather-predefined?location=San Francisco, CA&date=2024-01-15&time=14:00')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['date'] == '2024-01-15'
        assert data['time'] == '14:00'
        mock_weather_api.get_historical_weather.assert_called_once_with(37.7749, -122.4194, '2024-01-15', '14:00')
    
    def test_get_weather_predefined_missing_location(self, client):
        """Test weather predefined with missing location parameter"""
        response = client.get('/api/weather-predefined')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Location parameter is required' in data['error']
    
    def test_get_weather_predefined_location_not_found(self, client, mock_aws_fetcher):
        """Test weather predefined with non-existent location"""
        mock_aws_fetcher.get_location_coordinates.return_value = None
        
        response = client.get('/api/weather-predefined?location=Unknown City')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "not found" in data['error'].lower()
    
    def test_get_weather_predefined_invalid_date_format(self, client, mock_aws_fetcher):
        """Test weather predefined with invalid date format"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        
        response = client.get('/api/weather-predefined?location=San Francisco, CA&date=01-15-2024')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid date format' in data['error']
    
    def test_get_weather_predefined_invalid_time_format(self, client, mock_aws_fetcher):
        """Test weather predefined with invalid time format"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        
        response = client.get('/api/weather-predefined?location=San Francisco, CA&date=2024-01-15&time=25:00')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid time format' in data['error']
    
    def test_get_weather_predefined_api_failure(self, client, mock_aws_fetcher, mock_weather_api):
        """Test weather predefined when API returns None"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        mock_weather_api.get_current_weather.return_value = None
        
        response = client.get('/api/weather-predefined?location=San Francisco, CA')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to fetch current weather' in data['error']


class TestTemperatureGraphPredefinedRoute:
    """Test /api/temperature-graph-predefined GET endpoint"""
    
    def test_get_temperature_graph_predefined_success(self, mocker, client, mock_aws_fetcher, mock_weather_api):
        """Test successful temperature graph generation"""
        mock_generate_graphs = mocker.patch('app.utils.graph_generator.generate_historical_graphs')
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        
        # Mock AWS data for some years
        mock_aws_data = [{
            'location': 'San_Francisco_CA',
            'date': '2023-01-15',
            'hour': 13,
            'temperature_celsius': 18.5,
            'wind_speed_kmh': 12.3,
            'precipitation_mm': 5.0,
            'cloud_coverage_percent': 50
        }]
        mock_aws_fetcher.query_historic_data.side_effect = [
            mock_aws_data if i < 3 else []  # AWS data for first 3 years, then empty
            for i in range(10)
        ]
        
        # Mock Open-Meteo data for remaining years
        mock_meteo_data = {
            'temperature_celsius': 20.0,
            'wind_speed_kmh': 15.0,
            'precipitation_mm': 0.0,
            'cloud_coverage_percent': 30
        }
        mock_weather_api.get_historical_weather.return_value = mock_meteo_data
        
        # Mock graph generation
        mock_graphs = {
            'temperature_graph': 'base64_encoded_image',
            'wind_graph': 'base64_encoded_image',
            'precipitation_graph': 'base64_encoded_image',
            'cloud_coverage_graph': 'base64_encoded_image',
            'stats': {
                'temperature': {'min': 15.0, 'max': 25.0, 'avg': 20.0},
                'wind': {'min': 5.0, 'max': 20.0, 'avg': 12.0}
            }
        }
        mock_generate_graphs.return_value = mock_graphs
        
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA&date=2024-01-15&time=13:00')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'graph_data' in data
        assert 'data_source' in data
        assert data['years_count'] > 0
    
    def test_get_temperature_graph_predefined_missing_location(self, client):
        """Test temperature graph with missing location parameter"""
        response = client.get('/api/temperature-graph-predefined?date=2024-01-15')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Location parameter is required' in data['error']
    
    def test_get_temperature_graph_predefined_missing_date(self, client):
        """Test temperature graph with missing date parameter"""
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Date parameter is required' in data['error']
    
    def test_get_temperature_graph_predefined_location_not_found(self, client, mock_aws_fetcher):
        """Test temperature graph with non-existent location"""
        mock_aws_fetcher.get_location_coordinates.return_value = None
        
        response = client.get('/api/temperature-graph-predefined?location=Unknown City&date=2024-01-15')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "not found" in data['error'].lower()
    
    def test_get_temperature_graph_predefined_invalid_date_format(self, client, mock_aws_fetcher):
        """Test temperature graph with invalid date format"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA&date=01-15-2024')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid date format' in data['error']
    
    def test_get_temperature_graph_predefined_invalid_time_format(self, client, mock_aws_fetcher):
        """Test temperature graph with invalid time format"""
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA&date=2024-01-15&time=25:00')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid time format' in data['error']
    
    def test_get_temperature_graph_predefined_no_data(self, mocker, client, mock_aws_fetcher, mock_weather_api):
        """Test temperature graph when no historical data is available"""
        mock_generate_graphs = mocker.patch('app.utils.graph_generator.generate_historical_graphs')
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        mock_aws_fetcher.query_historic_data.return_value = []
        mock_weather_api.get_historical_weather.return_value = None
        
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA&date=2024-01-15&time=13:00')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No historical data available' in data['error']
    
    def test_get_temperature_graph_predefined_graph_generation_failure(self, mocker, client, mock_aws_fetcher, mock_weather_api):
        """Test temperature graph when graph generation fails"""
        mock_generate_graphs = mocker.patch('app.utils.graph_generator.generate_historical_graphs')
        mock_aws_fetcher.get_location_coordinates.return_value = {'lat': 37.7749, 'lon': -122.4194}
        mock_aws_fetcher.query_historic_data.return_value = [{
            'temperature_celsius': 18.5,
            'wind_speed_kmh': 12.3,
            'precipitation_mm': 5.0,
            'cloud_coverage_percent': 50
        }]
        mock_generate_graphs.return_value = {}
        
        response = client.get('/api/temperature-graph-predefined?location=San Francisco, CA&date=2024-01-15&time=13:00')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to generate graphs' in data['error']


class TestHealthCheckRoute:
    """Test /api/health GET endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert data['version'] == '1.0.0'
