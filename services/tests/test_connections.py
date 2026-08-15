"""Connection references never carry secrets (spec 12.1, 15.4)."""

import pytest

from packages.approval.models import ApprovalStatus
from packages.connections.models import ConnectionReference, CredentialClass
from packages.connections.reference import OpaqueHandle, resolve_reference


def _personal_ref() -> ConnectionReference:
    return ConnectionReference(
        id="user:employee-a/github-oauth",
        plugin="github",
        scope="user",
        principal="employee-a",
        credential_ref="secret://user/employee-a/github-oauth",
        credential_class=CredentialClass.PERSONAL,
        allowed_actions=("repository.read", "pull_request.create"),
        forbidden_actions=("repository.delete",),
        approval_policy="none_for_allowed_actions",
        owner="employee-a",
        profile_path="connection-references/github-oauth.yaml",
    )


def test_reference_never_carries_secret_value():
    ref = _personal_ref()
    dumped = ref.model_dump()
    assert "password" not in dumped
    assert "token" not in dumped
    assert "api_key" not in dumped
    assert dumped["credential_ref"].startswith("secret://")
    assert "ghp_" not in str(dumped)
    assert "sk-" not in str(dumped)
    assert ref.secret_value() is None


def test_resolve_returns_opaque_handle_not_credential():
    ref = _personal_ref()
    handle = resolve_reference(ref, action="repository.read")
    assert isinstance(handle, OpaqueHandle)
    dumped = handle.model_dump()
    assert "credential_ref" not in dumped
    assert "secret" not in str(dumped).lower() or "secret://" not in str(dumped)
    assert handle.connection_id == ref.id
    assert handle.handle_id.startswith("href_")
    assert handle.credential_class is CredentialClass.PERSONAL


def test_external_write_resolution_requires_approved_action():
    ref = _personal_ref()
    with pytest.raises(PermissionError, match="approvable"):
        resolve_reference(ref, action="pull_request.create")
    handle = resolve_reference(
        ref,
        action="pull_request.create",
        approval_status=ApprovalStatus.APPROVED,
        approval_id="apr_test",
    )
    assert handle.connection_id == ref.id
