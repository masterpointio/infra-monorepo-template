# Working with the example module tests

Start with the [README commands](../README.md#native-module-tests). This runner is
for `child-modules/random-pet`; it is not a deployment tool or a general monorepo
runner. It does not modify your checkout, state, or installed root-project versions.
macOS and Linux are supported by these instructions; Windows is not verified.

## What runs

Five native runs use `plan`: omitted-input defaults, custom input wiring, minimum
length, and rejection of zero/negative lengths. The sixth uses `apply` to check
that the module exports the actual local Random resource ID with the expected
prefix and number of name components. Native tests clean up that resource.

The runner uses a fresh temporary copy, a read-only provider lockfile, and no
backend initialization. It runs `init`, `validate`, and `test -json`, checks the
results, and removes temporary files. It prints readable diagnostics; `--verbose`
prints raw test events for debugging. Errors, skipped runs, missing original
coverage, truncated output, or discovered tests without final results fail CI.

The test tools are Terraform 1.13.3 and OpenTofu 1.12.6, with Random 3.9.1 pinned
in [separate test lockfiles](../child-modules/random-pet/tests/locks/).
The child module's consumer requirements remain TF `>= 1.0` and Random `>= 3.0`;
passing these tests does not establish compatibility with every allowed version.
The root Aqua configuration is unchanged. Root-module compatibility and deployment
must be verified separately.

## Add or adapt tests

Add a named `run` to the existing `.tftest.hcl` file or another `.tftest.hcl` file
in the same `tests/` directory. Additional passing tests are accepted automatically;
every discovered run must finish successfully. Do not add a `.tofutest.hcl` shadow
of the required file: both CLIs must execute the same example coverage.

When replacing this sample with your own module, deliberately update the module
path, required test file, and `RUNS` coverage set in
[the runner](../scripts/test_random_pet.py), along with both lockfiles and the
workflow's labels. Keep the coverage check: a native CLI can exit successfully
when it discovers no tests. The runner copies this child directory only; references
to sibling modules or shared fixtures outside it need an explicitly adapted runner.

This sample's apply is local-only because its only resource is Random. If you add
cloud resources to your tests, reassess credentials, cost, teardown, and execution
permissions before enabling those tests on pull requests. This workflow does not
provide cloud credentials.

The checker itself has regression tests using captured outputs from both CLIs:

```sh
python3 -m unittest discover -s scripts -p test_runner_contract.py
```

## Troubleshoot without changing your normal environment

- **Aqua not found:** install it, then run `aqua -c scripts/aqua.yaml install`.
  The runner resolves the scoped tools automatically, including when invoked from
  another directory. For an explicit alternative binary use `--binary /absolute/path`.
- **Download failure or timeout:** check access to GitHub and the provider registry.
  HTTP proxy and CA-certificate environment settings are retained. A command gets
  240 seconds by default, including Aqua lookup; use `--timeout 600` on a slow
  connection. CI still has a ten-minute job limit. Timeout or Ctrl-C stops the active
  command and its process group, including Aqua children, allows a short cleanup
  period, and removes any test temporary directory.
- **Unexpected local configuration:** `TF_*`/`TOFU_*` overrides, CLI config, and
  provider development overrides are intentionally ignored for repeatability.
  Custom provider mirrors and offline installation are not supported by this runner.
  Use native CLI commands in a disposable module copy for those workflows.
- **Defaults check blocked:** move auto-loaded `terraform.tfvars`, `*.auto.tfvars`,
  or their JSON equivalents outside this child directory. A named example such as
  `examples.tfvars` is fine; it is not automatically loaded.
- **Lockfile or checksum error:** do not bypass verification or use `init -upgrade`
  in CI. Follow the deliberate update procedure below and review both lock changes.
- **Failure details:** rerun with `--verbose` and capture both output streams, for
  example `python3 scripts/test_random_pet.py tofu --verbose > test-run.log 2>&1`.
  The native error and assertion text identify what failed; temporary state is not retained.

## Maintain tool versions

Renovate uses the inherited Aqua preset through `custom.regex` to discover CLI
versions and registry refs in both Aqua files, plus the workflow's `aqua_version`.
Keep that manager enabled. Updates follow the existing repository schedule and
release-age policy; review the proposed changes and both native test jobs.
The provider locks below still need their separate update procedure.

## Update test provider locks

These intentionally named test locks are copied into temporary directories, so
ordinary consumers do not inherit their pins. They are not assumed to receive
automatic Renovate lock maintenance. Update both together and rerun both test jobs.
Only test-tool pins belong in `scripts/aqua.yaml`; avoid changing root tool versions
as a side effect of maintaining tests.

From the repository root, run the following in Bash. Set `RANDOM_VERSION` to the
chosen release. The block works in temporary directories, then replaces only the
two test locks. Review the diff before committing; provider downloads need network access.

```bash
(
  set -eu
  RANDOM_VERSION=3.9.1
  lock_work=$(mktemp -d)
  trap 'rm -rf "$lock_work"' EXIT
  for tool in terraform tofu; do
    mkdir "$lock_work/$tool"
    cat > "$lock_work/$tool/versions.tf" <<EOF
terraform {
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "= $RANDOM_VERSION"
    }
  }
}
EOF
    binary=$(aqua -c scripts/aqua.yaml which "$tool")
    "$binary" -chdir="$lock_work/$tool" init -backend=false -input=false
    "$binary" -chdir="$lock_work/$tool" providers lock \
      -platform=darwin_arm64 -platform=darwin_amd64 \
      -platform=linux_amd64 -platform=linux_arm64
  done
  # Copy only after both tools have generated their locks successfully.
  for tool in terraform tofu; do
    cp "$lock_work/$tool/.terraform.lock.hcl" \
      "child-modules/random-pet/tests/locks/$tool.lock.hcl"
  done
)
python3 scripts/test_random_pet.py terraform
python3 scripts/test_random_pet.py tofu
```

## CI and coverage limits

`Module Tests` runs separate `random-pet (terraform)` and `random-pet (tofu)` jobs
on pull requests and pushes to `main`. Jobs have read-only repository access and
no inherited deployment secrets. Fork workflows may need maintainer approval.
Confirm the job names in an actual run before requiring them in branch protection.
The existing Lint workflow and its separate permissions are preserved.

Tests follow the native HCL approach used in
[terraform-spacelift-automation](https://github.com/masterpointio/terraform-spacelift-automation/tree/81edc1bdde7e0888152354b0539d0d87ae74ce0d/tests).
The shared test workflow requires AWS/Spacelift inputs; this sample uses a small
credential-free workflow instead. These checks do not certify root deployment,
documentation freshness, or alignment of every tool in the repository.
