# SEC-008 — CI least privilege and no long-lived cloud key

Workflow review and CI run #31 confirm:

- Default workflow permission is `contents: read`.
- Only `release-images` receives `id-token: write`, in addition to
  `contents: read`.
- That job runs only for `push` to `refs/heads/main`; pull requests do not
  receive cloud credentials or push images.
- Google authentication uses GitHub OIDC with repository variables for the
  Workload Identity Provider and writer service account. No service-account
  key is stored in the workflow.
- Workflow configuration contains no command that writes a credential, webhook
  or private key to its job summary; the published release output is limited to
  immutable image digests.

Run: <https://github.com/ngochai2909/kuberag-platform/actions/runs/30798179207>
