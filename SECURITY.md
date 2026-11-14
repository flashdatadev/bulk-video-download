# Security

Report credential exposure or a security issue privately to support@flashdata.dev.
Do not include credentials or signed URLs in public issues.

Keep real keys in a private Python settings file. `config.py`, `.env` files and runtime
directories are gitignored. The CLI executes the Python config you select, so only
load configuration you trust.

Checkpoints store IDs and input hashes, not API/storage credentials or signed upload
descriptors. Result inventories may contain private object locations and source IDs;
treat them as private project data.
