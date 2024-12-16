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

## Structure

This template includes a recommended layout for both root modules and child TF modules. Each file has a specific purpose and set of best practices. While many principles apply to both root and child modules, any differences are noted below.

For root modules:

```sh
.
├── README.md
├── main.tf
├── data.tf        (optional)
├── outputs.tf     (optional)
├── providers.tf
├── variables.tf
└── versions.tf
```

For child modules:

```sh
.
├── README.md
├── main.tf
├── data.tf        (optional)
├── outputs.tf     (optional)
├── variables.tf
└── versions.tf
```

### File-by-File Guidance

The principles below apply to both root and child modules, unless otherwise specified.

1. `main.tf`

- Purpose: Defines core resources and the module’s primary logic. In root modules, this may also include calls to child modules.
- Best Practices:
  - Resource definitions: Declare here all the primary resources that this module is responsible for managing.
  - Locals and expressions: Use locals blocks to simplify expressions and keep the code DRY (Don’t Repeat Yourself).
  - Comments and structure: Organize resources logically and use comments to explain complex or non-obvious configurations.
  - Minimal hard-coding: Use variables extensively to avoid embedding environment-specific values directly in the code.
  - Child module calls:
    - Use Terraform Registry Modules with Version Pinning:
      ```hcl
      module "vpc" {
        source  = "terraform-aws-modules/vpc/aws"
        version = "1.0.0"
      }
      ```
    - Use Git Sources with a Specific Tag or Commit
      ```hcl
        module "vpc" {
          source = "git::https://github.com/org/terraform-aws-vpc.git?ref=v1.0.0"
        }
      ```

2. `data.tf` (Optional)

- Purpose: Contains data sources that retrieve external information.
- Best Practices:
  - Data source declarations: Place all data blocks here, for example, `data "aws_ami" "linux" { ... }`.
  - Clear naming and purpose: Use descriptive names for data sources to indicate their role (e.g., `data "aws_ami" "ubuntu_latest"`).
  - Commenting and filtering: Document why each data source is used and ensure filters or queries are well explained.
  - Minimize external dependencies: Only query the minimum necessary information. Overly complicated data sources can slow down Terraform runs and confuse future maintainers.

3. `outputs.tf` (Optional)

- Purpose: Defines values exported from the module for use by its caller.
- Best Practices:
  - Descriptive output names: Use meaningful names (e.g., `instance_id`, `db_connection_string`).
  - Descriptions: Include description attributes to clarify the purpose of each output.
  - Minimal outputs: Only output what consumers need. For sensitive outputs, mark as `sensitive = true`.

4. `providers.tf` (Root Module Only)

- Purpose: Configures providers for the root module, such as authentication or default regions.
- Best Practices:
  - Provider configuration: Define providers (e.g., `aws {}`, `google {}`) and set their region, credentials, or other parameters.
  - Multiple provider configurations: If you need multiple configurations for the same provider (e.g., two AWS regions), define them here with explicit aliases.
  - Avoid hard-coded and static credentials: Instead of embedding static credentials directly in your code, consider:
    - AWS Assume Role: For the AWS provider, configure an assume role to obtain temporary credentials dynamically.
    - Encrypted Configuration Files: For providers requiring API tokens, use a tool like [SOPS](https://getsops.io/) to encrypt sensitive variables.

5. `variables.tf`

- Purpose: Defines input variables controlling the module’s configuration.
- Best Practices:
  - Descriptive variables: Use meaningful names and description attributes.
  - Default values: Provide reasonable defaults when possible. For mandatory inputs, omit defaults to enforce explicit user input.
  - Type constraints and validation: Use type constraints and validation blocks to catch incorrect inputs early.
  - Group related variables: Organize variables logically, adding comments to separate sections if many variables exist.

6. `versions.tf`

- Purpose: Sets Terraform and provider version requirements for consistency and compatibility.
- Best Practices:
  - See the detailed version constraints explanation in [Versioning TF and Providers](#versioning-tf-and-providers).
  - Regular Review: Update constraints as Terraform and providers evolve.

## Versioning TF and Providers

We’re particular about how we version providers and Terraform/OpenTofu in child and root modules. We recommend the following:

### Child Modules

Since child-modules are intended to be used many times throughout your code, it’s important to make it so that they create as little restrictions on the consuming consuming root module as possible.

This means you should:

- Identify the earliest Terraform/OpenTofu and provider versions your child module supports.
- Use the `>=` operator to ensure that consumers run at least these versions.

By setting a lower bound (e.g., `>= 1.3`) rather than pinning exact versions, you allow root modules to choose their own Terraform and provider versions. This means a root module can upgrade Terraform or providers without requiring updates to all child modules.

Example:

```hcl
terraform {
  required_version = ">= 1.3"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}
```

In this example, the child module only demands a minimum version (Terraform 1.3, Random provider 3.0), letting the root module run newer versions as they become available.

### Root Modules

Root modules are intended to be planned and applied and therefore they should be more prescriptive so that they’re called consistently in each case that you instantiate a new root module instance (i.e. a state file).

To accomplish that, you should do the following:

- Explicitly pin the latest version of Terraform/OpenTofu that your root module supports. You’ll need to upgrade this version each time you want to use a new TF version across your code base.
- Identify the highest stable provider versions your root module supports, then use the [pessimistic operator](https://developer.hashicorp.com/terraform/language/expressions/version-constraints#operators) `~>` to allow only patch-level updates. This gives you automatic bug fixes and minor improvements without risking major breaking changes.

Example:

```hcl
terraform {
  required_version = "1.3.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81.0"
    }
  }
}
```

In this example Terraform is pinned exactly at 1.3.7, the AWS provider is pinned with `~> 5.81.0`, which means it can update to 5.81.1, 5.81.2, etc., but not jump to 5.82.0.

## Additional Tips

- Testing and Examples: Consider adding an examples/ directory with sample configurations and a test/ directory (if using tools like terratest or native Terraform testing) to ensure the module works as intended
- Continuous Improvement: Update documentation and constraints (versions.tf) as Terraform and providers evolve, and as you refine the module’s functionality.
