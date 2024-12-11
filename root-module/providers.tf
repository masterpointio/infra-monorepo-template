# Purpose:
# The providers.tf file configures any providers the root module needs, including setting up authentication, default regions, or other provider-specific settings.

# Best Practices:
# - Provider configuration: Define providers (e.g., aws {}, azurerm {}, google {}) and set their region, credentials, or other parameters.
# - Multiple provider configurations: If you need multiple configurations for the same provider (e.g., two AWS regions), define them here with explicit aliases.
# - Avoid hard-coded and static credentials: Instead of embedding static credentials directly in your code, consider:
#     - AWS Assume Role: For the AWS provider, configure an assume role to obtain temporary credentials dynamically.
#     - Encrypted Configuration Files: For providers requiring API tokens, use a tool like SOPS to encrypt sensitive variables.

provider "random" {
  # Configuration options
}
