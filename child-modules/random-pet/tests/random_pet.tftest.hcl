# Keep defaults free of file-level variables so changes to the module defaults fail.
run "defaults" {
  command = plan

  assert {
    condition     = random_pet.template.length == 2 && random_pet.template.prefix == null
    error_message = "Defaults must forward length 2 and no prefix to random_pet."
  }
}

run "custom_inputs" {
  command = plan

  variables {
    length = 3
    prefix = "custom"
  }

  assert {
    condition     = random_pet.template.length == 3 && random_pet.template.prefix == "custom"
    error_message = "The resource must receive the caller's exact length and prefix."
  }
}

run "minimum_length" {
  command = plan

  variables {
    length = 1
  }

  assert {
    condition     = random_pet.template.length == 1
    error_message = "A length of one must be accepted and forwarded to random_pet."
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

# Random creates a local name only; this apply needs no cloud account.
run "generated_output" {
  command = apply

  variables {
    length = 2
    prefix = "ci"
  }

  assert {
    condition     = output.random_pet_name == random_pet.template.id
    error_message = "random_pet_name must export the generated resource ID."
  }

  assert {
    condition     = can(regex("^ci-[a-z]+-[a-z]+$", output.random_pet_name))
    error_message = "The generated name must contain the ci prefix and two name components."
  }
}
