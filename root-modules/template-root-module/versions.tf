terraform {
  required_version = "1.15.3"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"
    }
  }
}
