# AWS blueprint template

Use this repository as the starting point for one AWS Blueprint. The template
contains the Stack Repeat manifest and runtime scaffolding, but intentionally
contains no AWS resources or workload-specific implementation.

This is a **one Blueprint per repository** template. The manifest, Terraform
root, API helpers, documentation, and release history all belong to the same
Blueprint. Do not add a directory of multiple Blueprints.

## Get started

1. Select **Use this template** on GitHub and create a repository named for the
   Blueprint, for example `document-service-blueprint`.
2. Replace every `replace-me`, `Replace me`, `OWNER`, and `REPOSITORY` value in
   `stack-repeat-blueprint.json`.
3. Define the Blueprint's public inputs, outputs, dependencies, and catalogue
   visibility in the manifest.
4. Add the corresponding Terraform implementation to `terraform/`.
5. Add API helpers only for lifecycle work that cannot be modeled safely in
   Terraform.
6. Update this README with the Blueprint's purpose, architecture, inputs,
   outputs, dependencies, and operating guidance.
7. Open a pull request. The included GitHub Actions workflow validates the
   single-Blueprint structure and Terraform on a public `ubuntu-latest` runner
   without AWS credentials.

## Repository structure

```text
.
├── stack-repeat-blueprint.json       # The one Blueprint manifest
├── terraform/                        # The one Terraform root
│   ├── versions.tf
│   ├── .terraform.lock.hcl
│   ├── backend.jinja
│   └── stack-repeat-providers.jinja
├── api_helpers/
│   ├── pre-api-helpers.sh
│   ├── post-api-helpers.sh
│   └── python/requirements.txt
├── scripts/validate_blueprint.py
└── .github/workflows/checks.yml
```

The manifest must remain at the repository root and its `infrastructure.root`
must remain `terraform`. The validation script rejects additional
`stack-repeat-blueprint.json` files, Terraform roots outside `terraform/`, or
lifecycle hooks that escape the repository.

The Jinja files are part of the platform runtime contract. The runtime renders
them with the state backend, region, and target-account role. Do not replace
them with hard-coded credentials, account IDs, role ARNs, or backend values.

## Define the manifest

`stack-repeat-blueprint.json` is the contract between the Blueprint, catalogue,
and runtime. Keep it synchronized with the Terraform implementation.

- `blueprint` identifies and documents the Blueprint. Use stable, URL-safe IDs.
- `catalogue` controls discovery and organization access.
- `runtime` declares the compatible adapter versions and capabilities.
- `infrastructure` locates the Terraform root and minimum supported version.
- `lifecycle` declares supported operations and optional hooks.
- `inputs` lists values a release or requester must provide. A matching
  Terraform variable should exist for each Terraform-backed input.
- `outputs` lists values the runtime can report. A matching Terraform output
  should exist for each `terraform_output` entry.
- `artifacts` lists files or directories required at runtime.
- `dependencies` records services, images, network access, baseline resources,
  or other external capabilities the Blueprint needs.

Do not put secret values in input defaults, Terraform variables, helper source,
or documentation. Mark sensitive inputs and outputs in the manifest and pass
their values through the runtime's secret mechanism.

## Add Terraform resources

Add normal `.tf` files directly below `terraform/`, organized by
responsibility. Modules may live below `terraform/modules/`.

```text
terraform/
├── versions.tf
├── variables.tf
├── data.tf
├── network.tf
├── application.tf
├── outputs.tf
└── modules/
```

When adding resources:

- Use stable Terraform addresses and explicit state moves when renaming them.
- Avoid assumptions about account IDs, regions, DNS zones, or organization
  names; obtain them from inputs, data sources, or runtime-provided identity.
- Pin additional providers in `versions.tf`, run `terraform init -upgrade`, and
  commit the updated lock file.
- Make create, update, and destroy behavior agree with the lifecycle flags in
  the manifest.
- Keep inputs and outputs narrow. The manifest is a public interface, not a
  mirror of every internal Terraform value.
- Never commit credentials, Terraform state, plans, populated `.tfvars` files,
  or generated backend/provider files.

## Add API helpers

The pre- and post-Terraform entry points are no-ops by default. Use them only
when an operation cannot be represented safely in Terraform. Keep
`set -euo pipefail`, make every helper idempotent, and use the runtime AWS
identity instead of embedded credentials.

Add Python helpers below `api_helpers/python/` and pin any packages in
`requirements.txt`. If dependencies are installed with hashes in your runtime,
generate and commit a lock file and add it to the manifest's `artifacts` list.

## Test changes

Install Terraform 1.15.9 or a compatible patch release, then run:

```bash
make test
```

The test command:

- proves there is exactly one root Blueprint manifest;
- validates required manifest fields, paths, and identifier formats;
- rejects Terraform files outside the single configured root;
- checks Terraform formatting and initializes without the runtime backend;
- validates Terraform without contacting an AWS account; and
- checks shell helper syntax.

The same checks run for pull requests, pushes to `main`, and manual workflow
dispatches with read-only repository permissions. After creating a repository
from this template, you can make `Blueprint checks / Validate` required in its
branch protection rules.

## License

This template is available under the [Mozilla Public License 2.0](LICENSE).
