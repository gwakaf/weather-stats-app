#!/usr/bin/env python3
"""
Query Utilities for Weather Finder API
Handles database queries, API calls, and data fetching operations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import requests
import time

logger = logging.getLogger(__name__)

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude coordinates
    
    Args:
        lat: Latitude value
        lon: Longitude value
    
    Returns:
        True if coordinates are valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180

def validate_date_format(date_str: str) -> bool:
    """
    Validate date string format (YYYY-MM-DD)
    
    Args:
        date_str: Date string to validate
    
    Returns:
        True if date format is valid, False otherwise
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_time_format(time_str: str) -> bool:
    """
    Validate time string format (HH:MM)
    
    Args:
        time_str: Time string to validate
    
    Returns:
        True if time format is valid, False otherwise
    """
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

def extract_request_data(request_data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    Extract and validate request data from API calls
    
    Args:
        request_data: Request data dictionary
    
    Returns:
        Tuple of (lat, lon, date, time, location_name)
    """
    try:
        lat = float(request_data.get('lat', 0))
        lon = float(request_data.get('lon', 0))
        date = request_data.get('date')
        time = request_data.get('time', '12:00')
        location_name = request_data.get('location_name', f"{lat}, {lon}")
        
        # Validate coordinates
        if not validate_coordinates(lat, lon):
            logger.error(f"Invalid coordinates: lat={lat}, lon={lon}")
            return None, None, None, None, None
        
        # Validate date if provided
        if date and not validate_date_format(date):
            logger.error(f"Invalid date format: {date}")
            return None, None, None, None, None
        
        # Validate time if provided
        if time and not validate_time_format(time):
            logger.error(f"Invalid time format: {time}")
            return None, None, None, None, None
        
        return lat, lon, date, time, location_name
        
    except (ValueError, TypeError) as e:
        logger.error(f"Error extracting request data: {e}")
        return None, None, None, None, None

def retry_api_call(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
    """
    Retry API call with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function
    
    Returns:
        Function result or None if all retries failed
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (requests.RequestException, ConnectionError) as e:
            if attempt == max_retries:
                logger.error(f"API call failed after {max_retries} retries: {e}")
                return None
            
            wait_time = delay * (2 ** attempt)
            logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    return None

def build_query_parameters(lat: float, lon: float, date: str, time: str = "12:00") -> Dict[str, Any]:
    """
    Build query parameters for weather API calls
    
    Args:
        lat: Latitude
        lon: Longitude
        date: Date string (YYYY-MM-DD)
        time: Time string (HH:MM)
    
    Returns:
        Dictionary of query parameters
    """
    return {
        'latitude': lat,
        'longitude': lon,
        'start_date': date,
        'end_date': date,
        'hourly': 'temperature_2m,wind_speed_10m,precipitation,cloud_cover',
        'timezone': 'auto'
    }

def parse_weather_data(raw_data: Dict[str, Any], target_hour: int) -> Optional[Dict[str, Any]]:
    """
    Parse raw weather API response into structured data
    
    Args:
        raw_data: Raw API response data
        target_hour: Target hour to extract data for
    
    Returns:
        Parsed weather data dictionary or None if parsing fails
    """
    try:
        hourly_data = raw_data.get('hourly', {})
        times = hourly_data.get('time', [])
        temperatures = hourly_data.get('temperature_2m', [])
        wind_speeds = hourly_data.get('wind_speed_10m', [])
        precipitations = hourly_data.get('precipitation', [])
        cloud_covers = hourly_data.get('cloud_cover', [])
        
        # Find the index for the target hour
        target_time = f"{raw_data.get('start_date', '')}T{target_hour:02d}:00"
        if target_time in times:
            idx = times.index(target_time)
        else:
            # Fallback to first available data
            idx = 0
        
        return {
            'temperature_celsius': temperatures[idx] if idx < len(temperatures) else None,
            'wind_speed_kmh': wind_speeds[idx] if idx < len(wind_speeds) else None,
            'precipitation_mm': precipitations[idx] if idx < len(precipitations) else None,
            'cloud_coverage_percent': cloud_covers[idx] if idx < len(cloud_covers) else None,
            'hour': target_hour,
            'timestamp': times[idx] if idx < len(times) else None
        }
        
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parsing weather data: {e}")
        return None

def calculate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Calculate list of dates between start and end date
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
    
    Returns:
        List of date strings
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return dates
        
    except ValueError as e:
        logger.error(f"Error calculating date range: {e}")
        return [] 