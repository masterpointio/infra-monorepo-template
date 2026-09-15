# No variables blocks: exercise real defaults or the actual selected tfvars file.
run "shipped_example" {
  command = apply

  assert {
    condition     = output.random_pet_name == module.random_pet.random_pet_name
    error_message = "Root output must export the actual child output."
  }

  assert {
    condition     = can(regex("^random-[0-9]{8}-[a-z]+$", output.random_pet_name))
    error_message = "Root must forward the expected prefix and length to the real child output."
  }

  assert {
    condition = contains([
      formatdate("YYYYMMDD", plantimestamp()),
      formatdate("YYYYMMDD", timestamp()),
    ], split("-", output.random_pet_name)[1])
    error_message = "Output date must match this execution, including a UTC midnight crossing."
  }
}
