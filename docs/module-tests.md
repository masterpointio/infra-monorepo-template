# Checking the two Random examples

Start with the [README setup](../README.md#native-module-tests). Python 3.10+ and
Aqua are required for native checks; root Aqua installs the Trunk launcher.
Run `trunk install` to install the configured tools and Git hooks.
macOS ARM64 and Ubuntu AMD64 are the supported test targets. Commands work from
another directory when the Python script is referenced by its absolute path.
This is a two-example harness, not a deployment tool or general infrastructure runner.

## Commands and coverage

```sh
aqua install
export PATH="$(aqua root-dir)/bin:$PATH"
trunk install
python3 scripts/test_examples.py terraform --validate-only
python3 scripts/test_examples.py tofu --validate-only
python3 scripts/test_examples.py terraform
python3 scripts/test_examples.py tofu
python3 scripts/docs.py
python3 -m unittest discover -s scripts -p 'test_*contract.py'
trunk check --all --no-fix
```

Validation explicitly initializes and validates both supplied modules without an
apply. The test commands also validate each isolated fixture before running it.
`--module child-modules/random-pet` or `--module root-modules/template-root-module`
selects one example; the inventory/boundary check still examines both. Existing
`test_random_pet.py terraform` / `tofu` commands remain child-only aliases.

| Module / fixture        | Native runs                                                                             | Input source                                                               |
| ----------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Child / `tests`         | defaults, custom_inputs, minimum_length, zero_length, negative_length, generated_output | Declared defaults or explicit native test variables                        |
| Root / `tests`          | custom_inputs, minimum_length, zero_length, negative_length                             | Explicit native test variables for behavioral boundaries                   |
| Root / `tests/defaults` | defaults                                                                                | Declared defaults; omit only `example.auto.tfvars` from the isolated copy  |
| Root / `tests/example`  | shipped_example                                                                         | Actual working-tree `example.auto.tfvars`                                  |
| Root / `tests/dev`      | dev_file                                                                                | Actual `example.auto.tfvars`, then explicit `-var-file=tfvars/dev.tfvars`  |
| Root / `tests/prod`     | prod_file                                                                               | Actual `example.auto.tfvars`, then explicit `-var-file=tfvars/prod.tfvars` |

Each fixture has its own required manifest and native invocation. Every discovered
file/run must pass exactly once; empty, missing, skipped, duplicate, errored or
truncated results fail. Added passing tests are allowed without changing a total.
The root has eight required runs; the child keeps its original six.

The root default length is 2 and prefix is `random`. The shipped auto-file changes
length to 1. Dev/prod files override the prefix, while length remains 1 according
to actual CLI variable-file precedence. Workspaces select state, not tfvars files.
Default and file-precedence tests intentionally contain no `variables` blocks:
those blocks would override the inputs the tests are meant to observe.

Root positive tests apply the real local child and assert its actual exported
output, expected prefix and number of words. The date must equal either the UTC
plan date (`plantimestamp()`) or assertion date (`timestamp()`), allowing a check
that crosses midnight without accepting an arbitrary eight-digit date. No clock
input is added to the production module. The example's existing use of `timestamp()`
means a later-day plan/apply can change the name; this work preserves that behavior.
Zero/negative cases use named `expect_failures = [var.length]`. Null and fractional
inputs have not been given new validation rules; the public positive-number contract
is unchanged.

## Isolation and adding coverage

[The explicit inventory](../scripts/example_policy.py) declares modules, dependencies,
provider policy, apply permission and fixture manifests. Discovery examines direct
root/child directories containing `.tf` or `.tf.json` sources. Engine-specific
`.tofu` and `.tofu.json` files, including same-name shadows and files in test
directories, fail with a shared-source diagnostic before either engine starts.
An unknown module
fails before any executable starts. To replace/add a module, review its resources,
providers, dependency paths, lock selection and permitted operations, then update
the inventory, fixtures, docs and CI deliberately. Discovery never authorizes apply.
Only the reviewed Random examples are authorized by this harness.

The copy uses current working-tree source/test/tfvars bytes, including uncommitted
edits. It preserves the root's relative child path and copies only selected module
sources, selected native tests, declared tfvars and the engine's test lock. State,
plans, `.terraform`, ordinary consumer locks, personal files and local configuration
are excluded. Nested directories are not recursively treated as independent modules.
New test directories require a declared fixture; extra `.tftest.hcl` or `.tftest.json`
files in existing selected directories run automatically. Engine-specific test shadows
and module-top-level tests are rejected so both engines share the same test scope.

Symlinks, undeclared module sources, alternate test modules, mocks, non-Random
resources/providers, backend/cloud blocks, provisioners, data sources and filesystem
functions are outside this narrow reviewed execution/copy policy. Heredocs also
require an explicit boundary review. The guard reads declaration structure: ordinary
attributes, labels, comments and literal strings containing words such as `resource`
or `source` do not declare infrastructure. It inspects filesystem calls in expressions,
including string interpolations and template directives; escaped template markers
remain literal. JSON declaration positions follow the same policy. Ambiguous or
unsupported declaration shapes require review; native CLIs own full syntax validation.
The policy guard is not an HCL security
engine or a sandbox for hostile code: review source and tests before executing
untrusted contributions. Native tools still parse and validate the configuration.

Unexpected auto-loaded files (`terraform.tfvars`, `*.auto.tfvars`, and JSON forms)
in modules or selected test directories fail. The sole allowed auto-file is the
root's declared example. Do not add higher-precedence variables to a required
defaults/file fixture. The child default safeguard remains strict.

Native commands run with no backend initialization, empty CLI config, sanitized
`TF_*`/`TOFU_*` environment and separate temporary state/provider initialization.
HTTP proxy and CA settings are retained for downloads. No cloud credentials are
needed. Every subprocess, including Aqua lookup, has a timeout and process-group
cleanup; Ctrl-C returns 130. Temporary directories are removed on success/failure.

## Versions and maintenance

| Tool            | Pin source / tested selection                  | Purpose and update path                                                     |
| --------------- | ---------------------------------------------- | --------------------------------------------------------------------------- |
| Terraform       | Both Aqua files: 1.13.3                        | Normal and native checks; review both-engine runs after updates             |
| OpenTofu        | Both Aqua files and Trunk: 1.12.6              | Normal checks and Trunk formatting; drift checked before execution          |
| Random          | `tests/locks/{terraform,tofu}.lock.hcl`: 3.9.1 | Shared immutable test selection for both modules; manual procedure below    |
| Aqua            | CI installer: 2.62.3                           | Setup and CLI resolution; update workflow pin and verify fresh install      |
| Aqua registry   | Both Aqua files: v4.331.0                      | Package definitions; keep both copies aligned                               |
| Trunk launcher  | Root Aqua: 1.2.7                               | Bootstrap the CLI selected by Trunk config; verify fresh setup              |
| Prettier        | Trunk: 3.9.6                                   | Shared formatter for managed docs and normal Markdown                       |
| terraform-docs  | Root Aqua: 0.20.0                              | Existing authored docs generation; review generated diff                    |
| Trunk / plugins | `.trunk/trunk.yaml`: 1.25.0 / v1.11.0          | Existing lint/security/format pipeline; review configured tools             |
| Node            | Trunk: 24.11.0                                 | Renovate 44.53.0 requires `^24.11.0`; also verify Prettier and markdownlint |
| Python          | Caller: 3.10+; Trunk: 3.14.4                   | Stdlib native runner; Trunk-managed scanner runtime is separate             |

The root's `>= 1.12.6, <= 1.13.3` is the bounded compatibility interval spanning
our two supported engine versions. TF constraints cannot express an OR of exact
Terraform/OpenTofu versions, and an exact `1.13.3` rejects the supported OpenTofu
binary. Exact development/check versions remain in Aqua; only those two endpoints
are tested, not every admitted version. The reusable child keeps `>= 1.0` and
Random `>= 3.0`. The root keeps Random `~> 3.9.0`. These are consumer requirements,
not the test provider selection.

Renovate's inherited Aqua preset (`custom.regex`) discovers both engine/registry
pins and CI's Aqua pin under the existing schedule and release-age policy. Keep
that manager enabled. After changing versions, run both full native commands,
regressions and `trunk check --all`. A bounded preflight rejects diverging Aqua
engine/registry pins or a Trunk OpenTofu mismatch. Update the compatibility constraint
and generated module docs if the supported interval changes.

The prior Node 22 runtime fails full Renovate extraction with `RegExp.escape is not
a function`; config-validator success alone does not prove extraction works. Use
the Trunk-installed Node/runtime, not an out-of-band installation:

```sh
trunk install
LOG_LEVEL=debug .trunk/tools/renovate --platform=local --dry-run=extract
```

Inspect the extraction log's package files for both Aqua configs, the workflow
Aqua version and inherited preset. This local mode does not create update PRs.
Without a GitHub token, extraction can succeed while release lookup reports token
requirements. Discovery is not evidence of hosted scheduled update proposals.

## Update test provider locks

Both modules initialize from the child's engine-specific Random locks. Terraform
and OpenTofu registry identities remain separate. The root's compatible provider
constraint uses this same tested selection; ordinary consumer locks are unchanged.
Never disable checksums or use `init -upgrade` in test CI. Updates remain deliberate
and manual, not presumed to receive automatic Renovate lock maintenance.

From the repository root, run this in Bash after choosing `RANDOM_VERSION`. It
replaces only the two test locks after both succeed. Review the diff and rerun both
engines. Locks include checksums for macOS/Linux ARM64/AMD64; checksum availability
does not itself establish that every platform was tested.

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
python3 scripts/test_examples.py terraform
python3 scripts/test_examples.py tofu
```

## Documentation checks and regeneration

```sh
python3 scripts/docs.py
python3 scripts/docs.py --write
python3 scripts/docs.py
```

The first/last commands check without changing files or staging anything. `--write`
regenerates only the managed sections of both example READMEs. Authored text outside
the existing markers is preserved byte for byte. Review the diff and stage source,
config and generated sections deliberately; the second regeneration must be identical.
No provider initialization, state, cloud access or Terraform apply occurs.

Every invocation covers both modules, including helper-only or shared-config edits.
Current working-tree `.tf`/`.tf.json` files, including untracked source additions,
are copied into a temporary directory with the READMEs and reviewed configuration.
Missing/untracked READMEs, damaged/duplicate/reversed markers, unknown modules,
symlinks and engine-specific sources fail. State, caches, native fixtures and private
files are not copied. Missing tools, wrong versions, generator/formatter errors or
incomplete output also fail. All subprocesses share native timeout/cancellation cleanup.
From another directory, use the script's absolute path. `--binary` and `--formatter`
accept explicit executables matching the configured pins.

The pipeline runs pinned terraform-docs without recursive discovery and sends its
Markdown through Trunk's pinned Prettier in the temporary copy. `.prettierrc.json`
is the shared literal formatter configuration. `.terraform-docs.yaml` accepts only
the reviewed plain mappings for version, formatter, settings, sorting, recursion
and the existing output template. Custom content/includes, external header/footer
paths, YAML aliases/escaped forms, output values and executable Prettier configs
require a pipeline review; arbitrary templates could silently hide real source
changes. The helper explicitly requests all six standard sections and disables
external reads/output paths. Additions to these config forms must preserve the
copy boundary and drift-detection tests.

The local `terraform-docs` Trunk action replaces the inherited action with
`python3 scripts/docs.py --staged`. It reads exact Git index blobs, so a freshly
generated working-tree README cannot hide stale staged documentation. Executing
helpers must match the index; stage reviewed helper changes before committing.
The action never stages or regenerates files. The separate `trunk-fmt-pre-commit`
action retains normal Trunk formatting behavior. If formatting changes the index
during checking, the docs action fails and asks you to inspect and retry.
For partial staging, generate/check the source snapshot you intend to commit,
stage its matching README section, then restore remaining working edits. Review
`git diff` and `git diff --cached` after any hook failure before retrying.

## Troubleshooting

- **Missing Aqua/tool:** run `aqua install`; the scoped `aqua -c scripts/aqua.yaml install`
  remains supported. Use `--binary /absolute/path` for an explicitly selected binary
  matching the configured engine/version. Empty/mismatched paths fail clearly.
- **Downloads, registry or checksum failure:** inspect the native diagnostic; restore
  connectivity or deliberately refresh locks. Offline mirrors and development provider
  overrides are not supported. Do not bypass lock verification to obtain a pass.
- **Timeout/cancellation:** each command gets 240 seconds, including Aqua. Use
  `--timeout 600` for a slow connection; CI still has a ten-minute job bound. Cleanup
  signals the process group, allows five seconds, then kills remaining descendants.
- **Invalid config/assertion:** use `--verbose` for raw native events. Both streams
  retain diagnostics, and failures identify the engine, module, fixture and command.
- **Inventory/copy failure:** review the named path and register intentional additions.
  Move ambient variable files aside yourself; the checker does not modify them.
- **Title check after a PR title edit:** the existing Lint trigger does not subscribe
  to edited events. Use a conventional title such as `test: complete example checks`;
  after correcting a title, rerun the failed job and verify the new attempt.

## CI, adoption and optional maintenance

The [five-check table](../README.md#tf-linting--ci) maps each local command to its
coverage and actual job name. `example-checks (terraform)` and `example-checks
(tofu)` validate both modules and run all fixtures; `random-pet (terraform)` and
`random-pet (tofu)` retain child-only compatibility coverage. `documentation`
checks both managed READMEs; `full-quality` invokes the complete configured Trunk
pipeline with `--all --ci --no-fix --cache=false`. There are no path filters, so a
shared config/helper change cannot skip unchanged modules or scanner targets.
These repository-local jobs use the ordinary PR checkout or a push to `main`,
pinned actions, read-only contents access, no persisted checkout credentials and
no inherited secrets. Network access is needed for tool/provider/scanner downloads.

The shared PR-only Lint workflow is preserved, including its title check and
`actions: read`, `checks: write`, `contents: read`, `pull-requests: read` grants.
Its reporting path is separate from the read-only core jobs. No PR title exists
on a main-branch push, which runs the repository-local jobs only. Configure branch
protection/rulesets separately if these checks must block merges; this repository
does not establish which checks maintainers currently require.

For an adopter-owned copy, enable Actions and allow the pinned checkout/Aqua
installer actions and the existing public reusable workflow. Install Aqua/Python
locally, run the setup above, and keep both engine matrices enabled. Core jobs
require no Masterpoint-only secret. On fork-origin PRs, GitHub/maintainer policy
may require approval to start jobs, and the shared reporting workflow's write
permission may be restricted. The read-only core path avoids that write requirement.
For each adopter, verify a fork-origin PR and an adopter-owned PR/main push on
the same reviewed commit. Check that all six core jobs actually ran successfully;
local tests and permissions inspection do not substitute for hosted runs.

Recommended required checks for these examples are `random-pet (terraform)`,
`random-pet (tofu)`, `example-checks (terraform)`, `example-checks (tofu)`,
`documentation` and `full-quality`. Select the exact status contexts shown by a
successful run in the adopter's ruleset. The inherited Lint/title statuses are
additional policy choices; they have different trigger/reporting requirements.
This recommendation does not claim any existing ruleset has been configured.

The scheduled/dispatch-only `Trunk Upgrade` workflow is optional maintenance. It
uses the shared workflow and `MP_BOT_APP_ID`, `MP_BOT_APP_PRIVATE_KEY` and
`MASTERPOINT_TEAM_PAT`, with contents/PR write permission. An adopter must replace
those with its own correctly scoped automation credentials and verify the shared
workflow contract before enabling it. To defer it, disable **Trunk Upgrade** in
Actions or remove `.github/workflows/trunk-upgrade.yaml` in the adopter's copy.
No such credentials are needed for the core checks. Renovate proposals separately
require installing/configuring the Renovate app for the adopter's repository;
keeping its config alone does not schedule hosted proposals. Defer the app to
perform the documented updates manually. Neither optional service is a prerequisite
for local format/lint, validation, tests, docs checks or static scans.

Static scanner policy follows the pinned Trunk plugins: Checkov uses SARIF with
`--soft-fail` (Trunk interprets findings); Trivy uses `config`, not filesystem
vulnerability/secret modes; TruffleHog uses filesystem scanning with
`--only-verified --fail --no-update`; Zizmor checks workflow YAML with the pedantic
persona. TruffleHog's enabled filesystem mode does not scan Git history.
The pinned plugins select Checkov for Terraform, CloudFormation, Docker, YAML and
JSON; Trivy config for Docker, YAML and Terraform; TruffleHog for its filesystem
file targets; and Zizmor for GitHub workflow YAML. Trunk applies repository ignore
rules before selecting targets. The explicit Tofu exclusion is `**/backend.tf.json`;
it does not exclude those files from other configured scanners. Checkov's existing `CKV_TF_1` skip remains explicit, and TerraScan remains
disabled for the documented compatibility issue. Inspect configured file targets
and exclusions before generalizing coverage. An artificial scanner event can
verify failure reporting but cannot prove live secret detection. Safe static
fixtures must never be initialized or applied.
