terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
    # Módulo A/C/D: RDS, VPC Flow Logs y Security Hub de AWS (data-service, Golden Signals
    # de seguridad y correlación con AWS DevOps Guru).
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "aws" {
  region = var.aws_region
}

