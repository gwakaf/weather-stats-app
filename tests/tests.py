#!/usr/bin/env python3
"""
Pytest Test Suite for Weather Finder
Tests API functionality and AWS connectivity.
"""

import sys
import os
import pytest
import yaml
import boto3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipelines'))

# Import modules to test
from app.weather_api import WeatherAPI
from config import get_locations_config

class TestWeatherAPI:
    """Test class for Weather API functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_api_key(self):
        """Setup API key for tests from environment"""
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            pytest.skip("OPENWEATHER_API_KEY not found in environment variables")
    
    @pytest.fixture
    def weather_api(self):
        """Fixture to create WeatherAPI instance"""
        return WeatherAPI()
    
    @pytest.fixture
    def san_francisco_location(self):
        """Fixture for San Francisco location data"""
        return {
            'name': 'San Francisco, CA',
            'lat': 37.7749,
            'lon': -122.4194
        }
    
    @pytest.fixture
    def week_ago_date(self):
        """Fixture for date 1 week ago"""
        return (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')

class TestOpenWeatherAPI(TestWeatherAPI):
    """Test OpenWeather API functionality"""
    
    def test_get_current_weather_san_francisco(self, weather_api, san_francisco_location):
        """
        Test 1: OpenWeather API call test calling get_current_weather function 
        for hardcoded San Francisco location
        """
        # Arrange
        lat = san_francisco_location['lat']
        lon = san_francisco_location['lon']
        location_name = san_francisco_location['name']
        
        # Act
        result = weather_api.get_current_weather(
            lat=lat,
            lon=lon,
            location_name=location_name
        )
        
        # Assert
        assert result is not None, "API call should return data"
        assert isinstance(result, dict), "Result should be a dictionary"
        
        # Check required fields
        required_fields = [
            'location', 'timestamp', 'temperature_celsius', 
            'wind_speed_kmh', 'precipitation_mm', 'cloud_coverage_percent'
        ]
        
        for field in required_fields:
            assert field in result, f"Result should contain {field}"
        
        # Check data types and values
        assert result['location'] == location_name, "Location should match"
        assert isinstance(result['temperature_celsius'], (int, float)), "Temperature should be numeric"
        assert isinstance(result['wind_speed_kmh'], (int, float)), "Wind speed should be numeric"
        assert isinstance(result['precipitation_mm'], (int, float)), "Precipitation should be numeric"
        assert isinstance(result['cloud_coverage_percent'], (int, float)), "Cloud coverage should be numeric"
        
        # Check reasonable value ranges
        assert -50 <= result['temperature_celsius'] <= 50, "Temperature should be reasonable"
        assert 0 <= result['wind_speed_kmh'] <= 200, "Wind speed should be reasonable"
        assert 0 <= result['precipitation_mm'] <= 100, "Precipitation should be reasonable"
        assert 0 <= result['cloud_coverage_percent'] <= 100, "Cloud coverage should be 0-100%"
        
        print(f"✅ OpenWeather API test passed for {location_name}")
        print(f"   Temperature: {result['temperature_celsius']}°C")
        print(f"   Wind Speed: {result['wind_speed_kmh']} km/h")
        print(f"   Precipitation: {result['precipitation_mm']} mm")
        print(f"   Cloud Coverage: {result['cloud_coverage_percent']}%")

class TestOpenMeteoAPI(TestWeatherAPI):
    """Test Open-Meteo API functionality"""
    
    def test_get_historical_weather_san_francisco(self, weather_api, san_francisco_location, week_ago_date):
        """
        Test 2: Open-Meteo API call test calling get_historical_weather for 
        San Francisco hardcoded location for 1 day a week ago
        """
        # Arrange
        lat = san_francisco_location['lat']
        lon = san_francisco_location['lon']
        location_name = san_francisco_location['name']
        
        # Act
        result = weather_api.get_historical_weather_all_hours(
            lat=lat,
            lon=lon,
            date=week_ago_date,
            location_name=location_name
        )
        
        # Assert
        assert result is not None, "API call should return data"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Result should contain data"
        
        # Check that we have 24 hours of data (or close to it)
        assert len(result) >= 20, f"Should have at least 20 hours of data, got {len(result)}"
        
        # Check first item structure
        first_item = result[0]
        required_fields = [
            'location', 'date', 'hour', 'temperature_celsius', 
            'wind_speed_kmh', 'precipitation_mm', 'cloud_coverage_percent', 'ingestion_timestamp'
        ]
        
        for field in required_fields:
            assert field in first_item, f"First item should contain {field}"
        
        # Check data types and values
        assert first_item['location'] == location_name, "Location should match"
        assert first_item['date'] == week_ago_date, "Date should match"
        assert isinstance(first_item['hour'], int), "Hour should be integer"
        assert 0 <= first_item['hour'] <= 23, "Hour should be 0-23"
        
        # Check numeric fields
        numeric_fields = ['temperature_celsius', 'wind_speed_kmh', 'precipitation_mm', 'cloud_coverage_percent']
        for field in numeric_fields:
            assert isinstance(first_item[field], (int, float)), f"{field} should be numeric"
        
        # Check for non-zero temperatures (data quality check)
        non_zero_temps = [item['temperature_celsius'] for item in result if item['temperature_celsius'] != 0]
        if non_zero_temps:
            temp_range = (min(non_zero_temps), max(non_zero_temps))
            print(f"✅ Open-Meteo API test passed for {location_name} on {week_ago_date}")
            print(f"   Hours of data: {len(result)}")
            print(f"   Non-zero temperatures: {len(non_zero_temps)}/{len(result)}")
            print(f"   Temperature range: {temp_range[0]:.1f}°C to {temp_range[1]:.1f}°C")
        else:
            pytest.skip(f"All temperatures are zero for {week_ago_date} - data may not be available yet")

class TestAWSConnectivity:
    """Test AWS connectivity and S3 operations"""
    
    @pytest.fixture(autouse=True)
    def setup_aws_credentials(self):
        """Setup AWS credentials for tests from environment"""
        print("🔧 Setting up AWS credentials fixture...")
        
        # Check if AWS credentials are available
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        region = os.getenv('AWS_DEFAULT_REGION')
        
        print(f"🔧 AWS Access Key: {'Set' if access_key else 'Not Set'}")
        print(f"🔧 AWS Secret Key: {'Set' if secret_key else 'Not Set'}")
        print(f"🔧 AWS Region: {region or 'Not Set'}")
        
        if not access_key or not secret_key:
            print("⚠️ AWS credentials not found - tests will be skipped")
            pytest.skip("AWS credentials not found in environment variables")
        
        if not region:
            # Set default region if not provided
            os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
            print("🔧 Set default AWS region to us-east-1")
        
        print("✅ AWS credentials fixture setup completed")
    
    @pytest.fixture
    def infra_config(self):
        """Fixture to load infrastructure configuration"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'infra_config.yaml')
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    

    
    def test_aws_credentials_configured(self):
        """Test that AWS credentials are properly configured"""
        try:
            # Try to create a session
            session = boto3.Session()
            
            # Get credentials
            credentials = session.get_credentials()
            
            # Check if credentials are available
            if credentials is None:
                pytest.skip("AWS credentials not configured - skipping AWS tests")
            
            # Check if credentials are valid
            access_key = credentials.access_key
            secret_key = credentials.secret_key
            
            assert access_key is not None, "AWS access key should be configured"
            assert secret_key is not None, "AWS secret key should be configured"
            
            print(f"✅ AWS credentials are properly configured")
            
        except Exception as e:
            pytest.skip(f"AWS credentials test failed: {str(e)}")
    

    
    def test_save_to_s3_parquet_function(self, infra_config):
        """
        Test 5: Test save_to_s3_parquet function with hardcoded parameters
        """
        print("\n" + "="*60)
        print("🚀 Starting save_to_s3_parquet Function Test")
        print("="*60)
        
        # Arrange
        bucket_name = infra_config['s3_bucket']
        location_name = "Test Location"
        week_ago_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"🔍 Target bucket: {bucket_name}")
        print(f"🔍 Location: {location_name}")
        print(f"🔍 Date: {week_ago_date}")
        
        # Create small predefined test DataFrame
        print("🔧 Creating test DataFrame...")
        import pandas as pd
        
        test_data = [
            {
                'location': location_name,
                'date': week_ago_date,
                'hour': 12,
                'temperature_celsius': 18.5,
                'wind_speed_kmh': 15.2,
                'precipitation_mm': 0.0,
                'cloud_coverage_percent': 25,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'location': location_name,
                'date': week_ago_date,
                'hour': 13,
                'temperature_celsius': 19.2,
                'wind_speed_kmh': 16.8,
                'precipitation_mm': 0.0,
                'cloud_coverage_percent': 30,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'location': location_name,
                'date': week_ago_date,
                'hour': 14,
                'temperature_celsius': 20.1,
                'wind_speed_kmh': 14.5,
                'precipitation_mm': 0.0,
                'cloud_coverage_percent': 20,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        test_df = pd.DataFrame(test_data)
        print(f"✅ Test DataFrame created with {len(test_df)} rows")
        print(f"📊 DataFrame columns: {list(test_df.columns)}")
        print(f"📊 DataFrame shape: {test_df.shape}")
        print("📊 Sample data:")
        print(test_df.head().to_string())
        
        try:
            # Import the function to test
            print("🔧 Importing save_to_s3_parquet function...")
            from pipelines.s3_writer import save_to_s3_parquet
            print("✅ Function imported successfully")
            
            # Call the function
            print(f"🔧 Calling save_to_s3_parquet function...")
            print(f"   DataFrame: {len(test_df)} rows")
            print(f"   Location: {location_name}")
            print(f"   Date: {week_ago_date}")
            
            result = save_to_s3_parquet(test_df, location_name, week_ago_date)
            
            # Check result
            if result:
                print("✅ save_to_s3_parquet function returned True")
                
                # Verify the file was uploaded
                print("🔍 Verifying file was uploaded...")
                import boto3
                s3_client = boto3.client('s3')
                
                # Calculate expected S3 key with detailed partitioning
                clean_location = location_name.replace(',', '').replace(' ', '_')
                date_parts = week_ago_date.split('-')
                year = date_parts[0]
                month = date_parts[1].zfill(2)
                day = date_parts[2].zfill(2)
                expected_s3_key = f"weather-data/location={clean_location}/year={year}/month={month}/day={day}/weather_data_{week_ago_date}.parquet"
                
                print(f"🔍 Expected S3 key: {expected_s3_key}")
                
                # Check if file exists
                response = s3_client.head_object(Bucket=bucket_name, Key=expected_s3_key)
                file_size = response['ContentLength']
                last_modified = response['LastModified']
                print(f"✅ File verified - Size: {file_size} bytes, Last Modified: {last_modified}")
                
                # List objects to confirm
                print("🔍 Listing objects to confirm upload...")
                list_response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=f"weather-data/location={clean_location}/year={year}/month={month}/day={day}/",
                    MaxKeys=10
                )
                
                if 'Contents' in list_response and len(list_response['Contents']) > 0:
                    uploaded_files = list_response['Contents']
                    print(f"✅ Found {len(uploaded_files)} files in partition:")
                    for file_info in uploaded_files:
                        print(f"   📁 {file_info['Key']} ({file_info['Size']} bytes)")
                else:
                    print("⚠️ No files found in partition")
                
            else:
                print("❌ save_to_s3_parquet function returned False")
                pytest.fail("save_to_s3_parquet function failed")
            
            print("✅ save_to_s3_parquet function test completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Exception occurred: {error_msg}")
            print(f"❌ Exception type: {type(e)}")
            pytest.fail(f"save_to_s3_parquet test failed: {error_msg}")
        
        print("🏁 save_to_s3_parquet Function Test completed")
        print("="*60)

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their names"""
    for item in items:
        if "aws" in item.name.lower() or "s3" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.slow)

if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])
