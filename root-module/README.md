# root-module

This is a dummy root module.

## Recommenations (DO NOT INCLUDE THIS INTO THE REAL README)

- Nodule description: Briefly explain what the root module sets up (e.g., infrastructure for a production environment).
- Usage instructions: Include examples of how to run terraform init, terraform plan, and terraform apply.
- Documentation of variables and outputs: generate variables (from variables.tf) and outputs (from outputs.tf).
- Link to child modules and external resources: If the root module references child modules, mention where they’re located and link to their documentation.
- Maintain current information: Keep the README updated as the infrastructure evolves.

## Structure

Explore the contents of each file to understand their purpose and discover recommended best practices.

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

| Name                                                                     | Version |
| ------------------------------------------------------------------------ | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement_terraform) | ~> 1.0  |
| <a name="requirement_random"></a> [random](#requirement_random)          | ~> 3.0  |

## Providers

No providers.

## Modules

| Name                                                              | Source                   | Version |
| ----------------------------------------------------------------- | ------------------------ | ------- |
| <a name="module_random_pet"></a> [random_pet](#module_random_pet) | masterpointio/random/pet | 0.1.0   |

## Resources

No resources.

## Inputs

| Name                                                | Description                   | Type     | Default | Required |
| --------------------------------------------------- | ----------------------------- | -------- | ------- | :------: |
| <a name="input_length"></a> [length](#input_length) | The length of the random name | `number` | `2`     |    no    |

## Outputs

No outputs.

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
