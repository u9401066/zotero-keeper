"""Release version synchronization regression tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_version_sync.py"
SPEC = importlib.util.spec_from_file_location("check_version_sync", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
check_version_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_version_sync)


def test_current_repository_release_versions_are_synchronized() -> None:
    errors, extension_version, keeper_version = check_version_sync.collect_version_errors(REPO_ROOT, {})

    assert errors == []
    assert extension_version
    assert keeper_version


@pytest.mark.parametrize(
    "environment",
    [
        {"GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": "v1.2.3-ext"},
        {"GITHUB_REF_TYPE": "tag", "GITHUB_REF": "refs/tags/v4.5.6"},
    ],
)
def test_release_tag_accepts_matching_product_tag(
    environment: dict[str, str],
) -> None:
    errors: list[str] = []

    check_version_sync.validate_release_tag(environment, "1.2.3", "4.5.6", errors)

    assert errors == []


def test_release_tag_rejects_unrelated_tag() -> None:
    errors: list[str] = []

    check_version_sync.validate_release_tag(
        {"GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": "v9.9.9-ext"},
        "1.2.3",
        "4.5.6",
        errors,
    )

    assert errors == ["TAG MISMATCH: v9.9.9-ext is neither extension tag v1.2.3-ext nor Keeper tag v4.5.6"]
