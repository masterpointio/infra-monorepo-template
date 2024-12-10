# terraform-child-module-template

This repository serves as a template for creating Terraform [child modules](https://developer.hashicorp.com/terraform/language/modules#child-modules), providing a standardized structure and essential files for efficient module development. It's designed to ensure consistency and best practices across Terraform projects.

This README.md serves as the module’s primary documentation and entry point.

## Recommenations

We recommend to include:

- Module Description: Provide a concise explanation of what the module does and its intended use cases.
- Usage Instructions: Include code snippets demonstrating how to call the module from a [root module](https://developer.hashicorp.com/terraform/language/modules#the-root-module).
- Inputs & Outputs Summary: List the module’s input variables (with defaults and required ones highlighted) and outputs. We recommend using [terraform-docs](https://github.com/terraform-docs/terraform-docs) to keep the summary up-to-date.
- Prerequisites and Dependencies: Mention any dependencies, required providers, or external resources.
- Example Configurations: If applicable, include or link to example code snippets or a separate examples/ directory.

## Repository Structure

Below is the recommended structure for a Terraform child module. You'll fine the best practices for what to include inside each file. This layout helps maintain clarity, and consistency across your infrastructure code:

```sh
.
├── README.md
├── main.tf
├── data.tf        (optional)
├── outputs.tf
├── variables.tf
└── versions.tf
```

## Additional Tips

- Testing and Examples: Consider adding an examples/ directory with sample configurations and a test/ directory (if using tools like terratest or native Terraform testing) to ensure the module works as intended
- Continuous Improvement: Update documentation and constraints (versions.tf) as Terraform and providers evolve, and as you refine the module’s functionality.

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

| Name                                                                     | Version |
| ------------------------------------------------------------------------ | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement_terraform) | ~> 1.0  |
| <a name="requirement_random"></a> [random](#requirement_random)          | ~> 3.0  |

## Providers

| Name                                                      | Version |
| --------------------------------------------------------- | ------- |
| <a name="provider_random"></a> [random](#provider_random) | 3.6.3   |

## Modules

No modules.

## Resources

| Name                                                                                                      | Type     |
| --------------------------------------------------------------------------------------------------------- | -------- |
| [random_pet.template](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/pet) | resource |

## Inputs

| Name                                                | Description                   | Type     | Default | Required |
| --------------------------------------------------- | ----------------------------- | -------- | ------- | :------: |
| <a name="input_length"></a> [length](#input_length) | The length of the random name | `number` | `2`     |    no    |

## Outputs

| Name                                                                             | Description                   |
| -------------------------------------------------------------------------------- | ----------------------------- |
| <a name="output_random_pet_name"></a> [random_pet_name](#output_random_pet_name) | The generated random pet name |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
