#!/usr/bin/env bash
# Spec 36.6 release verification, adapted to this repo.
# Manifest is the spec 5.8 YAML (not the 21.1 JSON example).
# TODO fields are allowed on working-channel seeds; they fail --strict.
#
# Integrity: declared policy/plugins/skills/tree digests MUST match a
# recomputation. Missing fields or any digest mismatch fail the script.
set -euo pipefail

MANIFEST="${1:?manifest path required}"
DIST="${2:?distribution directory required}"
STRICT="${3:-}"

python3 - "$MANIFEST" "$DIST" "$STRICT" <<'PY'
import hashlib
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required\n")
    sys.exit(2)

manifest_path = Path(sys.argv[1]).resolve()
dist = Path(sys.argv[2]).resolve()
strict = sys.argv[3] == "--strict"

failed = 0
checks = 0


def note(msg: str) -> None:
    print(msg)


def record(name: str, ok: bool, detail: str = "") -> None:
    global failed, checks
    checks += 1
    status = "PASS" if ok else "FAIL"
    suffix = f"  {detail}" if detail else ""
    print(f"{status}  {name}{suffix}")
    if not ok:
        failed += 1


if not manifest_path.is_file():
    sys.stderr.write(f"manifest not found: {manifest_path}\n")
    sys.exit(1)
if not dist.is_dir():
    sys.stderr.write(f"distribution directory not found: {dist}\n")
    sys.exit(1)

try:
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
except yaml.YAMLError as exc:
    sys.stderr.write(f"manifest YAML parse failed: {exc}\n")
    sys.exit(1)

if not isinstance(data, dict):
    sys.stderr.write("manifest must be a mapping\n")
    sys.exit(1)

schema_path = dist / "manifests" / "manifest.schema.yaml"
schema = None
if schema_path.is_file():
    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        record("manifest schema YAML parse", False, str(exc))
        schema = None
else:
    record("manifest schema present", False, str(schema_path))

if schema is not None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            detail = "; ".join(
                f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
                for err in errors[:8]
            )
            record("manifest schema validation", False, detail)
        else:
            record("manifest schema validation", True, "jsonschema Draft 2020-12")
    except ImportError:
        required_from_schema = list(schema.get("required") or [])
        missing_from_schema = [k for k in required_from_schema if k not in data]
        extra = []
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties") or {})
            extra = sorted(set(data) - allowed)
        if missing_from_schema or extra:
            bits = []
            if missing_from_schema:
                bits.append("missing " + ", ".join(missing_from_schema))
            if extra:
                bits.append("unknown " + ", ".join(extra))
            record("manifest schema validation", False, "; ".join(bits) + " (jsonschema missing)")
        else:
            record(
                "manifest schema validation",
                True,
                "strict YAML parse + required field presence (jsonschema missing)",
            )

required = [
    "release_id",
    "created_at",
    "distribution_git_sha",
    "platform_git_sha",
    "agency_agents_git_sha",
    "hermes_image_digest",
    "knowledge_image_digest",
    "policy_bundle_sha256",
    "skills_manifest_sha256",
    "plugins_manifest_sha256",
    "distribution_tree_sha256",
    "eval_suite_version",
    "database_schema_revision",
    "approved_by",
]
missing = [k for k in required if k not in data]
record("required fields present", not missing, "missing: " + ", ".join(missing) if missing else "")

if "database_schema_revision" in data:
    record(
        "database_schema_revision is string",
        isinstance(data["database_schema_revision"], str),
        f"got {type(data['database_schema_revision']).__name__}",
    )


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for p in files:
        rel = p.relative_to(root).as_posix().encode()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(p.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def sha256_distribution_tree(root: Path, exclude: set[Path]) -> str:
    """Deterministic tree digest used for distribution_tree_sha256.

    Include every regular file under root, sorted by relative POSIX path,
    except .git/, the release manifest being verified, and recorded
    validation transcripts (tests/VALIDATION-*.txt). Generator and
    verifier MUST use these same path and newline rules (spec 36.6).
    """
    digest = hashlib.sha256()
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if ".git" in rel.parts:
            continue
        if p.resolve() in exclude:
            continue
        if rel.parts[:1] == ("tests",) and rel.name.startswith("VALIDATION-") and rel.suffix == ".txt":
            continue
        files.append(p)
    for p in sorted(files, key=lambda x: x.relative_to(root).as_posix()):
        rel = p.relative_to(root).as_posix().encode()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(p.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def assert_digest(field: str, actual: str | None) -> None:
    declared = data.get(field)
    if declared is None or declared == "":
        record(field, False, "declared value missing")
        return
    declared_s = str(declared)
    if actual is None:
        record(field, False, "source missing; cannot recompute")
        return
    if "TODO" in declared_s:
        record(field, False, "declared value is TODO; expected computed digest")
        return
    if declared_s != actual:
        record(field, False, f"mismatch declared={declared_s} computed={actual}")
        return
    record(field, True, actual)


policy = dist / "policies" / "capabilities.yaml"
plugins = dist / "plugins" / "plugins.yaml"
skills_root = dist / "skills"

assert_digest("policy_bundle_sha256", sha256_path(policy) if policy.is_file() else None)
assert_digest("plugins_manifest_sha256", sha256_path(plugins) if plugins.is_file() else None)
assert_digest("skills_manifest_sha256", sha256_tree(skills_root) if skills_root.is_dir() else None)
assert_digest(
    "distribution_tree_sha256",
    sha256_distribution_tree(dist, {manifest_path}),
)

todo = [k for k, v in data.items() if isinstance(v, str) and "TODO" in v]
if isinstance(data.get("approved_by"), list):
    if any(isinstance(x, str) and "TODO" in x for x in data["approved_by"]):
        todo.append("approved_by")

if strict:
    record("strict: no unresolved TODO fields", not todo, ", ".join(todo) if todo else "")
elif todo:
    note("INFO  unresolved_todo: " + ", ".join(todo))

note(f"checks={checks} failed={failed}")
if failed:
    note("Release verification FAILED")
    sys.exit(1)
note("Release verified (working-channel seed ok)" if todo else "Release verified")
PY
