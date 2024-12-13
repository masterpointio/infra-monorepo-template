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
