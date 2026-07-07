import json
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.api.schemas import DocumentMetadata, QueryFilters


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _metadata_key(value: str | None) -> str | None:
    clean_value = _clean_optional_text(value)
    return clean_value.lower() if clean_value else None


def normalize_tags(tags: list[str] | None) -> list[str]:
    clean_tags = []
    seen = set()

    for tag in tags or []:
        normalized = tag.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            clean_tags.append(normalized)
            seen.add(key)

    return clean_tags


def normalize_tag_keys(tags: list[str] | None) -> list[str]:
    return [tag.lower() for tag in normalize_tags(tags)]


def has_user_metadata(metadata: DocumentMetadata | None) -> bool:
    if metadata is None:
        return False

    return bool(
        _clean_optional_text(metadata.department)
        or _clean_optional_text(metadata.category)
        or _clean_optional_text(metadata.author)
        or normalize_tags(metadata.tags)
    )


def merge_document_metadata(
    user_metadata: DocumentMetadata | None,
    suggested_metadata: DocumentMetadata | None,
) -> DocumentMetadata:
    user_metadata = user_metadata or DocumentMetadata()
    suggested_metadata = suggested_metadata or DocumentMetadata()

    return DocumentMetadata(
        department=_clean_optional_text(user_metadata.department) or _clean_optional_text(suggested_metadata.department),
        category=_clean_optional_text(user_metadata.category) or _clean_optional_text(suggested_metadata.category),
        author=_clean_optional_text(user_metadata.author) or _clean_optional_text(suggested_metadata.author),
        tags=normalize_tags(user_metadata.tags) or normalize_tags(suggested_metadata.tags),
    )


def normalize_document_metadata(
    metadata: DocumentMetadata | None,
    source_type: str,
    source_name: str,
    source_info: str = "",
) -> dict[str, Any]:
    metadata = metadata or DocumentMetadata()

    return {
        "department": _clean_optional_text(metadata.department),
        "department_key": _metadata_key(metadata.department),
        "category": _clean_optional_text(metadata.category),
        "category_key": _metadata_key(metadata.category),
        "author": _clean_optional_text(metadata.author),
        "author_key": _metadata_key(metadata.author),
        "tags": normalize_tags(metadata.tags),
        "tags_key": normalize_tag_keys(metadata.tags),
        "source_type": source_type,
        "source_name": source_name,
        "source_info": source_info,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_metadata_json(raw_metadata: str | None) -> DocumentMetadata:
    if not raw_metadata:
        return DocumentMetadata()

    try:
        payload = json.loads(raw_metadata)
    except json.JSONDecodeError as exc:
        raise ValueError("metadata must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("metadata must be a JSON object")

    try:
        return DocumentMetadata(**payload)
    except ValidationError as exc:
        raise ValueError(f"metadata validation failed: {exc}") from exc


def normalize_query_filters(filters: QueryFilters | None) -> dict[str, Any]:
    if filters is None:
        return {}

    normalized = {
        "department": _metadata_key(filters.department),
        "category": _metadata_key(filters.category),
        "author": _metadata_key(filters.author),
        "tags": normalize_tag_keys(filters.tags),
        "source_type": _clean_optional_text(filters.source_type),
    }

    return {
        key: value
        for key, value in normalized.items()
        if value is not None and value != []
    }
