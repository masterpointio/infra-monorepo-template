# Purpose:
# The versions.tf file sets explicit Terraform and provider versions, ensuring that users run a known-compatible setup.

# Best Practices:
# - Pessimistic version constraints: Use version constraints (e.g., required_version = "~> 1.3") to allow patch updates but prevent breaking changes.
# - Stability over time: Regularly review and update version constraints as Terraform and providers evolve.

terraform {
  required_version = "~> 1.0"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
