"""Connections package (spec 12.1, 15.4)."""

from packages.connections.models import ConnectionReference, CredentialClass
from packages.connections.reference import OpaqueHandle, contains_credential_value, resolve_reference

__all__ = [
    "ConnectionReference",
    "CredentialClass",
    "OpaqueHandle",
    "contains_credential_value",
    "resolve_reference",
]
