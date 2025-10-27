#!/usr/bin/env python3
"""
AWS Data Fetching Service for Weather Finder Backend
Handles fetching weather data from AWS S3/Athena for predefined locations.
"""

import boto3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import os
import sys

# Import from the centralized config module
from config.config import get_infra_config, get_locations_config

logger = logging.getLogger(__name__)

# Add console handler for better visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

class AWSDataFetcher:
    """AWS data fetching service for weather data"""
    
    def __init__(self):
        """Initialize AWS services for weather data fetching"""
        try:
            # Get the configured region
            self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

            # Load infra config
            try:
                infra_config = get_infra_config()
                self.bucket_name = infra_config['s3_bucket']
                self.database_name = infra_config['glue_database']
                self.table_name = infra_config['glue_table']
                self.workgroup_name = infra_config['athena_workgroup']
                self.output_location = f"s3://{infra_config['athena_output_bucket']}/"
                logger.info("Successfully loaded AWS infrastructure config")
            except Exception as e:
                logger.warning(f"Failed to load AWS infrastructure config: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
                # Set default values for development
                self.bucket_name = "weather-data-dev"
                self.database_name = "weather_finder_db"
                self.table_name = "historic_weather"
                self.workgroup_name = "weather-finder-workgroup"
                self.output_location = "s3://weather-data-dev-athena-output/"

            # Load locations from config
            try:
                logger.info("Attempting to load locations config...")
                locations_config = get_locations_config()
                logger.info(f"Locations config loaded: {locations_config}")
                self.locations = {}
                for loc in locations_config.get('locations', []):
                    self.locations[loc['name']] = {
                        'lat': loc['lat'],
                        'lon': loc['lon']
                    }
                logger.info(f"Successfully loaded {len(self.locations)} locations from config: {list(self.locations.keys())}")
            except Exception as e:
                logger.error(f"Failed to load locations config: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Return empty locations dictionary - no hardcoded fallbacks
                self.locations = {}
                logger.warning("No locations available - returning empty dictionary")

            # Initialize AWS clients (only if AWS credentials are available)
            try:
                self.s3_client = boto3.client('s3', region_name=self.region)
                self.athena_client = boto3.client('athena', region_name=self.region)
                self.glue_client = boto3.client('glue', region_name=self.region)
                logger.info("Successfully initialized AWS clients")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS clients (this is normal for development): {e}")
                self.s3_client = None
                self.athena_client = None
                self.glue_client = None

        except Exception as e:
            logger.error(f"Error initializing AWSDataFetcher: {e}")
            # Set minimal defaults - no hardcoded locations
            self.locations = {}

    def get_available_locations(self) -> List[str]:
        """Get list of available predefined locations"""
        return list(self.locations.keys())

    def get_location_coordinates(self, location_name: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a predefined location"""
        return self.locations.get(location_name)

    def query_historic_data(self, location_name: str, target_date: str, target_hour: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Query historic weather data from AWS Athena"""
        try:
            logger.info(f"🔍 AWS Query: Starting query for {location_name} on {target_date} at hour {target_hour}")
            
            # Check if AWS clients are available
            if not self.athena_client:
                logger.warning("AWS clients not available, returning None for historic data query")
                return None
                
            # Build Athena query
            if target_hour is not None:
                query = f"""
                SELECT
                    location,
                    date,
                    hour,
                    temperature_celsius,
                    wind_speed_kmh,
                    precipitation_mm,
                    cloud_coverage_percent
                FROM {self.database_name}.{self.table_name}
                WHERE location = '{location_name}'
                AND date = '{target_date}'
                AND hour = {target_hour}
                ORDER BY date, hour
                """
            else:
                query = f"""
                SELECT
                    location,
                    date,
                    hour,
                    temperature_celsius,
                    wind_speed_kmh,
                    precipitation_mm,
                    cloud_coverage_percent
                FROM {self.database_name}.{self.table_name}
                WHERE location = '{location_name}'
                AND date = '{target_date}'
                ORDER BY date, hour
                """

            # Execute Athena query
            logger.info(f"📊 AWS Query: Executing query: {query[:100]}...")
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': self.database_name},
                WorkGroup=self.workgroup_name
            )

            query_execution_id = response['QueryExecutionId']
            logger.info(f"📊 AWS Query: Query started with ID: {query_execution_id}")

            # Wait for query to complete
            while True:
                query_status = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                state = query_status['QueryExecution']['Status']['State']
                logger.info(f"📊 AWS Query: Status: {state}")

                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break

                import time
                time.sleep(1)

            if state == 'SUCCEEDED':
                # Get results
                logger.info(f"✅ AWS Query: Query succeeded, fetching results...")
                results = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
                parsed_results = self._parse_athena_results(results)
                logger.info(f"📊 AWS Query: Found {len(parsed_results)} records")
                return parsed_results
            else:
                error_reason = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                logger.error(f"❌ AWS Query: Query failed with state: {state}")
                logger.error(f"❌ AWS Query: Error reason: {error_reason}")
                return None

        except Exception as e:
            logger.error(f"Error querying historic data: {e}")
            return None

    def _parse_athena_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Athena query results"""
        try:
            if 'ResultSet' not in results or 'Rows' not in results['ResultSet']:
                return []

            rows = results['ResultSet']['Rows']
            if len(rows) <= 1:  # Only header or no data
                return []

            # Skip header row
            data_rows = rows[1:]

            parsed_data = []
            for row in data_rows:
                data = row['Data']
                parsed_row = {
                    'location': data[0].get('VarCharValue', ''),
                    'date': data[1].get('VarCharValue', ''),
                    'hour': int(data[2].get('VarCharValue', 0)),
                    'temperature_celsius': float(data[3].get('VarCharValue', 0)),
                    'wind_speed_kmh': float(data[4].get('VarCharValue', 0)),
                    'precipitation_mm': float(data[5].get('VarCharValue', 0)),
                    'cloud_coverage_percent': float(data[6].get('VarCharValue', 0))
                }
                parsed_data.append(parsed_row)

            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing Athena results: {e}")
            return []

    def verify_infrastructure(self) -> bool:
        """Verify that required AWS infrastructure exists"""
        try:
            # Check if AWS clients are available
            if not self.s3_client or not self.athena_client or not self.glue_client:
                logger.warning("AWS clients not available, skipping infrastructure verification")
                return False
                
            # Check if S3 bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' is accessible")

            # Check if Glue database exists
            self.glue_client.get_database(Name=self.database_name)
            logger.info(f"Glue database '{self.database_name}' exists")

            # Check if Glue table exists
            self.glue_client.get_table(
                DatabaseName=self.database_name,
                Name=self.table_name
            )
            logger.info(f"Glue table '{self.table_name}' exists")

            # Check if Athena workgroup exists
            self.athena_client.get_work_group(WorkGroup=self.workgroup_name)
            logger.info(f"Athena workgroup '{self.workgroup_name}' exists")

            return True

        except Exception as e:
            logger.error(f"Infrastructure verification failed: {e}")
            logger.error("Please ensure Terraform infrastructure is deployed first")
            return False

# Global instance
aws_fetcher = AWSDataFetcher() 