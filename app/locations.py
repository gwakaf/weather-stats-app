#!/usr/bin/env python3
"""
Centralized locations configuration loader for Weather Finder
Used by all application components to load predefined locations
"""

import logging
from typing import Dict, List, Optional
from config.config import get_locations_config
import os

# This should point to weather-app/config/
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

logger = logging.getLogger(__name__)

def load_locations_from_config() -> Dict[str, Dict[str, float]]:
    """
    Load locations from the centralized locations configuration file using config.py
    Returns:
        Dictionary mapping location names to their coordinates
        Empty dictionary if configuration fails to load
    """
    try:
        config = get_locations_config()
        locations = {}
        for loc in config.get('locations', []):
            if isinstance(loc, dict) and 'name' in loc and 'lat' in loc and 'lon' in loc:
                locations[loc['name']] = {
                    'lat': loc['lat'],
                    'lon': loc['lon']
                }
        logger.info(f"📍 Loaded {len(locations)} locations from config")
        return locations
    except Exception as e:
        logger.error(f"Failed to load locations from config.py: {e}")
        logger.warning("Returning empty locations dictionary - no locations available")
        return {}

def get_available_locations() -> List[str]:
    locations = load_locations_from_config()
    return list(locations.keys())

def get_location_coordinates(location_name: str) -> Optional[Dict[str, float]]:
    locations = load_locations_from_config()
    return locations.get(location_name) 