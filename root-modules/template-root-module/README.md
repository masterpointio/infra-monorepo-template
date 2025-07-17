# template-root-module

This is a template root module that creates a random pet resource. It can be easily copied and updated for other use-cases.

## Using `tfvars` with [TF Workspaces](https://masterpoint.io/blog/terraform-opentofu-terminology-breakdown/#tf-cli-workspaces)

Terraform/OpenTofu workspaces are used with environment-specific tfvars files for separate TF state files to keep your configuration DRY. This allows you to maintain the same infrastructure code while using different variable values for different environments.

```bash
# Set up a new workspace for `dev` -- only needs to be done once
tofu workspace new dev
# Select the workspace, this is how TF knows where the state file is stored
tofu workspace select dev
# Apply the configuration with the corresponding tfvars file
tofu apply --var-file tfvars/dev.tfvars
```

This approach ensures that:

- Your infrastructure code remains consistent across environments
- Environment-specific configurations are isolated in tfvars files
- State files are automatically separated by workspace
- You can easily switch between environments

<!-- README TEMPLATE: AFTER READING THE BELOW SECTION, DELETE THE BELOW SECTION AND REPLACE WITH YOUR OWN CONTENT -->

## Documentation Recommendations (DO NOT INCLUDE THIS INTO THE REAL README)

- Module description: Briefly explain what the root module sets up (e.g., infrastructure for RDS Postgres instances).
- Use [terraform-docs](https://github.com/terraform-docs/terraform-docs) to ensure that variables, outputs, child module, and resource documentation is included.
- Maintain current information: Keep the README updated as the infrastructure evolves.

<!-- README TEMPLATE: ENDING DELETE MARKER -->

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
