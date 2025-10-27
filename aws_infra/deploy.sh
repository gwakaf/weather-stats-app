#!/bin/bash

# Weather Finder AWS Infrastructure Deployment Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the infra directory
if [ ! -f "main.tf" ]; then
    print_error "Please run this script from the infra directory"
    echo "  cd infra"
    echo "  ./deploy.sh"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install it first:"
    echo "  https://www.terraform.io/downloads.html"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS CLI is not configured. Please run:"
    echo "  aws configure"
    exit 1
fi

print_status "Starting Weather Finder AWS infrastructure deployment..."

# Step 1: Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Step 2: Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_warning "terraform.tfvars not found. Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    print_status "Please edit terraform.tfvars with your desired values, then run this script again."
    exit 0
fi

# Step 3: Check for existing resources
print_status "Checking for existing AWS resources..."
terraform plan -out=tfplan > /dev/null 2>&1 || true

# Step 4: Plan deployment
print_status "Planning Terraform deployment..."
terraform plan

# Step 5: Confirm deployment
echo
read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled."
    exit 0
fi

# Step 6: Apply deployment
print_status "Deploying infrastructure..."
terraform apply -auto-approve

# Step 7: Show outputs
print_success "Infrastructure deployment completed!"
echo
print_status "Terraform outputs:"
terraform output

# Step 8: Show resource status
echo
print_status "Resource Status:"
RESOURCE_STATUS=$(terraform output -json resource_status 2>/dev/null || echo "{}")

if echo "$RESOURCE_STATUS" | grep -q "true"; then
    print_warning "Some resources already existed and were not recreated:"
    echo "$RESOURCE_STATUS" | jq -r 'to_entries[] | select(.value == true) | "  ✅ \(.key | gsub("_"; " ") | ascii_upcase): Already exists"'
fi

if echo "$RESOURCE_STATUS" | grep -q "false"; then
    print_success "New resources created:"
    echo "$RESOURCE_STATUS" | jq -r 'to_entries[] | select(.value == false) | "   \(.key | gsub("_"; " ") | ascii_upcase): Created"'
fi

echo
print_success "Configuration is managed through infra/infra_config.yaml"
print_status "No need to update .env file - the application reads from config automatically"

# Step 9: Show next steps
echo
print_success "Next steps:"
echo "1. Configure your AWS credentials in your application (.env file)"
echo "2. Run data ingestion: python ingest_historic_data.py"
echo "3. Test integration: python test_aws_integration.py"
echo "4. Start the application: python app.py" 