from datetime import datetime, timedelta
import sys
import os
import logging
import pandas as pd

# Add project paths
app_path = os.path.join(os.path.dirname(__file__), '..', 'app')
sys.path.insert(0, app_path)
from weather_api import WeatherAPI

from pipelines.s3_writer import save_to_s3_parquet

logger = logging.getLogger(__name__)

def get_locations():
    """Load locations from centralized configuration."""
    try:
        logger.info(f"🔧 Loading locations from config...")
        
        # Import config module
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
        sys.path.insert(0, config_path)
        logger.info(f"🔧 Added config path: {config_path}")
        
        from config import get_locations_config
        logger.info(f"✅ Successfully imported get_locations_config")
        
        config = get_locations_config()
        logger.info(f"✅ Successfully loaded config: {type(config)}")
        logger.info(f"🔧 Config keys: {list(config.keys()) if config else 'None'}")
        
        locations = config.get('locations', [])
        logger.info(f"✅ Loaded {len(locations)} locations from centralized config")
        
        if locations:
            for i, loc in enumerate(locations):
                logger.info(f"   {i+1}. {loc['name']} ({loc['lat']}, {loc['lon']})")
        
        return locations
    except Exception as e:
        logger.error(f"❌ Failed to load locations from centralized config: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        logger.warning("📍 No locations available - returning empty list")
        return []

def run_daily_ingestion(**context):
    """
    Main function to run daily weather ingestion.
    Uses imported get_historical_weather_all_hours method for each location.
    
    Args:
        **context: Airflow context dictionary
        
    Returns:
        bool: True if successful, raises exception if failed
    """
    try:
        logger.info(f"🚀 Starting daily weather ingestion task")
        logger.info(f"📋 Context keys: {list(context.keys()) if context else 'None'}")
        
        # Get date from a week ago (instead of yesterday) since Open-Meteo has data delay
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        logger.info(f"📅 Processing data for {week_ago} (1 week ago)")
        
        # Load locations from configuration
        logger.info(f"📍 Loading locations from configuration...")
        locations = get_locations()
        logger.info(f"📍 Loaded {len(locations)} locations: {[loc['name'] for loc in locations]}")
        
        # Check if locations are available
        if not locations:
            logger.warning("📍 No locations configured - skipping ingestion")
            logger.warning("💡 Please check config/locations.yaml file")
            return True  # Return success to avoid DAG failure
        
        logger.info(f"📍 Processing {len(locations)} locations")
        
        # Initialize weather API
        logger.info(f"🌐 Initializing WeatherAPI...")
        weather_api = WeatherAPI()
        logger.info(f"✅ WeatherAPI initialized successfully")
        
        successful_uploads = 0
        failed_uploads = 0
        
        # Process each location
        for i, location in enumerate(locations):
            location_name = location['name']
            lat = location['lat']
            lon = location['lon']
            
            logger.info(f"📊 [{i+1}/{len(locations)}] Fetching weather for {location_name} ({lat}, {lon}) on {week_ago}")
            
            try:
                # Use imported get_historical_weather_all_hours method
                logger.info(f"   🔄 Calling weather_api.get_historical_weather_all_hours...")
                weather_data = weather_api.get_historical_weather_all_hours(
                    lat=lat, 
                    lon=lon, 
                    date=week_ago, 
                    location_name=location_name
                )
                
                logger.info(f"   📊 Weather API returned: {type(weather_data)}")
                if weather_data is not None:
                    logger.info(f"   📊 Weather data length: {len(weather_data)}")
                    if len(weather_data) > 0:
                        logger.info(f"   📊 First item keys: {list(weather_data[0].keys())}")
                        logger.info(f"   📊 Sample temperature: {weather_data[0].get('temperature_celsius')}")
                
                if weather_data is not None and len(weather_data) > 0:
                    logger.info(f"   ✅ Got weather data for {location_name}")
                    
                    # Convert to DataFrame
                    logger.info(f"   📋 Converting to DataFrame...")
                    df = pd.DataFrame(weather_data)
                    logger.info(f"   📋 DataFrame shape: {df.shape}")
                    logger.info(f"   📋 DataFrame columns: {list(df.columns)}")
                    
                    # Show sample data
                    logger.info(f"   📊 Sample data (first 2 rows):")
                    print(df.head(2).to_string())
                    
                    # Add location metadata if not already present
                    if 'location_name' not in df.columns:
                        df['location_name'] = location_name
                        logger.info(f"   ✅ Added location_name column")
                    if 'ingestion_timestamp' not in df.columns:
                        df['ingestion_timestamp'] = datetime.now().isoformat()
                        logger.info(f"   ✅ Added ingestion_timestamp column")
                    
                    # Use imported save_to_s3_parquet method
                    logger.info(f"   💾 Saving to S3...")
                    success = save_to_s3_parquet(df, location_name, week_ago)
                    if success:
                        successful_uploads += 1
                        logger.info(f"   ✅ Successfully processed {location_name} - {len(df)} records")
                    else:
                        failed_uploads += 1
                        logger.error(f"   ❌ Failed to save {location_name} to S3")
                else:
                    failed_uploads += 1
                    logger.warning(f"   ⚠️ No weather data available for {location_name} on {week_ago}")
                    logger.warning(f"   ⚠️ weather_data: {weather_data}")
                    
            except Exception as e:
                failed_uploads += 1
                logger.error(f"   ❌ Error processing {location_name}: {e}")
                import traceback
                logger.error(f"   ❌ Full traceback: {traceback.format_exc()}")
        
        # Summary
        logger.info(f"📈 Daily ingestion completed for {week_ago}")
        logger.info(f"   ✅ Successful: {successful_uploads}")
        logger.info(f"   ❌ Failed: {failed_uploads}")
        
        if failed_uploads > 0:
            logger.warning(f"⚠️ Some locations failed to process")
        
        if successful_uploads == 0:
            logger.warning(f"⚠️ No locations were successfully processed!")
        
        logger.info(f"🏁 Function returning: True")
        return True
        
    except Exception as e:
        logger.error(f"❌ Daily ingestion task failed: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise 