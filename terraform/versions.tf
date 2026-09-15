terraform {
  required_version = ">= 1.15.8, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.64.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.8.1"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.9.1"
    }
  }
}
