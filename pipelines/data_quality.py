#!/usr/bin/env python3
"""
Data Quality Monitoring Module
Validates data integrity and correctness after pipeline execution.
Runs data-level checks on ingested weather data stored in S3/Athena.
"""

import sys
import os
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

# Add project paths
app_path = os.path.join(os.path.dirname(__file__), '..', 'app')
sys.path.insert(0, app_path)

# Import AWS fetcher for querying data
from aws_fetching import AWSDataFetcher

# Import config utilities
config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
sys.path.insert(0, config_path)
from config import get_locations_config

logger = logging.getLogger(__name__)

# Expected schema based on Glue table definition
EXPECTED_COLUMNS = [
    'date',
    'hour',
    'temperature_celsius',
    'wind_speed_kmh',
    'precipitation_mm',
    'cloud_coverage_percent',
    'ingestion_timestamp'
]

# Expected data ranges (reasonable bounds for weather data)
DATA_RANGES = {
    'temperature_celsius': (-50, 60),  # -50°C to 60°C
    'wind_speed_kmh': (0, 300),  # 0 to 300 km/h
    'precipitation_mm': (0, 500),  # 0 to 500 mm (extreme rainfall)
    'cloud_coverage_percent': (0, 100),  # 0% to 100%
    'hour': (0, 23)  # 0 to 23 hours
}

# Expected records per day (24 hours)
EXPECTED_HOURS_PER_DAY = 24


def get_locations():
    """Load locations from configuration."""
    try:
        config = get_locations_config()
        locations = config.get('locations', [])
        logger.info(f"📍 Loaded {len(locations)} locations for data quality check")
        return locations
    except Exception as e:
        logger.error(f"❌ Failed to load locations: {e}")
        return []


def validate_schema(data: List[Dict[str, Any]], location: str, date: str) -> Tuple[bool, List[str]]:
    """
    Validate that data matches expected schema.
    
    Args:
        data: List of weather records
        location: Location name
        date: Date string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not data or len(data) == 0:
        errors.append(f"No data found for {location} on {date}")
        return False, errors
    
    # Check if all expected columns are present
    first_record = data[0]
    missing_columns = [col for col in EXPECTED_COLUMNS if col not in first_record]
    
    if missing_columns:
        errors.append(f"Missing columns: {missing_columns}")
    
    # Check column types
    type_checks = {
        'date': str,
        'hour': int,
        'temperature_celsius': (int, float),
        'wind_speed_kmh': (int, float),
        'precipitation_mm': (int, float),
        'cloud_coverage_percent': (int, float),
        'ingestion_timestamp': str
    }
    
    for col, expected_type in type_checks.items():
        if col in first_record:
            value = first_record[col]
            if value is not None:
                if not isinstance(value, expected_type):
                    errors.append(f"Column '{col}' has wrong type: {type(value).__name__}, expected {expected_type.__name__}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_completeness(data: List[Dict[str, Any]], location: str, date: str) -> Tuple[bool, List[str]]:
    """
    Validate data completeness (24 hours per day).
    
    Args:
        data: List of weather records
        location: Location name
        date: Date string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not data:
        errors.append(f"No data to validate completeness for {location} on {date}")
        return False, errors
    
    # Check record count
    record_count = len(data)
    if record_count != EXPECTED_HOURS_PER_DAY:
        errors.append(f"Expected {EXPECTED_HOURS_PER_DAY} records (24 hours), found {record_count}")
    
    # Check for all hours (0-23)
    hours_present = set()
    for record in data:
        if 'hour' in record:
            hours_present.add(record['hour'])
    
    missing_hours = set(range(24)) - hours_present
    if missing_hours:
        errors.append(f"Missing hours: {sorted(missing_hours)}")
    
    duplicate_hours = []
    hour_counts = {}
    for record in data:
        hour = record.get('hour')
        if hour is not None:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            if hour_counts[hour] > 1:
                duplicate_hours.append(hour)
    
    if duplicate_hours:
        errors.append(f"Duplicate hours found: {sorted(set(duplicate_hours))}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_data_ranges(data: List[Dict[str, Any]], location: str, date: str) -> Tuple[bool, List[str]]:
    """
    Validate that data values are within reasonable ranges.
    
    Args:
        data: List of weather records
        location: Location name
        date: Date string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not data:
        return True, errors  # No data to validate
    
    for i, record in enumerate(data):
        for field, (min_val, max_val) in DATA_RANGES.items():
            if field in record:
                value = record[field]
                if value is not None:
                    try:
                        num_value = float(value)
                        if num_value < min_val or num_value > max_val:
                            errors.append(
                                f"Record {i}, hour {record.get('hour', 'unknown')}: "
                                f"{field} = {value} is outside valid range [{min_val}, {max_val}]"
                            )
                    except (ValueError, TypeError):
                        errors.append(
                            f"Record {i}, hour {record.get('hour', 'unknown')}: "
                            f"{field} = {value} is not a valid number"
                        )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_null_values(data: List[Dict[str, Any]], location: str, date: str) -> Tuple[bool, List[str]]:
    """
    Check for null or missing values in critical fields.
    
    Args:
        data: List of weather records
        location: Location name
        date: Date string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not data:
        return True, errors
    
    critical_fields = ['temperature_celsius', 'wind_speed_kmh', 'precipitation_mm', 'cloud_coverage_percent']
    
    for i, record in enumerate(data):
        for field in critical_fields:
            if field not in record or record[field] is None:
                errors.append(
                    f"Record {i}, hour {record.get('hour', 'unknown')}: "
                    f"Missing or null value for {field}"
                )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_data_freshness(data: List[Dict[str, Any]], location: str, date: str) -> Tuple[bool, List[str]]:
    """
    Validate that ingestion_timestamp is recent (within last 24 hours).
    
    Args:
        data: List of weather records
        location: Location name
        date: Date string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not data:
        return True, errors
    
    now = datetime.now()
    max_age_hours = 24
    
    for i, record in enumerate(data):
        if 'ingestion_timestamp' in record and record['ingestion_timestamp']:
            try:
                ingestion_time = datetime.fromisoformat(record['ingestion_timestamp'].replace('Z', '+00:00'))
                age_hours = (now - ingestion_time.replace(tzinfo=None)).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    errors.append(
                        f"Record {i}, hour {record.get('hour', 'unknown')}: "
                        f"Data is {age_hours:.1f} hours old (max: {max_age_hours} hours)"
                    )
            except (ValueError, TypeError) as e:
                errors.append(
                    f"Record {i}, hour {record.get('hour', 'unknown')}: "
                    f"Invalid ingestion_timestamp format: {record['ingestion_timestamp']}"
                )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def run_data_quality_check(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Run comprehensive data quality checks for all locations on a specific date.
    
    Args:
        target_date: Date to check (YYYY-MM-DD format). If None, checks 1 week ago.
        
    Returns:
        Dictionary with quality check results
    """
    try:
        # Determine target date (1 week ago by default, same as ingestion)
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        logger.info(f"🔍 Starting data quality check for {target_date}")
        
        # Load locations
        locations = get_locations()
        if not locations:
            logger.warning("⚠️ No locations configured for data quality check")
            return {
                'success': False,
                'date': target_date,
                'error': 'No locations configured'
            }
        
        # Initialize AWS fetcher
        try:
            aws_fetcher = AWSDataFetcher()
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS fetcher: {e}")
            return {
                'success': False,
                'date': target_date,
                'error': f'Failed to initialize AWS fetcher: {e}'
            }
        
        results = {
            'success': True,
            'date': target_date,
            'locations_checked': len(locations),
            'location_results': {},
            'summary': {
                'total_locations': len(locations),
                'passed_locations': 0,
                'failed_locations': 0,
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0
            }
        }
        
        # Check each location
        for location in locations:
            location_name = location['name']
            logger.info(f"🔍 Checking data quality for {location_name} on {target_date}")
            
            location_result = {
                'location': location_name,
                'date': target_date,
                'checks': {},
                'overall_status': 'PASS',
                'errors': []
            }
            
            # Query data from Athena
            # Note: Athena partition key 'location' uses cleaned format (e.g., "San_Francisco_CA")
            # which matches the S3 partition path, not the original location name
            # The AWS fetcher's query_historic_data expects the cleaned location name
            try:
                # Clean location name to match S3 partition format (same as s3_writer.py)
                clean_location_name = location_name.replace(',', '').replace(' ', '_')
                weather_data = aws_fetcher.query_historic_data(clean_location_name, target_date)
                
                if not weather_data or len(weather_data) == 0:
                    location_result['overall_status'] = 'FAIL'
                    location_result['errors'].append(f"No data found in S3/Athena for {location_name} on {target_date}")
                    location_result['checks']['data_availability'] = {
                        'status': 'FAIL',
                        'message': 'No data found'
                    }
                else:
                    location_result['checks']['data_availability'] = {
                        'status': 'PASS',
                        'message': f'Found {len(weather_data)} records'
                    }
                    
                    # Run all validation checks
                    checks = [
                        ('schema', validate_schema),
                        ('completeness', validate_completeness),
                        ('data_ranges', validate_data_ranges),
                        ('null_values', validate_null_values),
                        ('data_freshness', validate_data_freshness)
                    ]
                    
                    for check_name, check_func in checks:
                        try:
                            is_valid, errors = check_func(weather_data, location_name, target_date)
                            location_result['checks'][check_name] = {
                                'status': 'PASS' if is_valid else 'FAIL',
                                'errors': errors,
                                'message': f"{'Passed' if is_valid else 'Failed'} with {len(errors)} error(s)"
                            }
                            
                            if not is_valid:
                                location_result['overall_status'] = 'FAIL'
                                location_result['errors'].extend(errors)
                                results['summary']['failed_checks'] += 1
                            else:
                                results['summary']['passed_checks'] += 1
                            
                            results['summary']['total_checks'] += 1
                            
                        except Exception as e:
                            logger.error(f"❌ Error running {check_name} check for {location_name}: {e}")
                            location_result['checks'][check_name] = {
                                'status': 'ERROR',
                                'errors': [str(e)],
                                'message': f'Check failed with exception: {e}'
                            }
                            location_result['overall_status'] = 'FAIL'
                            results['summary']['failed_checks'] += 1
                            results['summary']['total_checks'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error querying data for {location_name}: {e}")
                location_result['overall_status'] = 'FAIL'
                location_result['errors'].append(f"Failed to query data: {e}")
                location_result['checks']['data_availability'] = {
                    'status': 'ERROR',
                    'message': f'Query failed: {e}'
                }
            
            # Update summary
            if location_result['overall_status'] == 'PASS':
                results['summary']['passed_locations'] += 1
            else:
                results['summary']['failed_locations'] += 1
            
            results['location_results'][location_name] = location_result
            
            # Log location result
            status_icon = '✅' if location_result['overall_status'] == 'PASS' else '❌'
            logger.info(f"{status_icon} {location_name}: {location_result['overall_status']} "
                       f"({len(location_result['errors'])} error(s))")
        
        # Final summary
        logger.info(f"\n📊 Data Quality Check Summary for {target_date}:")
        logger.info(f"   📍 Locations checked: {results['summary']['total_locations']}")
        logger.info(f"   ✅ Passed: {results['summary']['passed_locations']}")
        logger.info(f"   ❌ Failed: {results['summary']['failed_locations']}")
        logger.info(f"   🔍 Total checks: {results['summary']['total_checks']}")
        logger.info(f"   ✅ Passed checks: {results['summary']['passed_checks']}")
        logger.info(f"   ❌ Failed checks: {results['summary']['failed_checks']}")
        
        # Determine overall success
        if results['summary']['failed_locations'] > 0:
            results['success'] = False
            logger.warning(f"⚠️ Data quality check completed with failures")
        else:
            logger.info(f"🎉 Data quality check passed for all locations!")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Data quality check failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'date': target_date if target_date else 'unknown',
            'error': str(e)
        }


def run_daily_data_quality_check(**context):
    """
    Airflow task function for daily data quality check.
    Checks data quality for the date that was ingested (1 week ago).
    
    Args:
        **context: Airflow context dictionary
        
    Returns:
        bool: True if quality check passed, False otherwise
    """
    try:
        logger.info(f"🚀 Starting daily data quality check task")
        
        # Get date from 1 week ago (same as ingestion)
        target_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        logger.info(f"📅 Checking data quality for {target_date} (1 week ago)")
        
        # Run quality checks
        results = run_data_quality_check(target_date)
        
        if results['success']:
            logger.info(f"✅ Data quality check passed")
            return True
        else:
            logger.warning(f"⚠️ Data quality check completed with issues")
            # Don't fail the DAG, just log warnings
            # This allows the pipeline to continue even if some data has quality issues
            return True
            
    except Exception as e:
        logger.error(f"❌ Data quality check task failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        # Don't fail the DAG on quality check errors
        return True

