# terraform-random-pet

This is a template child module.

<!-- README TEMPLATE: AFTER READING THE BELOW SECTION, DELETE THE BELOW SECTION AND REPLACE WITH YOUR OWN CONTENT -->

## Documentation Recommendations (DO NOT INCLUDE THIS INTO THE REAL README)

### Naming

The repository/directory name should follow this pattern:

```sh
[terraform-]<PROVIDER>-<NAME>
```

Here’s what this means:

1. [If it's a separate repository] The repository should start with `terraform-` if your module should be [published to and discovered on the Registry](https://opentofu.org/docs/language/modules/develop/publish/). Even if you don’t intend to publish the module, following this pattern is a good practice that helps differentiate your Terraform child modules from other code in your projects.
2. Include the provider name: Specify the primary provider your module is for, such as aws, google, datadog, etc.
3. Use descriptive name: Follow the provider name with a clear and concise identifier that describes the module’s purpose.
4. Use hyphens to separate words.

Also:

1. Keep name short and focused: While it should be descriptive, avoid overly long names. The goal is to convey the module’s purpose concisely:
   - Good: `terraform-aws-internal-lb`.
   - Not so good: `terraform-aws-internal-misc-module`.
   - Too long: `terraform-aws-internal-application-load-balancer-with-extra-rules`.
2. Module names should reflect their purpose rather than environment-specific details.

### Usage

To use this module, reference it from your main configuration and provide the necessary input variables. For example:

```hcl
module "sandbox_pet" {
  source  = "masterpointio/random/pet"
  # We recommend to pin the specific version
  # version = "X.X.X"

  # Input variables
  length = 2
  prefix = "sandbox"
}
```

Once applied, the random resource will produce a random name such as `sandbox-lively-parrot` (the exact name will vary). This name can be referenced via:

```hcl
output "pet_name" {
  value = module.sandbox_pet.random_pet_name
}
```

<!-- README TEMPLATE: ENDING DELETE MARKER -->

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

| Name                                                                     | Version |
| ------------------------------------------------------------------------ | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement_terraform) | >= 1.0  |
| <a name="requirement_random"></a> [random](#requirement_random)          | >= 3.0  |

## Providers

| Name                                                      | Version |
| --------------------------------------------------------- | ------- |
| <a name="provider_random"></a> [random](#provider_random) | >= 3.0  |

## Modules

No modules.

## Resources

| Name                                                                                                      | Type     |
| --------------------------------------------------------------------------------------------------------- | -------- |
| [random_pet.template](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/pet) | resource |

## Inputs

| Name                                                | Description                       | Type     | Default | Required |
| --------------------------------------------------- | --------------------------------- | -------- | ------- | :------: |
| <a name="input_length"></a> [length](#input_length) | The length of the random name.    | `number` | `2`     |    no    |
| <a name="input_prefix"></a> [prefix](#input_prefix) | A string to prefix the name with. | `string` | `null`  |    no    |

## Outputs

| Name                                                                             | Description                   |
| -------------------------------------------------------------------------------- | ----------------------------- |
| <a name="output_random_pet_name"></a> [random_pet_name](#output_random_pet_name) | The generated random pet name |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
