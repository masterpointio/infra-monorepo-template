# Purpose:
# The data.tf file contains Terraform data sources—these do not create resources but query existing infrastructure or configuration for reference.

# Best Practices:
# - Data sources in a root module often fetch information about existing shared infrastructure or external systems.
#   Keep these lookups minimal and well-documented, as the root module is usually the topmost layer of your configuration.
# - Data Source Declarations: Place all data blocks here, for example, data "aws_ami" "linux" { ... }.
# - Clear Naming and Purpose: Use descriptive names for data sources to indicate their role (e.g., data "aws_ami" "ubuntu_latest").
# - Commenting and Filtering: Document why each data source is used and ensure filters or queries are well explained.
# - Minimize External Dependencies: Only query the minimum necessary information. Overly complicated data sources can slow down Terraform runs and confuse future maintainers.
