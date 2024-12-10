# Purpose:
# The outputs.tf file defines values that the module exports for use by the caller.

# Best Practices:
# - Descriptive Output Names: Use meaningful names (e.g., instance_id, db_connection_string).
# - Descriptions: Include description attributes to clarify the purpose of each output.
# - Minimal Outputs: Only output what consumers need. For sensitive outputs, mark as sensitive = true.

output "random_pet_name" {
  description = "The generated random pet name"
  value       = random_pet.template.id
}
