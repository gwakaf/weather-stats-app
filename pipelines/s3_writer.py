import boto3
import io
import pandas as pd
from datetime import datetime
import logging
import os
import sys
import yaml

logger = logging.getLogger(__name__)

def get_s3_config():
    """Get S3 configuration from config file or environment variables."""
    try:
        # Try to load from config file directly
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'infra_config.yaml')
        with open(config_path, 'r') as f:
            infra_config = yaml.safe_load(f)
        return infra_config['s3_bucket']
    except Exception as e:
        logger.warning(f"Failed to load S3 config: {e}")
        # Fallback to environment variable
        return os.getenv('S3_BUCKET', 'weather-data-yy')

def save_to_s3_parquet(df, location_name, date):
    """
    Save DataFrame to S3 as a Parquet file in partitioned path: weather-data/location=.../year=.../month=.../day=.../weather_data_YYYY-MM-DD.parquet
    """
    try:
        # Get S3 configuration
        s3_bucket = get_s3_config()
        s3_prefix = 'weather-data/'
        
        # Clean location name for S3 key
        clean_location = location_name.replace(',', '').replace(' ', '_')
        
        # Parse date components (assuming date is in YYYY-MM-DD format)
        if '-' in date:
            date_parts = date.split('-')
            year = date_parts[0]
            month = date_parts[1].zfill(2)  # Ensure 2-digit format
            day = date_parts[2].zfill(2)    # Ensure 2-digit format
        else:
            # Fallback to current date if format is unexpected
            now = datetime.now()
            year = str(now.year)
            month = str(now.month).zfill(2)
            day = str(now.day).zfill(2)
        
        # Partitioned S3 path with year/month/day partitioning and descriptive filename
        s3_key = f"{s3_prefix}location={clean_location}/year={year}/month={month}/day={day}/weather_data_{date}.parquet"
        
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        # Convert DataFrame to parquet
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        
        # Upload to S3
        s3.upload_fileobj(buffer, s3_bucket, s3_key)
        logger.info(f"✅ Successfully uploaded weather data to s3://{s3_bucket}/{s3_key}")
        logger.info(f"   Location: {location_name}, Date: {date}, Records: {len(df)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to upload weather data to S3: {e}")
        logger.error(f"   Location: {location_name}, Date: {date}")
        return False 