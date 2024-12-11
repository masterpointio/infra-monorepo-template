# Purpose:
# The versions.tf file specifies the minimum allowed Terraform and provider versions using `>=`, ensuring consistency and compatibility.

# Best Practices:
# - Terraform requirements: Use required_version to pin known-compatible Terraform versions (e.g., required_version = ">= 1.3").
# - Provider requirements: Lock provider versions with required_providers to avoid unexpected upgrades (e.g., aws = { source = "hashicorp/aws" version = ">= 5.0" }).
# - Stability over time: Regularly review and update version constraints as Terraform and providers evolve.

terraform {
  required_version = ">= 1.0"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}
