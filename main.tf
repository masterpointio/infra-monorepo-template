# Purpose:
# The main.tf file contains the core resource definitions and logic that compose the module’s functionality.

# Best Practices:
# - Resource Definitions: Declare here all the primary resources that this module is responsible for managing.
# - Locals and Expressions: Use locals blocks to simplify expressions and keep the code DRY (Don’t Repeat Yourself).
# - Comments and Structure: Organize resources logically and use comments to explain complex or non-obvious configurations.
# - Minimal Hard-Coding: Use variables extensively to avoid embedding environment-specific values directly in the code.

resource "random_pet" "template" {
  length = var.length
}
