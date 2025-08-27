terraform {
  required_version = "1.13.1"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"
    }
  }
}
