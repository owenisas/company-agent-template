# company-audit

Spec 20.3. Adds trace context and emits redacted events. Credential
boundary: audit write token only, ideally through a local collector.

Phase 1a is a stub. Do not enable in stable until spec 20.4 review.
Rollback: remove from `plugins.enabled` and this directory.
