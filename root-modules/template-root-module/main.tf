locals {
  # Get the current timestamp and format it as YYYYMMDD, then concatenate with user-provided prefix
  prefix = "${var.prefix}-${formatdate("YYYYMMDD", timestamp())}"
}

module "random_pet" {
  # If using a module from Terraform/OpenTofu Registry:
  # source  = "masterpointio/random/pet"
  # version = "0.1.0"

  # If using a module from a local directory:
  source = "../../child-modules/random-pet"

  length = var.length
  prefix = local.prefix
}
