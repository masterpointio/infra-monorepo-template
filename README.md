# client-tf-templates

This repository serves as a template for creating Terraform [child](https://opentofu.org/docs/language/modules/#child-modules) and [root](https://opentofu.org/docs/language/modules/#the-root-module) modules, providing a standardized structure and essential files for efficient module development. It's designed to ensure consistency and best practices across Terraform projects.

Child module example is provided in [terraform-random-pet](./terraform-random-pet/) directory.

Root module example is provided in [root-module](./root-module/) directory.

This README.md serves as the module's primary documentation and entry point.

## Recommenations

We recommend to include:

- Module Description: Provide a concise explanation of what the module does and its intended use cases.
- Usage Instructions: Include code snippets demonstrating how to call the module from a [root module](https://developer.hashicorp.com/terraform/language/modules#the-root-module).
- Inputs & Outputs Summary: List the module’s input variables (with defaults and required ones highlighted) and outputs. We recommend using [terraform-docs](https://github.com/terraform-docs/terraform-docs) to keep the summary up-to-date.
- Prerequisites and Dependencies: Mention any dependencies, required providers, or external resources.
- Example Configurations: If applicable, include or link to example code snippets or a separate examples/ directory.

## Module Repository/Directory Structure

Below is a recommended structure for both TF child modules and root modules. Inside each file, you’ll find guidance and best practices that help maintain clarity and consistency across your infrastructure code.

```sh
.
├── README.md
├── main.tf
├── data.tf        (optional)
├── outputs.tf
├── providers.tf   (root module only)
├── variables.tf
└── versions.tf
```

## Additional Tips

- Testing and Examples: Consider adding an examples/ directory with sample configurations and a test/ directory (if using tools like terratest or native Terraform testing) to ensure the module works as intended
- Continuous Improvement: Update documentation and constraints (versions.tf) as Terraform and providers evolve, and as you refine the module’s functionality.
