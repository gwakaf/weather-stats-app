#!/usr/bin/env python3
"""
Unit tests for AWS Data Fetching Service
Tests AWSDataFetcher class methods with mocked AWS services.
"""

import os
import pytest

# Fixtures are automatically imported from conftest.py
from app.aws_fetching import AWSDataFetcher


class TestAWSDataFetcher:
    """Test class for AWSDataFetcher functionality"""
    
    def test_init_success(self, mocker, mock_infra_config, mock_locations_config, mock_aws_clients):
        """Test successful initialization of AWSDataFetcher"""
        # Setup mocks
        mock_get_infra = mocker.patch('app.aws_fetching.get_infra_config')
        mock_get_locations = mocker.patch('app.aws_fetching.get_locations_config')
        mock_boto3 = mocker.patch('app.aws_fetching.boto3.client')
        mocker.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'})
        
        mock_get_infra.return_value = mock_infra_config
        mock_get_locations.return_value = mock_locations_config
        
        # Mock boto3 clients
        mock_boto3.side_effect = lambda service, **kwargs: mock_aws_clients.get(service)
        
        # Create instance
        fetcher = AWSDataFetcher()
        
        # Assertions
        assert fetcher.region == 'us-east-1'
        assert fetcher.bucket_name == 'test-weather-data'
        assert fetcher.database_name == 'test_weather_db'
        assert fetcher.table_name == 'test_historic_weather'
        assert fetcher.workgroup_name == 'test-workgroup'
        assert len(fetcher.locations) == 2
        assert 'San Francisco, CA' in fetcher.locations
        assert fetcher.s3_client is not None
        assert fetcher.athena_client is not None
        assert fetcher.glue_client is not None
    
    def test_init_with_config_fallback(self, mocker):
        """Test initialization with config fallback to defaults"""
        # Setup mocks
        mock_get_infra = mocker.patch('app.aws_fetching.get_infra_config')
        mock_get_locations = mocker.patch('app.aws_fetching.get_locations_config')
        mocker.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-west-2'}, clear=True)
        
        # Simulate config loading failure
        mock_get_infra.side_effect = Exception("Config not found")
        mock_get_locations.side_effect = Exception("Locations not found")
        
        mocker.patch('app.aws_fetching.boto3.client', side_effect=Exception("No AWS credentials"))
        
        fetcher = AWSDataFetcher()
        
        # Should use default values
        assert fetcher.bucket_name == "weather-data-dev"
        assert fetcher.database_name == "weather_finder_db"
        assert fetcher.locations == {}
        assert fetcher.s3_client is None
        assert fetcher.athena_client is None
    
    def test_get_available_locations(self, setup_aws_mocks):
        """Test getting available locations"""
        fetcher = AWSDataFetcher()
        locations = fetcher.get_available_locations()
        
        assert isinstance(locations, list)
        assert len(locations) == 2
        assert 'San Francisco, CA' in locations
        assert 'Menlo Park, CA' in locations
    
    def test_get_location_coordinates_existing(self, setup_aws_mocks):
        """Test getting coordinates for existing location"""
        fetcher = AWSDataFetcher()
        coords = fetcher.get_location_coordinates('San Francisco, CA')
        
        assert coords is not None
        assert coords['lat'] == 37.7749
        assert coords['lon'] == -122.4194
    
    def test_get_location_coordinates_nonexistent(self, setup_aws_mocks):
        """Test getting coordinates for non-existent location"""
        fetcher = AWSDataFetcher()
        coords = fetcher.get_location_coordinates('Non-existent Location')
        
        assert coords is None
    
    def test_query_historic_data_no_client(self, mocker, mock_infra_config, mock_locations_config):
        """Test query_historic_data when AWS client is not available"""
        mock_get_infra = mocker.patch('app.aws_fetching.get_infra_config')
        mock_get_locations = mocker.patch('app.aws_fetching.get_locations_config')
        mock_get_infra.return_value = mock_infra_config
        mock_get_locations.return_value = mock_locations_config
        
        # Simulate no AWS client
        mocker.patch('app.aws_fetching.boto3.client', side_effect=Exception("No credentials"))
        
        fetcher = AWSDataFetcher()
        result = fetcher.query_historic_data('San Francisco, CA', '2024-01-15', 14)
        
        assert result is None
    
    def test_query_historic_data_success(self, mocker, setup_aws_mocks, mock_aws_clients):
        """Test successful query_historic_data"""
        # Mock sleep to speed up tests
        mocker.patch('app.aws_fetching.time.sleep')
        
        # Mock Athena query execution
        athena_client = mock_aws_clients['athena']
        athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-query-id-123'
        }
        
        # Mock query status - first pending, then succeeded
        athena_client.get_query_execution.side_effect = [
            {
                'QueryExecution': {
                    'Status': {'State': 'RUNNING'}
                }
            },
            {
                'QueryExecution': {
                    'Status': {'State': 'SUCCEEDED'}
                }
            }
        ]
        
        # Mock query results
        athena_client.get_query_results.return_value = {
            'ResultSet': {
                'Rows': [
                    {
                        'Data': [
                            {'VarCharValue': 'location'},
                            {'VarCharValue': 'date'},
                            {'VarCharValue': 'hour'},
                            {'VarCharValue': 'temperature_celsius'},
                            {'VarCharValue': 'wind_speed_kmh'},
                            {'VarCharValue': 'precipitation_mm'},
                            {'VarCharValue': 'cloud_coverage_percent'}
                        ]
                    },
                    {
                        'Data': [
                            {'VarCharValue': 'San_Francisco_CA'},
                            {'VarCharValue': '2024-01-15'},
                            {'VarCharValue': '14'},
                            {'VarCharValue': '18.5'},
                            {'VarCharValue': '12.3'},
                            {'VarCharValue': '0.0'},
                            {'VarCharValue': '45.0'}
                        ]
                    }
                ]
            }
        }
        
        fetcher = AWSDataFetcher()
        result = fetcher.query_historic_data('San Francisco, CA', '2024-01-15', 14)
        
        assert result is not None
        assert len(result) == 1
        assert result[0]['location'] == 'San_Francisco_CA'
        assert result[0]['date'] == '2024-01-15'
        assert result[0]['hour'] == 14
        assert result[0]['temperature_celsius'] == 18.5
        assert result[0]['wind_speed_kmh'] == 12.3
    
    def test_query_historic_data_failed_query(self, mocker, setup_aws_mocks, mock_aws_clients):
        """Test query_historic_data when query fails"""
        # Mock sleep to speed up tests
        mocker.patch('app.aws_fetching.time.sleep')
        
        athena_client = mock_aws_clients['athena']
        athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-query-id-123'
        }
        
        # Mock query status as FAILED
        athena_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {
                    'State': 'FAILED',
                    'StateChangeReason': 'Query syntax error'
                }
            }
        }
        
        fetcher = AWSDataFetcher()
        result = fetcher.query_historic_data('San Francisco, CA', '2024-01-15', 14)
        
        assert result is None
    
    def test_query_historic_data_without_hour(self, mocker, setup_aws_mocks, mock_aws_clients):
        """Test query_historic_data without specifying hour"""
        athena_client = mock_aws_clients['athena']
        athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-query-id-123'
        }
        
        fetcher = AWSDataFetcher()
        # Mock successful query
        athena_client.get_query_execution.return_value = {
            'QueryExecution': {'Status': {'State': 'SUCCEEDED'}}
        }
        athena_client.get_query_results.return_value = {
            'ResultSet': {'Rows': []}
        }
        
        result = fetcher.query_historic_data('San Francisco, CA', '2024-01-15')
        
        # Verify query was built without hour filter
        call_args = athena_client.start_query_execution.call_args
        assert 'hour' not in call_args[1]['QueryString'].lower() or 'AND hour' not in call_args[1]['QueryString']
    
    def test_parse_athena_results_empty(self, setup_aws_mocks):
        """Test parsing empty Athena results"""
        fetcher = AWSDataFetcher()
        
        # Test empty results
        empty_results = {'ResultSet': {'Rows': []}}
        parsed = fetcher._parse_athena_results(empty_results)
        assert parsed == []
        
        # Test only header row
        header_only = {
            'ResultSet': {
                'Rows': [
                    {'Data': [{'VarCharValue': 'location'}, {'VarCharValue': 'date'}]}
                ]
            }
        }
        parsed = fetcher._parse_athena_results(header_only)
        assert parsed == []
        
        # Test missing ResultSet
        no_resultset = {}
        parsed = fetcher._parse_athena_results(no_resultset)
        assert parsed == []
    
    def test_parse_athena_results_multiple_rows(self, setup_aws_mocks):
        """Test parsing Athena results with multiple data rows"""
        fetcher = AWSDataFetcher()
        
        results = {
            'ResultSet': {
                'Rows': [
                    # Header row
                    {
                        'Data': [
                            {'VarCharValue': 'location'},
                            {'VarCharValue': 'date'},
                            {'VarCharValue': 'hour'},
                            {'VarCharValue': 'temperature_celsius'},
                            {'VarCharValue': 'wind_speed_kmh'},
                            {'VarCharValue': 'precipitation_mm'},
                            {'VarCharValue': 'cloud_coverage_percent'}
                        ]
                    },
                    # Data row 1
                    {
                        'Data': [
                            {'VarCharValue': 'San_Francisco_CA'},
                            {'VarCharValue': '2024-01-15'},
                            {'VarCharValue': '12'},
                            {'VarCharValue': '20.0'},
                            {'VarCharValue': '10.5'},
                            {'VarCharValue': '0.0'},
                            {'VarCharValue': '30.0'}
                        ]
                    },
                    # Data row 2
                    {
                        'Data': [
                            {'VarCharValue': 'San_Francisco_CA'},
                            {'VarCharValue': '2024-01-15'},
                            {'VarCharValue': '13'},
                            {'VarCharValue': '21.5'},
                            {'VarCharValue': '11.2'},
                            {'VarCharValue': '0.5'},
                            {'VarCharValue': '35.0'}
                        ]
                    }
                ]
            }
        }
        
        parsed = fetcher._parse_athena_results(results)
        
        assert len(parsed) == 2
        assert parsed[0]['hour'] == 12
        assert parsed[0]['temperature_celsius'] == 20.0
        assert parsed[1]['hour'] == 13
        assert parsed[1]['temperature_celsius'] == 21.5
        assert parsed[1]['precipitation_mm'] == 0.5
    
    def test_verify_infrastructure_success(self, setup_aws_mocks, mock_aws_clients):
        """Test successful infrastructure verification"""
        # Mock successful infrastructure checks
        mock_aws_clients['s3'].head_bucket.return_value = None
        mock_aws_clients['glue'].get_database.return_value = {}
        mock_aws_clients['glue'].get_table.return_value = {}
        mock_aws_clients['athena'].get_work_group.return_value = {}
        
        fetcher = AWSDataFetcher()
        result = fetcher.verify_infrastructure()
        
        assert result is True
        mock_aws_clients['s3'].head_bucket.assert_called_once_with(Bucket='test-weather-data')
        mock_aws_clients['glue'].get_database.assert_called_once_with(Name='test_weather_db')
        mock_aws_clients['glue'].get_table.assert_called_once_with(
            DatabaseName='test_weather_db',
            Name='test_historic_weather'
        )
        mock_aws_clients['athena'].get_work_group.assert_called_once_with(WorkGroup='test-workgroup')
    
    def test_verify_infrastructure_no_clients(self, mocker, mock_infra_config, mock_locations_config):
        """Test infrastructure verification when clients are not available"""
        mock_get_infra = mocker.patch('app.aws_fetching.get_infra_config')
        mock_get_locations = mocker.patch('app.aws_fetching.get_locations_config')
        mock_get_infra.return_value = mock_infra_config
        mock_get_locations.return_value = mock_locations_config
        
        # Simulate no AWS clients
        mocker.patch('app.aws_fetching.boto3.client', side_effect=Exception("No credentials"))
        
        fetcher = AWSDataFetcher()
        result = fetcher.verify_infrastructure()
        
        assert result is False
    
    def test_verify_infrastructure_bucket_not_found(self, setup_aws_mocks, mock_aws_clients):
        """Test infrastructure verification when bucket doesn't exist"""
        # Mock bucket not found error
        from botocore.exceptions import ClientError
        mock_aws_clients['s3'].head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadBucket'
        )
        
        fetcher = AWSDataFetcher()
        result = fetcher.verify_infrastructure()
        
        assert result is False
    
    def test_query_historic_data_exception_handling(self, setup_aws_mocks, mock_aws_clients):
        """Test query_historic_data handles exceptions gracefully"""
        athena_client = mock_aws_clients['athena']
        athena_client.start_query_execution.side_effect = Exception("AWS service error")
        
        fetcher = AWSDataFetcher()
        result = fetcher.query_historic_data('San Francisco, CA', '2024-01-15', 14)
        
        assert result is None
