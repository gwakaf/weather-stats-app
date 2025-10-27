from datetime import datetime, timedelta
import sys
import os
import logging
import pandas as pd
import time
import yaml

# Add project paths
app_path = os.path.join(os.path.dirname(__file__), '..', 'app')
sys.path.insert(0, app_path)
from weather_api import WeatherAPI

from pipelines.s3_writer import save_to_s3_parquet

logger = logging.getLogger(__name__)

def load_backfilling_config(config_file="backfilling_config.yaml"):
    """Load backfilling configuration from YAML file."""
    try:
        # Try multiple possible paths for the config file
        possible_paths = [
            # Config directory
            os.path.join(os.path.dirname(__file__), '..', 'config', config_file),
            # Current directory (pipelines)
            os.path.join(os.path.dirname(__file__), config_file),
            # Root directory
            os.path.join(os.path.dirname(__file__), '..', config_file),
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if config_path is None:
            raise FileNotFoundError(f"Could not find {config_file} in any of the expected locations")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"✅ Loaded backfilling config from: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"❌ Failed to load backfilling config file {config_file}: {e}")
        # Return default configuration
        logger.warning("📋 Using default backfilling configuration")
        return {
            'start_date': '2025-01-01',
            'end_date': '2025-06-30',
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

def get_location_coordinates(location_name):
    """Get coordinates for a location name from the centralized config."""
    try:
        # Import config module
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
        sys.path.insert(0, config_path)
        from config import get_locations_config
        
        # Load locations config
        locations_config = get_locations_config()
        locations = locations_config.get('locations', [])
        
        # Find the location
        for loc in locations:
            if loc['name'] == location_name:
                return {
                    'lat': loc['lat'],
                    'lon': loc['lon'],
                    'name': loc['name']
                }
        
        logger.error(f"❌ Location '{location_name}' not found in configuration")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting location coordinates: {e}")
        return None

def backfill_historic_weather(start_date, end_date, location_name, save_to_s3=True):
    """
    Backfill historic weather data for a location over a date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        location_name (str): Location name to backfill
        save_to_s3 (bool): Whether to save data to S3 (default: True)
    
    Returns:
        tuple: (successful_days, total_days, failed_days)
    """
    logger.info(f"🌤️ Starting historic weather backfilling")
    logger.info(f"📅 Date range: {start_date} to {end_date}")
    logger.info(f"📍 Location: {location_name}")
    
    # Get location coordinates
    location_data = get_location_coordinates(location_name)
    if not location_data:
        logger.error(f"❌ Could not get coordinates for location: {location_name}")
        return 0, 0, 0
    
    lat = location_data['lat']
    lon = location_data['lon']
    
    logger.info(f"📍 Coordinates: {lat}, {lon}")
    
    # Initialize weather API (API key handling is internal to WeatherAPI)
    weather_api = WeatherAPI()
    
    # Load backfilling configuration
    backfill_config = load_backfilling_config()
    api_config = backfill_config.get('api', {})
    delay_between_requests = api_config.get('delay_between_requests', 1)
    max_retries = api_config.get('max_retries', 3)
    
    logger.info(f"⚙️ API settings: {delay_between_requests}s delay, {max_retries} max retries")
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 0, 0, 0
    
    # Calculate total days
    total_days = (end_dt - start_dt).days + 1
    successful_days = 0
    failed_days = 0
    
    logger.info(f"📊 Processing {total_days} days from {start_dt} to {end_dt}")
    
    # Process each day
    current_date = start_dt
    while current_date <= end_dt:
        date_str = current_date.strftime('%Y-%m-%d')
        logger.info(f"📅 Processing {date_str} ({current_date - start_dt + 1}/{total_days})")
        
        try:
            # Get full day weather data using the centralized weather API
            # WeatherAPI handles all API key management and requests internally
            weather_data = weather_api.get_historical_weather_all_hours(
                lat, lon, date_str, location_name=location_name
            )
            
            if weather_data is not None and len(weather_data) > 0:
                # Convert to DataFrame
                df = pd.DataFrame(weather_data)
                
                # Add location metadata if not already present
                if 'location_name' not in df.columns:
                    df['location_name'] = location_name
                if 'ingestion_timestamp' not in df.columns:
                    df['ingestion_timestamp'] = datetime.now().isoformat()
                
                # Save to S3 if requested
                if save_to_s3:
                    success = save_to_s3_parquet(df, location_name, date_str)
                    if success:
                        successful_days += 1
                        logger.info(f"✅ Successfully processed {date_str} - {len(df)} records")
                        
                        # Log sample weather data
                        if len(df) > 0:
                            sample = df.iloc[0]
                            temp = sample.get('temperature_celsius', 'N/A')
                            wind = sample.get('wind_speed_kmh', 'N/A')
                            precip = sample.get('precipitation_mm', 'N/A')
                            clouds = sample.get('cloud_coverage_percent', 'N/A')
                            logger.info(f"🌡️ Sample data: Temp={temp}°C, Wind={wind}km/h, Precip={precip}mm, Clouds={clouds}%")
                    else:
                        failed_days += 1
                        logger.error(f"❌ Failed to save {date_str} to S3")
                else:
                    # Just log success without saving
                    successful_days += 1
                    logger.info(f"✅ Successfully fetched {date_str} - {len(df)} records (not saved to S3)")
            else:
                failed_days += 1
                logger.warning(f"⚠️ No weather data available for {date_str}")
                
        except Exception as e:
            failed_days += 1
            logger.error(f"❌ Error processing {date_str}: {e}")
        
        # Add delay between requests (except for the last day)
        if current_date < end_dt:
            logger.info(f"⏳ Waiting {delay_between_requests}s before next request...")
            time.sleep(delay_between_requests)
        
        current_date += timedelta(days=1)
    
    # Summary
    logger.info(f"\n📊 Backfilling Summary:")
    logger.info(f"   📅 Date range: {start_date} to {end_date}")
    logger.info(f"   📍 Location: {location_name}")
    logger.info(f"   ✅ Successful days: {successful_days}/{total_days}")
    logger.info(f"   ❌ Failed days: {failed_days}/{total_days}")
    logger.info(f"   📈 Success rate: {(successful_days/total_days)*100:.1f}%")
    
    if successful_days == total_days:
        logger.info(f"🎉 Backfilling completed successfully!")
    elif successful_days > 0:
        logger.warning(f"⚠️ Backfilling completed with some failures")
    else:
        logger.error(f"❌ Backfilling failed completely")
    
    return successful_days, total_days, failed_days

def backfill_multiple_locations(start_date, end_date, locations, save_to_s3=True):
    """
    Backfill historic weather data for multiple locations over a date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        locations (list): List of location names to backfill
        save_to_s3 (bool): Whether to save data to S3 (default: True)
    
    Returns:
        dict: Summary of results for each location
    """
    logger.info(f"🌤️ Starting multi-location historic weather backfilling")
    logger.info(f"📅 Date range: {start_date} to {end_date}")
    logger.info(f"📍 Locations: {', '.join(locations)}")
    
    results = {}
    total_successful = 0
    total_failed = 0
    
    for location in locations:
        logger.info(f"\n🏙️ Processing location: {location}")
        successful, total, failed = backfill_historic_weather(
            start_date, end_date, location, save_to_s3
        )
        
        results[location] = {
            'successful_days': successful,
            'total_days': total,
            'failed_days': failed,
            'success_rate': (successful/total)*100 if total > 0 else 0
        }
        
        total_successful += successful
        total_failed += failed
    
    # Overall summary
    total_days = sum(result['total_days'] for result in results.values())
    overall_success_rate = (total_successful/total_days)*100 if total_days > 0 else 0
    
    logger.info(f"\n🎯 Multi-Location Backfilling Summary:")
    logger.info(f"   📍 Total locations: {len(locations)}")
    logger.info(f"   ✅ Total successful days: {total_successful}")
    logger.info(f"   ❌ Total failed days: {total_failed}")
    logger.info(f"   📈 Overall success rate: {overall_success_rate:.1f}%")
    
    return results
