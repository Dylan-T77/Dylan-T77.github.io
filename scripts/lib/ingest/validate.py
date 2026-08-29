"""Validate normalized information records."""

from __future__ import annotations

REQUIRED = (
    "id",
    "title",
    "canonical_url",
    "original_url",
    "source",
    "source_id",
    "source_type",
    "editorial_state",
    "publish",
    "ingested_at",
)


def validate_item(item: dict) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED:
        if key not in item:
            issues.append(f"missing {key}")
    if item.get("publish") is True:
        issues.append("publish must remain false for inbox records")
    if item.get("editorial_state") != "INBOX":
        issues.append("editorial_state must be INBOX")
    if not item.get("title"):
        issues.append("empty title")
    if not item.get("canonical_url"):
        issues.append("empty canonical_url")
    return issues


def validate_items(items: list[dict]) -> tuple[list[dict], list[str]]:
    valid: list[dict] = []
    errors: list[str] = []
    for item in items:
        issues = validate_item(item)
        if issues:
            errors.append(f"{item.get('id', '?')}: {', '.join(issues)}")
            continue
        valid.append(item)
    return valid, errors
