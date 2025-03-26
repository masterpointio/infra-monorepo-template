# example-tf

This repository serves as an example and template for how Masterpoint thinks about organizing a vanilla Terraform or OpenTofu (from now on referred to as "TF") monorepo with root modules, child modules, and accompanying tooling.

This includes example configurations and recommendations around the following topics:

<!-- TODO: Link to what Multi-instance root modules are once https://github.com/masterpointio/masterpoint.io/pull/49 ships -->

1. Example organizational structure for an IaC Monorepo (Multi-instance Root Modules + Child Modules)
   1. Root module example is provided in the [root-modules/template-root-module](./root-modules/template-root-module/) directory.
   2. Child module example is provided in the [child-modules/random-pet](./child-modules/random-pet/) directory
2. [Recommendations for module file structure](#structure) with [file-by-file guidance](#file-by-file-guidance)
3. [Recommendations for version pinning TF + Providers](#versioning-tf-and-providers)
4. [Managing which TF binary is used per project](#managing-which-tf-binary-is-used-per-project)
5. [Guidance on linting + CI for TF](#tf-linting--ci)
6. [Frequently Asked Questions](#frequently-asked-questions)

<!-- TODO
1. Example Native TF Tests with accompanying GitHub Action workflow for running tests
 -->

## Recommendations (TODO: Discuss)

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

<!-- TODO: Update to link Child Modules to Terms blog post once live -->

Since child-modules are intended to be used many times throughout your or others code, it’s important to make it so that they create as little restrictions on the consuming root module as possible.

This means you should:

- Identify the earliest Terraform/OpenTofu and provider versions your child module supports.
- Use the `>=` operator to ensure that consumers run at least these versions.

By setting a lower bound (e.g., `>= 1.3`) rather than pinning exact versions, you allow root modules to choose their own Terraform/OpenTofu and provider versions. This means a root module can upgrade their TF or providers versions without requiring updates to the child modules that they consume.

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

In this example, the child module only demands a minimum version (Terraform or OpenTofu 1.3, Random provider 3.0), letting the root module run newer versions as they become available.

### Root Modules

<!-- TODO: Update to link Root Modules to Terms blog post once live -->

Root modules are intended to be planned and applied and therefore they should be more prescriptive so that they’re called consistently in each case that you instantiate a new root module instance (i.e. create a new state file).

To accomplish that, you should do the following:

- Explicitly pin the latest version of TF that your root module supports. You’ll need to upgrade this version each time you want to use a new TF version across your code base.
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

In this example two things are happening:

1. TF is pinned exactly at `1.3.7`, which ensures your entire team will use the correct version with this root module.
2. The AWS provider is pinned with `~> 5.81.0`, which means it can update to `5.81.1`, `5.81.2`, etc., but not jump to `5.82.0`.

If you're more willing to use the bleeding edge of providers, you can always use the `~>` operator on the minor version like so `version = "~> 5.81"`. This will enable any new minor version updates and is essentially a shorthand for `>= 5.81.0 && < 6.0`. Be aware that providers do break and this has the possibility to frustrating bugs from providers to affect your project.

## Managing which TF binary is used per project

At Masterpoint, we're big fans of [Aqua](https://aquasecurity.github.io/aqua/) for managing which TF binary is used per project. This allows us to have a single TF binary that is used across our entire project, but still enables us to use root module specific TF versions if needed.

Check out the [aqua.yaml](.aqua/aqua.yaml) file to see how simple it is to use aqua for this project and check out [the Aqua docs](https://aquasecurity.github.io/aqua/getting-started/installation/) on how you can use this tool for your own project.

<!--
TODO: Work these into other sections.
## Additional Tips

- Testing and Examples: Consider adding an examples/ directory with sample configurations and a test/ directory (if using tools like terratest or native Terraform testing) to ensure the module works as intended
- Continuous Improvement: Update documentation and constraints (versions.tf) as Terraform and providers evolve, and as you refine the module’s functionality. -->

## TF Linting + CI

There are many tools to format, lint, and ensure consistency of TF code. The tool that we recommend is [trunk Code Quality](https://docs.trunk.io/code-quality). This single tool allows us to do the following:

1. Format our TF code with `terraform fmt` or `tofu fmt` within our IDE and ensure this is run on each commit.
   1. [This is handled by the trunk `terraform` or `tofu` linter](https://docs.trunk.io/code-quality/linters/supported/tofu).
2. Validate our TF code with `terraform validate` or `tofu validate` within our IDE and ensure this is run on each commit.
   1. [This is handled by the trunk `terraform` or `tofu` linter](https://docs.trunk.io/code-quality/linters/supported/tofu).
3. Generate documentation for our TF code with `terraform-docs` and ensure it is kept up-to-date on each commit.
   1. [This is handled by the trunk `terraform-docs` action](https://github.com/trunk-io/plugins/tree/main/actions/terraform-docs), which [Masterpoint originally developed](https://github.com/trunk-io/plugins/pull/966).
4. Run TFLint against our code to ensure it is written against the best practices.
   1. [This is handled by the trunk `tflint` linter](https://docs.trunk.io/code-quality/linters/supported/tflint).
5. Run a TF security scan against our code to ensure we're not introducing any security vulnerabilities.
   1. [This is handled by the trunk `trivy` linter](https://docs.trunk.io/code-quality/linters/supported/trivy).
6. Run these checks in a CI pipeline to ensure they're enforced on each PR.
   1. [This is handled by the trunk-action workflow](https://docs.trunk.io/code-quality/setup-and-installation/github-integration) in the [.github/workflows/lint.yaml](.github/workflows/lint.yaml) file.

As you can see, this is a LOT of checks that trunk is supporting for us and this consolidation on one tool to support this (and much more) is a huge win.

Check out our [.trunk/trunk.yaml](.trunk/trunk.yaml) file to see how we configure this and [check the trunk Code Quality getting started documentation](https://docs.trunk.io/code-quality) on how you can use this tool for your own project.

## Frequently Asked Questions

### Why do you prefer DRY (Don't Repeat Yourself) Root Modules vs WET (Write Every Time) Root Modules?

We advocate IaC should be treated like code and traditional software. You encode some level of business logic into it, and consistently copying+pasting that logic as part of your day-to-day processes creates a maintenance burden that we believe should be avoided. This particularly shows up when IaC is managed at scale and we have seen these types of setups lead to a lot of toil and a lot of technical debt.

We will write up more on this soon and link to it here.

### Why don't you use a TF Framework like [Terragrunt](https://terragrunt.gruntwork.io/), [Terramate](https://terramate.io/), or [Atmos](https://atmos.tools/)?

We're big fans of the frameworks (particularly Atmos + Terramate, which we have a good deal of experience with), and we believe they're fantastic options for sophisticated teams that are starting from scratch. But for projects that aren't starting from scratch or have a desire to keep things simple, we believe Vanilla TF combined with a strong automation platform is a great option.
