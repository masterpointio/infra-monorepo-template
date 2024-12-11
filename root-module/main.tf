# Purpose:
# The main.tf file in a root module is the entry point for defining and orchestrating your infrastructure.
# It may include resource definitions, calls to child modules, and overall configuration logic.

# Best Practices:
# - Resource declarations: Place core resources that are unique to this layer of your infrastructure.
# - Module calls:
#   - Use Terraform Registry Modules with Version Pinning:
#       module "vpc" {
#         source  = "terraform-aws-modules/vpc/aws"
#         version = "1.0.0"
#       }
#   - Use Git Sources with a Specific Tag or Commit:
#       module "vpc" {
#         source = "git::https://github.com/org/terraform-aws-vpc.git?ref=v1.0.0".
#       }
# - Logical grouping: Group related resources and modules logically and use comments to explain complex logic.
# - Minimal hard-coding: Use variables defined in variables.tf instead of hard-coded values for flexibility and reusability.

locals {
  # Get the current timestamp and format it as YYYYMMDD
  prefix = formatdate("YYYYMMDD", timestamp())
}

module "random_pet" {
  source  = "masterpointio/random/pet"
  version = "0.1.0"

  length = var.length
  prefix = local.prefix
}
