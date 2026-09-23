terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "ml-app-terraform-state"
    key    = "ml-app/eks/terraform.tfstate"
    region = "us-east-1"

    dynamodb_table = "ml-app-terraform-locks"

    endpoint          = "http://localhost:4566"
    dynamodb_endpoint = "http://localhost:4566"

    access_key                  = "test"
    secret_key                  = "test"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    force_path_style            = true

  }
}

provider "aws" {
  region = "us-east-1"

  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    s3       = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    ec2      = "http://localhost:4566"
    iam      =  "http://localhost:4566"
    ecr = "http://localhost:4566"
     eks      = "http://localhost:4566"
     elbv2 = "http://localhost:4566"
    rds      = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "tf_state" {
  bucket = "ml-app-terraform-state"
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "tf_lock" {
  name         = "ml-app-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

