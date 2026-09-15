run "custom_inputs" {
  command = apply

  variables {
    length = 3
    prefix = "custom"
  }

  assert {
    condition     = output.random_pet_name == module.random_pet.random_pet_name
    error_message = "Root output must export the actual child output."
  }

  assert {
    condition     = can(regex("^custom-[0-9]{8}-[a-z]+-[a-z]+-[a-z]+$", output.random_pet_name))
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

run "minimum_length" {
  command = apply

  variables {
    length = 1
    prefix = "minimum"
  }

  assert {
    condition     = output.random_pet_name == module.random_pet.random_pet_name
    error_message = "Root output must export the actual child output."
  }

  assert {
    condition     = can(regex("^minimum-[0-9]{8}-[a-z]+$", output.random_pet_name))
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

run "zero_length" {
  command = plan
  variables {
    length = 0
  }
  expect_failures = [var.length]
}

run "negative_length" {
  command = plan
  variables {
    length = -1
  }
  expect_failures = [var.length]
}
