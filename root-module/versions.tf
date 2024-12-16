terraform {
  required_version = "1.8.7"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0.0"
    }
  }
}
