#!/usr/bin/env python3
"""
Response Formatter Utilities for Weather Finder API
Handles response formatting, unit conversions, and data transformation.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
plt.style.use('default')
sns.set_palette("husl")

def celsius_to_fahrenheit(celsius: Optional[float]) -> Optional[float]:
    """Convert Celsius to Fahrenheit"""
    if celsius is None:
        return None
    return (celsius * 9/5) + 32

def kmh_to_mph(kmh: Optional[float]) -> Optional[float]:
    """Convert kilometers per hour to miles per hour"""
    if kmh is None:
        return None
    return kmh * 0.621371

def format_weather_response(weather_data: Dict[str, Any], unit: str = 'celsius') -> Dict[str, Any]:
    """
    Format weather data response with proper units and structure
    
    Args:
        weather_data: Raw weather data dictionary
        unit: Temperature unit ('celsius' or 'fahrenheit')
    
    Returns:
        Formatted weather response dictionary
    """
    if not weather_data:
        return {'success': False, 'error': 'No weather data available'}
    
    # Extract basic weather data
    temp = weather_data.get('temperature_celsius')
    wind = weather_data.get('wind_speed_kmh')
    precip = weather_data.get('precipitation_mm')
    cloud_cover = weather_data.get('cloud_coverage_percent')
    
    # Convert units if needed
    if unit == 'fahrenheit':
        temp = celsius_to_fahrenheit(temp)
        wind = kmh_to_mph(wind)
        wind_unit = 'mph'
        temp_unit = '°F'
    else:
        wind_unit = 'km/h'
        temp_unit = '°C'
    
    return {
        'success': True,
        'data': {
            'temperature': temp,
            'wind_speed': wind,
            'precipitation': precip,
            'cloud_coverage': cloud_cover,
            'temperature_unit': temp_unit,
            'wind_unit': wind_unit,
            'location': weather_data.get('location'),
            'timestamp': weather_data.get('timestamp'),
            'date': weather_data.get('date'),
            'hour': weather_data.get('hour')
        }
    }

def format_error_response(error_message: str, status_code: int = 400) -> Tuple[Dict[str, Any], int]:
    """
    Format error response with consistent structure
    
    Args:
        error_message: Error message to include
        status_code: HTTP status code
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    return {
        'success': False,
        'error': error_message,
        'timestamp': datetime.now().isoformat()
    }, status_code

def format_locations_response(locations: List[str]) -> Dict[str, Any]:
    """
    Format locations list response
    
    Args:
        locations: List of location names
    
    Returns:
        Formatted locations response
    """
    return {
        'success': True,
        'data': {
            'locations': locations,
            'count': len(locations)
        }
    }

def format_historic_data_response(data: List[Dict[str, Any]], unit: str = 'celsius') -> Dict[str, Any]:
    """
    Format historic weather data response
    
    Args:
        data: List of historic weather data points
        unit: Temperature unit ('celsius' or 'fahrenheit')
    
    Returns:
        Formatted historic data response
    """
    if not data:
        return {'success': False, 'error': 'No historic data available'}
    
    # Convert units if needed
    if unit == 'fahrenheit':
        for item in data:
            if 'temperature_celsius' in item:
                item['temperature_fahrenheit'] = celsius_to_fahrenheit(item['temperature_celsius'])
            if 'wind_speed_kmh' in item:
                item['wind_speed_mph'] = kmh_to_mph(item['wind_speed_kmh'])
    
    return {
        'success': True,
        'data': {
            'records': data,
            'count': len(data),
            'unit': unit
        }
    } 