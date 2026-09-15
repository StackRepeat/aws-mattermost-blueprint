#!/usr/bin/env python3
"""Validate the repository's single-Blueprint layout and core manifest contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "stack-repeat-blueprint.json"
BLUEPRINT_ID = re.compile(r"^blueprint:[a-z0-9][a-z0-9-]*$")
ORGANISATION_ID = re.compile(r"^organisation:[a-z0-9][a-z0-9-]*$")


class ValidationError(ValueError):
    """Raised when the Blueprint repository contract is invalid."""


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a JSON object")
    return value


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be a JSON array")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value


def require_keys(value: dict[str, Any], name: str, keys: set[str]) -> None:
    missing = sorted(keys - value.keys())
    if missing:
        raise ValidationError(f"{name} is missing: {', '.join(missing)}")


def repository_path(value: Any, name: str) -> Path:
    relative = Path(require_string(value, name))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError(f"{name} must stay within the repository")

    resolved = (ROOT / relative).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise ValidationError(f"{name} must stay within the repository")
    if not resolved.exists():
        raise ValidationError(f"{name} does not exist: {relative}")
    return resolved


def validate_named_items(items: Any, name: str) -> None:
    values = require_list(items, name)
    seen: set[str] = set()
    for index, item_value in enumerate(values):
        item = require_object(item_value, f"{name}[{index}]")
        item_name = require_string(item.get("name"), f"{name}[{index}].name")
        if item_name in seen:
            raise ValidationError(f"{name} contains duplicate name: {item_name}")
        seen.add(item_name)


def validate() -> None:
    manifests = sorted(ROOT.rglob("stack-repeat-blueprint.json"))
    if manifests != [MANIFEST_PATH]:
        locations = ", ".join(str(path.relative_to(ROOT)) for path in manifests)
        raise ValidationError(
            "exactly one stack-repeat-blueprint.json must exist at the repository "
            f"root; found: {locations or 'none'}"
        )

    try:
        manifest = require_object(
            json.loads(MANIFEST_PATH.read_text(encoding="utf-8")), "manifest"
        )
    except json.JSONDecodeError as error:
        raise ValidationError(f"invalid JSON: {error}") from error

    require_keys(
        manifest,
        "manifest",
        {
            "manifest_version",
            "blueprint",
            "catalogue",
            "runtime",
            "infrastructure",
            "lifecycle",
            "inputs",
            "outputs",
            "artifacts",
            "dependencies",
        },
    )
    require_string(manifest["manifest_version"], "manifest_version")

    blueprint = require_object(manifest["blueprint"], "blueprint")
    require_keys(
        blueprint,
        "blueprint",
        {
            "contract_version",
            "blueprint_id",
            "name",
            "owner_organisation_id",
            "summary",
            "description",
            "tags",
            "documentation_url",
        },
    )
    blueprint_id = require_string(blueprint["blueprint_id"], "blueprint.blueprint_id")
    if not BLUEPRINT_ID.fullmatch(blueprint_id):
        raise ValidationError("blueprint.blueprint_id must match blueprint:<kebab-case-id>")
    organisation_id = require_string(
        blueprint["owner_organisation_id"], "blueprint.owner_organisation_id"
    )
    if not ORGANISATION_ID.fullmatch(organisation_id):
        raise ValidationError(
            "blueprint.owner_organisation_id must match organisation:<kebab-case-id>"
        )
    for field in ("contract_version", "name", "summary", "description", "documentation_url"):
        require_string(blueprint[field], f"blueprint.{field}")
    require_list(blueprint["tags"], "blueprint.tags")

    catalogue = require_object(manifest["catalogue"], "catalogue")
    require_string(catalogue.get("visibility"), "catalogue.visibility")
    require_list(
        catalogue.get("allowed_organisation_ids"),
        "catalogue.allowed_organisation_ids",
    )

    runtime = require_object(manifest["runtime"], "runtime")
    for field in ("adapter", "version_constraint"):
        require_string(runtime.get(field), f"runtime.{field}")
    require_list(runtime.get("required_capabilities"), "runtime.required_capabilities")

    infrastructure = require_object(manifest["infrastructure"], "infrastructure")
    if infrastructure.get("engine") != "terraform":
        raise ValidationError("infrastructure.engine must be terraform")
    if infrastructure.get("root") != "terraform":
        raise ValidationError("infrastructure.root must be terraform")
    require_string(
        infrastructure.get("minimum_version"), "infrastructure.minimum_version"
    )
    terraform_root = repository_path(infrastructure["root"], "infrastructure.root")

    lifecycle = require_object(manifest["lifecycle"], "lifecycle")
    for field in ("create_supported", "update_supported", "destroy_supported"):
        if not isinstance(lifecycle.get(field), bool):
            raise ValidationError(f"lifecycle.{field} must be a boolean")
    for field in ("pre_hook", "post_hook"):
        repository_path(lifecycle.get(field), f"lifecycle.{field}")

    for section in ("inputs", "outputs", "dependencies"):
        validate_named_items(manifest[section], section)

    artifacts = require_list(manifest["artifacts"], "artifacts")
    validate_named_items(artifacts, "artifacts")
    for index, artifact_value in enumerate(artifacts):
        artifact = require_object(artifact_value, f"artifacts[{index}]")
        repository_path(artifact.get("path"), f"artifacts[{index}].path")

    terraform_files = sorted(ROOT.rglob("*.tf"))
    outside_root = [path for path in terraform_files if terraform_root not in path.parents]
    if outside_root:
        locations = ", ".join(str(path.relative_to(ROOT)) for path in outside_root)
        raise ValidationError(f"Terraform files must stay in terraform/: {locations}")
    if not (terraform_root / "versions.tf").is_file():
        raise ValidationError("terraform/versions.tf is required")


def main() -> int:
    try:
        validate()
    except (OSError, ValidationError) as error:
        print(f"Blueprint validation failed: {error}", file=sys.stderr)
        return 1
    print("Blueprint structure is valid (one manifest, one Terraform root).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
