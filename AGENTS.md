# Maintenance

- Keep the implementation Python-only and use the official `flashdata` SDK.
- Show placeholder API keys directly in Python as the primary setup method.
- API input is a UTF-8 text file of 11-character video IDs, one per line. URL/CSV imports must normalize locally before submission; never upload URLs to the API.
- Persist accepted job IDs before uploading or starting work. Never automatically repeat creation.
- Do not store API keys, storage credentials or signed upload URLs in run checkpoints.
- Preserve completed exports; interrupted exports must not publish partial retry lists.
- Tests and the default demo are offline. The separate `live-demo` command requires explicit live-run authorization and real credentials; never submit billable requests for routine verification.
- Run pytest, Ruff lint/format checks, package build and the offline demo before publishing code.
