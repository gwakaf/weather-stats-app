# Weather Finder AWS Infrastructure

This directory contains Terraform configuration files to deploy the AWS infrastructure required for the Weather Finder application.

## Infrastructure Components

- **S3 Buckets**: 
  - Weather data storage (Parquet files)
  - Athena query output
- **Glue Database & Table**: Metadata catalog for the weather data
- **Athena Workgroup**: Query engine configuration
- **IAM Roles & Policies**: Access permissions for the application

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** (version >= 1.0)
3. **AWS Permissions** for:
   - S3 (create buckets, manage objects)
   - Glue (create database, tables)
   - Athena (create workgroup, execute queries)
   - IAM (create roles, policies)

## Configuration

All AWS resource names are configured in `infra_config.yaml`:

```yaml
s3_bucket: weather-data-yy
athena_output_bucket: weather-data-yy-athena-output
glue_database: weather_finder_db
glue_table: historic_weather
athena_workgroup: weather-finder-workgroup
```

**Important**: 
- Terraform reads these values from `infra_config.yaml`
- The application also reads from the same file
- No need to manually sync configuration between Terraform and the app
- Only AWS credentials and region should be in `.env` file

## Deployment Steps

1. **Initialize Terraform**:
   ```bash
   cd infra
   terraform init
   ```

2. **Configure Variables** (Optional):
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your desired values
   ```

3. **Plan Deployment**:
   ```bash
   terraform plan
   ```

4. **Deploy Infrastructure**:
   ```bash
   terraform apply
   ```

## Environment Variables

The application automatically reads AWS resource names from `infra_config.yaml`. You only need to set these in your `.env` file:

- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key  
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)

## Cleanup

To destroy the infrastructure:

```bash
terraform destroy
```

**Warning**: This will delete all data stored in S3 buckets.

## File Structure

- `main.tf` - Main configuration, providers, variables, and outputs
- `s3.tf` - S3 bucket configurations
- `glue.tf` - Glue database and table definitions
- `athena.tf` - Athena workgroup and IAM permissions
- `infra_config.yaml` - AWS resource configuration
- `terraform.tfvars.example` - Example variables file
- `deploy.sh` - Deployment script
- `README.md` - This file

## Security Features

- S3 buckets are encrypted with AES256
- Public access is blocked on all S3 buckets
- IAM policies follow least privilege principle
- Versioning enabled on S3 buckets
- Lifecycle policies for automatic cleanup of old Athena results

## Troubleshooting

### Common Issues

1. **Terraform not found**: Install Terraform from https://terraform.io
2. **AWS credentials not configured**: Run `aws configure` or set environment variables
3. **Permission denied**: Ensure your AWS user has the required permissions
4. **Bucket already exists**: Change the bucket name in `infra_config.yaml`

### Getting Help

- Check Terraform logs for detailed error messages
- Verify AWS credentials and permissions
- Ensure all prerequisites are installed
- Review the main project README for additional setup instructions 