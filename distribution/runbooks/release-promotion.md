# Runbook: release promotion

Spec 16.7, 21, 5.8. Skill `release-promotion`.

Working -> testing -> stable:

1. Feature branch into `testing`.
2. Run `tests/run_validation.sh` and `scripts/verify-release.sh`.
3. Human acceptance on testing.
4. Protected PR into `main` (stable branch). Two reviewers for policy/plugin
   changes (D017).
5. Create a signed tag only after Section 35 acceptance tests pass.
6. Record SHAs and digests in `manifests/`. `distribution_git_sha` after push.
7. Users update only when a release owner announces the SHA
   (`hermes profile update`, spec 17.6). Phase 1a does not install profiles.

Rollback: previous release manifest and its pinned artifacts (spec 21.4).
