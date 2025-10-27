# Glue Database
resource "aws_glue_catalog_database" "weather_db" {
  count       = 1
  name        = local.database_name
  description = "Weather Finder historic data database"

  catalog_id = data.aws_caller_identity.current.account_id
}

# Glue Table for weather data
resource "aws_glue_catalog_table" "weather_table" {
  count         = 1
  name          = local.table_name
  database_name = aws_glue_catalog_database.weather_db[0].name
  catalog_id    = data.aws_caller_identity.current.account_id

  description = "Historic weather data table"

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${try(aws_s3_bucket.weather_data[0].bucket, data.aws_s3_bucket.existing_weather_data[0].bucket)}/weather-data/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "date"
      type = "string"
    }

    columns {
      name = "hour"
      type = "int"
    }

    columns {
      name = "temperature_celsius"
      type = "double"
    }

    columns {
      name = "wind_speed_kmh"
      type = "double"
    }

    columns {
      name = "precipitation_mm"
      type = "double"
    }

    columns {
      name = "cloud_coverage_percent"
      type = "double"
    }

    columns {
      name = "ingestion_timestamp"
      type = "string"
    }
  }

  partition_keys {
    name = "location"
    type = "string"
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  partition_keys {
    name = "day"
    type = "int"
  }

  parameters = {
    "EXTERNAL" = "TRUE"
    "parquet.compression" = "SNAPPY"
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {} 