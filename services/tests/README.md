# How to run the offline Phase 2–3 scaffold suite
#
# No database, no network, no Docker, no credentials.
#
# From the repo root:
#
#   python3 -m pytest tests/ -x -q
#
# Or with a scratch venv (does not install system-wide):
#
#   uv venv /tmp/p3venv
#   VIRTUAL_ENV=/tmp/p3venv uv pip install pytest pydantic fastapi httpx
#   /tmp/p3venv/bin/python -m pytest tests/ -x -q
#
# Required tests:
#   tests/test_authz.py                zero-unauthorized-retrieval matrix
#   tests/test_retrieval_acl.py        ACL prefilter SQL fragment
#   tests/test_citations.py            exact source locators on research packets
#   tests/test_separation.py           raw vs derived provenance
#   tests/test_config.py               spec 13.4 layering
#   tests/test_capabilities.py         registry deny-by-default
#   tests/test_approval.py             fingerprint / two-person / expiry
#   tests/test_connections.py          reference never carries a secret
#   tests/test_attribution.py          spec 30.2 consistency
#   tests/test_preview_apply.py        preview → approval → apply
#   tests/test_no_secrets_in_context.py shared credential never in context
#   tests/test_readonly_mcps.py        GitHub/CRM MCP stubs
#   tests/test_connectors.py           Notion + future-connector registry
#
# Recorded results: tests/PHASE-2-SCAFFOLD-TESTS.txt
#                   tests/PHASE-3-SCAFFOLD-TESTS.txt
