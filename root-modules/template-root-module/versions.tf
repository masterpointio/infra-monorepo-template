terraform {
  required_version = "1.16.6"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9.0"
    }
  }
}
