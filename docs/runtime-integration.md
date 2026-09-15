# Attach the application URL to the workload

The public application URL is Terraform output `endpoint`, a non-sensitive
string such as `https://dexample.cloudfront.net`. No secret is included in it.

The blueprint post hook verifies `/api/v4/system/ping` over HTTPS. Nginx is enabled
only after the administrator and private demo team have been created, so this
check does not succeed against an uninitialized public signup screen. Destroy
skips the check entirely.

The companion change in [StackRepeat/aws-platform PR #72](https://github.com/StackRepeat/aws-platform/pull/72)
adds this runtime contract:

1. After Terraform apply and a successful blueprint post hook, read
   `terraform output -json` inside the executor.
2. Select only `endpoint`, require a non-sensitive string and an HTTPS URL with
   no embedded credentials, and export it as CodeBuild `WORKLOAD_ENDPOINT`.
3. Read that export from the successful workload build and persist it with the
   workspace state before sending the existing authenticated `ready` callback.
4. Send it as `payload.endpoint`; the control plane already consumes that field.

This requires upgrading both the rendered workload executor buildspec and the
runtime Lambda image. Older runtimes use an AWS Console fallback for non-Sandbox
workloads; this repository alone cannot change that installed runtime behavior.
The post hook still prints the usable application URL in the deployment log.

The endpoint change does not alter workload policy enforcement. Deploy this
public demo only in a scope whose effective policies permit public ingress.
Secure Foundation v1 is incompatible with the public demo. Catalogue import and
release publication do not grant permission to override that policy.
