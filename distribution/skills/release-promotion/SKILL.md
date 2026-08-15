---
name: release-promotion
description: Promote a distribution commit working to testing to stable.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Release Promotion

Domain: release. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use when a reviewed commit is ready to change channel. Does not push tags itself unless approved.

## Procedure

1. Run scripts/verify-release.sh against the candidate manifest.
2. Confirm two reviewers for stable policy/plugin changes (D017).
3. Promote only by PR into testing, then main, then a signed tag (spec 16.7).
4. Record SHAs in the release manifest. Do not use floating latest tags.

## Safety

- Users do not self-update stable (spec 17.6).
- Rollback is the previous manifest, not a hotfix on main.
