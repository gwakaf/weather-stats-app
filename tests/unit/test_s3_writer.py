#!/usr/bin/env python3
"""
Unit tests for S3 Writer
Tests S3 writer functions with mocked dependencies using pytest-mock.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import mock_open


class TestGetS3Config:
    """Test get_s3_config function"""
    
    def test_get_s3_config_from_file(self, mocker, mock_infra_config):
        """Test successful S3 config loading from file"""
        from pipelines.s3_writer import get_s3_config
        
        # Mock file content
        mock_file_content = "s3_bucket: test-weather-data\n"
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data=mock_file_content))
        
        # Mock yaml.safe_load
        mocker.patch('pipelines.s3_writer.yaml.safe_load', return_value={'s3_bucket': 'test-weather-data'})
        
        result = get_s3_config()
        
        assert result == 'test-weather-data'
    
    def test_get_s3_config_file_not_found(self, mocker):
        """Test S3 config loading when file not found, falls back to env var"""
        from pipelines.s3_writer import get_s3_config
        
        # Mock file not found
        mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))
        
        # Mock environment variable
        mocker.patch.dict('os.environ', {'S3_BUCKET': 'fallback-bucket'})
        
        result = get_s3_config()
        
        assert result == 'fallback-bucket'
    
    def test_get_s3_config_file_error_fallback(self, mocker):
        """Test S3 config loading when file read fails, falls back to env var"""
        from pipelines.s3_writer import get_s3_config
        
        # Mock file read error
        mocker.patch('builtins.open', side_effect=Exception("Read error"))
        
        # Mock environment variable
        mocker.patch.dict('os.environ', {'S3_BUCKET': 'env-bucket'})
        
        result = get_s3_config()
        
        assert result == 'env-bucket'
    
    def test_get_s3_config_no_env_var_default(self, mocker):
        """Test S3 config loading when no env var, uses default"""
        from pipelines.s3_writer import get_s3_config
        
        # Mock file read error
        mocker.patch('builtins.open', side_effect=Exception("Read error"))
        
        # No environment variable set
        mocker.patch.dict('os.environ', {}, clear=True)
        mocker.patch('pipelines.s3_writer.os.getenv', return_value='weather-data-yy')
        
        result = get_s3_config()
        
        assert result == 'weather-data-yy'


class TestSaveToS3Parquet:
    """Test save_to_s3_parquet function"""
    
    def test_save_to_s3_parquet_success(self, mocker, sample_dataframe, mock_infra_config):
        """Test successful S3 parquet upload"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        # Mock get_s3_config
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        # Mock boto3 client
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        result = save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', '2024-01-15')
        
        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()
        
        # Verify S3 key format
        call_args = mock_s3_client.upload_fileobj.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert 'location=San_Francisco_CA' in call_args[1]['Key']
        assert 'year=2024' in call_args[1]['Key']
        assert 'month=01' in call_args[1]['Key']
        assert 'day=15' in call_args[1]['Key']
        assert 'weather_data_2024-01-15.parquet' in call_args[1]['Key']
    
    def test_save_to_s3_parquet_location_name_cleaning(self, mocker, sample_dataframe):
        """Test that location name is properly cleaned for S3 key"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        save_to_s3_parquet(sample_dataframe, 'Menlo Park, CA', '2024-01-15')
        
        call_args = mock_s3_client.upload_fileobj.call_args
        assert 'location=Menlo_Park_CA' in call_args[1]['Key']
    
    def test_save_to_s3_parquet_date_format(self, mocker, sample_dataframe):
        """Test that date is properly formatted in S3 key"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', '2024-12-25')
        
        call_args = mock_s3_client.upload_fileobj.call_args
        assert 'year=2024' in call_args[1]['Key']
        assert 'month=12' in call_args[1]['Key']
        assert 'day=25' in call_args[1]['Key']
        assert 'weather_data_2024-12-25.parquet' in call_args[1]['Key']
    
    def test_save_to_s3_parquet_single_digit_month_day(self, mocker, sample_dataframe):
        """Test that single-digit months and days are zero-padded"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', '2024-1-5')
        
        call_args = mock_s3_client.upload_fileobj.call_args
        assert 'month=01' in call_args[1]['Key']
        assert 'day=05' in call_args[1]['Key']
    
    def test_save_to_s3_parquet_invalid_date_format(self, mocker, sample_dataframe):
        """Test that invalid date format falls back to current date"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        # Mock datetime.now() to return a fixed date
        mock_now = datetime(2024, 6, 15, 12, 0, 0)
        mocker.patch('pipelines.s3_writer.datetime', wraps=datetime)
        mocker.patch('pipelines.s3_writer.datetime.now', return_value=mock_now)
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', 'invalid-date')
        
        call_args = mock_s3_client.upload_fileobj.call_args
        assert 'year=2024' in call_args[1]['Key']
        assert 'month=06' in call_args[1]['Key']
        assert 'day=15' in call_args[1]['Key']
    
    def test_save_to_s3_parquet_boto3_error(self, mocker, sample_dataframe):
        """Test S3 upload when boto3 client raises error"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj.side_effect = Exception("S3 upload error")
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        result = save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', '2024-01-15')
        
        assert result is False
    
    def test_save_to_s3_parquet_dataframe_error(self, mocker):
        """Test S3 upload when DataFrame conversion fails"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        # Create a DataFrame that will fail when converting to parquet
        # by mocking to_parquet to raise an error
        mock_df = mocker.Mock(spec=pd.DataFrame)
        mock_df.to_parquet.side_effect = Exception("Parquet conversion error")
        
        result = save_to_s3_parquet(mock_df, 'San Francisco, CA', '2024-01-15')
        
        assert result is False
    
    def test_save_to_s3_parquet_empty_dataframe(self, mocker):
        """Test S3 upload with empty DataFrame"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        empty_df = pd.DataFrame()
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        result = save_to_s3_parquet(empty_df, 'San Francisco, CA', '2024-01-15')
        
        assert result is True
        mock_s3_client.upload_fileobj.assert_called_once()
    
    def test_save_to_s3_parquet_s3_key_structure(self, mocker, sample_dataframe):
        """Test that S3 key has correct partitioned structure"""
        from pipelines.s3_writer import save_to_s3_parquet
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        save_to_s3_parquet(sample_dataframe, 'New York, NY', '2024-03-20')
        
        call_args = mock_s3_client.upload_fileobj.call_args
        s3_key = call_args[1]['Key']
        
        # Verify key structure: weather-data/location=.../year=.../month=.../day=.../weather_data_....parquet
        assert s3_key.startswith('weather-data/')
        assert 'location=New_York_NY' in s3_key
        assert 'year=2024' in s3_key
        assert 'month=03' in s3_key
        assert 'day=20' in s3_key
        assert s3_key.endswith('weather_data_2024-03-20.parquet')
    
    def test_save_to_s3_parquet_buffer_operations(self, mocker, sample_dataframe):
        """Test that buffer operations are correct"""
        from pipelines.s3_writer import save_to_s3_parquet
        import io
        
        mocker.patch('pipelines.s3_writer.get_s3_config', return_value='test-bucket')
        
        mock_s3_client = mocker.Mock()
        mock_s3_client.upload_fileobj = mocker.Mock()
        mocker.patch('pipelines.s3_writer.boto3.client', return_value=mock_s3_client)
        
        result = save_to_s3_parquet(sample_dataframe, 'San Francisco, CA', '2024-01-15')
        
        assert result is True
        # Verify upload_fileobj was called
        mock_s3_client.upload_fileobj.assert_called_once()
        # Verify the first argument is a file-like object (buffer)
        call_args = mock_s3_client.upload_fileobj.call_args
        assert hasattr(call_args[0][0], 'read')  # Buffer should have read method
