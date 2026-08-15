"""Discover Hermes profiles on this host."""

from __future__ import annotations

import shutil
import subprocess

from .config import hermes_bin, hermes_home


def _parse_profile_list(text: str) -> list[str]:
    names: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("profile") and "model" in lower:
            continue
        if set(line.replace(" ", "")) <= {"─", "-", "━", "–"}:
            continue
        cleaned = line.lstrip("◆*• ").strip()
        if not cleaned:
            continue
        name = cleaned.split()[0]
        if name in {"Profile", "──", "—"}:
            continue
        names.append(name)
    # preserve order, drop dupes
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _from_disk() -> list[str]:
    root = hermes_home()
    names = ["default"]
    profiles_dir = root / "profiles"
    if profiles_dir.is_dir():
        for child in sorted(profiles_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                names.append(child.name)
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def list_host_profiles() -> list[str]:
    binary = shutil.which(hermes_bin()) or hermes_bin()
    try:
        proc = subprocess.run(
            [binary, "profile", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _from_disk()
    names = _parse_profile_list(proc.stdout or "")
    if not names:
        return _from_disk()
    return names


def profile_exists(name: str) -> bool:
    return name in list_host_profiles()
