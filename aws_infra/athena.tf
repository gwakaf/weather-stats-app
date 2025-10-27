# Athena Workgroup
resource "aws_athena_workgroup" "weather_workgroup" {
  count = 1
  name  = local.workgroup_name

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_output[0].bucket}/"
      
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }

  tags = {
    Name = "Weather Finder Athena Workgroup"
  }
}

# Note: IAM roles and policies removed since the app uses direct user credentials
# The user's AWS credentials should have the required permissions for:
# - S3 access (read/write to buckets)
# - Athena access (query execution)
# - Glue access (database/table operations) 