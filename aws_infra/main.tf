terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "weather-finder"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "weather-finder"
}

# Read configuration from aws_infra_config.yaml
locals {
  config = yamldecode(file("${path.module}/../config/aws_infra_config.yaml"))
  
  # Extract values from config
  bucket_name           = local.config.s3_bucket
  athena_output_bucket  = local.config.athena_output_bucket
  database_name         = local.config.glue_database
  table_name            = local.config.glue_table
  workgroup_name        = local.config.athena_workgroup
}

# Data sources to check for existing resources (only for resources that support data sources)
data "aws_s3_bucket" "existing_weather_data" {
  bucket = local.bucket_name
  count  = var.check_existing_resources ? 1 : 0
}

# Note: Athena output bucket data source removed since it doesn't exist yet
# It will be created by Terraform if needed

# Variable to control resource existence checks
variable "check_existing_resources" {
  description = "Check for existing resources before creating new ones"
  type        = bool
  default     = true
}

# Outputs with existence checks
output "s3_bucket_name" {
  description = "Name of the S3 bucket for weather data"
  value       = try(aws_s3_bucket.weather_data[0].bucket, data.aws_s3_bucket.existing_weather_data[0].bucket, "Not found")
}

output "athena_output_bucket" {
  description = "Name of the S3 bucket for Athena output"
  value       = try(aws_s3_bucket.athena_output[0].bucket, "Not found")
}

output "glue_database_name" {
  description = "Name of the Glue database"
  value       = try(aws_glue_catalog_database.weather_db[0].name, "Not found")
}

output "glue_table_name" {
  description = "Name of the Glue table"
  value       = try(aws_glue_catalog_table.weather_table[0].name, "Not found")
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = try(aws_athena_workgroup.weather_workgroup[0].name, "Not found")
}

# Resource existence status outputs (simplified)
output "resource_status" {
  description = "Status of each resource"
  value = {
    s3_bucket_exists          = try(data.aws_s3_bucket.existing_weather_data[0].bucket, null) != null
    athena_output_exists      = "Will be created by Terraform"
    glue_database_exists      = "Unknown - will be created if needed"
    athena_workgroup_exists   = "Unknown - will be created if needed"
  }
} 