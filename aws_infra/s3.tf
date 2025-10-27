# S3 Bucket for weather data storage
resource "aws_s3_bucket" "weather_data" {
  count  = var.check_existing_resources && try(data.aws_s3_bucket.existing_weather_data[0].bucket, null) == null ? 1 : 0
  bucket = local.bucket_name

  tags = {
    Name        = "Weather Finder Data"
    Description = "S3 bucket for storing weather data in Parquet format"
  }

  lifecycle {
    ignore_changes = [bucket]
  }
}

# S3 Bucket versioning for weather data
resource "aws_s3_bucket_versioning" "weather_data" {
  count  = var.check_existing_resources && try(data.aws_s3_bucket.existing_weather_data[0].bucket, null) == null ? 1 : 0
  bucket = aws_s3_bucket.weather_data[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption for weather data
resource "aws_s3_bucket_server_side_encryption_configuration" "weather_data" {
  count  = var.check_existing_resources && try(data.aws_s3_bucket.existing_weather_data[0].bucket, null) == null ? 1 : 0
  bucket = aws_s3_bucket.weather_data[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket public access block for weather data
resource "aws_s3_bucket_public_access_block" "weather_data" {
  count  = var.check_existing_resources && try(data.aws_s3_bucket.existing_weather_data[0].bucket, null) == null ? 1 : 0
  bucket = aws_s3_bucket.weather_data[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket for Athena output
resource "aws_s3_bucket" "athena_output" {
  count  = 1
  bucket = local.athena_output_bucket

  tags = {
    Name        = "Weather Finder Athena Output"
    Description = "S3 bucket for Athena query results"
  }

  lifecycle {
    ignore_changes = [bucket]
  }
}

# S3 Bucket versioning for Athena output
resource "aws_s3_bucket_versioning" "athena_output" {
  count  = 1
  bucket = aws_s3_bucket.athena_output[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption for Athena output
resource "aws_s3_bucket_server_side_encryption_configuration" "athena_output" {
  count  = 1
  bucket = aws_s3_bucket.athena_output[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket public access block for Athena output
resource "aws_s3_bucket_public_access_block" "athena_output" {
  count  = 1
  bucket = aws_s3_bucket.athena_output[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket lifecycle policy for Athena output (clean up old query results)
resource "aws_s3_bucket_lifecycle_configuration" "athena_output" {
  count  = 1
  bucket = aws_s3_bucket.athena_output[0].id

  rule {
    id     = "cleanup_old_query_results"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
} 