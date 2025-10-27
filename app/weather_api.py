#!/usr/bin/env python3
"""
Weather API Handler for Weather Finder
Provides functions for fetching weather data from OpenWeather API.
Used by both web interface and daily ingestion DAG.
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time
import os

logger = logging.getLogger(__name__)

class WeatherAPI:
    """Weather API handler for multiple weather services
    
    - Current weather: OpenWeather API (requires API key)
    - Historical weather: Open-Meteo API (free, no API key required)
    """
    
    def __init__(self):
        self.base_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine"
        self.current_url = "https://api.openweathermap.org/data/2.5/weather"
        self.geocoding_url = "https://api.openweathermap.org/geo/1.0/direct"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WeatherFinder/1.0 (https://github.com/weather-finder)'
        })
        # Get API key from environment
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            logger.warning("No OpenWeather API key found in environment variables (required for geocoding only)")
    
    def get_current_weather(self, lat: float, lon: float, location_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get current weather data for a location using Open-Meteo Forecast API (free!)
        No API key required - uses Open-Meteo instead of OpenWeather for current weather
        """
        try:
            # Use Open-Meteo Forecast API for current weather (free, no API key needed)
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,wind_speed_10m,precipitation,cloud_cover,relative_humidity_2m',
                'timezone': 'auto'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            current = data.get('current', {})
            
            # Extract and format the data to match our standard format
            current_weather = {
                'location': location_name or f"{lat}, {lon}",
                'timestamp': current.get('time', datetime.now().isoformat()),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'hour': datetime.now().hour,
                'temperature_celsius': current.get('temperature_2m'),
                'wind_speed_kmh': current.get('wind_speed_10m'),
                'precipitation_mm': current.get('precipitation', 0),
                'cloud_coverage_percent': current.get('cloud_cover'),
                'humidity': current.get('relative_humidity_2m')
            }
            
            logger.info(f"Retrieved current weather for {current_weather['location']} from Open-Meteo")
            return current_weather
            
        except Exception as e:
            logger.error(f"Error fetching current weather for {location_name or f'{lat}, {lon}'}: {e}")
            return None
    
    def get_historical_weather(self, lat: float, lon: float, date: str, time: str = "12:00") -> Optional[Dict[str, Any]]:
        """Get historical weather data for a specific date and time using Open-Meteo API (free)"""
        try:
            # Use Open-Meteo API for historical data (free)
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                'latitude': lat,
                'longitude': lon,
                'start_date': date,
                'end_date': date,
                'hourly': 'temperature_2m,wind_speed_10m,precipitation,cloud_cover',
                'timezone': 'auto'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Find the specific hour data
            hourly_data = data.get('hourly', {})
            times = hourly_data.get('time', [])
            target_hour = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").hour
            
            weather_data = {
                'location': f"{lat}, {lon}",
                'date': date,
                'hour': target_hour,
                'temperature_celsius': None,
                'wind_speed_kmh': None,
                'precipitation_mm': None,
                'cloud_coverage_percent': None
            }
            
            # Find the hour that matches our target
            for i, time_str in enumerate(times):
                time_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if time_obj.hour == target_hour:
                    weather_data.update({
                        'temperature_celsius': hourly_data.get('temperature_2m', [None])[i],
                        'wind_speed_kmh': hourly_data.get('wind_speed_10m', [None])[i],
                        'precipitation_mm': hourly_data.get('precipitation', [None])[i],
                        'cloud_coverage_percent': hourly_data.get('cloud_cover', [None])[i]
                    })
                    break
            
            logger.info(f"Retrieved historical weather for {weather_data['location']} on {date} at {time} via Open-Meteo")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching historical weather for {lat}, {lon} on {date} at {time}: {e}")
            return None
    
    def get_historical_weather_all_hours(self, lat: float, lon: float, date: str, location_name: str = None, max_retries: int = 3) -> Optional[list]:
        """Get historical weather data for all 24 hours of a specific date with ONE API call and robust error handling"""
        import requests
        from requests.exceptions import RequestException, Timeout, ConnectionError
        
        for attempt in range(max_retries):
            try:
                # Use Open-Meteo API for historical data (free, no API key required)
                url = "https://archive-api.open-meteo.com/v1/archive"
                params = {
                    'latitude': lat,
                    'longitude': lon,
                    'start_date': date,
                    'end_date': date,
                    'hourly': 'temperature_2m,wind_speed_10m,precipitation,cloud_cover',
                    'timezone': 'auto'
                }
                
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    data = response.json()
                    
                    # Validate response structure
                    if 'hourly' not in data or 'time' not in data['hourly']:
                        logger.error(f"Invalid API response structure for {location_name or f'{lat}, {lon}'} on {date}")
                        return None
                    
                    # Process all 24 hours
                    hourly_data = data.get('hourly', {})
                    times = hourly_data.get('time', [])
                    
                    if len(times) == 0:
                        logger.warning(f"No hourly data returned for {location_name or f'{lat}, {lon}'} on {date}")
                        return None
                    
                    daily_weather = []
                    
                    for i, time_str in enumerate(times):
                        try:
                            time_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            
                            # Extract data with validation
                            temp = hourly_data.get('temperature_2m', [None])[i] if i < len(hourly_data.get('temperature_2m', [])) else None
                            wind = hourly_data.get('wind_speed_10m', [None])[i] if i < len(hourly_data.get('wind_speed_10m', [])) else None
                            precip = hourly_data.get('precipitation', [None])[i] if i < len(hourly_data.get('precipitation', [])) else None
                            cloud_cover = hourly_data.get('cloud_cover', [None])[i] if i < len(hourly_data.get('cloud_cover', [])) else None
                            
                            hour_data = {
                                'location': location_name or f"{lat}, {lon}",
                                'date': date,
                                'hour': time_obj.hour,
                                'temperature_celsius': temp if temp is not None else 0,
                                'wind_speed_kmh': wind if wind is not None else 0,
                                'precipitation_mm': precip if precip is not None else 0,
                                'cloud_coverage_percent': cloud_cover if cloud_cover is not None else 0,
                                'ingestion_timestamp': datetime.now().isoformat()
                            }
                            daily_weather.append(hour_data)
                            
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Error processing hour {i} for {location_name or f'{lat}, {lon}'} on {date}: {e}")
                            # Add default data for this hour
                            hour_data = {
                                'location': location_name or f"{lat}, {lon}",
                                'date': date,
                                'hour': i,
                                'temperature_celsius': 0,
                                'wind_speed_kmh': 0,
                                'precipitation_mm': 0,
                                'cloud_coverage_percent': 0,
                                'ingestion_timestamp': datetime.now().isoformat()
                            }
                            daily_weather.append(hour_data)
                    
                    logger.info(f"Retrieved historical weather for {location_name or f'{lat}, {lon}'} on {date} ({len(daily_weather)} hours) via Open-Meteo API - 1 API call")
                    return daily_weather
                    
                elif response.status_code == 429:  # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit exceeded for {location_name or f'{lat}, {lon}'} on {date}. Retry after {retry_after} seconds. Attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts for {location_name or f'{lat}, {lon}'} on {date}")
                        return None
                        
                elif response.status_code == 400:  # Bad request
                    logger.error(f"Bad request (400) for {location_name or f'{lat}, {lon}'} on {date}: {response.text}")
                    return None
                    
                elif response.status_code == 404:  # Not found
                    logger.error(f"Data not found (404) for {location_name or f'{lat}, {lon}'} on {date}")
                    return None
                    
                elif response.status_code >= 500:  # Server error
                    logger.warning(f"Server error ({response.status_code}) for {location_name or f'{lat}, {lon}'} on {date}. Attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Server error after {max_retries} attempts for {location_name or f'{lat}, {lon}'} on {date}")
                        return None
                        
                else:
                    logger.error(f"Unexpected HTTP status {response.status_code} for {location_name or f'{lat}, {lon}'} on {date}: {response.text}")
                    return None
                    
            except Timeout:
                logger.warning(f"Request timeout for {location_name or f'{lat}, {lon}'} on {date}. Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Request timeout after {max_retries} attempts for {location_name or f'{lat}, {lon}'} on {date}")
                    return None
                    
            except ConnectionError:
                logger.warning(f"Connection error for {location_name or f'{lat}, {lon}'} on {date}. Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Connection error after {max_retries} attempts for {location_name or f'{lat}, {lon}'} on {date}")
                    return None
                    
            except RequestException as e:
                logger.warning(f"Request error for {location_name or f'{lat}, {lon}'} on {date}: {e}. Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Request error after {max_retries} attempts for {location_name or f'{lat}, {lon}'} on {date}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error for {location_name or f'{lat}, {lon}'} on {date}: {e}")
                return None
        
        return None
    
    def get_coordinates_by_name(self, location_name: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get coordinates (lat/lon) for a location by name using OpenWeather Geocoding API
        
        Args:
            location_name: Location name (e.g., "San Francisco, CA" or "Paris, France")
            limit: Number of results to return (default: 1)
        
        Returns:
            Dictionary with {name, lat, lon, country, state} or None if not found
        
        Note: Requires OpenWeather API key
        """
        try:
            if not self.api_key:
                logger.error("OpenWeather API key required for geocoding")
                return None
            
            params = {
                'q': location_name,
                'limit': limit,
                'appid': self.api_key
            }
            
            response = self.session.get(self.geocoding_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or len(data) == 0:
                logger.warning(f"No coordinates found for location: {location_name}")
                return None
            
            # Return the first (best) result
            result = data[0]
            coordinates = {
                'name': result.get('name'),
                'lat': result.get('lat'),
                'lon': result.get('lon'),
                'country': result.get('country'),
                'state': result.get('state', '')
            }
            
            logger.info(f"📍 Geocoded '{location_name}' → {coordinates['name']}, {coordinates['state']} ({coordinates['lat']}, {coordinates['lon']})")
            return coordinates
            
        except Exception as e:
            logger.error(f"Error geocoding location '{location_name}': {e}")
            return None

# Global instance
weather_api = WeatherAPI()

# Convenience functions for backward compatibility
def get_current_temperature(lat: float, lon: float, location_name: str = None) -> Optional[float]:
    """Get current temperature for a location"""
    weather = weather_api.get_current_weather(lat, lon, location_name)
    return weather.get('temperature_celsius') if weather else None

def get_current_wind_speed(lat: float, lon: float, location_name: str = None) -> Optional[float]:
    """Get current wind speed for a location"""
    weather = weather_api.get_current_weather(lat, lon, location_name)
    return weather.get('wind_speed_kmh') if weather else None

def get_current_precipitation(lat: float, lon: float, location_name: str = None) -> Optional[float]:
    """Get current precipitation for a location"""
    weather = weather_api.get_current_weather(lat, lon, location_name)
    return weather.get('precipitation_mm') if weather else None

def get_current_cloud_coverage(lat: float, lon: float, location_name: str = None) -> Optional[float]:
    """Get current cloud coverage for a location"""
    weather = weather_api.get_current_weather(lat, lon, location_name)
    return weather.get('cloud_coverage_percent') if weather else None

# Historical data functions for backward compatibility
def get_historical_temperature_openmeteo(lat: float, lon: float, date: str, time: str = "12:00") -> Optional[float]:
    """Get historical temperature for a specific date and time"""
    weather = weather_api.get_historical_weather(lat, lon, date, time)
    return weather.get('temperature_celsius') if weather else None

def get_historical_wind_openmeteo(lat: float, lon: float, date: str, time: str = "12:00") -> Optional[float]:
    """Get historical wind speed for a specific date and time"""
    weather = weather_api.get_historical_weather(lat, lon, date, time)
    return weather.get('wind_speed_kmh') if weather else None

def get_historical_precipitation_openmeteo(lat: float, lon: float, date: str, time: str = "12:00") -> Optional[float]:
    """Get historical precipitation for a specific date and time"""
    weather = weather_api.get_historical_weather(lat, lon, date, time)
    return weather.get('precipitation_mm') if weather else None

def get_historical_cloud_coverage_openmeteo(lat: float, lon: float, date: str, time: str = "12:00") -> Optional[float]:
    """Get historical cloud coverage for a specific date and time"""
    weather = weather_api.get_historical_weather(lat, lon, date, time)
    return weather.get('cloud_coverage_percent') if weather else None 