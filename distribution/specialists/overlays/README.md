# Specialist policy overlays

Spec 18.7. Each wrapper in `../manifest.yaml` points at a YAML overlay
in this directory. The overlay is company policy, not a permission
grant. Capability enforcement lives in `policies/capabilities.yaml`
and the approval service.

| Overlay | Status |
|---|---|
| `legal-document-review.yaml` | Format example present |
| All other `policy_overlay` paths in the roster | TODO — write before enabling the specialist (D041) |

Until an overlay file exists, the specialist is **not installable** on
`testing` or `stable`.
