# Attach the application URL to the workload

The public application URL is Terraform output `endpoint`, a non-sensitive
string such as `https://dexample.cloudfront.net`. No secret is included in it.

Terraform writes the non-sensitive URL into the ignored local file
`terraform/.stackrepeat-endpoint` with permissions `0600`. The post hook reads
that file, so it does not need access to the management-account Terraform backend
while running with workload-account AWS credentials. Terraform recreates the
file in each fresh executor workspace and removes it on destroy.

The blueprint post hook verifies `/api/v4/system/ping` over HTTPS. Nginx is enabled
only after the administrator and private demo team have been created, so this
check does not succeed against an uninitialized public signup screen. Destroy
skips the check entirely.

The companion change in [StackRepeat/aws-platform PR #72](https://github.com/StackRepeat/aws-platform/pull/72)
was merged on 15 September 2026 as
`24abaca75858a661ee1658467274e5e86a37f2ab`. It adds this runtime contract:

1. After Terraform apply and a successful blueprint post hook, read
   `terraform output -json` inside the executor.
2. Select only `endpoint`, require a non-sensitive string and an HTTPS URL with
   no embedded credentials, and export it as CodeBuild `WORKLOAD_ENDPOINT`.
3. Read that export from the successful workload build and persist it with the
   workspace state before sending the existing authenticated `ready` callback.
4. Send it as `payload.endpoint`; the control plane already consumes that field.

[AWS runtime v2.3.58](https://github.com/StackRepeat/aws-platform/tree/v2.3.58)
contains this change. Upgrade the installed platform to **v2.3.58 or later** through
the console, updating both the rendered workload executor buildspec and runtime
Lambda image. The control plane discovers published releases from its S3 catalogue
on the next request after its default 30-second cache expires; no control-plane
redeployment is needed. Runtime `v2.3.57` predates the fix and does not include endpoint reporting.
Use blueprint **v0.1.2 or later**: it uses compatible catalogue tags, supports the runtime's Terraform 1.15.8 and
includes the local URL handoff. Blueprint v0.1.0 inherited a newer Terraform
minimum and attempted to read backend state from the workload-role hook.
Older runtimes use an AWS Console fallback for non-Sandbox
workloads; this repository alone cannot change that installed runtime behavior.
The post hook still prints the usable application URL in the deployment log.

The endpoint change does not alter workload policy enforcement. Deploy this
public demo only in a scope whose effective policies permit public ingress.
Secure Foundation v1 is incompatible with the public demo. Catalogue import and
release publication do not grant permission to override that policy.
